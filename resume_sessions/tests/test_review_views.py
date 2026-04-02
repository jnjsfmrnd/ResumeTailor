"""Tests for the review and edit workspace views (D1)."""

import json
import uuid

from django.test import Client, TestCase, override_settings
from django.urls import reverse

from resume_sessions.models import CoverLetterDraft, ResumeSection, ResumeSession
from resume_sessions.views import _overflow_risk


@override_settings(
    DATABASES={
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }
)
class ReviewWorkspaceViewTests(TestCase):
    """GET /sessions/<id>/review/ — renders the workspace template."""

    def _make_session(self, mode=ResumeSession.GenerationMode.RESUME_ONLY):
        return ResumeSession.objects.create(
            source_pdf_path="uploads/test.pdf",
            job_description="Build great things.",
            generation_mode=mode,
        )

    def _make_section(self, session, key="summary", order=0, tailored="Tailored content."):
        return ResumeSection.objects.create(
            session=session,
            section_key=key,
            order_index=order,
            page_number=1,
            bbox_x0=50.0,
            bbox_y0=700.0,
            bbox_x1=550.0,
            bbox_y1=750.0,
            original_content="Original content.",
            tailored_content=tailored,
        )

    def setUp(self):
        self.client = Client()

    def test_review_page_returns_200(self):
        session = self._make_session()
        self._make_section(session)
        url = reverse("resume_sessions:review", kwargs={"session_id": session.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_review_page_shows_sections(self):
        session = self._make_session()
        self._make_section(session, key="summary")
        url = reverse("resume_sessions:review", kwargs={"session_id": session.pk})
        response = self.client.get(url)
        self.assertContains(response, "Original content.")
        self.assertContains(response, "Tailored content.")

    def test_cover_letter_panel_hidden_for_resume_only(self):
        session = self._make_session(mode=ResumeSession.GenerationMode.RESUME_ONLY)
        self._make_section(session)
        url = reverse("resume_sessions:review", kwargs={"session_id": session.pk})
        response = self.client.get(url)
        self.assertNotContains(response, "cover-letter-area")

    def test_cover_letter_panel_shown_for_resume_and_cover_letter(self):
        session = self._make_session(
            mode=ResumeSession.GenerationMode.RESUME_AND_COVER_LETTER
        )
        self._make_section(session)
        CoverLetterDraft.objects.create(
            session=session,
            original_grounding_summary="Summary.",
            tailored_content="Dear Hiring Manager,",
        )
        url = reverse("resume_sessions:review", kwargs={"session_id": session.pk})
        response = self.client.get(url)
        self.assertContains(response, "cover-letter-area")
        self.assertContains(response, "Dear Hiring Manager,")

    def test_download_cover_letter_button_absent_for_resume_only(self):
        session = self._make_session(mode=ResumeSession.GenerationMode.RESUME_ONLY)
        self._make_section(session)
        url = reverse("resume_sessions:review", kwargs={"session_id": session.pk})
        response = self.client.get(url)
        self.assertNotContains(response, "Download cover letter PDF")

    def test_download_cover_letter_button_present_for_dual_mode(self):
        session = self._make_session(
            mode=ResumeSession.GenerationMode.RESUME_AND_COVER_LETTER
        )
        self._make_section(session)
        CoverLetterDraft.objects.create(
            session=session,
            original_grounding_summary="Summary.",
            tailored_content="Dear Hiring Manager,",
        )
        url = reverse("resume_sessions:review", kwargs={"session_id": session.pk})
        response = self.client.get(url)
        self.assertContains(response, "Download cover letter PDF")

    def test_overflow_warning_shown_when_risk_detected(self):
        session = self._make_session()
        # Very small bbox, long content → overflow risk.
        ResumeSection.objects.create(
            session=session,
            section_key="summary",
            order_index=0,
            page_number=1,
            bbox_x0=50.0,
            bbox_y0=740.0,
            bbox_x1=100.0,  # only 50pt wide
            bbox_y1=755.0,  # only 15pt tall
            original_content="x",
            tailored_content="A" * 500,
        )
        url = reverse("resume_sessions:review", kwargs={"session_id": session.pk})
        response = self.client.get(url)
        # The overflow warning block and badge both contain "Overflow risk"
        self.assertContains(response, "Overflow risk")

    def test_404_for_nonexistent_session(self):
        url = reverse(
            "resume_sessions:review",
            kwargs={"session_id": uuid.uuid4()},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


@override_settings(
    DATABASES={
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }
)
class SectionEditViewTests(TestCase):
    """POST /sessions/<id>/sections/<id>/edit/ — persists user edits."""

    def _setup(self):
        session = ResumeSession.objects.create(
            source_pdf_path="uploads/test.pdf",
            job_description="Build great things.",
        )
        section = ResumeSection.objects.create(
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
        return session, section

    def _url(self, session, section):
        return reverse(
            "resume_sessions:section-edit",
            kwargs={"session_id": session.pk, "section_id": section.pk},
        )

    def test_saves_user_edited_content(self):
        session, section = self._setup()
        response = self.client.post(
            self._url(session, section),
            data=json.dumps({"user_edited_content": "My edit."}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        section.refresh_from_db()
        self.assertEqual(section.user_edited_content, "My edit.")

    def test_returns_resolved_content(self):
        session, section = self._setup()
        response = self.client.post(
            self._url(session, section),
            data=json.dumps({"user_edited_content": "My edit."}),
            content_type="application/json",
        )
        data = response.json()
        self.assertEqual(data["resolved_content"], "My edit.")

    def test_resolved_content_falls_back_to_tailored(self):
        session, section = self._setup()
        response = self.client.post(
            self._url(session, section),
            data=json.dumps({"user_edited_content": ""}),
            content_type="application/json",
        )
        data = response.json()
        self.assertEqual(data["resolved_content"], "Tailored.")

    def test_invalid_json_returns_400(self):
        session, section = self._setup()
        response = self.client.post(
            self._url(session, section),
            data="not json",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_method_not_allowed(self):
        session, section = self._setup()
        response = self.client.get(self._url(session, section))
        self.assertEqual(response.status_code, 405)

    def test_404_for_wrong_session(self):
        session, section = self._setup()
        url = reverse(
            "resume_sessions:section-edit",
            kwargs={"session_id": uuid.uuid4(), "section_id": section.pk},
        )
        response = self.client.post(
            url,
            data=json.dumps({"user_edited_content": "x"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)


@override_settings(
    DATABASES={
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }
)
class CoverLetterEditViewTests(TestCase):
    """POST /sessions/<id>/cover-letter/edit/ — persists cover letter edits."""

    def _setup(self):
        session = ResumeSession.objects.create(
            source_pdf_path="uploads/test.pdf",
            job_description="Build great things.",
            generation_mode=ResumeSession.GenerationMode.RESUME_AND_COVER_LETTER,
        )
        draft = CoverLetterDraft.objects.create(
            session=session,
            original_grounding_summary="Summary.",
            tailored_content="Dear Hiring Manager,",
        )
        return session, draft

    def _url(self, session):
        return reverse(
            "resume_sessions:cover-letter-edit",
            kwargs={"session_id": session.pk},
        )

    def test_saves_user_edited_content(self):
        session, draft = self._setup()
        response = self.client.post(
            self._url(session),
            data=json.dumps({"user_edited_content": "Edited letter."}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        draft.refresh_from_db()
        self.assertEqual(draft.user_edited_content, "Edited letter.")

    def test_returns_resolved_content(self):
        session, draft = self._setup()
        response = self.client.post(
            self._url(session),
            data=json.dumps({"user_edited_content": "Edited letter."}),
            content_type="application/json",
        )
        data = response.json()
        self.assertEqual(data["resolved_content"], "Edited letter.")

    def test_404_when_no_draft(self):
        session = ResumeSession.objects.create(
            source_pdf_path="uploads/test.pdf",
            job_description="Build great things.",
        )
        url = self._url(session)
        response = self.client.post(
            url,
            data=json.dumps({"user_edited_content": "x"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)


@override_settings(
    DATABASES={
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }
)
class OverflowRiskTests(TestCase):
    """Unit tests for the _overflow_risk helper."""

    def _make_section(self, content, x0=50, y0=700, x1=550, y1=750):
        session = ResumeSession.objects.create(
            source_pdf_path="uploads/test.pdf",
            job_description="x",
        )
        return ResumeSection(
            session=session,
            section_key="summary",
            order_index=0,
            page_number=1,
            bbox_x0=x0,
            bbox_y0=y0,
            bbox_x1=x1,
            bbox_y1=y1,
            original_content="x",
            tailored_content=content,
        )

    def test_short_content_no_risk(self):
        section = self._make_section("Short text.", x0=50, y0=700, x1=550, y1=750)
        self.assertFalse(_overflow_risk(section))

    def test_very_long_content_has_risk(self):
        section = self._make_section("x" * 2000, x0=50, y0=740, x1=100, y1=755)
        self.assertTrue(_overflow_risk(section))

    def test_zero_width_bbox_no_risk(self):
        section = self._make_section("content", x0=50, y0=700, x1=50, y1=750)
        self.assertFalse(_overflow_risk(section))

    def test_zero_height_bbox_no_risk(self):
        section = self._make_section("content", x0=50, y0=700, x1=550, y1=700)
        self.assertFalse(_overflow_risk(section))
