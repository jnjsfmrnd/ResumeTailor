# SPEC-0002: Frontend UX Implementation Plan (Django Full Stack)

**Status**: Approved for Planning
**Date**: 2026-04-02
**Mode**: Plan only, no implementation in this artifact
**Related PRD**: [PRD-0001.md](../prd/PRD-0001.md)
**Related Core Spec**: [SPEC-0001.md](SPEC-0001.md)
**Related UX Spec**: [UX-0001.md](../../ux/UX-0001.md)
**Related Design Guide**: [DESIGN-GUIDE-0001.md](../../ux/DESIGN-GUIDE-0001.md)

## 1. Purpose

Define the execution-ready plan to deliver the missing user-facing frontend flow as a Django full-stack experience, while preserving existing review and export behavior.

## 2. Current State Snapshot

### Existing

1. Review and edit workspace exists and is routed.
2. Export endpoints for resume and cover letter exist.
3. Root URL includes ingestion routes.

### Missing

1. Primary upload and settings screen as a complete interactive UX surface.
2. Unified visual system across upload and review surfaces using shared tokens.
3. State-complete UX behavior for upload, credential mode, model selection, and generation start.

## 3. Scope

### In Scope

1. Screen 1: upload plus settings plus generation start.
2. Screen 2: review and edit refinements for full design consistency.
3. Shared styles and scripts under Django static assets.
4. Accessibility, responsive behavior, and state handling per UX-0001.

### Out of Scope

1. Production deployment changes.
2. New non-PDF input formats.
3. Any change to model provider boundaries.

## 4. Council Agent Execution Plan

## 4.1 Platform Lead (coordination and contract freeze)

### Actions

1. Freeze frontend contract map before implementation starts.
2. Confirm lane boundaries and shared interface ownership.
3. Enforce planning-first governance and dependency order.

### Deliverables

1. Frontend contract freeze checklist.
2. Integration gate checklist for lane handoffs.

### Exit Gate

1. No lane starts implementation before shared UI contracts and copy contracts are frozen.

## 4.2 Product Manager lens (scope and acceptance)

### Actions

1. Lock frontend V1 to two user surfaces: setup and review.
2. Freeze user-facing copy for security and timeout behavior.
3. Confirm acceptance criteria mapping to stories 1 through 6.

### Deliverables

1. Scope lock section in this spec.
2. Copy lock matrix in section 7.

### Exit Gate

1. No unresolved ambiguity in generation modes, error copy, or export behavior.

## 4.3 UX Designer lens (interaction and visual system)

### Actions

1. Convert the design guide into concrete UI states for Screen 1.
2. Keep Screen 2 behavior aligned with existing conditional logic.
3. Define keyboard and assistive technology behavior for all controls.

### Deliverables

1. State table in section 6.
2. Token usage policy in section 8.

### Exit Gate

1. Every visible state has explicit trigger, message, and recovery path.

## 4.4 Architect lens (Django full-stack structure)

### Actions

1. Define template hierarchy, view responsibilities, and URL ownership.
2. Define server-rendered initial state plus client-side enhancement boundaries.
3. Define sensitive data handling boundaries in request and logging paths.

### Deliverables

1. File blueprint in section 5.
2. Data flow and security constraints in section 9.

### Exit Gate

1. All frontend behavior traces to existing domain contracts without new API ambiguity.

## 4.5 Engineer lanes

### Engineer A (upload/session)

1. Build upload and validation UI behavior.
2. Wire session bootstrap outcomes to next-step UX states.

### Engineer C (credentials/model/timeouts)

1. Build credential-mode controls and conditional key field behavior.
2. Build model shortlist selector and timeout-state UX messaging.

### Engineer D (review/export)

1. Preserve existing review/edit logic.
2. Align visual and interaction language with Screen 1.
3. Keep separate resume and cover-letter download actions with no ZIP output.

### Engineer E (QA gates)

1. Ensure static asset and template changes are included in QA validation flow.
2. Add frontend checks to smoke path.

### Engineer F (runtime consistency)

1. Ensure frontend additions respect SQLite QA constraints and existing deployment profile.
2. Validate no environment-specific regressions in template and static handling.

### Exit Gate

1. All lane changes satisfy shared acceptance criteria and pass reviewer gate.

## 4.6 Data Scientist lens (evaluation observability)

### Actions

1. Define non-sensitive UX quality signals for generation path.
2. Ensure no sensitive content leakage in telemetry.

### Deliverables

1. UX instrumentation checklist in section 10.

### Exit Gate

1. Metrics are actionable and compliant with no-content-logging policy.

## 4.7 Tester lens (verification plan)

### Actions

1. Produce scenario matrix for happy path and failure path coverage.
2. Validate accessibility and responsive behavior.

### Deliverables

1. Test matrix in section 11.

### Exit Gate

1. Every required UX state is covered by at least one deterministic test.

## 4.8 Reviewer lens (decision gate)

### Actions

1. Audit scope consistency against PRD, SPEC-0001, UX-0001.
2. Audit risk posture and missing evidence.

### Deliverables

1. Council review memo in docs/artifacts/reviews/REVIEW-0004-FRONTEND-COUNCIL.md.

### Exit Gate

1. No High severity planning gaps remain.

## 5. File-Level Blueprint (Implementation Target)

