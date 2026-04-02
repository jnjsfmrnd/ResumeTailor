# QA Evidence Log

**Owner**: Engineer E
**Environment**: QA (`eastus`)

Each deployment gate execution produces one entry here (or a separate dated file).
Copy the template below for each run and fill in every field.

---

## Template

```
### Run: YYYY-MM-DD — <git SHA or image tag>

**Date**: YYYY-MM-DD
**Executor**: <name or CI>
**Image Tag**: <SHA or semver>
**Baseline Manifest Version**: <e.g. 1.0.0>
**Prompt Version**: <e.g. v1>
**Model Selected**: <e.g. gpt-5.1>
**Model Revision Date**: <YYYY-MM-DD>

#### Deployment Gate

| Check | Result | Notes |
|-------|--------|-------|
| Bicep build passes | ☐ PASS / ☐ FAIL | |
| Bicep what-if passes | ☐ PASS / ☐ FAIL | |
| Image build (web) | ☐ PASS / ☐ FAIL | |
| Image build (worker) | ☐ PASS / ☐ FAIL | |
| Image push to ACR | ☐ PASS / ☐ FAIL | |
| Infrastructure deployment succeeds | ☐ PASS / ☐ FAIL | |
| Django migrations succeed | ☐ PASS / ☐ FAIL | |

#### Health Checks

| Check | Result | Notes |
|-------|--------|-------|
| /health/ → 200 | ☐ PASS / ☐ FAIL | |
| /health/ready/ → 200 | ☐ PASS / ☐ FAIL | |
| /health/ready/ database=ok | ☐ PASS / ☐ FAIL | |
| /health/ready/ redis=ok | ☐ PASS / ☐ FAIL | |

#### Regression Gate

| Check | Threshold | Result | Notes |
|-------|-----------|--------|-------|
| Structured output validity | 100% | ☐ PASS / ☐ FAIL | |
| Required field completeness | 100% | ☐ PASS / ☐ FAIL | |
| Overflow warning coverage | 100% | ☐ PASS / ☐ FAIL | |
| p95 generation time | ≤ 120 s | ☐ PASS / ☐ FAIL | |
| Factual invention (sampled) | 0 tolerated | ☐ PASS / ☐ FAIL | |

#### Policy Checks

| Policy | Result | Notes |
|--------|--------|-------|
| No ZIP export | ☐ PASS / ☐ FAIL | |
| No raw user key persisted | ☐ PASS / ☐ FAIL | |
| User-key timeout message exact match | ☐ PASS / ☐ FAIL | |
| App-key timeout message exact match | ☐ PASS / ☐ FAIL | |
| Cover letter absent from resume_only sessions | ☐ PASS / ☐ FAIL | |
| Export filenames exact: tailored-resume.pdf / cover-letter.pdf | ☐ PASS / ☐ FAIL | |

#### Gate Decision

- [ ] All deployment gate checks PASS
- [ ] All health checks PASS
- [ ] All regression blocking gates PASS
- [ ] All policy checks PASS

**Overall Result**: PASS / FAIL / BLOCKED

**Blocker IDs (if BLOCKED)**: 

**Notes**:
```

---

## Run Log

_No runs recorded yet. First run will be logged after initial QA deployment._
