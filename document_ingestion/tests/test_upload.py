"""Tests for the document ingestion lane — upload entry flow and session bootstrap.

Stories covered:
  - Engineer A Story A1: Upload Entry Flow
  - Engineer A Story A2: Session Bootstrap

Acceptance criteria verified:
  - Supported digital PDF → session created and returned.
  - Image-only PDF → 422 rejection with clear message.
  - Missing required fields → 400 with per-field errors.
  - Invalid credential_mode or generation_mode or selected_model → 400.
  - File too large → 400.
  - Non-PDF file → 400.
  - generation_mode=resume_and_cover_letter → output_artifact_type=dual_pdf.
  - generation_mode=resume_only → output_artifact_type=single_pdf.
  - Session transitions pending → ingesting after successful upload.
  - user_key is never persisted to the session.
  - session_id and status returned in 201 response.
"""

import io
import tempfile
from unittest.mock import MagicMock, patch

import fitz  # PyMuPDF
from django.test import TestCase, override_settings

from resume_sessions.models import ResumeSession

_UPLOAD_URL = "/upload/"
_CURATED_MODELS = ["gpt-5.1", "claude-sonnet-4", "o3", "gpt-4.1", "llama-4-maverick"]


# ── PDF fixture helpers ───────────────────────────────────────────────────────


def _make_text_pdf(text: str = "John Smith\nSoftware Engineer") -> bytes:
    """Return bytes of a minimal valid PDF containing selectable text."""
    with fitz.open() as doc:
        page = doc.new_page()
        page.insert_text((72, 72), text)
        return doc.tobytes()


def _make_image_only_pdf() -> bytes:
    """Return bytes of a minimal PDF with no selectable text (simulates a scan)."""
    with fitz.open() as doc:
        doc.new_page()  # blank page — no text, no images
        return doc.tobytes()


def _valid_post_data(**overrides):
    """Return a dict of valid POST field values, optionally overriding keys."""
    data = {
        "job_description": "Build backend services in Python.",
        "credential_mode": "app_key",
        "selected_model": "gpt-5.1",
        "generation_mode": "resume_only",
    }
    data.update(overrides)
    return data


# ── helpers ───────────────────────────────────────────────────────────────────


def _post_upload(client, pdf_bytes: bytes, filename: str = "resume.pdf", **field_overrides):
    """POST to /upload/ with the given PDF bytes and form fields."""
    data = _valid_post_data(**field_overrides)
    data["pdf_file"] = io.BytesIO(pdf_bytes)
    data["pdf_file"].name = filename
    return client.post(_UPLOAD_URL, data, format="multipart")


# ── test cases ────────────────────────────────────────────────────────────────


