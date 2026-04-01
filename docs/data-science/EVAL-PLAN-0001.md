# AI Evaluation Plan: ResumeTailor V1 Round 2

**Scope**: Resume tailoring and optional cover letter generation through GitHub Models
**Date**: 2026-04-01
**Status**: Approved (Planning Only)

## 1. Objectives

- Prevent factual invention in tailored output.
- Validate structured output needed for rendering.
- Support a blocking QA gate without requiring LLM-as-judge.

## 2. Model Policy

- Model platform: GitHub Models only
- Default model: GPT-5.1
- Shortlist size: 5 models
- Fallback must remain inside GitHub Models
- Release configuration must pin a concrete GitHub Models model identifier and revision date for the default and fallback entries

## 3. Baseline Dataset

- 25 representative resume and job-description pairs
- Include resume-only and resume-and-cover-letter cases
- Include supported PDFs, overflow-risk PDFs, and unsupported PDFs
- Store the baseline dataset manifest at `docs/data-science/baselines/resume-tailor-v1-baseline.json`
- Version the dataset manifest whenever records are added, removed, or re-labeled
- Record the prompt version and model revision used for each blocking run

## 4. Blocking Gates

| Dimension | Threshold |
|-----------|-----------|
| Factual invention | 0 tolerated in checked sample |
| Structured output validity | 100 percent |
| Required field completeness | 100 percent |
| Overflow warning coverage | 100 percent of known cases |
| p95 generation time | <= 120 seconds |

## 5. Review Method

Blocking QA uses:

- deterministic schema checks
- deterministic required-field checks
- human grounding review on sampled outputs
- manual review of timeout and retry messaging
- dataset-manifest version checks for reproducibility

LLM-as-judge is optional for later benchmarking, but it is not required for V1 release readiness.

## 6. Timeout Validation

- Validate that user-key timeout messaging says: `Request timed out. Check your API key and retry.`
- Validate that app-key timeout messaging says: `Request timed out. Retry the request.`

## 7. QA Deployment Tie-In

- The regression runner executes against the QA environment only.
- Results block QA signoff if any blocking gate fails.
- The regression runner output must record dataset-manifest version, prompt version, selected model, and model revision date.

## 8. Governance Gate

- This evaluation plan is approved for specification and QA gate design.
- Implementation and automation work remain blocked until explicit CEO approval.

