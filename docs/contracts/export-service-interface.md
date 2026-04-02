# Contract: Export Service Interface

**Version**: v1.0.0
**Status**: Frozen
**Owner**: Engineer D
**Approved By**: Platform Lead
**Date**: 2026-04-01

## Purpose

Defines the interface for the export service, which converts approved session content into downloadable PDF artifacts. This contract governs how the review lane hands off to export and what download actions are exposed.

## Service Interface

### `ExportService.export(request: ExportRequest) → ExportResult`

#### ExportRequest

| Field | Type | Required | Notes |
|---|---|---|---|
| `session_id` | UUID (string) | Yes | Session to export. |
| `generation_mode` | enum | Yes | `resume_only` or `resume_and_cover_letter`. Determines number of output files. |
| `resolved_sections` | list[ResolvedSection] | Yes | Ordered list of sections with resolved content (see [Resolved Content](#resolved-content)). |
| `cover_letter` | ResolvedCoverLetter | No | Required when `generation_mode = resume_and_cover_letter`. Must be absent for `resume_only`. |

#### ResolvedSection

| Field | Type | Required | Notes |
|---|---|---|---|
| `section_key` | string | Yes | |
| `order_index` | integer | Yes | |
| `page_number` | integer | Yes | |
| `bounding_box` | BoundingBox | Yes | From the section-output-schema. |
| `resolved_content` | string | Yes | Final content after applying the resolved content precedence rule. |
| `has_overflow_risk` | boolean | Yes | True if the resolved content may exceed the bounding box. |

#### ResolvedCoverLetter

| Field | Type | Required | Notes |
|---|---|---|---|
| `resolved_content` | string | Yes | Final cover letter text after applying the resolved content precedence rule. |

#### ExportResult

| Field | Type | Required | Notes |
|---|---|---|---|
| `status` | enum | Yes | See [Export Status Values](#export-status-values). |
| `artifacts` | list[ExportArtifact] | Yes | One or two artifacts depending on `generation_mode`. |
| `overflow_blocked_sections` | list[string] | No | Section keys that blocked export due to overflow. Empty on success. |

#### ExportArtifact

| Field | Type | Required | Notes |
|---|---|---|---|
| `filename` | string | Yes | Must be exactly `tailored-resume.pdf` or `cover-letter.pdf`. No other filenames are valid. |
| `storage_path` | string | Yes | Storage path where the exported PDF was written. |
| `size_bytes` | integer | Yes | File size in bytes. |

### Export Status Values

| Value | Description |
|---|---|
| `success` | All artifacts produced and stored successfully. |
| `overflow_blocked` | One or more sections exceeded their bounding box. Export blocked; `overflow_blocked_sections` populated. |
| `failed` | Unrecoverable export error. |

## Output Rules

| Session mode | Required artifacts | Forbidden |
|---|---|---|
| `resume_only` | `tailored-resume.pdf` only | `cover-letter.pdf`, any ZIP file |
| `resume_and_cover_letter` | `tailored-resume.pdf` and `cover-letter.pdf` as separate downloads | Any ZIP file |

**No ZIP packaging is produced under any circumstance.**

## Overflow Policy

- If any section's `has_overflow_risk` is `true`, the export service must flag the section before writing.
- Export must be blocked (status `overflow_blocked`) if any flagged section cannot be safely fit into its bounding box.
- The user must resolve overflowing sections before export can proceed.
- The overflow warning must be visible on the review page before the user initiates export.

## Resolved Content Rule (reference)

Resolved content is determined by section-output-schema precedence:

1. `user_edited_content` — if present and non-empty.
2. `tailored_content` — else if present and non-empty.
3. `original_content` — fallback.

The export service receives already-resolved content in `resolved_content`; it does not re-apply this rule.

## Constraints

- Download filenames must match the exact values listed above.
- Session `status` must be set to `complete` after successful export.
- Session `output_pdf_path` must be updated with the storage path(s) of produced artifacts.
- Export artifacts must be encrypted at rest.

## Change Log

| Version | Date | Change | Author |
|---|---|---|---|
| v1.0.0 | 2026-04-01 | Initial freeze | Platform Lead |