@override_settings(
    RESUME_TAILOR_CURATED_MODELS=_CURATED_MODELS,
    RESUME_TAILOR_DEFAULT_MODEL="gpt-5.1",
)
class UploadViewTests(TestCase):
    """Tests for POST /upload/ (Story A1 + A2)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Use a TemporaryDirectory for MEDIA_ROOT so it is cleaned up after tests.
        cls._temp_media_dir = tempfile.TemporaryDirectory()
        cls._media_override = override_settings(MEDIA_ROOT=cls._temp_media_dir.name)
        cls._media_override.enable()

    @classmethod
    def tearDownClass(cls):
        # Disable MEDIA_ROOT override and clean up the temporary directory.
        cls._media_override.disable()
        cls._temp_media_dir.cleanup()
        super().tearDownClass()

    def setUp(self):
        # Mock the Celery task dispatch so tests don't need a running Redis broker.
        ingest_patcher = patch("document_ingestion.tasks.ingest_resume_task.delay")
        self.mock_ingest_task_delay = ingest_patcher.start()
        self.addCleanup(ingest_patcher.stop)

        # Mock ingest_resume and GenerationService for the user_key synchronous
        # path so tests don't require a PDF on disk or a live GitHub Models endpoint.
        ingest_sync_patcher = patch("document_ingestion.views.ingest_resume")
        self.mock_ingest_resume = ingest_sync_patcher.start()
        self.mock_ingest_resume.return_value = []  # no sections
        self.addCleanup(ingest_sync_patcher.stop)

        gen_service_patcher = patch("generation.service.GenerationService")
        self.mock_gen_service_cls = gen_service_patcher.start()
        self.mock_gen_service_cls.return_value.run.return_value = MagicMock()
        self.addCleanup(gen_service_patcher.stop)

    # ── A1: happy-path upload ─────────────────────────────────────────────────

    def test_valid_pdf_returns_201_with_session(self):
        """A supported digital PDF produces a session and 201 response."""
        pdf = _make_text_pdf()
        resp = _post_upload(self.client, pdf)
        self.assertEqual(resp.status_code, 201)
        body = resp.json()
        self.assertIn("session_id", body)
        self.assertEqual(body["status"], "ingesting")

    def test_session_exists_in_db(self):
        """The created session is persisted to the database."""
        pdf = _make_text_pdf()
        resp = _post_upload(self.client, pdf)
        session_id = resp.json()["session_id"]
        self.assertTrue(ResumeSession.objects.filter(id=session_id).exists())

    # ── A2: session bootstrap ─────────────────────────────────────────────────

    def test_session_status_is_ingesting(self):
        """Session transitions to `ingesting` immediately after upload."""
        pdf = _make_text_pdf()
        resp = _post_upload(self.client, pdf)
        session = ResumeSession.objects.get(id=resp.json()["session_id"])
        self.assertEqual(session.status, ResumeSession.Status.INGESTING)

    def test_session_fields_match_form_input(self):
        """Session fields reflect the submitted form values."""
        pdf = _make_text_pdf()
        resp = _post_upload(
            self.client,
            pdf,
            job_description="Design distributed systems.",
            credential_mode="user_key",
            user_key="ghs_testkey123",
            selected_model="o3",
            generation_mode="resume_and_cover_letter",
        )
        session = ResumeSession.objects.get(id=resp.json()["session_id"])
        self.assertEqual(session.job_description, "Design distributed systems.")
        self.assertEqual(session.credential_mode, "user_key")
        self.assertEqual(session.selected_model, "o3")
        self.assertEqual(session.generation_mode, "resume_and_cover_letter")

    def test_source_pdf_path_is_set(self):
        """source_pdf_path is populated after upload."""
        pdf = _make_text_pdf()
        resp = _post_upload(self.client, pdf)
        session = ResumeSession.objects.get(id=resp.json()["session_id"])
        self.assertTrue(session.source_pdf_path)

    # ── output_artifact_type derivation ──────────────────────────────────────

    def test_resume_only_yields_single_pdf_artifact_type(self):
        pdf = _make_text_pdf()
        resp = _post_upload(self.client, pdf, generation_mode="resume_only")
        session = ResumeSession.objects.get(id=resp.json()["session_id"])
        self.assertEqual(
            session.output_artifact_type, ResumeSession.OutputArtifactType.SINGLE_PDF
        )

    def test_resume_and_cover_letter_yields_dual_pdf_artifact_type(self):
        pdf = _make_text_pdf()
        resp = _post_upload(
            self.client, pdf, generation_mode="resume_and_cover_letter"
        )
        session = ResumeSession.objects.get(id=resp.json()["session_id"])
        self.assertEqual(
            session.output_artifact_type, ResumeSession.OutputArtifactType.DUAL_PDF
        )

    # ── user_key is never persisted ───────────────────────────────────────────

    def test_user_key_is_not_stored_on_session(self):
        """user_key submitted in the form is never written to the database."""
        pdf = _make_text_pdf()
        data = _valid_post_data(credential_mode="user_key")
        data["pdf_file"] = io.BytesIO(pdf)
        data["pdf_file"].name = "resume.pdf"
        data["user_key"] = "ghs_supersecretkey123"
        resp = self.client.post(_UPLOAD_URL, data, format="multipart")
        self.assertEqual(resp.status_code, 201)
        session = ResumeSession.objects.get(id=resp.json()["session_id"])
        # ResumeSession has no user_key field — verify it was not added
        self.assertFalse(hasattr(session, "user_key"))

    # ── A1: image-only PDF rejection ─────────────────────────────────────────

    def test_image_only_pdf_returns_422(self):
        """A PDF with no selectable text is rejected with HTTP 422."""
        pdf = _make_image_only_pdf()
        resp = _post_upload(self.client, pdf)
        self.assertEqual(resp.status_code, 422)

    def test_image_only_pdf_error_message_is_clear(self):
        """The 422 error contains a user-readable explanation."""
        pdf = _make_image_only_pdf()
        resp = _post_upload(self.client, pdf)
        body = resp.json()
        self.assertIn("errors", body)
        self.assertIn("pdf_file", body["errors"])
        msg = body["errors"]["pdf_file"]
        self.assertIn("image-only", msg.lower())

    def test_image_only_pdf_does_not_create_session(self):
        """No session is created when the PDF is rejected."""
        before = ResumeSession.objects.count()
        pdf = _make_image_only_pdf()
        _post_upload(self.client, pdf)
        self.assertEqual(ResumeSession.objects.count(), before)

    # ── validation: missing fields ────────────────────────────────────────────

    def test_missing_pdf_file_returns_400(self):
        data = _valid_post_data()
        resp = self.client.post(_UPLOAD_URL, data, format="multipart")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("pdf_file", resp.json()["errors"])

    def test_missing_job_description_returns_400(self):
        pdf = _make_text_pdf()
        resp = _post_upload(self.client, pdf, job_description="")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("job_description", resp.json()["errors"])

    # ── validation: invalid field values ─────────────────────────────────────

    def test_invalid_credential_mode_returns_400(self):
        pdf = _make_text_pdf()
        resp = _post_upload(self.client, pdf, credential_mode="invalid")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("credential_mode", resp.json()["errors"])

    def test_invalid_selected_model_returns_400(self):
        pdf = _make_text_pdf()
        resp = _post_upload(self.client, pdf, selected_model="gpt-99-turbo")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("selected_model", resp.json()["errors"])

    def test_invalid_generation_mode_returns_400(self):
        pdf = _make_text_pdf()
        resp = _post_upload(self.client, pdf, generation_mode="all_docs")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("generation_mode", resp.json()["errors"])

    def test_non_pdf_file_returns_400(self):
        data = _valid_post_data()
        data["pdf_file"] = io.BytesIO(b"not a pdf at all")
        data["pdf_file"].name = "resume.docx"
        resp = self.client.post(_UPLOAD_URL, data, format="multipart")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("pdf_file", resp.json()["errors"])

    def test_oversized_pdf_returns_400(self):
        """A file exceeding 20 MB is rejected before any PDF parsing."""
        oversized = b"%PDF-1.4\n" + b"x" * (20 * 1024 * 1024 + 1)
        data = _valid_post_data()
        data["pdf_file"] = io.BytesIO(oversized)
        data["pdf_file"].name = "big.pdf"
        resp = self.client.post(_UPLOAD_URL, data, format="multipart")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("pdf_file", resp.json()["errors"])

    # ── all curated models are accepted ──────────────────────────────────────

    def test_all_curated_models_are_accepted(self):
        """Every model in the curated shortlist is a valid selection."""
        for model in _CURATED_MODELS:
            pdf = _make_text_pdf()
            resp = _post_upload(self.client, pdf, selected_model=model)
            self.assertEqual(
                resp.status_code,
                201,
                msg=f"Model '{model}' was unexpectedly rejected.",
            )

    # ── multiple uploads produce independent sessions ─────────────────────────

    def test_two_uploads_produce_different_sessions(self):
        pdf = _make_text_pdf()
        r1 = _post_upload(self.client, pdf)
        r2 = _post_upload(self.client, pdf)
        self.assertNotEqual(r1.json()["session_id"], r2.json()["session_id"])

    # ── dispatch: ingest task dispatched for app_key ──────────────────────────

    def test_app_key_upload_dispatches_ingest_task(self):
        """A successful app_key upload dispatches ingest_resume_task."""
        pdf = _make_text_pdf()
        resp = _post_upload(self.client, pdf, credential_mode="app_key")
        self.assertEqual(resp.status_code, 201)
        session_id = resp.json()["session_id"]
        self.mock_ingest_task_delay.assert_called_once_with(session_id)

    def test_user_key_upload_does_not_dispatch_ingest_task(self):
        """A user_key upload runs synchronously and never dispatches the ingest task."""
        pdf = _make_text_pdf()
        resp = _post_upload(self.client, pdf, credential_mode="user_key", user_key="ghs_testkey456")
        self.assertEqual(resp.status_code, 201)
        self.mock_ingest_task_delay.assert_not_called()

    def test_missing_user_key_for_user_key_mode_returns_400(self):
        """Submitting credential_mode=user_key without a user_key returns 400."""
        pdf = _make_text_pdf()
        resp = _post_upload(self.client, pdf, credential_mode="user_key")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("user_key", resp.json()["errors"])
