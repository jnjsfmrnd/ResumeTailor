"""Tests for the ExportService (D2)."""

from django.test import TestCase, override_settings

from document_rendering.services import ExportError, ExportService
from resume_sessions.models import CoverLetterDraft, ResumeSection, ResumeSession


@override_settings(
    DATABASES={
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }
)
class BuildResumePdfTests(TestCase):
    """ExportService.build_resume_pdf() — plain PDF path (no source file)."""

    def _make_session(self):
        return ResumeSession.objects.create(
            source_pdf_path="",
            job_description="Build great things.",
        )

    def _make_section(self, session, key="summary", order=0, tailored="Tailored."):
        return ResumeSection.objects.create(
            session=session,
            section_key=key,
            order_index=order,
            page_number=1,
            bbox_x0=50.0,
            bbox_y0=700.0,
            bbox_x1=550.0,
            bbox_y1=750.0,
            original_content="Original.",
            tailored_content=tailored,
        )

    def test_returns_pdf_bytes(self):
        session = self._make_session()
        sections = [self._make_section(session)]
        service = ExportService()
        result = service.build_resume_pdf(session, sections)
        self.assertIsInstance(result, bytes)
        # PDF files start with %PDF
        self.assertTrue(result.startswith(b"%PDF"))

    def test_pdf_with_multiple_sections(self):
        session = self._make_session()
        sections = [
            self._make_section(session, key="summary", order=0, tailored="Summary text."),
            self._make_section(session, key="experience", order=1, tailored="Experience text."),
            self._make_section(session, key="education", order=2, tailored="Education text."),
        ]
        service = ExportService()
        result = service.build_resume_pdf(session, sections)
        self.assertTrue(result.startswith(b"%PDF"))

    def test_uses_user_edited_content_when_present(self):
        """resolved_content precedence: user_edited > tailored > original."""
        session = self._make_session()
        section = self._make_section(session, tailored="Tailored.")
        section.user_edited_content = "User edited."
        section.save()
        self.assertEqual(section.resolved_content, "User edited.")

    def test_falls_back_to_original_when_no_tailored(self):
        session = self._make_session()
        section = self._make_section(session, tailored="")
        self.assertEqual(section.resolved_content, "Original.")

    def test_empty_sections_returns_valid_pdf(self):
        session = self._make_session()
        service = ExportService()
        result = service.build_resume_pdf(session, [])
        self.assertTrue(result.startswith(b"%PDF"))


@override_settings(
    DATABASES={
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }
)
class BuildCoverLetterPdfTests(TestCase):
    """ExportService.build_cover_letter_pdf() — generates cover letter PDF."""

    def _make_draft(self, content="Dear Hiring Manager, I am a great fit."):
        session = ResumeSession.objects.create(
            source_pdf_path="",
            job_description="x",
            generation_mode=ResumeSession.GenerationMode.RESUME_AND_COVER_LETTER,
        )
        return CoverLetterDraft.objects.create(
            session=session,
            original_grounding_summary="Summary.",
            tailored_content=content,
        )

    def test_returns_pdf_bytes(self):
        draft = self._make_draft()
        service = ExportService()
        result = service.build_cover_letter_pdf(draft)
        self.assertIsInstance(result, bytes)
        self.assertTrue(result.startswith(b"%PDF"))

    def test_uses_user_edited_content(self):
        draft = self._make_draft()
        draft.user_edited_content = "Custom cover letter text."
        draft.save()
        self.assertEqual(draft.resolved_content, "Custom cover letter text.")

    def test_long_content_still_produces_valid_pdf(self):
        long_content = "This is a sentence about my qualifications. " * 200
        draft = self._make_draft(content=long_content)
        service = ExportService()
        result = service.build_cover_letter_pdf(draft)
        self.assertTrue(result.startswith(b"%PDF"))
