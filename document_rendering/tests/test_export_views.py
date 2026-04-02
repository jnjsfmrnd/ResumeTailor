"""Tests for the export download views (D2)."""

import uuid

from django.test import Client, TestCase, override_settings
from django.urls import reverse

from resume_sessions.models import CoverLetterDraft, ResumeSection, ResumeSession


@override_settings(
    DATABASES={
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }
)
class ExportResumeViewTests(TestCase):
    """GET /sessions/<id>/export/resume/ — serves tailored-resume.pdf."""

    def _make_session(self, mode=ResumeSession.GenerationMode.RESUME_ONLY):
        return ResumeSession.objects.create(
            source_pdf_path="",
            job_description="Build great things.",
            generation_mode=mode,
        )

    def _make_section(self, session):
        return ResumeSection.objects.create(
            session=session,
            section_key="summary",
            order_index=0,
            page_number=1,
            bbox_x0=50.0,
            bbox_y0=700.0,
            bbox_x1=550.0,
            bbox_y1=750.0,
            original_content="Original.",
            tailored_content="Tailored.",
        )

    def setUp(self):
        self.client = Client()

    def test_returns_pdf_response(self):
        session = self._make_session()
        self._make_section(session)
        url = reverse("document_rendering:export-resume", kwargs={"session_id": session.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")

    def test_filename_is_tailored_resume_pdf(self):
        session = self._make_session()
        self._make_section(session)
        url = reverse("document_rendering:export-resume", kwargs={"session_id": session.pk})
        response = self.client.get(url)
        self.assertIn("tailored-resume.pdf", response["Content-Disposition"])

    def test_session_status_set_to_complete(self):
        session = self._make_session()
        self._make_section(session)
        url = reverse("document_rendering:export-resume", kwargs={"session_id": session.pk})
        self.client.get(url)
        session.refresh_from_db()
        self.assertEqual(session.status, ResumeSession.Status.COMPLETE)

    def test_pdf_content_is_valid(self):
        session = self._make_session()
        self._make_section(session)
        url = reverse("document_rendering:export-resume", kwargs={"session_id": session.pk})
        response = self.client.get(url)
        self.assertTrue(response.content.startswith(b"%PDF"))

    def test_404_for_nonexistent_session(self):
        url = reverse(
            "document_rendering:export-resume",
            kwargs={"session_id": uuid.uuid4()},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_method_not_allowed(self):
        session = self._make_session()
        url = reverse("document_rendering:export-resume", kwargs={"session_id": session.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 405)


@override_settings(
    DATABASES={
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }
)
class ExportCoverLetterViewTests(TestCase):
    """GET /sessions/<id>/export/cover-letter/ — serves cover-letter.pdf."""

    def _make_session_with_draft(self):
        session = ResumeSession.objects.create(
            source_pdf_path="",
            job_description="Build great things.",
            generation_mode=ResumeSession.GenerationMode.RESUME_AND_COVER_LETTER,
        )
        CoverLetterDraft.objects.create(
            session=session,
            original_grounding_summary="Summary.",
            tailored_content="Dear Hiring Manager,",
        )
        return session

    def setUp(self):
        self.client = Client()

    def test_returns_pdf_response(self):
        session = self._make_session_with_draft()
        url = reverse(
            "document_rendering:export-cover-letter",
            kwargs={"session_id": session.pk},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")

    def test_filename_is_cover_letter_pdf(self):
        session = self._make_session_with_draft()
        url = reverse(
            "document_rendering:export-cover-letter",
            kwargs={"session_id": session.pk},
        )
        response = self.client.get(url)
        self.assertIn("cover-letter.pdf", response["Content-Disposition"])

    def test_pdf_content_is_valid(self):
        session = self._make_session_with_draft()
        url = reverse(
            "document_rendering:export-cover-letter",
            kwargs={"session_id": session.pk},
        )
        response = self.client.get(url)
        self.assertTrue(response.content.startswith(b"%PDF"))

    def test_404_for_resume_only_session(self):
        """Contract: cover-letter.pdf must not be served for resume_only sessions."""
        session = ResumeSession.objects.create(
            source_pdf_path="",
            job_description="x",
            generation_mode=ResumeSession.GenerationMode.RESUME_ONLY,
        )
        url = reverse(
            "document_rendering:export-cover-letter",
            kwargs={"session_id": session.pk},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_404_for_nonexistent_session(self):
        url = reverse(
            "document_rendering:export-cover-letter",
            kwargs={"session_id": uuid.uuid4()},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_404_when_draft_missing(self):
        """Session is dual-mode but draft was never created."""
        session = ResumeSession.objects.create(
            source_pdf_path="",
            job_description="x",
            generation_mode=ResumeSession.GenerationMode.RESUME_AND_COVER_LETTER,
        )
        url = reverse(
            "document_rendering:export-cover-letter",
            kwargs={"session_id": session.pk},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_method_not_allowed(self):
        session = self._make_session_with_draft()
        url = reverse(
            "document_rendering:export-cover-letter",
            kwargs={"session_id": session.pk},
        )
        response = self.client.post(url)
        self.assertEqual(response.status_code, 405)
