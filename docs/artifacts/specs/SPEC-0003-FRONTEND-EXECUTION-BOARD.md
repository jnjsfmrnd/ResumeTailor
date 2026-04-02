# SPEC-0003: Frontend Execution Board Per Agent

**Status**: Planning Approved
**Date**: 2026-04-02
**Scope**: Frontend UX implementation scheduling and ownership
**Related Plan**: [SPEC-0002-FRONTEND-UX-PLAN.md](SPEC-0002-FRONTEND-UX-PLAN.md)
**Related Review**: [REVIEW-0005-AGENTX-FRONTEND-COUNCIL.md](../reviews/REVIEW-0005-AGENTX-FRONTEND-COUNCIL.md)
**Related Merge Protocol**: [SPEC-0004-FRONTEND-MERGE-PROTOCOL.md](SPEC-0004-FRONTEND-MERGE-PROTOCOL.md)

## 1. Objective

Define the fastest safe execution plan for the frontend implementation with clear ownership, dependencies, and completion gates per agent.

## 2. Global Rules

1. Scope stays locked to two primary surfaces: setup workspace and review workspace.
2. Setup workspace implementation and review workspace asset refactor must land in the same implementation pass.
3. No agent may introduce new workflow steps, new pages, or new provider scope.
4. Shared design tokens are the single source of truth for color and shape styling.
5. All blocking issues are fixed before handoff; non-blocking polish is deferred.
6. Merge sequencing must follow SPEC-0004.

## 3. Sequencing Overview

### Phase 0: Kickoff Lock

1. Platform Lead locks route naming, icon set, loader baseline, and merge order.
2. Tester prepares acceptance checklist from the frontend state table.
3. Engineer E prepares QA and smoke-check update plan.

### Phase 1: Shared Foundation and Setup Workspace

1. Engineer D builds shared base layout and style system.
2. Engineer A builds setup route, view, and server-rendered template structure.
3. Engineer C builds credential, model, and loading behavior on the setup workspace.

### Phase 2: Review Workspace Integration

1. Engineer D migrates review workspace onto shared assets.
2. Engineer A connects setup completion to session bootstrap and review redirect.
3. Engineer C validates timeout and security copy behavior.
4. Engineer F validates runtime and deployment consistency are not regressed.

### Phase 3: QA and Final Review

1. Engineer E runs QA validation and smoke updates.
2. Tester executes workflow, accessibility, and responsive checks.
3. Reviewer performs focused regression and spec-alignment review.

## 4. Plan Per Agent

## 4.1 Platform Lead

### Mission

Keep the pass fast by preventing scope drift and forcing integration discipline.

### Tasks

1. Freeze kickoff choices before code starts:
   - canonical route name
   - icon library
   - loading animation baseline
   - merge order
2. Confirm each engineer is working against SPEC-0002 and SPEC-0003 only.
3. Run two integration checkpoints per day.
4. Block any work that introduces non-scoped UI changes.

### Dependencies

1. Existing planning artifacts only.

### Deliverables

1. Kickoff lock note.
2. Daily integration status.
3. Blocker list with owner and ETA.

### Done Gate

1. No unresolved cross-lane ambiguity remains.
2. No scope creep enters the implementation pass.

## 4.2 Engineer A

### Mission

Build the setup workspace shell and the upload-to-session entry flow.

### Tasks

1. Implement the setup route and server-rendered page structure.
2. Build upload dropzone and file-picker presentation.
3. Add validation display for invalid file and unsupported PDF states.
4. Wire successful setup submission to session bootstrap.
5. Redirect completed setup flow to the review workspace.

### Dependencies

1. Platform Lead kickoff lock.
2. Shared base layout from Engineer D.

### Deliverables

1. Setup page route and template.
2. Upload and validation workflow.
3. Session bootstrap handoff into review flow.

### Done Gate

1. User can reach review after valid setup submission.
2. Invalid and unsupported files show recoverable inline messages.

## 4.3 Engineer B

### Mission

Support the frontend pass only where PDF validation details affect user-facing upload behavior.

### Tasks

1. Confirm supported-PDF and image-only rejection reasons are stable.
2. Provide deterministic rejection mapping for setup-page error copy.
3. Support Engineer A if upload validation edge cases block progress.

### Dependencies

1. Existing ingestion contracts.

### Deliverables

1. Stable rejection reason mapping.
2. Support notes for upload validation edge cases.

### Done Gate

1. Upload rejection reasons match the UX copy and are deterministic.

## 4.4 Engineer C

### Mission

Own the smart setup controls: credential mode, model choice, loading state, and timeout UX.

### Tasks

