"""Celery tasks for the generation lane.

Design note on credential modes:
  - app_key mode: the API key lives in settings; task arguments are safe to
    pass through the Celery broker.
  - user_key mode: the raw user key must NEVER be written to the broker
    (Redis) or any persistent storage. Callers must invoke
    GenerationService().run() directly (synchronously) for user_key mode.
"""

from celery import shared_task

from .service import GenerationRequest, GenerationService, SectionInput


@shared_task(bind=True, name="generation.run_generation")
def run_generation(
    self,
    session_id: str,
    model_name: str,
    section_inputs: list[dict],
    job_description: str,
    generation_mode: str,
) -> dict:
    """Async generation task for app_key credential mode only.

    Args:
        session_id: UUID string of the owning ResumeSession.
        model_name: One of the curated shortlist model identifiers.
        section_inputs: List of dicts with keys section_key, order_index,
            original_content. Serialised form of SectionInput.
        job_description: Raw job description text.
        generation_mode: "resume_only" or "resume_and_cover_letter".

    Returns:
        Dict representation of GenerationResult.
    """
    sections = [
        SectionInput(
            section_key=s["section_key"],
            order_index=s["order_index"],
            original_content=s["original_content"],
        )
        for s in section_inputs
    ]

    request = GenerationRequest(
        session_id=session_id,
        credential_mode="app_key",
        model_name=model_name,
        sections=sections,
        job_description=job_description,
        generation_mode=generation_mode,
    )

    result = GenerationService().run(request)

    return {
        "run_id": result.run_id,
        "status": result.status,
        "tailored_sections": [
            {"section_key": s.section_key, "tailored_content": s.tailored_content}
            for s in result.tailored_sections
        ],
        "cover_letter_draft": (
            {
                "original_grounding_summary": result.cover_letter_draft.original_grounding_summary,
                "tailored_content": result.cover_letter_draft.tailored_content,
            }
            if result.cover_letter_draft is not None
            else None
        ),
        "error_code": result.error_code,
    }
