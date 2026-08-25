#!/usr/bin/env python3
"""Validate the standard-risk professional frontend Make extension surface."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "make/frontend_professional_extensions.mk"

TARGET_NAME = r"verify\.frontend\.professional\.[a-z0-9_.-]+\.unit"
ALLOWED = (
    re.compile(r"^$"),
    re.compile(r"^#[^\r\n]*$"),
    re.compile(rf"^\.PHONY: (?:{TARGET_NAME})(?: (?:{TARGET_NAME}))*$"),
    re.compile(rf"^PROFESSIONAL_FRONTEND_EXTENSION_TARGETS :=(?: (?:{TARGET_NAME}))*$"),
    re.compile(rf"^PROFESSIONAL_FRONTEND_EXTENSION_TARGETS \+=(?: (?:{TARGET_NAME}))*$"),
    re.compile(rf"^(?:{TARGET_NAME}): guard\.prod\.forbid$"),
    re.compile(
        r"^\t@frontend/apps/web/node_modules/\.bin/esbuild "
        r"frontend/apps/web/scripts/[a-z0-9_]+_test\.ts --bundle --platform=node "
        r"--format=esm --outfile=/tmp/[a-z0-9-]+-test\.mjs >/dev/null$"
    ),
    re.compile(r"^\t@node /tmp/[a-z0-9-]+-test\.mjs$"),
    re.compile(r"^\t@python3 -m unittest scripts(?:/|\.)verify(?:/|\.)test_frontend_professional_[a-z0-9_]+(?:\.py)?$"),
    re.compile(r"^\t@python3 scripts/verify/frontend_professional_[a-z0-9_]+_guard\.py$"),
    re.compile(r"^\t@python3 addons/[a-z0-9_]+/tests/test_[a-z0-9_]+\.py$"),
    re.compile(r"^\t@python3 scripts/ci/frontend_professional_extension_guard\.py$"),
    re.compile(
        r'^\t@if test -n "\$\(strip \$\(PROFESSIONAL_FRONTEND_EXTENSION_TARGETS\)\)"; '
        r'then \$\(MAKE\) --no-print-directory \$\(PROFESSIONAL_FRONTEND_EXTENSION_TARGETS\); fi$'
    ),
    re.compile(
        r'^\t@echo "\[verify\.frontend\.professional\.extensions\.unit\] '
        r'PASS targets=\$\(words \$\(PROFESSIONAL_FRONTEND_EXTENSION_TARGETS\)\)"$'
    ),
)


def validate(text: str) -> list[str]:
    failures: list[str] = []
    for number, line in enumerate(text.splitlines(), 1):
        if not any(pattern.fullmatch(line) for pattern in ALLOWED):
            failures.append(f"line={number} unsupported professional extension syntax")
    if "verify.frontend.professional.extensions.unit" not in text:
        failures.append("extension aggregator is missing")
    return failures


def main() -> int:
    failures = validate(TARGET.read_text(encoding="utf-8"))
    if failures:
        print("[frontend_professional_extension_guard] FAIL", file=sys.stderr)
        for failure in failures:
            print(f" - {failure}", file=sys.stderr)
        return 1
    print("[frontend_professional_extension_guard] PASS grammar=restricted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
