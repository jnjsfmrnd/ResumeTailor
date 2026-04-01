# Integration Gate — Daily Checklist

**Owner**: Platform Lead
**Cadence**: Daily during active delivery (Weeks 1–2)
**Format**: Complete each section. Log blockers in BLOCKERS.md with owner and ETA.

---

## Gate Execution Record

> Copy this template for each daily run. File as `GATE-YYYY-MM-DD.md` or append below.

---

### Gate Date: ___________

**Executor**: Platform Lead
**Status**: PASS / FAIL / BLOCKED

---

## Section 1 — Contract Health

| Check | Result | Notes |
|---|---|---|
| All 5 contract files present in `docs/contracts/` | ☐ | |
| `CONTRACT-VERSION.md` versions match file headers | ☐ | |
| No contract file modified without a version bump | ☐ | |
| No open PRs that mutate a contract without platform lead approval | ☐ | |

---

## Section 2 — Cross-Lane Dependency Status

| Lane | Status | Blocking On | ETA |
|---|---|---|---|
| Engineer A (Upload/Session) | | | |
| Engineer B (PDF Ingestion) | | | |
| Engineer C (Generation) | | | |
| Engineer D (Review/Export) | | | |
| Engineer E (QA/Deployment) | | | |

Lane status values: `Not Started` / `In Progress` / `Blocked` / `Complete`

---

## Section 3 — Handoff Readiness

| Handoff | From | To | Ready? | Notes |
|---|---|---|---|---|
| Session + upload → Generation | A | C | ☐ | |
| PDF sections → Generation | B | C | ☐ | |
| Generated sections → Review | C | D | ☐ | |
| Approved sections → Export | D | D | ☐ | |
| Contract paths + artifact locations → QA | Lead + All | E | ☐ | |

---

## Section 4 — Policy Compliance

| Policy | Result | Notes |
|---|---|---|
| No ZIP export in any lane | ☐ | |
| No raw user key persisted anywhere | ☐ | |
| Timeout messages match credential mode exactly | ☐ | |
| Cover letter absent from `resume_only` sessions | ☐ | |
| Export filenames are exactly `tailored-resume.pdf` / `cover-letter.pdf` | ☐ | |

---

## Section 5 — Blockers Logged

| Blocker ID | Description | Owner | ETA | Resolved? |
|---|---|---|---|---|
| | | | | |

See [BLOCKERS.md](BLOCKERS.md) for full blocker log.

---

## Section 6 — Gate Decision

- [ ] All Section 1 contract checks pass
- [ ] No lane is blocked without a logged ETA
- [ ] No policy violations outstanding
- [ ] All prior-day blockers are resolved or have updated ETAs

**Gate Result**: PASS / FAIL / BLOCKED

**Notes**:

---
