# ResumeTailor Interview Prep Master Document

**Project**: ResumeTailor V1
**Audience**: Senior Software Engineer interviews
**Purpose**: Explain the project clearly, defend technical decisions, and answer architecture and tradeoff questions without overstating implementation maturity.
**Date**: 2026-04-01

## 1. The Safe Framing

Use this framing first so your explanation is accurate and strong:

- ResumeTailor is an AI-assisted resume tailoring system designed around controlled document editing, grounded generation, mandatory human review, and QA-first operational boundaries.
- The repository is planning-complete and architecture-rich, with implementation intentionally blocked pending explicit authorization.
- Describe the runtime posture as single-user and QA-first, not local-first, because the planned validation environment is hosted.
- The senior-level value of the project is in the decisions, constraints, delivery slicing, and risk management, not in pretending it is already a production-hardened system.

## 2. The 30-Second Answer

ResumeTailor is a Django-based AI-assisted workflow for taking a PDF resume and a target job description, generating a tailored resume and optional cover letter, requiring human review before export, and preparing a QA-only Azure deployment path. The interesting engineering work was not basic CRUD. It was deciding how to handle PDF fidelity, grounded generation, API key safety, deterministic evaluation, and tight V1 scope control so the system stayed useful without becoming operationally bloated.

## 3. The 2-Minute Answer

I worked on ResumeTailor as a tightly scoped AI workflow product. The user uploads a digital PDF resume, pastes a job description, selects a GitHub Models-backed generation path, optionally asks for a cover letter, reviews and edits the output, and then exports approved PDFs. The main challenge was balancing AI assistance with deterministic controls.

From an architecture perspective, we chose a Django monolith with PostgreSQL, Celery, and Redis because V1 is single-user, QA-first, and planning-only. That let us keep the system simple while still separating web requests, background generation work, persistence, and queueing. We intentionally limited model access to GitHub Models only, with a curated top-5 shortlist, to reduce provider sprawl, credential complexity, and the test matrix.

We also made some explicit trust and safety decisions. User-supplied API keys are in-memory only and never persisted. Human review is mandatory before export. Release blocking relies on deterministic checks and human grounding review rather than LLM-as-judge. We also constrained deployment to one QA environment in eastus using Azure Container Apps and Bicep, because the senior decision here was to avoid pretending we had production requirements before the product and document workflow risks were better understood.

## 4. The Whiteboard Architecture Walkthrough

Use this flow when an interviewer asks you to walk through the system end to end:

1. Input layer: user uploads a supported digital PDF and pastes job-description text.
2. Session layer: the app creates a ResumeSession with generation mode, credential mode, selected model, and review state.
3. Ingestion layer: PDF content is parsed into ordered sections and bounded regions so edits can later be rendered back into the document safely.
4. Generation layer: a background job calls GitHub Models using the selected model and produces structured tailored content and, if requested, a cover letter draft.
5. Validation layer: outputs pass schema and required-field checks, timeout handling, and overflow-risk checks.
6. Review layer: the user edits the generated content before anything is exported.
7. Rendering/export layer: the approved resume is rendered to PDF; cover letter export is separate when selected.
8. QA layer: smoke checks, regression checks, and evaluation runs execute against a single QA deployment.

## 5. The Technical Decisions You Should Defend

### Decision 1: Django monolith instead of microservices

Why we chose it:

- V1 is single-user and planning-first.
- The domain is cohesive: upload, parse, generate, review, render, export.
- Operational simplicity mattered more than independent scaling.

How to defend it:

I chose a monolith because it kept change coordination, deployment, and debugging simple while the main risks were still product-fit and document fidelity, not service-scale. I still separated responsibilities logically with background jobs and clear domain boundaries, so the system can be decomposed later if usage patterns justify it.

### Decision 2: PostgreSQL, Celery, and Redis

Why we chose it:

- PostgreSQL gives durable session and artifact metadata storage.
- Celery moves generation and evaluation work off the request path.
- Redis is the queue/cache layer for background orchestration.

How to defend it:

I wanted mature, boring infrastructure choices for a workflow app with asynchronous AI calls and deterministic state tracking. The risk was not novelty; it was controllability and recoverability.

### Decision 3: PDF-only editable input in V1

Why we chose it:

- It matches the actual user workflow.
- It keeps the scope focused.
- It forces fidelity and rendering concerns into the design early.

How to defend it:

This was intentionally hard. Supporting PDFs first meant accepting document-layout complexity, but it aligned with the user job-to-be-done. I would rather design around the real hard constraint than build an easier but less relevant V1.

### Decision 4: GitHub Models only, not multi-provider

Why we chose it:

- Smaller credential surface area.
- Lower operational complexity.
- Easier QA and evaluation.
- Smaller policy and timeout matrix.

How to defend it:

Multi-provider support is attractive in theory, but it multiplies testing, error handling, configuration, and support complexity. For V1, I prioritized a narrow, clean path over optionality.

### Decision 5: Two credential modes, but BYO keys are never persisted

Why we chose it:

- App-managed key is the default low-friction path.
- User-supplied key supports direct usage flexibility.
- In-memory-only handling reduces security and compliance exposure.

