# Contract: Session Schema

**Version**: v1.0.0
**Status**: Frozen
**Owner**: Engineer A
**Approved By**: Platform Lead
**Date**: 2026-04-01

## Purpose

Defines the canonical shape of a `ResumeSession`. All lanes that create, read, or update session state must conform to this schema.

## Schema

### ResumeSession

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | UUID (string) | Yes | Primary identifier, generated on session creation. |
| `status` | enum | Yes | See [Status Values](#status-values). |
| `source_pdf_path` | string | Yes | Storage path to the uploaded source PDF. |
| `output_pdf_path` | string | No | Storage path(s) for exported PDF(s). Null until export completes. |
| `output_artifact_type` | enum | Yes | `single_pdf` or `dual_pdf`. Derived from `generation_mode`. |
| `generation_mode` | enum | Yes | `resume_only` or `resume_and_cover_letter`. |
| `credential_mode` | enum | Yes | `app_key` or `user_key`. |
| `selected_model` | string | Yes | One of the curated top-5 GitHub Models shortlist identifiers. |
| `job_description` | string | Yes | Raw pasted job description text. |
| `created_at` | ISO 8601 datetime | Yes | UTC timestamp of session creation. |
| `updated_at` | ISO 8601 datetime | Yes | UTC timestamp of last state change. |

### Status Values

| Value | Description |
|---|---|
| `pending` | Session created; upload not yet confirmed. |
| `ingesting` | PDF is being parsed into sections. |
| `generating` | Tailored content is being generated. |
| `review` | Generation complete; awaiting user review and edits. |
| `exporting` | Export is in progress. |
| `complete` | Export succeeded; output PDFs are ready. |
| `failed` | Unrecoverable error; see associated `GenerationRun` for details. |

### Generation Mode to Artifact Type Mapping

| `generation_mode` | `output_artifact_type` | Export behavior |
|---|---|---|
| `resume_only` | `single_pdf` | One download: `tailored-resume.pdf` |
| `resume_and_cover_letter` | `dual_pdf` | Two separate downloads: `tailored-resume.pdf` and `cover-letter.pdf` |

## Invariants

- `output_artifact_type` must be derived from `generation_mode` and must never contradict it.
- A session in `resume_only` mode must never have an associated `CoverLetterDraft`.
- No raw or encrypted user-supplied key material may be stored on the session.
- `credential_mode = user_key` means the key is passed in-memory for the active request only.

## Change Log

| Version | Date | Change | Author |
|---|---|---|---|
| v1.0.0 | 2026-04-01 | Initial freeze | Platform Lead |
