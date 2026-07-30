#!/usr/bin/env python3
"""Fail closed when customer migration aliases enter the standard product."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


FORBIDDEN = ("p1_" + "visible_", "uc_" + "formal_")
PRODUCTION_ROOTS = (
    Path("addons/smart_core"),
    Path("addons/smart_construction_core"),
    Path("frontend/apps/web/src"),
    Path("scripts/ops"),
)
IGNORED_PARTS = {"tests", "migrations", "__pycache__"}
TEXT_SUFFIXES = {".py", ".xml", ".js", ".ts", ".tsx", ".vue", ".json", ".csv", ".md"}


def scan(root: Path) -> list[dict[str, object]]:
    violations: list[dict[str, object]] = []
    for relative_root in PRODUCTION_ROOTS:
        target = root / relative_root
        if not target.exists():
            continue
        for path in target.rglob("*"):
            if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
                continue
            if any(part in IGNORED_PARTS for part in path.relative_to(root).parts):
                continue
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except UnicodeDecodeError:
                continue
            for line_no, line in enumerate(lines, 1):
                for token in FORBIDDEN:
                    if token in line:
                        violations.append({
                            "path": path.relative_to(root).as_posix(),
                            "line": line_no,
                            "reason_code": "FORMAL_PRODUCT_LEGACY_ALIAS",
                            "token": token,
                        })
    return violations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--json-output")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    violations = scan(root)
    report = {
        "schema_version": "field-arch-p0-02.purity.v1",
        "result": "PASS" if not violations else "FAIL",
        "product_source_legacy_alias_count": len(violations),
        "violations": violations,
    }
    if args.json_output:
        Path(args.json_output).write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(report, ensure_ascii=False))
    return 0 if not violations else 1


if __name__ == "__main__":
    raise SystemExit(main())
