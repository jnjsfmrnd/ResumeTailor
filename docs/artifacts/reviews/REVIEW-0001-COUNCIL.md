# Council Review: ResumeTailor Round 2 Artifact Set

**Artifacts Reviewed**: PRD-0001, ADR-0001, SPEC-0001, UX-0001, DESIGN-GUIDE-0001, EVAL-PLAN-0001, AZURE-DEPLOYMENT-0001, STORIES-0001, prototype
**Date**: 2026-04-01
**Reviewer Mode**: Multi-agent council synthesis
**Decision**: Planning approved after artifact-sync fixes; implementation remains blocked pending explicit CEO authorization

## Summary

The round-2 planning set is broadly coherent and now covers the previously missing UX, deployment, and evaluation surfaces. The remaining issues were primarily artifact drift: stale review notes, stale repository memory, a prototype that still reflected the earlier multi-provider concept, and a few underspecified operational details around retention, reproducibility, and export packaging.

## Findings

### 1. Prototype drift was the main source of current confusion

**Agents raising concern**: UX Designer, Engineer, Reviewer

The prototype had still been showing provider choices and model options from an earlier concept instead of the settled GitHub Models-only round-2 scope. It also omitted the generation mode selector and the optional cover-letter review surface.

**Resolution applied**:
- Align prototype controls to credential mode, not provider mode.
- Keep the model list inside the GitHub Models shortlist.
- Add the `Resume only` and `Resume and cover letter` selector.
- Show the cover-letter review panel when that path is selected.

### 2. Repository memory and prior review notes had become stale

**Agents raising concern**: AgentX Auto, Product Manager, Reviewer

The repository memory and the older council review still described superseded decisions such as OpenAI and Gemini BYO flows and a QA-plus-production hosting plan. Because this project uses retrieval-led reasoning, stale guidance is itself a project risk.

**Resolution applied**:
- Update repository decision memory to match round-2 scope.
- Replace stale council findings with the current review state.

### 3. Sensitive-content lifecycle rules needed to be explicit

**Agents raising concern**: Security lens, Architect, DevOps

The spec already prohibited persistence of user-supplied keys, but it did not say enough about retention and deletion for resumes, job descriptions, edited content, and generated artifacts.

**Resolution applied**:
- Add encryption-at-rest expectations for uploaded and generated documents.
- Add a 7-day QA retention limit with scheduled purge.
- Add immediate session deletion expectations from the review flow.
- Clarify that logs and traces must not include document text.

### 4. Evaluation reproducibility needed one more layer of specificity

**Agents raising concern**: Data Scientist, Tester, DevOps

The evaluation plan had thresholds, but not enough reproducibility detail to make blocking runs stable over time.

**Resolution applied**:
- Add a baseline dataset manifest location.
- Require dataset versioning when examples change.
- Record prompt version, selected model, and model revision date for blocking runs.
- Require pinned model identifiers and revision dates in release configuration.

### 5. Export behavior is now explicit

**Agents raising concern**: Product Manager, Engineer, Tester

The earlier wording left the cover-letter export shape ambiguous.

**Resolution applied**:
- `Resume only` exports `tailored-resume.pdf`.
- `Resume and cover letter` provides separate downloads for `tailored-resume.pdf` and `cover-letter.pdf`.

## Agent Rollup

| Agent | Council Position |
|-------|------------------|
| AgentX Auto | Planning set is usable after sync fixes |
| Product Manager | Scope is now consistent and story-shaped enough for execution |
| Architect | Core boundaries are clear; retention and export rules are now explicit |
| UX Designer | UX artifacts exist and can guide implementation once prototype stays aligned |
| Data Scientist | Eval plan is serviceable with reproducibility details added |
| Engineer | Ready for implementation planning against the current contracts |
| Reviewer | No blocking artifact gaps remain in the current document set |
| DevOps Engineer | QA-only deployment plan is sufficiently bounded for V1 |
| Tester | Acceptance criteria are materially clearer after export and eval updates |

## Residual Watch Items

1. Keep the prototype aligned with UX and ADR when the shortlist changes.
2. Keep the dataset manifest and prompt versions under version control once implementation begins.
3. Validate that the 7-day purge job and session-deletion flow are implemented, not just documented.