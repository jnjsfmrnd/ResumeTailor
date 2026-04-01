# Story Decomposition: ResumeTailor V1 Round 2

## Story 0: Freeze Contracts

**As a** team,
**I want** the core session, generation, and export contracts frozen first,
**So that** engineers can work in parallel without stepping on each other.

### Acceptance Criteria

- [ ] Session schema is documented.
- [ ] Section output schema is documented.
- [ ] Cover letter draft schema is documented.
- [ ] Generation and export service interfaces are documented.

## Story 1: Upload PDF and Create Session

**As a** user,
**I want** to upload a supported PDF and start a session,
**So that** tailoring begins from my existing resume.

### Acceptance Criteria

- [ ] Given a supported digital PDF, when I upload it, then the session is created.
- [ ] Given an image-only PDF, when I upload it, then the app rejects it with a clear message.

## Story 2: Choose Credential Mode and Model

**As a** user,
**I want** to choose how GitHub Models is accessed and which curated model is used,
**So that** generation is predictable.

### Acceptance Criteria

- [ ] Given the default path, when I open the form, then the app key mode is selected.
- [ ] Given a user key path, when I enter a key, then the key field is masked.
- [ ] Given model selection, then only the curated top-5 GitHub Models shortlist is shown.

## Story 3: Choose Resume Only or Resume and Cover Letter

**As a** user,
**I want** to choose whether a cover letter is generated,
**So that** I control the output files.

### Acceptance Criteria

- [ ] Given the generation options, then I can choose `Resume only` or `Resume and cover letter`.
- [ ] Given `Resume only`, then no cover letter draft is generated.
- [ ] Given `Resume and cover letter`, then a cover letter draft is generated for review.

## Story 4: Generate Tailored Content

**As a** user,
**I want** grounded tailored content,
**So that** I can adapt faster for a target role.

### Acceptance Criteria

- [ ] Given supported inputs, when generation runs, then editable tailored output is returned.
- [ ] Given a timeout while using my own key, then the app tells me to check my API key and retry.
- [ ] Given generated output, then no unsupported factual invention is accepted in blocking review.

## Story 5: Review and Edit Before Export

**As a** user,
**I want** to review and edit the generated resume and optional cover letter,
**So that** I approve the final content.

### Acceptance Criteria

- [ ] Given a generated draft, when I edit content, then my edits are preserved for export.
- [ ] Given an overflow risk, then the warning is visible before export.

## Story 6: Export PDF Files

**As a** user,
**I want** to export approved PDF files,
**So that** I can use the tailored output.

### Acceptance Criteria

- [ ] Given a resume-only session, when I export, then a tailored resume PDF is produced.
- [ ] Given a resume-and-cover-letter session, when I export, then separate downloads are available for `tailored-resume.pdf` and `cover-letter.pdf`.

## Story 7: Deploy to QA in eastus

**As an** operator,
**I want** one QA deployment in `eastus`,
**So that** V1 can be validated without production complexity.

### Acceptance Criteria

- [ ] Given an infrastructure change, when CI runs, then Bicep validation succeeds.
- [ ] Given a release candidate, when deployment runs, then the app deploys to QA in `eastus`.
- [ ] Given a QA deployment, when health checks run, then all required checks pass.

## Story 8: Run QA Validation

**As a** team,
**I want** measurable QA checks,
**So that** V1 quality is enforceable.

### Acceptance Criteria

- [ ] Structured output validation passes for the baseline dataset.
- [ ] Required smoke checks pass in QA.
- [ ] LLM-as-judge is not required for the blocking QA gate.

## Parallel Work Plan

### Immediate Parallel Capacity

After Story 0 is complete, 5 engineers can work in parallel with low overlap.

### Lane Ownership

1. Engineer A: Stories 1 and part of 7
2. Engineer B: Story 1 parsing support and Story 6 rendering support
3. Engineer C: Stories 2 and 4
4. Engineer D: Stories 3, 5, and part of 6
5. Engineer E: Stories 7 and 8

### Low-Overlap Rules

- Engineer A owns session and upload contracts.
- Engineer B owns PDF contracts.
- Engineer C owns model and generation contracts.
- Engineer D owns review and export UI contracts.
- Engineer E owns infra and QA contracts.

## Engineer and Lead Story Pack

### Platform Lead (Foundation and Integration)

#### Lead Story L1: Freeze Shared Contracts

**As a** platform lead,
**I want** session, section, generation, and export contracts frozen,
**So that** all engineers can deliver in parallel with low conflict.

Acceptance Criteria

- [ ] Contract files are published for session schema, section schema, cover letter schema, generation interface, and export interface.
- [ ] Each contract has a version tag and owner.
- [ ] Any contract change requires a version bump and change note.

#### Lead Story L2: Integration Gate Control

**As a** platform lead,
**I want** a daily integration gate,
**So that** incompatible changes are caught before merge.

Acceptance Criteria

- [ ] Daily integration checklist is executed.
- [ ] Cross-lane contract tests run before accepting merges.
- [ ] Blockers are logged with owner and ETA.

