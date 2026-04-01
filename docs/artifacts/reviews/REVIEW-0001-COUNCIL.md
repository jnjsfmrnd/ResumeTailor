# Council Review: ResumeTailor Round 2 Artifact Set

**Artifacts Reviewed**: PRD-0001, ADR-0001, SPEC-0001, UX-0001, DESIGN-GUIDE-0001, EVAL-PLAN-0001, AZURE-DEPLOYMENT-0001, STORIES-0001, prototype
**Date**: 2026-04-01
**Reviewer Mode**: Multi-agent council synthesis
**Decision**: Planning approved after artifact-sync and semantic-consistency fixes; implementation remains blocked pending explicit CEO authorization

## Summary

The round-2 planning set is now internally aligned across product, architecture, UX, evaluation, deployment, coaching, and prototype artifacts. The final hardening pass closed the remaining semantic gaps around runtime posture wording, UX conditional states, and review-language accuracy.

## Findings

### 1. Runtime posture language is now consistent

**Agents raising concern**: Product Manager, Architect, Reviewer

The packet had been using `local-first` language in some product and coaching artifacts while the actual V1 runtime plan centered on a hosted QA environment in Azure. That wording risked overstating privacy posture and understating the hosted validation model.

**Resolution applied**:
- Replace ambiguous `local-first` phrasing with single-user and QA-first wording in product and coaching artifacts.
- Keep the SPEC and deployment plan as the authoritative description of hosted runtime shape.

### 2. UX wireframes and prototype now describe the same conditional states

**Agents raising concern**: UX Designer, Engineer, Reviewer

The UX source of truth had been internally inconsistent: the component rules said the user-key field and cover-letter controls were conditional, while the wireframes read as if they were always visible. The prototype already behaved conditionally, so the documents needed to catch up.

**Resolution applied**:
- Mark the upload wireframe as the user-key state.
- Mark the review wireframe as the `Resume and cover letter` state.
- Add explicit text that `Resume only` omits cover-letter controls.

### 3. Sensitive-content lifecycle rules are explicit

**Agents raising concern**: Security lens, Architect, DevOps

The spec already prohibited persistence of user-supplied keys, but it did not say enough about retention and deletion for resumes, job descriptions, edited content, and generated artifacts.

**Resolution applied**:
- Add encryption-at-rest expectations for uploaded and generated documents.
- Add a 7-day QA retention limit with scheduled purge.
- Add immediate session deletion expectations from the review flow.
- Clarify that logs and traces must not include document text.

### 4. Evaluation reproducibility is explicit

**Agents raising concern**: Data Scientist, Tester, DevOps

The evaluation plan had thresholds, but not enough reproducibility detail to make blocking runs stable over time.

**Resolution applied**:
- Add a baseline dataset manifest location.
- Require dataset versioning when examples change.
- Record prompt version, selected model, and model revision date for blocking runs.
- Require pinned model identifiers and revision dates in release configuration.

### 5. Export behavior is explicit

**Agents raising concern**: Product Manager, Engineer, Tester

The earlier wording left the cover-letter export shape ambiguous.

**Resolution applied**:
- `Resume only` exports `tailored-resume.pdf`.
- `Resume and cover letter` provides separate downloads for `tailored-resume.pdf` and `cover-letter.pdf`.

### 6. Approval and coaching language no longer overstates readiness

**Agents raising concern**: Reviewer, Platform Lead, Interview Prep Tutor

The prior review language was stronger than the actual consistency state of the packet, and the interview-prep artifact inherited the same runtime-posture ambiguity. That risked presenting the plan as more settled than it really was.

**Resolution applied**:
- Update the go/no-go recheck to include semantic consistency checks.
- Update the coaching artifact to mirror the final runtime posture accurately.
- Keep implementation blocked until the CEO makes an explicit authorization decision.

## Agent Rollup

| Agent | Council Position |
|-------|------------------|
| AgentX Auto | Planning set is usable after sync and semantic-consistency fixes |
| Product Manager | Scope is consistent and story-shaped enough for execution |
| Architect | Core boundaries are clear; runtime posture and retention rules are explicit |
| UX Designer | UX artifacts and prototype now describe the same conditional behavior |
| Data Scientist | Eval plan is serviceable with reproducibility details added |
| Engineer | Ready for implementation planning against the current contracts |
| Reviewer | No blocking artifact or semantic-consistency gaps remain in the current document set |
| DevOps Engineer | QA-only deployment plan is sufficiently bounded for V1 |
| Tester | Acceptance criteria are materially clearer after export and UX alignment |

## Residual Watch Items

1. Keep the prototype aligned with UX and ADR when the shortlist changes.
2. Keep the dataset manifest and prompt versions under version control once implementation begins.
3. Validate that the 7-day purge job and session-deletion flow are implemented, not just documented.