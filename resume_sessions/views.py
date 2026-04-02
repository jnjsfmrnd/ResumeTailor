"""Views for the review and edit workspace (D1).

Contracts consumed:
  - session-schema v1.0.0
  - section-output-schema v1.0.0
  - cover-letter-draft-schema v1.0.0
"""

import json

from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_POST

from .models import CoverLetterDraft, ResumeSection, ResumeSession

# Rough estimate of PDF points used per character at 10pt in a typical font.
_POINTS_PER_CHAR = 6.0
# Rough estimate of PDF points per line at 10pt with standard line spacing.
_POINTS_PER_LINE = 14.0


def _overflow_risk(section: ResumeSection) -> bool:
    """Return True if resolved_content likely exceeds the section bounding box.

    Uses a conservative character-density heuristic.  A section is flagged when
    the estimated line count for the resolved text exceeds the lines that fit in
    the bounding box height.
    """
    width = section.bbox_x1 - section.bbox_x0
    height = section.bbox_y1 - section.bbox_y0
    if width <= 0 or height <= 0:
        return False
    chars_per_line = max(1.0, width / _POINTS_PER_CHAR)
    lines_available = height / _POINTS_PER_LINE
    content = section.resolved_content
    estimated_lines = len(content) / chars_per_line
    return estimated_lines > lines_available


@require_GET
def review_workspace(request, session_id):
    """Render the side-by-side review and edit workspace for a session."""
    session = get_object_or_404(ResumeSession, pk=session_id)
    sections = list(session.sections.order_by("order_index"))

    show_cover_letter = (
        session.generation_mode
        == ResumeSession.GenerationMode.RESUME_AND_COVER_LETTER
    )
    cover_letter = None
    if show_cover_letter:
        cover_letter = getattr(session, "cover_letter_draft", None)

    overflow_sections = []
    for section in sections:
        risk = _overflow_risk(section)
        section.has_overflow_risk = risk  # attach flag for template access
        if risk:
            overflow_sections.append(section)

    context = {
        "session": session,
        "sections": sections,
        "cover_letter": cover_letter,
        "show_cover_letter": show_cover_letter,
        "overflow_section_count": len(overflow_sections),
        "has_overflow": bool(overflow_sections),
    }
    return render(request, "resume_sessions/review.html", context)


@require_POST
def section_edit(request, session_id, section_id):
    """Persist user_edited_content for a single section (JSON API)."""
    section = get_object_or_404(ResumeSection, pk=section_id, session_id=session_id)
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON body."}, status=400)

    user_edited = data.get("user_edited_content", "")
    if not isinstance(user_edited, str):
        return JsonResponse({"error": "user_edited_content must be a string."}, status=400)

    section.user_edited_content = user_edited
    section.save(update_fields=["user_edited_content"])
    return JsonResponse(
        {
            "section_id": str(section.pk),
            "resolved_content": section.resolved_content,
        }
    )


@require_POST
def cover_letter_edit(request, session_id):
    """Persist user_edited_content for the session cover letter (JSON API)."""
    try:
        draft = CoverLetterDraft.objects.get(session_id=session_id)
    except CoverLetterDraft.DoesNotExist:
        raise Http404("No cover letter draft for this session.")

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON body."}, status=400)

    user_edited = data.get("user_edited_content", "")
    if not isinstance(user_edited, str):
        return JsonResponse({"error": "user_edited_content must be a string."}, status=400)

    draft.user_edited_content = user_edited
    draft.save(update_fields=["user_edited_content"])
    return JsonResponse(
        {
            "resolved_content": draft.resolved_content,
        }
    )
