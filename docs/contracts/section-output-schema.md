# Contract: Section Output Schema

**Version**: v1.0.0
**Status**: Frozen
**Owner**: Engineer B
**Approved By**: Platform Lead
**Date**: 2026-04-01

## Purpose

Defines the canonical shape of a `ResumeSection`. Engineer B produces sections during PDF ingestion; Engineers C, D, and the export lane consume them. All lanes must conform to this schema.

## Schema

### ResumeSection

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | UUID (string) | Yes | Primary identifier. |
| `session_id` | UUID (string) | Yes | Foreign key to the owning `ResumeSession`. |
| `section_key` | string | Yes | Stable label for the section (e.g. `experience`, `education`). Unique within a session. |
| `order_index` | integer | Yes | Zero-based position of this section in document order. Deterministic across runs for the same input. |
| `page_number` | integer | Yes | One-based page number where the section starts. |
| `bounding_box` | object | Yes | See [Bounding Box](#bounding-box). |
| `original_content` | string | Yes | Verbatim text extracted from the source PDF. |
| `tailored_content` | string | No | Tailored text produced by generation. Null until generation completes. |
| `user_edited_content` | string | No | Text saved by the user during review. Null if the user made no edits. |
| `review_status` | enum | Yes | See [Review Status Values](#review-status-values). |

### Bounding Box

Coordinates are in PDF user-space units (points), measured from the bottom-left origin.

| Field | Type | Required | Notes |
|---|---|---|---|
| `x0` | float | Yes | Left edge of the bounding box. |
| `y0` | float | Yes | Bottom edge of the bounding box. |
| `x1` | float | Yes | Right edge of the bounding box. |
| `y1` | float | Yes | Top edge of the bounding box. |

### Review Status Values

| Value | Description |
|---|---|
| `pending` | Generation not yet complete for this section. |
| `approved` | User has approved the resolved content. |
| `rejected` | User has rejected the tailored content; original will be used. |

## Resolved Content Rule

When producing output for export, resolved content is determined by precedence:

1. `user_edited_content` — if present and non-empty, use this.
2. `tailored_content` — else if present and non-empty, use this.
3. `original_content` — fallback; always present.

This precedence must be implemented consistently across the generation and export lanes.

## Invariants

- `order_index` values are unique within a session and form a contiguous zero-based sequence.
- `section_key` values are unique within a session.
- `bounding_box` coordinates satisfy `x0 < x1` and `y0 < y1`.
- `original_content` is never null or empty after ingestion.

## Change Log

| Version | Date | Change | Author |
|---|---|---|---|
| v1.0.0 | 2026-04-01 | Initial freeze | Platform Lead |
