"""Export download views (D2).

Contract: docs/contracts/export-service-interface.md v1.0.0

Endpoints:
  GET /sessions/<session_id>/export/resume/        → tailored-resume.pdf
  GET /sessions/<session_id>/export/cover-letter/  → cover-letter.pdf

Output rules (contract-enforced):
  - resume_only sessions expose only the resume download.
  - resume_and_cover_letter sessions expose both downloads separately.
  - No ZIP output is produced.
  - Session status is set to COMPLETE after a successful export.
"""

import logging

from django.core.files.storage import default_storage
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET

from resume_sessions.models import ResumeSession

from .services import ExportError, ExportService

_logger = logging.getLogger(__name__)
_RESUME_FILENAME = "tailored-resume.pdf"
_COVER_LETTER_FILENAME = "cover-letter.pdf"



def _load_source_pdf(session: ResumeSession) -> bytes | None:
    """Attempt to load the source PDF bytes from storage.

    Returns None silently when the file is not accessible (e.g. storage not yet
    populated), allowing the export service to fall back to a plain-text PDF.
    """
    path = session.source_pdf_path
    if not path:
        return None
    try:
        with default_storage.open(path, "rb") as fh:
            return fh.read()
    except (FileNotFoundError, OSError):
        return None


@require_GET
def export_resume(request, session_id):
    """Serve tailored-resume.pdf for the given session.

    Available for both resume_only and resume_and_cover_letter sessions.
    """
    session = get_object_or_404(ResumeSession, pk=session_id)
    sections = list(session.sections.order_by("order_index"))

    source_bytes = _load_source_pdf(session)
    service = ExportService()
    try:
        pdf_bytes = service.build_resume_pdf(session, sections, source_bytes)
    except ExportError as exc:
        _logger.exception("Resume PDF export failed for session %s: %s", session_id, exc)
        return HttpResponse(
            "Resume PDF export failed. Please try again.",
            status=500,
            content_type="text/plain",
        )

    session.status = ResumeSession.Status.COMPLETE
    session.save(update_fields=["status", "updated_at"])

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="{_RESUME_FILENAME}"'
    )
    response["Content-Length"] = len(pdf_bytes)
    return response


@require_GET
def export_cover_letter(request, session_id):
    """Serve cover-letter.pdf for the given session.

    Only available when generation_mode == resume_and_cover_letter.
    Returns 404 for resume_only sessions (no cover letter artifact exists).
    """
    session = get_object_or_404(ResumeSession, pk=session_id)

    if session.generation_mode != ResumeSession.GenerationMode.RESUME_AND_COVER_LETTER:
        raise Http404(
            "Cover letter PDF is not available for resume-only sessions."
        )

    draft = getattr(session, "cover_letter_draft", None)
    if draft is None:
        raise Http404("No cover letter draft found for this session.")

    service = ExportService()
    try:
        pdf_bytes = service.build_cover_letter_pdf(draft)
    except ExportError as exc:
        _logger.exception(
            "Cover letter PDF export failed for session %s: %s", session_id, exc
        )
        return HttpResponse(
            "Cover letter PDF export failed. Please try again.",
            status=500,
            content_type="text/plain",
        )

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="{_COVER_LETTER_FILENAME}"'
    )
    response["Content-Length"] = len(pdf_bytes)
    return response
