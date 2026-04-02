"""Management command: run_regression

Executes the QA regression gate against the baseline dataset manifest
(docs/data-science/baselines/resume-tailor-v1-baseline.json).

Blocking gates (from EVAL-PLAN-0001):
  - Structured output validity: 100%
  - Required field completeness: 100%
  - Overflow warning coverage: 100% of known cases
  - p95 generation time <= 120 seconds
  - Dataset manifest version is recorded in the run output

Usage:
    python manage.py run_regression [--baseline PATH] [--output PATH]

Exit codes:
    0 — all blocking gates passed
    1 — one or more blocking gates failed
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

DEFAULT_BASELINE = Path(__file__).resolve().parents[3] / \
    "docs" / "data-science" / "baselines" / "resume-tailor-v1-baseline.json"

REQUIRED_SECTION_FIELDS = {"section_key", "original_content"}
REQUIRED_SESSION_FIELDS = {"id", "generation_mode", "credential_mode"}

P95_THRESHOLD_SECONDS = 120


class Command(BaseCommand):
    help = "Run the QA regression gate against the baseline dataset manifest."

    def add_arguments(self, parser):
        parser.add_argument(
            "--baseline",
            type=Path,
            default=DEFAULT_BASELINE,
            help="Path to the baseline JSON manifest.",
        )
        parser.add_argument(
            "--output",
            type=Path,
            default=None,
            help="Optional path to write the evidence log JSON.",
        )

    def handle(self, *args, **options):
        baseline_path: Path = options["baseline"]
        output_path: Path | None = options["output"]

        # Load manifest
        if not baseline_path.exists():
            raise CommandError(f"Baseline manifest not found: {baseline_path}")

        with open(baseline_path) as f:
            manifest = json.load(f)

        manifest_version = manifest.get("manifestVersion", "unknown")
        records = manifest.get("records", [])
        record_count = len(records)

        self.stdout.write(f"Baseline manifest version : {manifest_version}")
        self.stdout.write(f"Records to evaluate       : {record_count}")

        if record_count == 0:
            self.stdout.write(
                self.style.WARNING(
                    "Baseline manifest contains 0 records. "
                    "Populate docs/data-science/baselines/resume-tailor-v1-baseline.json "
                    "before running a real regression gate."
                )
            )

        failures = []
        timings_seconds = []

        for i, record in enumerate(records, start=1):
            record_id = record.get("id", f"record-{i}")
            self._validate_record(record, record_id, failures, timings_seconds)

        # Compute p95 if we have timing data
        p95_ok = True
        p95_value = None
        if timings_seconds:
            sorted_timings = sorted(timings_seconds)
            p95_index = int(len(sorted_timings) * 0.95)
            p95_value = sorted_timings[min(p95_index, len(sorted_timings) - 1)]
            if p95_value > P95_THRESHOLD_SECONDS:
                failures.append(
                    f"p95 generation time {p95_value:.1f}s exceeds threshold "
                    f"{P95_THRESHOLD_SECONDS}s"
                )
                p95_ok = False

        passed = len(failures) == 0

        # Build evidence log
        evidence = {
            "runDate": datetime.now(timezone.utc).isoformat(),
            "manifestVersion": manifest_version,
            "recordCount": record_count,
            "gatesChecked": [
                "structured_output_validity",
                "required_field_completeness",
                "overflow_warning_coverage",
                "p95_generation_time",
            ],
            "p95GenerationSeconds": p95_value,
            "p95Threshold": P95_THRESHOLD_SECONDS,
            "failures": failures,
            "result": "PASS" if passed else "FAIL",
        }

        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                json.dump(evidence, f, indent=2)
            self.stdout.write(f"Evidence log written to: {output_path}")

        if passed:
            self.stdout.write(self.style.SUCCESS(f"Regression gate: PASS ({record_count} records)"))
        else:
            self.stdout.write(self.style.ERROR(f"Regression gate: FAIL — {len(failures)} failure(s):"))
            for failure in failures:
                self.stdout.write(f"  - {failure}")
            sys.exit(1)

    def _validate_record(self, record, record_id, failures, timings_seconds):
        """Validate a single baseline record against all blocking gates."""
        # Required session fields
        for field in REQUIRED_SESSION_FIELDS:
            if field not in record:
                failures.append(f"{record_id}: missing required field '{field}'")

        # Structured output validity — record must have a 'sections' list
        sections = record.get("sections")
        if not isinstance(sections, list):
            failures.append(f"{record_id}: 'sections' must be a list (structured output validity)")
            return

        # Required field completeness — each section must have required fields
        for j, section in enumerate(sections):
            for field in REQUIRED_SECTION_FIELDS:
                if not section.get(field):
                    failures.append(
                        f"{record_id} section[{j}]: missing required field '{field}'"
                    )

        # Overflow warning coverage — if record flags overflow, an overflow_warning must be present
        if record.get("has_overflow_risk") and not record.get("overflow_warning"):
            failures.append(
                f"{record_id}: overflow_risk flagged but no overflow_warning present"
            )

        # Collect timing for p95 check
        duration_ms = record.get("expected_duration_ms")
        if isinstance(duration_ms, (int, float)) and duration_ms > 0:
            timings_seconds.append(duration_ms / 1000.0)
