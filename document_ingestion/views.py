"""Upload view for the document ingestion lane.

Contracts:
  - session-schema v1.0.0
  - section-output-schema v1.0.0 (unsupported-PDF gate)
  - generation-service-interface v1.0.0 (error_code: unsupported_pdf)

Owns: form submission, PDF validation, storage wiring, session creation,
and the status transition pending → ingesting.

Dispatch strategy:
  - app_key: dispatches ``ingest_resume_task`` async; Celery then chains to
    ``run_generation``. Returns 201 immediately.
  - user_key: runs ingestion + generation synchronously in-request.
    The raw user_key must never be written to persistent storage or the
    Celery broker (Redis), so the async chain cannot be used.
"""

import os
import tempfile
import uuid

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from resume_sessions.models import ResumeSession

from .services import ingest_resume, is_pdf_text_extractable

# 20 MB upload limit.
_MAX_PDF_BYTES = 20 * 1024 * 1024

_UNSUPPORTED_PDF_MESSAGE = (
    "This PDF appears to be image-only and cannot be processed. "
    "Please upload a digital PDF with selectable text."
)


@method_decorator(csrf_exempt, name="dispatch")
class UploadView(View):
    """Accept a PDF upload and create a ResumeSession.

    POST /upload/

    Multipart form fields
    ─────────────────────
    pdf_file         (file, required)
    job_description  (str, required)
    credential_mode  (str, required) — "app_key" | "user_key"
    selected_model   (str, required) — one of RESUME_TAILOR_CURATED_MODELS
    generation_mode  (str, optional) — "resume_only" (default) | "resume_and_cover_letter"
    user_key         (str, optional) — present only when credential_mode=user_key;
                                       used only for this request and NEVER persisted.

    Success response (201)
    ──────────────────────
    {
        "session_id": "<uuid>",
        "status":     "ingesting"
    }

    Error response (400 / 422)
    ──────────────────────────
    {
        "errors": {
            "<field>": "<message>",
            ...
        }
    }
    """

    def get(self, request):
        curated_models = getattr(settings, "RESUME_TAILOR_CURATED_MODELS", [])
        default_model = getattr(settings, "RESUME_TAILOR_DEFAULT_MODEL", "")
        return render(request, "document_ingestion/upload.html", {
            "curated_models": curated_models,
            "default_model": default_model,
        })

    def post(self, request):
        errors = {}

        # ── field extraction ────────────────────────────────────────────────
        pdf_file = request.FILES.get("pdf_file")
        job_description = request.POST.get("job_description", "").strip()
        credential_mode = request.POST.get("credential_mode", "").strip()
        selected_model = request.POST.get("selected_model", "").strip()
        generation_mode = request.POST.get(
            "generation_mode",
            ResumeSession.GenerationMode.RESUME_ONLY,
        ).strip()
        user_key = request.POST.get("user_key", "").strip()

        # ── field validation ────────────────────────────────────────────────
        if not pdf_file:
            errors["pdf_file"] = "A PDF file is required."
        else:
            if not pdf_file.name.lower().endswith(".pdf"):
                errors["pdf_file"] = "Only PDF files are supported."
            elif pdf_file.size > _MAX_PDF_BYTES:
                errors["pdf_file"] = "PDF must be 20 MB or smaller."

        if not job_description:
            errors["job_description"] = "Job description is required."

        valid_credential_modes = (
            ResumeSession.CredentialMode.APP_KEY,
            ResumeSession.CredentialMode.USER_KEY,
        )
        if credential_mode not in valid_credential_modes:
            errors["credential_mode"] = (
                "credential_mode must be 'app_key' or 'user_key'."
            )
        elif credential_mode == ResumeSession.CredentialMode.USER_KEY and not user_key:
            errors["user_key"] = "user_key is required when credential_mode is 'user_key'."

        curated_models = getattr(settings, "RESUME_TAILOR_CURATED_MODELS", [])
        if selected_model not in curated_models:
            errors["selected_model"] = (
                f"selected_model must be one of: {', '.join(curated_models)}."
            )

        valid_generation_modes = (
            ResumeSession.GenerationMode.RESUME_ONLY,
            ResumeSession.GenerationMode.RESUME_AND_COVER_LETTER,
        )
        if generation_mode not in valid_generation_modes:
            errors["generation_mode"] = (
                "generation_mode must be 'resume_only' or 'resume_and_cover_letter'."
            )

        if errors:
            return JsonResponse({"errors": errors}, status=400)

        # ── PDF content validation ───────────────────────────────────────────
        pdf_bytes = pdf_file.read()
        if not is_pdf_text_extractable(pdf_bytes):
            return JsonResponse(
                {"errors": {"pdf_file": _UNSUPPORTED_PDF_MESSAGE}},
                status=422,
            )

        # ── persist file ─────────────────────────────────────────────────────
        storage_name = f"uploads/{uuid.uuid4()}.pdf"
        saved_path = default_storage.save(storage_name, ContentFile(pdf_bytes))

        # ── derive output_artifact_type from generation_mode ─────────────────
        if generation_mode == ResumeSession.GenerationMode.RESUME_AND_COVER_LETTER:
            output_artifact_type = ResumeSession.OutputArtifactType.DUAL_PDF
        else:
            output_artifact_type = ResumeSession.OutputArtifactType.SINGLE_PDF

        # ── create session ────────────────────────────────────────────────────
        # user_key is intentionally never stored — it lives only in this request.
        try:
            session = ResumeSession.objects.create(
                status=ResumeSession.Status.PENDING,
                source_pdf_path=saved_path,
                generation_mode=generation_mode,
                output_artifact_type=output_artifact_type,
                credential_mode=credential_mode,
                selected_model=selected_model,
                job_description=job_description,
            )
        except Exception:
            # Roll back the uploaded file to avoid storage orphans.
            default_storage.delete(saved_path)
            raise

        # ── dispatch to ingestion + generation lanes ──────────────────────
        if credential_mode == ResumeSession.CredentialMode.APP_KEY:
            # Async path: ingest task → generation task (Celery chain).
            from .tasks import ingest_resume_task

            session.status = ResumeSession.Status.INGESTING
            session.save(update_fields=["status", "updated_at"])
            ingest_resume_task.delay(str(session.id))
        else:
            # Synchronous path for user_key: the raw key must never touch
            # persistent storage or the Celery broker, so the full pipeline
            # runs in-request.
            from .exceptions import UnsupportedPDFError
            from generation.service import (
                GenerationRequest,
                GenerationService,
                SectionInput,
            )

            session.status = ResumeSession.Status.INGESTING
            session.save(update_fields=["status", "updated_at"])

            try:
                # Write pdf_bytes to a temp file because ingest_resume
                # expects a filesystem path; the stored path is relative to
                # MEDIA_ROOT and may not be resolvable from the process CWD.
                tmp_fd, tmp_path = tempfile.mkstemp(suffix=".pdf")
                try:
                    with os.fdopen(tmp_fd, "wb") as f:
                        f.write(pdf_bytes)
                    sections = ingest_resume(session, tmp_path)
                finally:
                    os.unlink(tmp_path)
            except UnsupportedPDFError:
                session.status = ResumeSession.Status.FAILED
                session.save(update_fields=["status", "updated_at"])
                return JsonResponse(
                    {"errors": {"pdf_file": _UNSUPPORTED_PDF_MESSAGE}},
                    status=422,
                )

            session.status = ResumeSession.Status.GENERATING
            session.save(update_fields=["status", "updated_at"])

            gen_request = GenerationRequest(
                session_id=str(session.id),
                credential_mode=credential_mode,
                model_name=selected_model,
                sections=[
                    SectionInput(
                        section_key=s.section_key,
                        order_index=s.order_index,
                        original_content=s.original_content,
                    )
                    for s in sections
                ],
                job_description=job_description,
                generation_mode=generation_mode,
                user_key=user_key,
            )
            # user_key lives only in gen_request (in memory) and is
            # discarded after GenerationService.run() returns.
            GenerationService().run(gen_request)

        return JsonResponse(
            {
                "session_id": str(session.id),
                "status": session.status,
            },
            status=201,
        )
