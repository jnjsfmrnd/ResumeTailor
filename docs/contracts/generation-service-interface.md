# Contract: Generation Service Interface

**Version**: v1.0.0
**Status**: Frozen
**Owner**: Engineer C
**Approved By**: Platform Lead
**Date**: 2026-04-01

## Purpose

Defines the interface between the session/upload lane and the generation lane, and between the generation lane and the review/export lane. Engineer C implements this interface; Engineers A and D consume it.

## GenerationRun Record

Persisted for every generation attempt. Used for audit, evaluation, and failure diagnosis.

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | UUID (string) | Yes | Primary identifier. |
| `session_id` | UUID (string) | Yes | Foreign key to the owning `ResumeSession`. |
| `model_name` | string | Yes | Concrete GitHub Models identifier used (e.g. `gpt-5.1`). |
| `credential_mode` | enum | Yes | `app_key` or `user_key`. |
| `prompt_version` | string | Yes | Semver identifier of the prompt template used. |
| `status` | enum | Yes | See [Run Status Values](#run-status-values). |
| `error_code` | string | No | See [Error Codes](#error-codes). Null on success. |
| `error_summary` | string | No | Human-readable error description. Must not include resume text, cover letter text, or job description text. |
| `started_at` | ISO 8601 datetime | Yes | UTC timestamp when generation began. |
| `completed_at` | ISO 8601 datetime | No | UTC timestamp when generation ended. Null if still in progress. |
| `duration_ms` | integer | No | Wall-clock duration in milliseconds. Null if not yet complete. |

### Run Status Values

| Value | Description |
|---|---|
| `pending` | Run queued; not yet started. |
| `running` | Generation actively in progress. |
| `succeeded` | Generation completed successfully. |
| `failed` | Generation failed; see `error_code` and `error_summary`. |
| `timed_out` | Generation exceeded the allowed time limit. |

### Error Codes

| Code | Trigger condition | User-facing message |
|---|---|---|
| `timeout_user_key` | Generation timed out with `credential_mode = user_key` | `Request timed out. Check your API key and retry.` |
| `timeout_app_key` | Generation timed out with `credential_mode = app_key` | `Request timed out. Retry the request.` |
| `unsupported_pdf` | Source PDF is image-only or unreadable | Clear rejection message per UX-0001. |
| `structured_output_invalid` | Model output failed schema validation | Internal; not surfaced directly to user. |
| `model_unavailable` | Selected model is not reachable on GitHub Models | Internal; retry logic applies. |

## Service Interface

### `GenerationService.run(request: GenerationRequest) → GenerationResult`

#### GenerationRequest

| Field | Type | Required | Notes |
|---|---|---|---|
| `session_id` | UUID (string) | Yes | Session to generate for. |
| `credential_mode` | enum | Yes | `app_key` or `user_key`. |
| `model_name` | string | Yes | One of the curated top-5 GitHub Models shortlist identifiers. |
| `user_key` | string | No | Present only when `credential_mode = user_key`. Kept in memory; never persisted. |
| `sections` | list[SectionInput] | Yes | Ordered list of parsed resume sections (from section-output-schema). |
| `job_description` | string | Yes | Raw pasted job description text. |
| `generation_mode` | enum | Yes | `resume_only` or `resume_and_cover_letter`. |

#### SectionInput (subset of ResumeSection for generation)

| Field | Type | Required | Notes |
|---|---|---|---|
| `section_key` | string | Yes | |
| `order_index` | integer | Yes | |
| `original_content` | string | Yes | |

#### GenerationResult

| Field | Type | Required | Notes |
|---|---|---|---|
| `run_id` | UUID (string) | Yes | ID of the persisted `GenerationRun`. |
| `status` | enum | Yes | Final run status. |
| `tailored_sections` | list[SectionOutput] | No | Present on success. Empty on failure. |
| `cover_letter_draft` | CoverLetterDraftOutput | No | Present only when `generation_mode = resume_and_cover_letter` and generation succeeded. |
| `error_code` | string | No | Populated on failure or timeout. |

#### SectionOutput

| Field | Type | Required | Notes |
|---|---|---|---|
| `section_key` | string | Yes | Must match the input `section_key`. |
| `tailored_content` | string | Yes | Tailored text. Must be grounded in `original_content` and `job_description`. No invented facts. |

#### CoverLetterDraftOutput

| Field | Type | Required | Notes |
|---|---|---|---|
| `original_grounding_summary` | string | Yes | |
| `tailored_content` | string | Yes | |

## Curated Model Shortlist

Only the following model identifiers are valid values for `model_name` in V1:

1. `gpt-5.1`
2. `claude-sonnet-4`
3. `o3`
4. `gpt-4.1`
5. `llama-4-maverick`

The default model is `gpt-5.1`. Any shortlist change requires a MINOR version bump.

## Constraints

- `user_key` must never be written to persistent storage, logs, or traces.
- `error_summary` must never contain resume text, cover letter text, or job description text.
- Timeout threshold is configurable per deployment. QA default: 120 seconds.
- All generated `tailored_content` must be grounded only in `original_content` and `job_description`.

## Change Log

| Version | Date | Change | Author |
|---|---|---|---|
| v1.0.0 | 2026-04-01 | Initial freeze | Platform Lead |
