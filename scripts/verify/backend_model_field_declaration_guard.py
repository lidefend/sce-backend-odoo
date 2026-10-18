#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fail closed on any field declared by more than one class block.

One field fact has exactly one declaration site. A second class that re-declares
the same field does not override the first: Odoo merges both definitions
attribute by attribute, so the effective field is a union that neither file
shows. Adding ``help``, ``string``, ``index`` or ``readonly`` in another class
therefore silently changes the first declaration instead of extending it.

This guard is intentionally stricter than the money-fact registry: there is no
registration escape hatch for a duplicate. Consolidate the attributes into the
owning declaration, or create a new field with a distinct name.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import backend_model_field_declarations as declarations
import sc_data_scope_rule_coverage_guard as scope_guard


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODULE_SETS = scope_guard.DEFAULT_MODULE_SETS
DEFAULT_JSON = ROOT / "artifacts/backend/backend_model_field_declaration_guard.json"
DEFAULT_MARKDOWN = ROOT / "artifacts/backend/backend_model_field_declaration_guard.md"


def check(root: Path = ROOT, module_sets_path: str = DEFAULT_MODULE_SETS) -> dict:
    modules = scope_guard.product_modules(root, module_sets_path)
    scanned = declarations.scan(root, modules)
    cross_class, same_class = declarations.conflicts(scanned)
    failures = [
        f"{key}: declared by more than one class block: "
        + ", ".join(
            f"{item['file']}:{item['line']} ({item['class_name']}, {item['role']}, {item['field_type']})"
            for item in items
        )
        for key, items in cross_class.items()
    ]
    failures.extend(
        f"{item['model']}.{item['field']}: declared more than once in class "
        + ", ".join(
            f"{declaration['file']}:{declaration['line']} ({declaration['class_name']})"
            for declaration in item["declarations"]
        )
        for item in same_class
    )
    return {
        "schema_version": "backend-model-field-declaration.v1",
        "status": "failed" if failures else "passed",
        "modules": modules,
        "declaration_count": len(scanned),
        "model_field_count": len({(item.model, item.field) for item in scanned}),
        "duplicate_count": len(cross_class),
        "same_class_duplicate_count": len(same_class),
        "duplicates": cross_class,
        "same_class_duplicates": same_class,
        "failures": failures,
    }


def write_markdown(report: dict, path: Path) -> None:
    lines = [
        "# Backend Model Field Declaration Guard",
        "",
        f"- status: {report['status']}",
        f"- modules: {len(report['modules'])}",
        f"- field declarations: {report['declaration_count']}",
        f"- model.fields: {report['model_field_count']}",
        f"- cross-class duplicates: {report['duplicate_count']}",
        f"- same-class duplicates: {report['same_class_duplicate_count']}",
        "",
        "## Duplicates",
        "",
    ]
    if report["duplicates"]:
        for key, items in report["duplicates"].items():
            lines.append(f"### `{key}`")
            for item in items:
                lines.append(
                    f"- `{item['file']}:{item['line']}` `{item['class_name']}` "
                    f"({item['role']}, `fields.{item['field_type']}`)"
                )
    else:
        lines.append("- none")
    if report["same_class_duplicates"]:
        lines.extend(["", "## Same-class duplicates", ""])
        for item in report["same_class_duplicates"]:
            lines.append(f"- `{item['model']}.{item['field']}`")
            for declaration in item["declarations"]:
                lines.append(
                    f"  - `{declaration['file']}:{declaration['line']}` "
                    f"`{declaration['class_name']}`"
                )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--module-sets", default=DEFAULT_MODULE_SETS)
    parser.add_argument("--json-output", default=str(DEFAULT_JSON))
    parser.add_argument("--markdown-output", default=str(DEFAULT_MARKDOWN))
    args = parser.parse_args()
    report = check(Path(args.root), args.module_sets)
    json_path = Path(args.json_output)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(report, Path(args.markdown_output))
    for failure in report["failures"]:
        print(f"FAIL {failure}")
    print(
        "BACKEND_MODEL_FIELD_DECLARATION="
        + json.dumps(
            {
                "status": report["status"],
                "duplicate_count": report["duplicate_count"],
                "same_class_duplicate_count": report["same_class_duplicate_count"],
                "declaration_count": report["declaration_count"],
                "json": str(json_path),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 1 if report["failures"] else 0


if __name__ == "__main__":
    sys.exit(main())
