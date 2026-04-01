#!/usr/bin/env python3
"""Planning-only scaffold.

This file exists to satisfy planning readiness checks.
Implementation is intentionally blocked until explicit CEO approval.
"""

import sys


def main() -> int:
    message = (
        "Planning-only scaffold: implementation is blocked until explicit CEO approval."
    )
    sys.stderr.write(message + "\n")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
