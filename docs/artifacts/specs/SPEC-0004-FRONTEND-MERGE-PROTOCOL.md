# SPEC-0004: Frontend Merge Protocol

**Status**: Planning Approved
**Date**: 2026-04-02
**Scope**: Required merge and integration protocol for the frontend implementation pass
**Related Execution Board**: [SPEC-0003-FRONTEND-EXECUTION-BOARD.md](SPEC-0003-FRONTEND-EXECUTION-BOARD.md)
**Related Frontend Plan**: [SPEC-0002-FRONTEND-UX-PLAN.md](SPEC-0002-FRONTEND-UX-PLAN.md)

## 1. Purpose

Define the exact order, ownership, and acceptance gates for merging the parallel frontend workstreams into one coordinated implementation pass.

## 2. Protocol Status

This protocol is mandatory for the frontend implementation pass when implementation is authorized.

1. No agent may bypass this merge order without Platform Lead approval.
2. No frontend lane may merge directly to the final integration target unless its upstream dependency gate is passed.
3. Setup workspace creation and review workspace asset migration are treated as one coordinated release unit.

## 3. Integration Ownership

1. Platform Lead owns merge sequencing and approval to advance between merge stages.
2. AgentX Auto owns orchestration and task-pull routing between stages.
3. Engineer D is the technical integration pivot for shared frontend assets.
4. Tester, Reviewer, Engineer E, and Engineer F are required gate approvers before final integration is complete.

## 4. Merge Model

Use a controlled integration stack, not ad hoc independent merges.

### Stage 1: Shared Foundation

Owner: Engineer D

Contents:

1. Shared base layout
2. Shared CSS token file
3. Shared frontend component stylesheet
4. Shared JS extraction plan or stubs needed by both screens

Acceptance Gate:

1. Platform Lead confirms the shared asset structure is stable.
2. Tester confirms no obvious regression in the existing review surface if partial rendering is exercised.
3. Engineer F confirms no runtime-path or static-path assumption is broken.

Rule:

1. No setup-screen UI merge may proceed until Stage 1 is accepted.

### Stage 2: Setup Workspace Structure

Owner: Engineer A

Contents:

1. Setup route and view wiring
2. Upload page template structure
3. Upload control presentation
4. Validation message scaffolding
5. Session bootstrap and redirect skeleton

Acceptance Gate:

1. Platform Lead confirms route naming matches SPEC-0002.
2. Engineer D confirms Stage 2 uses shared assets instead of isolated styles.
3. Tester confirms basic setup reachability and validation states are testable.

Rule:

1. No interactive setup behavior merge may proceed until Stage 2 is accepted.

### Stage 3: Setup Workspace Interactions

Owner: Engineer C

Contents:

1. Credential mode behavior
2. Masked key field behavior
3. Curated model selector behavior
4. Loading-state behavior
5. Timeout-state behavior

Acceptance Gate:

1. Platform Lead confirms scope is still within setup interactions only.
2. Tester confirms critical state coverage is now reachable.
3. Reviewer confirms timeout and security copy match the spec.

Rule:

1. Review workspace migration must rebase onto the accepted Stage 3 result, not an earlier snapshot.

### Stage 4: Review Workspace Migration

Owner: Engineer D

Contents:

1. Move review page inline CSS to shared assets.
2. Move review page inline JS to shared assets.
3. Align review surface visually with setup surface.
4. Preserve autosave, overflow warning, and export behavior.

Acceptance Gate:

1. Tester confirms review functionality is not regressed.
2. Reviewer confirms setup and review now share the same asset system.
3. Engineer F confirms the shared asset migration introduces no runtime-path regression.

Rule:

1. Frontend pass is not considered integration-complete until Stage 4 is accepted.

### Stage 5: QA and Runtime Validation

Owners: Engineer E and Engineer F

Contents:

1. QA/static asset validation
2. Smoke checks for setup and review reachability
3. Runtime and deployment consistency verification

Acceptance Gate:

1. Engineer E provides QA evidence.
2. Engineer F provides runtime consistency evidence.
3. Tester confirms no blocking functional, accessibility, or responsive defect remains.

Rule:

1. No final approval is possible until Stage 5 is accepted.

### Stage 6: Final Review and Merge Approval

Owners: Reviewer and Platform Lead

Contents:

1. Final regression review
2. Spec alignment review
3. Confirmation that the coordinated release unit is complete

Acceptance Gate:

1. Reviewer reports no unresolved High or Medium findings.
2. Platform Lead confirms all prior stages are accepted.
3. AgentX Auto confirms no unmerged required task remains open.

## 5. Rebase and Update Rules

1. Every downstream stage rebases onto the latest accepted upstream stage.
2. No stage may continue building on a stale foundation once an upstream stage changes.
3. If Stage 1 changes materially, Stages 2 through 4 must refresh before seeking acceptance.
4. If Stage 3 changes interaction contracts, Stage 4 must re-verify review asset integration before acceptance.

## 6. Stop and Escalate Conditions

Stop the merge pipeline and escalate to Platform Lead if any of the following occur:

1. A lane introduces new pages or new workflow steps.
2. A lane adds isolated styles or scripts that bypass the shared asset system.
3. Review migration is proposed as a later follow-up instead of the same coordinated pass.
4. QA reveals deployment-specific static asset issues that require architecture changes.
5. Timeout or security copy diverges from SPEC-0002.

## 7. Implementation Promise

When implementation is authorized, this merge protocol becomes the required integration contract for the frontend pass.