### Engineer A (Upload and Session Lane)

#### Engineer A Story A1: Upload Entry Flow

**As a** user,
**I want** to upload a supported PDF,
**So that** I can begin tailoring.

Acceptance Criteria

- [ ] Upload supports drag-and-drop and file picker.
- [ ] Unsupported or image-only PDF is rejected with a clear message.

#### Engineer A Story A2: Session Bootstrap

**As a** user,
**I want** a session created after successful upload,
**So that** all later actions are tracked consistently.

Acceptance Criteria

- [ ] Session identifier is created and returned.
- [ ] Session status transitions follow the contract.

### Engineer B (PDF Ingestion Lane)

#### Engineer B Story B1: Section Detection

**As a** system,
**I want** to parse PDF sections with stable ordering,
**So that** review and rendering remain predictable.

Acceptance Criteria

- [ ] Sections include key, order index, page number, and bounding box.
- [ ] Parsed section order is deterministic across runs for the same input.

#### Engineer B Story B2: Supported-PDF Gate

**As a** system,
**I want** to detect unsupported PDFs early,
**So that** failed generation attempts are prevented.

Acceptance Criteria

- [ ] Image-only PDFs are detected and rejected.
- [ ] Rejection reasons map to user-facing error copy in UX.

### Engineer C (Generation Lane)

#### Engineer C Story C1: Credential and Model Policy

**As a** user,
**I want** GitHub Models credential mode and curated model selection,
**So that** generation behavior is controlled and transparent.

Acceptance Criteria

- [ ] Only curated top-5 models are selectable.
- [ ] User key mode keeps key material in memory only.
- [ ] Default model selection is applied by policy.

#### Engineer C Story C2: Timeout and Error Handling

**As a** user,
**I want** clear timeout guidance by credential mode,
**So that** I can recover quickly.

Acceptance Criteria

- [ ] User-key timeout message is exact and actionable.
- [ ] App-key timeout message is exact and actionable.

### Engineer D (Review and Export Lane)

#### Engineer D Story D1: Review and Edit Workspace

**As a** user,
**I want** to review and edit generated content,
**So that** I approve final outputs.

Acceptance Criteria

- [ ] Original and tailored sections are shown side-by-side on desktop.
- [ ] User edits are persisted for export.
- [ ] Cover letter panel is shown only when `Resume and cover letter` mode is selected.

#### Engineer D Story D2: Dual PDF Export

**As a** user,
**I want** download actions for resume and cover letter PDFs,
**So that** I can export without ZIP packaging.

Acceptance Criteria

- [ ] `Resume only` exposes `tailored-resume.pdf` download.
- [ ] `Resume and cover letter` exposes separate downloads for `tailored-resume.pdf` and `cover-letter.pdf`.
- [ ] No ZIP package is produced.

### Engineer E (QA and Deployment Lane)

#### Engineer E Story E1: QA Infrastructure Scaffold

**As an** operator,
**I want** QA infra definitions in `eastus`,
**So that** deployment validation is repeatable.

Acceptance Criteria

- [ ] Bicep main and QA parameter files exist and validate.
- [ ] Resource naming and environment values match deployment plan.

#### Engineer E Story E2: Planning and Quality Gates

**As a** team,
**I want** CI planning and validation gates,
**So that** readiness and policy drift are detected early.

Acceptance Criteria

- [ ] Planning-gate workflow validates mandatory artifacts.
- [ ] Eval baseline manifest is present and versioned.
- [ ] QA checklist execution path is documented.

## Schedule of Work (10-Day Guide)

The day numbers represent a suggested sequencing, not a hard calendar gate. Lanes that finish early hand off immediately and downstream lanes begin without waiting for the day boundary. The goal is working software, not calendar compliance.

### Week 1

1. Day 1: Platform lead completes L1 contract freeze and dependency map.
2. Day 2: Engineer A starts A1 and A2; Engineer B starts B1; Engineer E starts E1 scaffold validation.
3. Day 3: Engineer B completes B1 and starts B2; Engineer C starts C1 against frozen contracts.
4. Day 4: Engineer A closes A2; Engineer C continues C1 and starts C2; platform lead runs L2 integration gate.
5. Day 5: Engineer D starts D1 using outputs from A and B; Engineer E starts E2 CI and checklist alignment.

### Week 2

1. Day 6: Engineer D continues D1 and begins D2 dual-download flow; Engineer C finalizes C2 timeout paths.
2. Day 7: Cross-lane integration checkpoint led by platform lead; fix contract mismatches only.
3. Day 8: Engineer E runs QA readiness checklist dry run; all lanes fix findings.
4. Day 9: End-to-end story walkthrough against acceptance criteria across A-E lanes.
5. Day 10: Council recheck and executive readiness review for implementation authorization.

## Dependency and Handoff Rules

1. A and B outputs are prerequisites for D to complete review and export behavior.
2. C depends on lead-frozen generation and credential contracts.
3. E depends on final contract paths and artifact locations from lead and all lanes.
4. Platform lead owns daily conflict resolution and contract-change approval.

