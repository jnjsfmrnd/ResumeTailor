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

import fitz  # PyMuPDF
from django.test import TestCase, override_settings
from django.urls import reverse

from resume_sessions.models import ResumeSession

_UPLOAD_URL = "/upload/"
_CURATED_MODELS = ["gpt-5.1", "claude-sonnet-4", "o3", "gpt-4.1", "llama-4-maverick"]


# ── PDF fixture helpers ───────────────────────────────────────────────────────


def _make_text_pdf(text: str = "John Smith\nSoftware Engineer") -> bytes:
    """Return bytes of a minimal valid PDF containing selectable text."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    return doc.tobytes()


def _make_image_only_pdf() -> bytes:
    """Return bytes of a minimal PDF with no selectable text (simulates a scan)."""
    doc = fitz.open()
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


def _pdf_upload_file(content: bytes, filename: str = "resume.pdf"):
    return io.BytesIO(content), filename


# ── helpers ───────────────────────────────────────────────────────────────────


def _post_upload(client, pdf_bytes: bytes, filename: str = "resume.pdf", **field_overrides):
    """POST to /upload/ with the given PDF bytes and form fields."""
    data = _valid_post_data(**field_overrides)
    data["pdf_file"] = io.BytesIO(pdf_bytes)
    data["pdf_file"].name = filename
    return client.post(_UPLOAD_URL, data, format="multipart")


# ── test cases ────────────────────────────────────────────────────────────────


@override_settings(
    MEDIA_ROOT=tempfile.mkdtemp(),
    RESUME_TAILOR_CURATED_MODELS=_CURATED_MODELS,
    RESUME_TAILOR_DEFAULT_MODEL="gpt-5.1",
)
class UploadViewTests(TestCase):
    """Tests for POST /upload/ (Story A1 + A2)."""

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
