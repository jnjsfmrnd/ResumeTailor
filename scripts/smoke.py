#!/usr/bin/env python3
"""Smoke test script for the ResumeTailor QA environment.

Checks that the deployment is live and all health probes pass.

Usage:
    SMOKE_BASE_URL=https://ca-web-resumetailor-qa.azurecontainerapps.io \
        python scripts/smoke.py

Exit codes:
    0 — all checks passed
    1 — one or more checks failed
"""

import json
import os
import sys
import urllib.error
import urllib.request

BASE_URL = os.environ.get("SMOKE_BASE_URL", "http://localhost:8000").rstrip("/")
TIMEOUT = 30  # seconds per request

_failures = []


def check(name: str, url: str, expected_status: int = 200, expected_key: str = "status") -> None:
    """Perform a single HTTP GET smoke check."""
    print(f"  {name} → {url} ... ", end="", flush=True)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ResumeTailor-SmokeTest/1.0"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            status = resp.status
            body = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        status = exc.code
        try:
            body = json.loads(exc.read().decode())
        except Exception:
            body = {}
    except Exception as exc:
        print(f"FAIL ({exc})")
        _failures.append(f"{name}: connection error — {exc}")
        return

    if status != expected_status:
        print(f"FAIL (HTTP {status})")
        _failures.append(f"{name}: expected HTTP {expected_status}, got {status}")
        return

    if expected_key and body.get(expected_key) != "ok":
        print(f"FAIL (body={body})")
        _failures.append(f"{name}: expected {expected_key}=ok, got {body}")
        return

    print("OK")


def main() -> int:
    print(f"Smoke tests against {BASE_URL}\n")

    check("Liveness probe", f"{BASE_URL}/health/")
    check("Readiness probe", f"{BASE_URL}/health/ready/")

    if _failures:
        print(f"\n{len(_failures)} check(s) FAILED:")
        for f in _failures:
            print(f"  - {f}")
        return 1

    print("\nAll smoke checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
