"""Celery tasks for document ingestion."""

import logging

from celery import shared_task

from resume_sessions.models import ResumeSession

from .exceptions import UnsupportedPDFError
from .services import ingest_resume

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=0)
def ingest_resume_task(self, session_id: str) -> None:
    """Parse the session's source PDF into ResumeSection objects.

    Status transitions::

        pending  ──► ingesting  ──► generating   (success)
                                └──► failed       (UnsupportedPDFError or unexpected error)

    The task does not retry on failure: unsupported PDFs and unexpected
    errors both land the session in ``failed`` status immediately.
    """
    try:
        session = ResumeSession.objects.get(pk=session_id)
    except ResumeSession.DoesNotExist:
        logger.error("ingest_resume_task: session %s not found", session_id)
        return

    session.status = ResumeSession.Status.INGESTING
    session.save(update_fields=["status", "updated_at"])

    try:
        ingest_resume(session, session.source_pdf_path)
    except UnsupportedPDFError as exc:
        logger.warning(
            "ingest_resume_task: unsupported PDF for session %s: %s",
            session_id,
            exc,
        )
        session.status = ResumeSession.Status.FAILED
        session.save(update_fields=["status", "updated_at"])
        return
    except Exception:
        logger.exception(
            "ingest_resume_task: unexpected error ingesting session %s",
            session_id,
        )
        session.status = ResumeSession.Status.FAILED
        session.save(update_fields=["status", "updated_at"])
        return

    session.status = ResumeSession.Status.GENERATING
    session.save(update_fields=["status", "updated_at"])
    logger.info(
        "ingest_resume_task: session %s ingested successfully, status → generating",
        session_id,
    )
