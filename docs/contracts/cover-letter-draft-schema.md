# Contract: Cover Letter Draft Schema

**Version**: v1.0.0
**Status**: Frozen
**Owner**: Engineer D
**Approved By**: Platform Lead
**Date**: 2026-04-01

## Purpose

Defines the canonical shape of a `CoverLetterDraft`. This artifact is created only when the session `generation_mode` is `resume_and_cover_letter`. It must never exist for `resume_only` sessions.

## Schema

### CoverLetterDraft

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | UUID (string) | Yes | Primary identifier. |
| `session_id` | UUID (string) | Yes | Foreign key to the owning `ResumeSession`. |
| `original_grounding_summary` | string | Yes | Summary of resume content used to ground the cover letter. Not shown to the user; used internally for audit and evaluation. |
| `tailored_content` | string | Yes | Cover letter text produced by generation. |
| `user_edited_content` | string | No | Text saved by the user during review. Null if the user made no edits. |
| `review_status` | enum | Yes | See [Review Status Values](#review-status-values). |

### Review Status Values

| Value | Description |
|---|---|
| `pending` | Generation not yet complete or user review not started. |
| `approved` | User has approved the resolved content. |

## Resolved Content Rule

When producing output for export, resolved content is determined by precedence:

1. `user_edited_content` — if present and non-empty, use this.
2. `tailored_content` — fallback; always present after generation.

## Invariants

- A `CoverLetterDraft` must not exist when the session `generation_mode` is `resume_only`.
- Exactly one `CoverLetterDraft` may exist per session.
- `tailored_content` is never null or empty after generation completes.
- `original_grounding_summary` must not contain raw job description text or any PII beyond what is in the source resume.

## Export Behavior

| Session mode | Cover letter draft | Export action |
|---|---|---|
| `resume_only` | Must not exist | No cover letter download exposed |
| `resume_and_cover_letter` | Must exist and be `approved` | Separate `cover-letter.pdf` download |

No ZIP packaging is produced in any mode.

## Change Log

| Version | Date | Change | Author |
|---|---|---|---|
| v1.0.0 | 2026-04-01 | Initial freeze | Platform Lead |