Planned target files for implementation phase:

1. `document_ingestion/views.py` (render setup workspace + input validation messaging)
2. `document_ingestion/urls.py` (lock setup route naming as `document_ingestion:upload` at `/upload/` and add optional root redirect only if needed)
3. `templates/document_ingestion/upload.html` (new Screen 1 template)
4. `templates/base.html` (new shared base layout)
5. `templates/partials/_status_banner.html` (new reusable state banner)
6. `templates/resume_sessions/review.html` (migrate inline style/script into shared assets in the same change set as Screen 1)
7. `static/css/design-tokens.css` (new canonical token file from design guide)
8. `static/css/app.css` (new shared component styles for both setup and review screens)
9. `static/js/review-editor.js` (new extracted autosave logic)
10. `static/js/upload-workspace.js` (new setup interactions)

No file changes are executed by this planning artifact.

### Route Naming Lock

1. Canonical setup page route name: `document_ingestion:upload`
2. Canonical setup page path: `/upload/`
3. Root path behavior: keep root routed through ingestion ownership; implementation may redirect `/` to `/upload/` but must preserve one canonical named route.
4. Canonical review page route name remains `resume_sessions:review`.

### Coordinated Change Rule

1. Screen 1 implementation and Screen 2 asset extraction must land in the same implementation pass.
2. No partial pass may leave Screen 1 on shared assets while Screen 2 still uses inline CSS/JS.
3. Shared design tokens must be the only source of color values for both screens after the pass.

## 6. Screen 1 State Table

| State | Trigger | UX Behavior | Recovery |
|------|---------|-------------|----------|
| Default | Initial load | Upload dropzone, JD input, credential and model controls visible | User proceeds by filling required fields |
| Drag active | File dragged over dropzone | Border and background highlight, helper text update | Drop file or leave dropzone |
| Invalid file type | Non-PDF file selected | Inline error near upload control | Select a PDF |
| Unsupported PDF | Image-only or unsupported PDF | Inline error with clear reason | Upload a supported digital PDF |
| User key mode | Credential toggle to user key | Masked key field and security copy shown | Enter valid key or switch mode |
| App key mode | Credential toggle to app key | Key field hidden, app-key notice shown | Continue |
| Model selection invalid | Model outside curated list | Selector validation error | Choose curated model |
| Start generation pending | Start Tailoring clicked | Button loading state and progress feedback | Await completion |
| Timeout user key | User-key request timed out | Exact copy: Request timed out. Check your API key and retry. | Retry with corrected key |
| Timeout app key | App-key request timed out | Exact copy: Request timed out. Retry the request. | Retry |

## 7. Copy Lock Matrix

1. User key security copy: Your key is used only for this request and is not saved.
2. Timeout copy (user key): Request timed out. Check your API key and retry.
3. Timeout copy (app key): Request timed out. Retry the request.
4. Generation mode labels:
   - Resume only
   - Resume and cover letter
5. Export action labels:
   - Download resume PDF
   - Download cover letter PDF

## 8. Design System Plan

1. Move all color and shape values to CSS custom properties from DESIGN-GUIDE-0001.
2. Keep Indigo as primary and Spice Orange as accent; do not add additional accent colors.
3. Use GameCube motifs in surface and component treatment:
   - Handle-like panel cutouts in header and control grouping
   - Subtle circular vent pattern backgrounds
   - Beveled cards with layered shadows
   - Glossy gradient primary CTA
4. Preserve functional mobile fallback (single-column stacked workflow).
5. Icon source lock: use one consistent icon set with geometric strokes; all icons must render inside a circle or rounded-square container.
6. Loading pattern lock: use the spinning disc as the primary generation-state animation and reserve the red Power LED pulse for secondary background-task indicators only.

### Ownership Notes

1. Engineer C owns loading-state behavior and timeout-state UX implementation.
2. UX signoff is required on the spinning-disc loading treatment before merge.
3. Engineer D owns applying the icon-container rule consistently on review and export controls.

## 9. Data and Security Constraints for Frontend

1. Never persist user-supplied key in database, session storage, or logs.
2. Do not log resume, cover-letter, or job-description text in frontend error telemetry.
3. Keep CSRF-safe POST behavior for edit and generation actions.
4. Maintain credential-mode-specific timeout messaging.

## 10. UX Instrumentation Checklist (Non-Sensitive)

1. Time from setup page load to generation start.
2. Generation completion time by credential mode and model identifier.
3. Failure counts by state category (validation, timeout, unsupported PDF).
4. Review save failure counts without content payload capture.

## 11. Test Matrix Summary

1. Functional tests:
   - Upload success, invalid file, unsupported PDF
   - Credential toggle behavior
   - Model shortlist enforcement
   - Generation mode conditional behavior
   - Review autosave and export action visibility
2. Accessibility tests:
   - Keyboard focus order
   - Labels and aria announcements for validation and save states
   - Contrast checks for critical controls and warnings
3. Responsive tests:
   - Desktop two-column review layout
   - Tablet/mobile stacked layout with full functionality

## 12. Implementation Readiness Gate

Ready when all checks pass:

1. Scope lock complete.
2. State table complete.
3. File blueprint accepted by platform lead.
4. Copy lock complete.
5. Tester matrix accepted.
6. Reviewer decision is Approved with no High findings.
