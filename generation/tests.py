"""Tests for the generation service.

Covers:
  - C1: Model shortlist validation and default model policy.
  - C1: user_key credential mode keeps key in memory only (never persisted).
  - C2: Timeout error codes are credential-mode-aware.
  - C2: error_summary never contains user-supplied text.
  - Structured output validation rejects malformed model responses.
"""

import json
from unittest.mock import MagicMock, patch

import httpx
import openai
from django.test import TestCase, override_settings

from resume_sessions.models import (
    CoverLetterDraft,
    GenerationRun,
    ResumeSection,
    ResumeSession,
)

from .service import (
    CoverLetterDraftOutput,
    GenerationRequest,
    GenerationResult,
    GenerationService,
    SectionInput,
    SectionOutput,
    TIMEOUT_USER_MESSAGES,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CURATED_MODELS = ["gpt-5.1", "claude-sonnet-4", "o3", "gpt-4.1", "llama-4-maverick"]
_DEFAULT_MODEL = "gpt-5.1"

_FAKE_API_BASE = "https://models.test.example.com"
_FAKE_APP_KEY = "app-key-abc"
_FAKE_USER_KEY = "user-key-xyz"

_TIMEOUT_REQUEST = httpx.Request("POST", "https://models.test.example.com")


def _make_session(**kwargs) -> ResumeSession:
    defaults = dict(source_pdf_path="test.pdf", job_description="")
    defaults.update(kwargs)
    return ResumeSession.objects.create(**defaults)


def _make_section_inputs(count: int = 1) -> list[SectionInput]:
    return [
        SectionInput(
            section_key=f"section_{i}",
            order_index=i,
            original_content=f"Original content for section {i}.",
        )
        for i in range(count)
    ]


def _make_request(session: ResumeSession, **kwargs) -> GenerationRequest:
    defaults = dict(
        session_id=str(session.id),
        credential_mode="app_key",
        model_name=_DEFAULT_MODEL,
        sections=_make_section_inputs(),
        job_description="Software engineer role requiring Python.",
        generation_mode="resume_only",
    )
    defaults.update(kwargs)
    return GenerationRequest(**defaults)


def _mock_openai_response(tailored_sections: list[dict], cover_letter: dict | None = None) -> MagicMock:
    """Build a mock openai ChatCompletion response with JSON content."""
    payload: dict = {"tailored_sections": tailored_sections}
    if cover_letter is not None:
        payload["cover_letter"] = cover_letter

    message = MagicMock()
    message.content = json.dumps(payload)
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    return response


@override_settings(
    GITHUB_MODELS_API_BASE=_FAKE_API_BASE,
    GITHUB_MODELS_API_KEY=_FAKE_APP_KEY,
    RESUME_TAILOR_CURATED_MODELS=_CURATED_MODELS,
    RESUME_TAILOR_DEFAULT_MODEL=_DEFAULT_MODEL,
    RESUME_TAILOR_GENERATION_TIMEOUT=120,
)
class TestModelShortlistPolicy(TestCase):
    """C1 — only curated models are accepted."""

    def setUp(self):
        self.session = _make_session()

    def test_valid_model_accepted(self):
        for model in _CURATED_MODELS:
            req = _make_request(self.session, model_name=model)
            with patch("generation.service.openai.OpenAI") as mock_cls:
                mock_cls.return_value.chat.completions.create.return_value = (
                    _mock_openai_response([
                        {"section_key": "section_0", "tailored_content": "Tailored."}
                    ])
                )
                # Should not raise
                result = GenerationService().run(req)
                self.assertEqual(result.status, GenerationRun.Status.SUCCEEDED)

    def test_invalid_model_raises_value_error(self):
        req = _make_request(self.session, model_name="not-a-real-model")
        with self.assertRaises(ValueError) as ctx:
            GenerationService().run(req)
        self.assertIn("not-a-real-model", str(ctx.exception))
        self.assertIn("curated shortlist", str(ctx.exception))

    def test_invalid_model_creates_no_generation_run(self):
        req = _make_request(self.session, model_name="gpt-99-fake")
        with self.assertRaises(ValueError):
            GenerationService().run(req)
        self.assertEqual(GenerationRun.objects.filter(session=self.session).count(), 0)


@override_settings(
    GITHUB_MODELS_API_BASE=_FAKE_API_BASE,
    GITHUB_MODELS_API_KEY=_FAKE_APP_KEY,
    RESUME_TAILOR_CURATED_MODELS=_CURATED_MODELS,
    RESUME_TAILOR_DEFAULT_MODEL=_DEFAULT_MODEL,
    RESUME_TAILOR_GENERATION_TIMEOUT=120,
)
class TestCredentialModePolicy(TestCase):
    """C1 — credential mode handling and user_key non-persistence."""

    def setUp(self):
        self.session = _make_session()

    def test_user_key_never_persisted_on_timeout(self):
        """user_key must not appear in any GenerationRun field after a timeout."""
        req = _make_request(
            self.session,
            credential_mode="user_key",
            user_key=_FAKE_USER_KEY,
        )
        with patch("generation.service.openai.OpenAI") as mock_cls:
            mock_cls.return_value.chat.completions.create.side_effect = (
                openai.APITimeoutError(request=_TIMEOUT_REQUEST)
            )
            GenerationService().run(req)

        run = GenerationRun.objects.get(session=self.session)
        for field_value in [
            run.model_name,
            run.credential_mode,
            run.prompt_version,
            run.error_code,
            run.error_summary,
        ]:
            self.assertNotIn(_FAKE_USER_KEY, str(field_value))

    def test_user_key_never_persisted_on_success(self):
        """user_key must not appear in any GenerationRun field on success."""
        req = _make_request(
            self.session,
            credential_mode="user_key",
            user_key=_FAKE_USER_KEY,
        )
        with patch("generation.service.openai.OpenAI") as mock_cls:
            mock_cls.return_value.chat.completions.create.return_value = (
                _mock_openai_response([
                    {"section_key": "section_0", "tailored_content": "Tailored."}
                ])
            )
            GenerationService().run(req)

        run = GenerationRun.objects.get(session=self.session)
        for field_value in [
            run.model_name,
            run.credential_mode,
            run.prompt_version,
            run.error_code,
            run.error_summary,
        ]:
            self.assertNotIn(_FAKE_USER_KEY, str(field_value))

    def test_user_key_missing_for_user_key_mode_raises(self):
        req = _make_request(self.session, credential_mode="user_key", user_key=None)
        with self.assertRaises(ValueError) as ctx:
            GenerationService().run(req)
        self.assertIn("user_key", str(ctx.exception))

    def test_app_key_mode_uses_settings_key(self):
        """In app_key mode, the OpenAI client is constructed with the settings key."""
        req = _make_request(self.session, credential_mode="app_key")
        with patch("generation.service.openai.OpenAI") as mock_cls:
            mock_cls.return_value.chat.completions.create.return_value = (
                _mock_openai_response([
                    {"section_key": "section_0", "tailored_content": "Tailored."}
                ])
            )
            GenerationService().run(req)

        mock_cls.assert_called_once()
        _, kwargs = mock_cls.call_args
        self.assertEqual(kwargs["api_key"], _FAKE_APP_KEY)

    def test_user_key_mode_uses_provided_key(self):
        """In user_key mode, the OpenAI client is constructed with the user's key."""
        req = _make_request(
            self.session,
            credential_mode="user_key",
            user_key=_FAKE_USER_KEY,
        )
        with patch("generation.service.openai.OpenAI") as mock_cls:
            mock_cls.return_value.chat.completions.create.return_value = (
                _mock_openai_response([
                    {"section_key": "section_0", "tailored_content": "Tailored."}
                ])
            )
            GenerationService().run(req)

        mock_cls.assert_called_once()
        _, kwargs = mock_cls.call_args
        self.assertEqual(kwargs["api_key"], _FAKE_USER_KEY)


@override_settings(
    GITHUB_MODELS_API_BASE=_FAKE_API_BASE,
    GITHUB_MODELS_API_KEY=_FAKE_APP_KEY,
    RESUME_TAILOR_CURATED_MODELS=_CURATED_MODELS,
    RESUME_TAILOR_DEFAULT_MODEL=_DEFAULT_MODEL,
    RESUME_TAILOR_GENERATION_TIMEOUT=120,
)
class TestTimeoutErrorCodes(TestCase):
    """C2 — timeout error codes are credential-mode-aware."""

    def setUp(self):
        self.session = _make_session()

    def test_timeout_with_user_key_yields_timeout_user_key(self):
        req = _make_request(
            self.session,
            credential_mode="user_key",
            user_key=_FAKE_USER_KEY,
        )
        with patch("generation.service.openai.OpenAI") as mock_cls:
            mock_cls.return_value.chat.completions.create.side_effect = (
                openai.APITimeoutError(request=_TIMEOUT_REQUEST)
            )
            result = GenerationService().run(req)

        self.assertEqual(result.status, GenerationRun.Status.TIMED_OUT)
        self.assertEqual(result.error_code, GenerationRun.ErrorCode.TIMEOUT_USER_KEY)

        run = GenerationRun.objects.get(session=self.session)
        self.assertEqual(run.status, GenerationRun.Status.TIMED_OUT)
        self.assertEqual(run.error_code, GenerationRun.ErrorCode.TIMEOUT_USER_KEY)

    def test_timeout_with_app_key_yields_timeout_app_key(self):
        req = _make_request(self.session, credential_mode="app_key")
        with patch("generation.service.openai.OpenAI") as mock_cls:
            mock_cls.return_value.chat.completions.create.side_effect = (
                openai.APITimeoutError(request=_TIMEOUT_REQUEST)
            )
            result = GenerationService().run(req)

        self.assertEqual(result.status, GenerationRun.Status.TIMED_OUT)
        self.assertEqual(result.error_code, GenerationRun.ErrorCode.TIMEOUT_APP_KEY)

        run = GenerationRun.objects.get(session=self.session)
        self.assertEqual(run.status, GenerationRun.Status.TIMED_OUT)
        self.assertEqual(run.error_code, GenerationRun.ErrorCode.TIMEOUT_APP_KEY)

    def test_timeout_user_key_message_is_exact(self):
        """The user-facing message for timeout_user_key matches the contract exactly."""
        self.assertEqual(
            TIMEOUT_USER_MESSAGES[GenerationRun.ErrorCode.TIMEOUT_USER_KEY],
            "Request timed out. Check your API key and retry.",
        )

    def test_timeout_app_key_message_is_exact(self):
        """The user-facing message for timeout_app_key matches the contract exactly."""
        self.assertEqual(
            TIMEOUT_USER_MESSAGES[GenerationRun.ErrorCode.TIMEOUT_APP_KEY],
            "Request timed out. Retry the request.",
        )

    def test_error_summary_does_not_contain_user_content(self):
        """error_summary must not contain job description or resume text."""
        job_desc = "Senior Python Engineer at Acme Corp."
        original_content = "Worked on internal tooling at Acme Corp."
        req = _make_request(
            self.session,
            credential_mode="app_key",
            job_description=job_desc,
            sections=[
                SectionInput(
                    section_key="experience",
                    order_index=0,
                    original_content=original_content,
                )
            ],
        )
        with patch("generation.service.openai.OpenAI") as mock_cls:
            mock_cls.return_value.chat.completions.create.side_effect = (
                openai.APITimeoutError(request=_TIMEOUT_REQUEST)
            )
            GenerationService().run(req)

        run = GenerationRun.objects.get(session=self.session)
        self.assertNotIn("Acme Corp", run.error_summary)
        self.assertNotIn("Senior Python Engineer", run.error_summary)
        self.assertNotIn("internal tooling", run.error_summary)


@override_settings(
    GITHUB_MODELS_API_BASE=_FAKE_API_BASE,
    GITHUB_MODELS_API_KEY=_FAKE_APP_KEY,
    RESUME_TAILOR_CURATED_MODELS=_CURATED_MODELS,
    RESUME_TAILOR_DEFAULT_MODEL=_DEFAULT_MODEL,
    RESUME_TAILOR_GENERATION_TIMEOUT=120,
)
class TestStructuredOutputValidation(TestCase):
    """Malformed model responses are handled as structured_output_invalid."""

    def setUp(self):
        self.session = _make_session()

    def _run_with_raw_response(self, raw: str) -> GenerationResult:
        req = _make_request(self.session)
        with patch("generation.service.openai.OpenAI") as mock_cls:
            message = MagicMock()
            message.content = raw
            choice = MagicMock()
            choice.message = message
            response = MagicMock()
            response.choices = [choice]
            mock_cls.return_value.chat.completions.create.return_value = response
            return GenerationService().run(req)

    def test_invalid_json_yields_structured_output_invalid(self):
        result = self._run_with_raw_response("not json at all")
        self.assertEqual(result.status, GenerationRun.Status.FAILED)
        self.assertEqual(result.error_code, GenerationRun.ErrorCode.STRUCTURED_OUTPUT_INVALID)

    def test_missing_tailored_sections_key(self):
        result = self._run_with_raw_response(json.dumps({"other_key": []}))
        self.assertEqual(result.error_code, GenerationRun.ErrorCode.STRUCTURED_OUTPUT_INVALID)

    def test_missing_section_in_output(self):
        """If the model omits a section, the output is invalid."""
        # Request has section_0 but the response returns section_99
        result = self._run_with_raw_response(
            json.dumps({"tailored_sections": [
                {"section_key": "section_99", "tailored_content": "Wrong section."}
            ]})
        )
        self.assertEqual(result.error_code, GenerationRun.ErrorCode.STRUCTURED_OUTPUT_INVALID)

    def test_missing_cover_letter_when_required(self):
        req = _make_request(self.session, generation_mode="resume_and_cover_letter")
        with patch("generation.service.openai.OpenAI") as mock_cls:
            mock_cls.return_value.chat.completions.create.return_value = (
                _mock_openai_response([
                    {"section_key": "section_0", "tailored_content": "Tailored."}
                ])
                # No cover_letter key
            )
            result = GenerationService().run(req)
        self.assertEqual(result.error_code, GenerationRun.ErrorCode.STRUCTURED_OUTPUT_INVALID)


@override_settings(
    GITHUB_MODELS_API_BASE=_FAKE_API_BASE,
    GITHUB_MODELS_API_KEY=_FAKE_APP_KEY,
    RESUME_TAILOR_CURATED_MODELS=_CURATED_MODELS,
    RESUME_TAILOR_DEFAULT_MODEL=_DEFAULT_MODEL,
    RESUME_TAILOR_GENERATION_TIMEOUT=120,
)
class TestSuccessfulGeneration(TestCase):
    """Happy-path behaviour: DB write-back and result shape."""

    def setUp(self):
        self.session = _make_session()
        # Pre-create ResumeSection rows (normally done by engineer B ingestion)
        self.section = ResumeSection.objects.create(
            session=self.session,
            section_key="experience",
            order_index=0,
            page_number=1,
            bbox_x0=0.0,
            bbox_y0=0.0,
            bbox_x1=100.0,
            bbox_y1=50.0,
            original_content="Original experience content.",
        )

    def test_tailored_content_written_to_resume_section(self):
        req = _make_request(
            self.session,
            sections=[
                SectionInput(
                    section_key="experience",
                    order_index=0,
                    original_content="Original experience content.",
                )
            ],
        )
        with patch("generation.service.openai.OpenAI") as mock_cls:
            mock_cls.return_value.chat.completions.create.return_value = (
                _mock_openai_response([
                    {"section_key": "experience", "tailored_content": "Tailored experience."}
                ])
            )
            result = GenerationService().run(req)

        self.assertEqual(result.status, GenerationRun.Status.SUCCEEDED)
        self.section.refresh_from_db()
        self.assertEqual(self.section.tailored_content, "Tailored experience.")

    def test_cover_letter_draft_created_for_cover_letter_mode(self):
        req = _make_request(
            self.session,
            sections=[
                SectionInput(
                    section_key="experience",
                    order_index=0,
                    original_content="Original experience content.",
                )
            ],
            generation_mode="resume_and_cover_letter",
        )
        with patch("generation.service.openai.OpenAI") as mock_cls:
            mock_cls.return_value.chat.completions.create.return_value = (
                _mock_openai_response(
                    tailored_sections=[
                        {"section_key": "experience", "tailored_content": "Tailored."}
                    ],
                    cover_letter={
                        "original_grounding_summary": "Used experience section.",
                        "tailored_content": "Dear Hiring Manager,\n\nI am excited...",
                    },
                )
            )
            result = GenerationService().run(req)

        self.assertEqual(result.status, GenerationRun.Status.SUCCEEDED)
        self.assertIsNotNone(result.cover_letter_draft)

        draft = CoverLetterDraft.objects.get(session=self.session)
        self.assertEqual(draft.tailored_content, "Dear Hiring Manager,\n\nI am excited...")
        self.assertEqual(draft.original_grounding_summary, "Used experience section.")

    def test_cover_letter_draft_not_created_for_resume_only_mode(self):
        req = _make_request(
            self.session,
            sections=[
                SectionInput(
                    section_key="experience",
                    order_index=0,
                    original_content="Original experience content.",
                )
            ],
            generation_mode="resume_only",
        )
        with patch("generation.service.openai.OpenAI") as mock_cls:
            mock_cls.return_value.chat.completions.create.return_value = (
                _mock_openai_response([
                    {"section_key": "experience", "tailored_content": "Tailored."}
                ])
            )
            result = GenerationService().run(req)

        self.assertEqual(result.status, GenerationRun.Status.SUCCEEDED)
        self.assertIsNone(result.cover_letter_draft)
        self.assertFalse(CoverLetterDraft.objects.filter(session=self.session).exists())

    def test_generation_run_record_created_and_completed(self):
        req = _make_request(
            self.session,
            sections=[
                SectionInput(
                    section_key="experience",
                    order_index=0,
                    original_content="Original experience content.",
                )
            ],
        )
        with patch("generation.service.openai.OpenAI") as mock_cls:
            mock_cls.return_value.chat.completions.create.return_value = (
                _mock_openai_response([
                    {"section_key": "experience", "tailored_content": "Tailored."}
                ])
            )
            result = GenerationService().run(req)

        run = GenerationRun.objects.get(id=result.run_id)
        self.assertEqual(run.status, GenerationRun.Status.SUCCEEDED)
        self.assertIsNotNone(run.completed_at)
        self.assertIsNotNone(run.duration_ms)
        self.assertEqual(run.model_name, _DEFAULT_MODEL)
        self.assertEqual(run.prompt_version, "1.0.0")
        self.assertEqual(run.error_code, "")  # blank on success, not None

    def test_model_connection_failure_yields_model_unavailable(self):
        req = _make_request(self.session)
        with patch("generation.service.openai.OpenAI") as mock_cls:
            mock_cls.return_value.chat.completions.create.side_effect = (
                openai.APIConnectionError(request=_TIMEOUT_REQUEST)
            )
            result = GenerationService().run(req)

        self.assertEqual(result.status, GenerationRun.Status.FAILED)
        self.assertEqual(result.error_code, GenerationRun.ErrorCode.MODEL_UNAVAILABLE)

    def test_timeout_sets_duration_ms(self):
        req = _make_request(self.session)
        with patch("generation.service.openai.OpenAI") as mock_cls:
            mock_cls.return_value.chat.completions.create.side_effect = (
                openai.APITimeoutError(request=_TIMEOUT_REQUEST)
            )
            GenerationService().run(req)

        run = GenerationRun.objects.get(session=self.session)
        self.assertIsNotNone(run.duration_ms)
        self.assertGreaterEqual(run.duration_ms, 0)
