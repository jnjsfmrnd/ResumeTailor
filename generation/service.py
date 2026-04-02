"""Generation service implementing the GenerationService interface.

Contracts:
  - generation-service-interface v1.0.0

Key invariants enforced here:
  - Only curated models (from settings) are accepted.
  - user_key is NEVER written to persistent storage, logs, or traces.
  - error_summary NEVER contains resume text, cover letter text, or job description text.
  - Timeout error codes are credential-mode-aware:
      credential_mode=user_key  → error_code=timeout_user_key
      credential_mode=app_key   → error_code=timeout_app_key
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import openai
from django.conf import settings

from resume_sessions.models import CoverLetterDraft, GenerationRun, ResumeSection, ResumeSession

logger = logging.getLogger(__name__)

PROMPT_VERSION = "1.0.0"

# Exact user-facing messages per generation-service-interface v1.0.0 §Error Codes
TIMEOUT_USER_MESSAGES: dict[str, str] = {
    GenerationRun.ErrorCode.TIMEOUT_USER_KEY: "Request timed out. Check your API key and retry.",
    GenerationRun.ErrorCode.TIMEOUT_APP_KEY: "Request timed out. Retry the request.",
}


# ---------------------------------------------------------------------------
# Data Transfer Objects (mirror of generation-service-interface v1.0.0)
# ---------------------------------------------------------------------------

@dataclass
class SectionInput:
    """Subset of ResumeSection passed to the generation service."""

    section_key: str
    order_index: int
    original_content: str


@dataclass
class GenerationRequest:
    """Input to GenerationService.run()."""

    session_id: str
    credential_mode: str  # ResumeSession.CredentialMode: "app_key" | "user_key"
    model_name: str       # Must be in the curated shortlist
    sections: list[SectionInput]
    job_description: str
    generation_mode: str  # ResumeSession.GenerationMode: "resume_only" | "resume_and_cover_letter"
    # Present only when credential_mode="user_key". NEVER persisted or logged.
    user_key: Optional[str] = None


@dataclass
class SectionOutput:
    """Tailored content for a single resume section."""

    section_key: str
    tailored_content: str


@dataclass
class CoverLetterDraftOutput:
    """Cover letter produced by the generation service."""

    original_grounding_summary: str
    tailored_content: str


@dataclass
class GenerationResult:
    """Return value of GenerationService.run()."""

    run_id: str
    status: str  # GenerationRun.Status value
    tailored_sections: list[SectionOutput] = field(default_factory=list)
    cover_letter_draft: Optional[CoverLetterDraftOutput] = None
    error_code: Optional[str] = None


# ---------------------------------------------------------------------------
# Internal exception
# ---------------------------------------------------------------------------

class _StructuredOutputError(Exception):
    """Raised when the model response does not conform to the expected schema."""


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class GenerationService:
    """Implements GenerationService.run() per generation-service-interface v1.0.0."""

    # System prompt instructs the model on grounding rules and output format.
    _SYSTEM_PROMPT = (
        "You are a professional resume tailoring assistant. "
        "Your task is to rewrite the provided resume sections so they better match "
        "the target job description.\n\n"
        "RULES:\n"
        "1. Ground every rewrite ONLY in the original resume content and the job "
        "description. Do not invent credentials, dates, titles, companies, or "
        "experiences that are not present in the original resume.\n"
        "2. Preserve factual accuracy. Enhance framing and keyword alignment only.\n"
        "3. Return a single JSON object with this exact structure:\n"
        '   {"tailored_sections": [{"section_key": "<key>", "tailored_content": "<text>"}, ...]}\n'
        "   Each input section_key must appear exactly once in the output.\n"
        "4. When instructed to generate a cover letter, add a top-level "
        '"cover_letter" key:\n'
        '   {"tailored_sections": [...], "cover_letter": '
        '{"original_grounding_summary": "<brief internal note on which resume '
        'facts were used — must not quote the job description>", '
        '"tailored_content": "<cover letter text>"}}\n'
        "5. Respond with JSON only. No markdown fences, no prose outside the JSON."
    )

    def run(self, request: GenerationRequest) -> GenerationResult:
        """Execute generation for a session and return the result.

        Creates a GenerationRun audit record. On success, writes tailored_content
        back to the session's ResumeSection rows and creates/updates CoverLetterDraft.

        Raises:
            ValueError: If model_name is not in the curated shortlist.
        """
        self._validate_model(request.model_name)

        # Resolve API key BEFORE creating any DB records so the key never
        # touches a code path that writes to persistent storage.
        api_key = self._resolve_api_key(request)

        started_at = datetime.now(timezone.utc)
        run = GenerationRun.objects.create(
            session_id=request.session_id,
            model_name=request.model_name,
            credential_mode=request.credential_mode,
            prompt_version=PROMPT_VERSION,
            status=GenerationRun.Status.PENDING,
            started_at=started_at,
        )

        try:
            run.status = GenerationRun.Status.RUNNING
            run.save(update_fields=["status"])

            timeout = int(getattr(settings, "RESUME_TAILOR_GENERATION_TIMEOUT", 120))
            client = openai.OpenAI(
                base_url=settings.GITHUB_MODELS_API_BASE,
                api_key=api_key,
                timeout=float(timeout),
            )
            # Clear the local reference; the key is now only inside the client object.
            api_key = None

            response = client.chat.completions.create(
                model=request.model_name,
                messages=self._build_messages(request),
                response_format={"type": "json_object"},
            )

            raw_content = response.choices[0].message.content or ""
            tailored_sections, cover_letter_draft = self._parse_and_validate_output(
                raw_content, request
            )

            self._persist_outputs(request, tailored_sections, cover_letter_draft)

            completed_at = datetime.now(timezone.utc)
            run.status = GenerationRun.Status.SUCCEEDED
            run.completed_at = completed_at
            run.duration_ms = int((completed_at - started_at).total_seconds() * 1000)
            run.save(update_fields=["status", "completed_at", "duration_ms"])

            return GenerationResult(
                run_id=str(run.id),
                status=GenerationRun.Status.SUCCEEDED,
                tailored_sections=tailored_sections,
                cover_letter_draft=cover_letter_draft,
            )

        except openai.APITimeoutError:
            return self._handle_timeout(run, request, started_at)

        except openai.APIConnectionError:
            return self._handle_failure(
                run,
                started_at,
                GenerationRun.ErrorCode.MODEL_UNAVAILABLE,
                "Connection to the model endpoint failed.",
            )

        except _StructuredOutputError:
            return self._handle_failure(
                run,
                started_at,
                GenerationRun.ErrorCode.STRUCTURED_OUTPUT_INVALID,
                "Model response did not match the required output schema.",
            )

        except Exception:
            logger.exception("Unexpected error in generation run %s", run.id)
            return self._handle_failure(
                run,
                started_at,
                GenerationRun.ErrorCode.STRUCTURED_OUTPUT_INVALID,
                "An unexpected error occurred during generation.",
            )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _validate_model(self, model_name: str) -> None:
        curated: list[str] = getattr(settings, "RESUME_TAILOR_CURATED_MODELS", [])
        if model_name not in curated:
            raise ValueError(
                f"Model '{model_name}' is not in the curated shortlist. "
                f"Allowed models: {curated}"
            )

    def _resolve_api_key(self, request: GenerationRequest) -> str:
        """Return the API key for the given credential mode.

        For user_key mode, returns request.user_key directly (caller's
        responsibility to supply it).  This value must never be persisted
        or logged — it exists only in memory for the duration of this call.
        """
        if request.credential_mode == ResumeSession.CredentialMode.USER_KEY:
            if not request.user_key:
                raise ValueError(
                    "user_key must be provided when credential_mode is 'user_key'."
                )
            return request.user_key
        return settings.GITHUB_MODELS_API_KEY

    def _build_messages(self, request: GenerationRequest) -> list[dict]:
        """Build the chat messages list for the API call."""
        section_lines = []
        for s in request.sections:
            section_lines.append(
                f"--- SECTION: {s.section_key} (order_index={s.order_index}) ---\n"
                f"{s.original_content}"
            )

        user_content = (
            f"JOB DESCRIPTION:\n{request.job_description}\n\n"
            f"RESUME SECTIONS TO TAILOR:\n\n"
            + "\n\n".join(section_lines)
        )

        if request.generation_mode == ResumeSession.GenerationMode.RESUME_AND_COVER_LETTER:
            user_content += (
                "\n\nAlso generate a cover letter. Include the 'cover_letter' key "
                "in your JSON response per the schema in your instructions."
            )

        return [
            {"role": "system", "content": self._SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

    def _parse_and_validate_output(
        self,
        raw_content: str,
        request: GenerationRequest,
    ) -> tuple[list[SectionOutput], Optional[CoverLetterDraftOutput]]:
        """Parse and validate the model's JSON response.

        Raises:
            _StructuredOutputError: If the response is malformed or missing fields.
        """
        try:
            data = json.loads(raw_content)
        except json.JSONDecodeError as exc:
            raise _StructuredOutputError("Response was not valid JSON.") from exc

        if not isinstance(data, dict):
            raise _StructuredOutputError("Response root must be a JSON object.")

        raw_sections = data.get("tailored_sections")
        if not isinstance(raw_sections, list):
            raise _StructuredOutputError(
                "'tailored_sections' must be a list in the model response."
            )

        # Validate each section entry and map by section_key
        output_by_key: dict[str, str] = {}
        for item in raw_sections:
            if not isinstance(item, dict):
                raise _StructuredOutputError(
                    "Each entry in 'tailored_sections' must be an object."
                )
            key = item.get("section_key")
            content = item.get("tailored_content")
            if not isinstance(key, str) or not key:
                raise _StructuredOutputError(
                    "Each tailored section must have a non-empty 'section_key'."
                )
            if not isinstance(content, str) or not content:
                raise _StructuredOutputError(
                    f"Section '{key}' is missing non-empty 'tailored_content'."
                )
            output_by_key[key] = content

        # Ensure all input section_keys are represented in the output
        input_keys = {s.section_key for s in request.sections}
        missing = input_keys - output_by_key.keys()
        if missing:
            raise _StructuredOutputError(
                f"Model response is missing tailored output for sections: {sorted(missing)}"
            )

        tailored_sections = [
            SectionOutput(section_key=k, tailored_content=v)
            for k, v in output_by_key.items()
            if k in input_keys
        ]

        cover_letter_draft: Optional[CoverLetterDraftOutput] = None
        if request.generation_mode == ResumeSession.GenerationMode.RESUME_AND_COVER_LETTER:
            raw_cl = data.get("cover_letter")
            if not isinstance(raw_cl, dict):
                raise _StructuredOutputError(
                    "'cover_letter' object is required for resume_and_cover_letter mode."
                )
            grounding = raw_cl.get("original_grounding_summary")
            cl_content = raw_cl.get("tailored_content")
            if not isinstance(grounding, str) or not grounding:
                raise _StructuredOutputError(
                    "Cover letter 'original_grounding_summary' must be a non-empty string."
                )
            if not isinstance(cl_content, str) or not cl_content:
                raise _StructuredOutputError(
                    "Cover letter 'tailored_content' must be a non-empty string."
                )
            cover_letter_draft = CoverLetterDraftOutput(
                original_grounding_summary=grounding,
                tailored_content=cl_content,
            )

        return tailored_sections, cover_letter_draft

    def _persist_outputs(
        self,
        request: GenerationRequest,
        tailored_sections: list[SectionOutput],
        cover_letter_draft: Optional[CoverLetterDraftOutput],
    ) -> None:
        """Write tailored content back to DB after successful generation."""
        output_map = {s.section_key: s.tailored_content for s in tailored_sections}

        sections_to_update = ResumeSection.objects.filter(
            session_id=request.session_id,
            section_key__in=list(output_map.keys()),
        )
        for section in sections_to_update:
            section.tailored_content = output_map[section.section_key]

        ResumeSection.objects.bulk_update(sections_to_update, ["tailored_content"])

        if cover_letter_draft is not None:
            CoverLetterDraft.objects.update_or_create(
                session_id=request.session_id,
                defaults={
                    "original_grounding_summary": cover_letter_draft.original_grounding_summary,
                    "tailored_content": cover_letter_draft.tailored_content,
                },
            )

    def _handle_timeout(
        self,
        run: GenerationRun,
        request: GenerationRequest,
        started_at: datetime,
    ) -> GenerationResult:
        """Resolve credential-mode-specific timeout error code and finalise the run."""
        if request.credential_mode == ResumeSession.CredentialMode.USER_KEY:
            error_code = GenerationRun.ErrorCode.TIMEOUT_USER_KEY
        else:
            error_code = GenerationRun.ErrorCode.TIMEOUT_APP_KEY

        # error_summary is an internal audit field; it must not include user content.
        timeout_sec = getattr(settings, "RESUME_TAILOR_GENERATION_TIMEOUT", 120)
        error_summary = (
            f"Generation timed out after {timeout_sec}s "
            f"(credential_mode={request.credential_mode})."
        )
        return self._handle_failure(run, started_at, error_code, error_summary, timed_out=True)

    def _handle_failure(
        self,
        run: GenerationRun,
        started_at: datetime,
        error_code: str,
        error_summary: str,
        *,
        timed_out: bool = False,
    ) -> GenerationResult:
        """Persist failure state on the run record and return a failed result."""
        completed_at = datetime.now(timezone.utc)
        run.status = GenerationRun.Status.TIMED_OUT if timed_out else GenerationRun.Status.FAILED
        run.error_code = error_code
        run.error_summary = error_summary
        run.completed_at = completed_at
        run.duration_ms = int((completed_at - started_at).total_seconds() * 1000)
        run.save(update_fields=["status", "error_code", "error_summary", "completed_at", "duration_ms"])

        return GenerationResult(
            run_id=str(run.id),
            status=run.status,
            error_code=error_code,
        )