How to defend it:

This is a strong boundary decision. If you accept user-owned keys, the safest practical V1 behavior is to use them for the active request only and never store them in sessions, logs, queues, or the database.

### Decision 6: Mandatory human review before export

Why we chose it:

- Resume tailoring is high-trust, low-error-tolerance work.
- AI output can be useful without being final.
- This reduces hallucination and tone-risk exposure.

How to defend it:

I did not want to design a system that pretends AI-generated resume content should ship directly. The human-in-the-loop step is part of the product, not just a safeguard bolted on afterward.

### Decision 7: Deterministic release gates instead of LLM-as-judge

Why we chose it:

- More reproducible evaluation.
- Easier to explain and audit.
- Better fit for blocking QA gates.

How to defend it:

I treated LLM-as-judge as a potentially useful benchmark, not a release gate. For blocking decisions, I preferred schema validation, required-field checks, timing thresholds, overflow checks, and human grounding review because they are more stable and explainable.

### Decision 8: QA-only Azure deployment in eastus

Why we chose it:

- Avoid fake production readiness.
- Keep IaC and deployment scope bounded.
- Create one clean validation target for smoke and regression checks.

How to defend it:

Constraining the system to one QA environment was a maturity decision. It prevented the team from spending energy on environments, rollout logic, and production posturing before the core workflow was proven.

## 6. How Deep To Go In Interviews

### Default depth

Start with product + architecture + 2 or 3 big decisions. Stop there unless they pull on a thread.

### If the interviewer is backend-focused

Go deeper on:

- session and state modeling
- background job orchestration
- timeout paths
- persistence boundaries
- why a monolith is enough for V1

### If the interviewer is AI/ML-focused

Go deeper on:

- why GitHub Models only
- grounding and structured output
- evaluation design
- prompt/version reproducibility
- why human review stays mandatory

### If the interviewer is platform-focused

Go deeper on:

- Azure Container Apps choice
- Bicep and QA-only environment strategy
- secret handling
- retention and cleanup rules
- smoke and regression gating

### If the interviewer is staff-plus or architecture-focused

Go deeper on:

- what you intentionally did not build
- what decisions reduce complexity now
- what would trigger decomposition later
- where the real product and technical risks are

## 7. What Not To Say

- Do not imply this is already production-proven.
- Do not claim real scalability numbers you do not have.
- Do not say microservices were unnecessary forever; say they were unnecessary for this phase.
- Do not overclaim AI reliability.
- Do not pretend the planning-first posture makes the project less real. It makes the decision quality more visible.

## 8. Strong Follow-Up Answers

### Why not microservices?

Because the dominant V1 risks were product correctness, document fidelity, and safe orchestration, not independent service scaling. A monolith reduced operational drag while still allowing clean internal boundaries.

### Why not support OpenAI, Anthropic, and others immediately?

Because provider flexibility would have expanded the credential, timeout, model-policy, observability, and QA matrix too early. I preferred a smaller surface area with better control.

### Why require human review if the model is good?

Because resume tailoring is reputationally sensitive. The product value is faster drafting, not automatic submission without oversight.

### Why is planning-only still interview-worthy?

Because senior engineers are expected to make sound architectural decisions before code volume hides weak thinking. This repo demonstrates how scope, architecture, AI safety, and operational boundaries were reasoned about deliberately.

### What would you build next if implementation were approved?

I would freeze contracts first, implement session and upload handling, build PDF parsing and supported-file gating, add the generation lane with strict key handling, then implement review/export, and finally wire QA validation into the Azure path.

## 9. Interviewer Questions You Should Practice

1. Why was Django the right choice here?
2. What would make you split this monolith later?
3. How would you prevent hallucinated resume claims from reaching users?
4. Why did you choose GitHub Models only?
5. What are the security implications of user-supplied API keys?
6. How would you model retries and timeout behavior for long-running generation?
7. What are the hardest parts of PDF-first editing?
8. Why is QA-only deployment a good decision rather than a missing feature?
9. What metrics would you track once implementation starts?
10. What was deliberately left out of V1 and why?

## 10. Good Senior Signals To Emphasize

- You reduced scope intentionally.
- You made tradeoffs explicit.
- You optimized for controllability, not hype.
- You separated product ambition from operational maturity.
- You designed the evaluation strategy before implementation.
- You treated security and retention as first-class concerns.

## 11. Final Positioning Line

If I needed to summarize the project in one line during an interview, I would say: ResumeTailor is a deliberately scoped AI-assisted document workflow where the hardest engineering work was deciding how to keep generation useful, reviewable, secure, and operationally simple enough to be defensible.

## 12. Source Artifacts

- PRD: docs/artifacts/prd/PRD-0001.md
- ADR: docs/artifacts/adr/ADR-0001.md
- SPEC: docs/artifacts/specs/SPEC-0001.md
- UX: docs/ux/UX-0001.md
- Evaluation plan: docs/data-science/EVAL-PLAN-0001.md
- Deployment plan: docs/deployment/AZURE-DEPLOYMENT-0001.md