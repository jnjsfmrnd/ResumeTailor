"""Celery tasks for document ingestion."""

import logging

from celery import shared_task
from django.db import transaction

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

    Duplicate delivery safety: the task acquires a row-level lock and checks
    the current status before proceeding so that a second concurrent delivery
    is a no-op instead of causing uniqueness-constraint violations.

    Handoff to generation lane:
    - app_key sessions: dispatches ``generation.run_generation`` Celery task.
    - user_key sessions: generation cannot be run asynchronously (user_key is
      never persisted). The upload view handles user_key sessions synchronously
      and does not dispatch this task for them.
    """
    try:
        with transaction.atomic():
            session = ResumeSession.objects.select_for_update().get(pk=session_id)
            if session.status not in (
                ResumeSession.Status.PENDING,
                ResumeSession.Status.INGESTING,
            ):
                logger.info(
                    "ingest_resume_task: session %s already in status '%s', skipping",
                    session_id,
                    session.status,
                )
                return
            session.status = ResumeSession.Status.INGESTING
            session.save(update_fields=["status", "updated_at"])
    except ResumeSession.DoesNotExist:
        logger.error("ingest_resume_task: session %s not found", session_id)
        return

    try:
        from django.core.files.storage import default_storage

        try:
            pdf_path = default_storage.path(session.source_pdf_path)
            sections = ingest_resume(session, pdf_path)
        except NotImplementedError:
            # Cloud storage backends (e.g. Azure) don't support local path
            # resolution. Download the file to a temporary location so that
            # fitz can open it via a real filesystem path.
            import os
            import tempfile

            tmp_fd, tmp_path = tempfile.mkstemp(suffix=".pdf")
            try:
                with os.fdopen(tmp_fd, "wb") as f:
                    with default_storage.open(session.source_pdf_path, "rb") as src:
                        f.write(src.read())
                sections = ingest_resume(session, tmp_path)
            finally:
                os.unlink(tmp_path)
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

    # ── dispatch generation (app_key only) ───────────────────────────────
    # user_key sessions are handled synchronously in the upload view because
    # the raw key must never be written to the Celery broker (Redis).
    if session.credential_mode == ResumeSession.CredentialMode.APP_KEY:
        from generation.tasks import run_generation  # local import avoids circular import

        section_inputs = [
            {
                "section_key": s.section_key,
                "order_index": s.order_index,
                "original_content": s.original_content,
            }
            for s in sections
        ]
        run_generation.delay(
            session_id=str(session.id),
            model_name=session.selected_model,
            section_inputs=section_inputs,
            job_description=session.job_description,
            generation_mode=session.generation_mode,
        )
        logger.info(
            "ingest_resume_task: dispatched run_generation for session %s",
            session_id,
        )