1. Implement credential mode toggle behavior.
2. Implement masked user-key field behavior and security copy state.
3. Implement curated top-5 model selector behavior.
4. Implement Start Tailoring loading state using the spinning-disc pattern.
5. Implement exact timeout messaging by credential mode.

### Dependencies

1. Platform Lead kickoff lock.
2. Setup template structure from Engineer A.
3. Shared UI assets from Engineer D.

### Deliverables

1. Credential-mode interaction logic.
2. Model selector behavior.
3. Loading and timeout behavior.

### Done Gate

1. User-key and app-key modes behave differently and correctly.
2. Timeout copy exactly matches the spec.
3. No user-key material is persisted or exposed.

## 4.5 Engineer D

### Mission

Provide the shared visual system and align the review workspace to it.

### Tasks

1. Create shared base layout and shared CSS token file.
2. Create shared component stylesheet for setup and review surfaces.
3. Extract review-page inline CSS and JS into shared assets.
4. Keep review/edit behavior intact while aligning the visual language.
5. Apply icon-container and export-control styling consistently.

### Dependencies

1. Platform Lead kickoff lock.

### Deliverables

1. Shared frontend asset foundation.
2. Refactored review workspace using shared assets.
3. Consistent GameCube-inspired visual treatment across both screens.

### Done Gate

1. Setup and review surfaces use the same shared assets.
2. Review functionality is not regressed.

## 4.6 Engineer E

### Mission

Prevent the frontend pass from stalling at QA.

### Tasks

1. Update QA validation plan to include templates and static assets.
2. Update smoke-check path for frontend reachability and critical flows.
3. Validate static asset handling in the QA deployment shape.
4. Collect evidence that the frontend pass remains within V1 deployment boundaries.

### Dependencies

1. Shared assets from Engineer D.
2. Setup and review flow completion from Engineers A and C.

### Deliverables

1. QA validation updates.
2. Smoke evidence for core frontend flow.

### Done Gate

1. QA can serve the new frontend assets correctly.
2. Smoke checks cover setup and review reachability.

## 4.7 Engineer F

### Mission

Make sure the frontend pass does not destabilize the runtime and deployment contract.

### Tasks

1. Validate that static and template changes do not introduce runtime-path regressions.
2. Confirm SQLite and QA operating assumptions remain untouched.
3. Confirm Docker, CI, and deployment paths do not require unplanned changes.
4. Flag any coupling between frontend asset changes and runtime configuration.

### Dependencies

1. Shared asset structure from Engineer D.
2. QA validation shape from Engineer E.

### Deliverables

1. Runtime consistency validation note.
2. Deployment-impact check.

### Done Gate

1. No runtime, CI, or QA contract regression is introduced by the frontend pass.

## 4.8 Tester

### Mission

Test in parallel so regressions are found before the pass piles up.

### Tasks

1. Convert the Screen 1 state table into executable checks.
2. Validate setup flow, review flow, and export visibility.
3. Validate keyboard access and screen-reader-friendly error states.
4. Validate tablet and mobile stacked behavior.

### Dependencies

1. SPEC-0002 state table.
2. Incremental feature availability from Engineers A, C, and D.

### Deliverables

1. Acceptance checklist.
2. Defect list ordered by severity.

### Done Gate

1. All critical states are tested.
2. No blocking accessibility or responsive defect remains.

## 4.9 Reviewer

### Mission

Deliver one focused pass on correctness, regression risk, and spec alignment.

### Tasks

1. Review the final integrated frontend pass.
2. Check scope discipline against SPEC-0002.
3. Check for regressions in review and export behavior.
4. Check that shared assets replaced review-page inline assets.

### Dependencies

1. Integrated implementation pass.
2. Tester evidence.
3. QA evidence from Engineer E.

### Deliverables

1. Final review findings.
2. Approval or rejection decision.

### Done Gate

1. No High or Medium findings remain unresolved.

## 5. Fastest Execution Path

1. Start with Platform Lead, Engineer D, and Tester as the initial unblocked pull sequence.
2. Bring Engineer A in as soon as base layout is stable.
3. Bring Engineer C in as soon as setup template structure exists.
4. Use Engineer B only to resolve upload-validation edge cases.
5. Start Engineer E and Engineer F before implementation finishes so QA and runtime checks are not delayed.

Rule:

1. This execution path is task-pull based, not day-based.

## 6. Stop Conditions

Stop and escalate if any of the following occur:

1. A new screen or workflow step is proposed.
2. Setup and review work are split into separate release passes.
3. A route or UI contract changes without Platform Lead approval.
4. QA/static asset handling requires unplanned architecture changes.
