#!/usr/bin/env python3
"""Fail-closed check that every declared P1 model carries a company-scope rule.

The registered 744-model registry is inspection scope, not a rewrite list. This
guard only verifies the explicit declaration in data_scope_declarations.json:

* every ``enforced`` model has a *global* ir.rule (no groups, so no group union
  can widen it) whose domain constrains the declared company anchor path;
* every exemption carries a reason, and no model is both enforced and exempt;
* rule xml ids stay unique across the security files.

It reads source only, so it runs in the offline lane.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DECLARATIONS = ROOT / "scripts/verify/data_scope_declarations.json"


def record_ref(record: ET.Element) -> str | None:
    for field in record.findall("field"):
        if field.get("name") == "model_id":
            return field.get("ref") or field.get("eval")
    return None


def record_domain(record: ET.Element) -> str:
    for field in record.findall("field"):
        if field.get("name") == "domain_force":
            return "".join(field.itertext()).strip()
    return ""


def record_is_global(record: ET.Element) -> bool:
    for field in record.findall("field"):
        if field.get("name") == "groups":
            expression = (field.get("eval") or "").strip()
            text = "".join(field.itertext()).strip()
            return expression == "[]" or (not expression and not text)
    return True


def normalize_ref(raw: str | None, module: str) -> tuple[str, str] | None:
    if not raw:
        return None
    value = raw.strip()
    if value.startswith("ref(") and value.endswith(")"):
        value = value[4:-1].strip().strip("'\"")
    if not value:
        return None
    if "." in value:
        prefix, _, name = value.partition(".")
        return prefix, name
    return module, value


def scan_security_files(root: Path) -> tuple[dict[str, list[dict]], list[str]]:
    by_model_ref: dict[str, list[dict]] = {}
    ids: list[str] = []
    for path in sorted(root.glob("addons/*/security/*.xml")):
        module = path.parts[-3]
        try:
            tree = ET.parse(path)
        except ET.ParseError as exc:  # a broken security file is itself a failure
            raise SystemExit(f"unparsable security file {path}: {exc}") from exc
        for record in tree.getroot().iter("record"):
            if record.get("model") != "ir.rule":
                continue
            xml_id = record.get("id")
            if xml_id:
                ids.append(xml_id)
            parsed = normalize_ref(record_ref(record), module)
            if not parsed:
                continue
            owner, name = parsed
            by_model_ref.setdefault(name, []).append(
                {
                    "xmlid": xml_id,
                    "owner_module": owner,
                    "file": path.relative_to(root).as_posix(),
                    "global": record_is_global(record),
                    "domain": record_domain(record),
                }
            )
    return by_model_ref, ids


def defined_models(root: Path, modules: set[str]) -> dict[str, set[str]]:
    """Model names each module defines, so an unreachable ir.rule ref fails here
    instead of at install time in a governed environment."""
    found: dict[str, set[str]] = {}
    for module in sorted(modules):
        names: set[str] = set()
        base = root / "addons" / module
        if not base.is_dir():
            found[module] = names
            continue
        for path in base.rglob("*.py"):
            if "tests" in path.parts:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            names.update(m.group(1) for m in re.finditer(r"_name\s*=\s*[\"']([\w.]+)[\"']", text))
        found[module] = names
    return found


def check(root: Path, declarations_path: Path) -> dict:
    declaration = json.loads(declarations_path.read_text(encoding="utf-8"))
    enforced = declaration.get("enforced") or []
    exempt = declaration.get("exempt") or []
    by_ref, ids = scan_security_files(root)

    failures: list[str] = []
    seen: set[str] = set()
    owners: dict[str, set[str]] = {}
    for entry in enforced:
        model = entry["model"]
        anchor = entry["anchor"]
        if model in seen:
            failures.append(f"duplicate enforced entry: {model}")
        seen.add(model)
        expected = "model_" + model.replace(".", "_")
        candidates = by_ref.get(expected, [])
        if not candidates:
            failures.append(f"{model}: no ir.rule references {expected}")
            continue
        needle = f"('{anchor}'"
        scoped = [r for r in candidates if r["global"] and needle in r["domain"]]
        for owner in {r["owner_module"] for r in scoped}:
            if owner not in owners:
                owners.update(defined_models(root, {owner}))
            if model not in owners[owner]:
                failures.append(
                    f"{model}: rule in {owner} cannot resolve; {owner} does not define it"
                )
        if not scoped:
            global_rules = [r for r in candidates if r["global"]]
            detail = (
                f"{len(global_rules)} global rule(s) but none constrains {anchor}"
                if global_rules
                else "every matching rule is group-scoped (group union could widen it)"
            )
            failures.append(f"{model}: {detail}")
    for entry in exempt:
        if not (entry.get("reason") or "").strip():
            failures.append(f"{entry.get('model')}: exemption without a reason")
    overlap = sorted(seen & {entry["model"] for entry in exempt})
    if overlap:
        failures.append(f"model declared enforced and exempt: {', '.join(overlap)}")
    duplicates = sorted({xml_id for xml_id in ids if ids.count(xml_id) > 1})
    if duplicates:
        failures.append(f"duplicate ir.rule xml ids: {', '.join(duplicates)}")

    return {
        "status": "failed" if failures else "passed",
        "enforced": len(enforced),
        "exempt": len(exempt),
        "global_rules_seen": sum(1 for rules in by_ref.values() for r in rules if r["global"]),
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--declarations", default=str(DEFAULT_DECLARATIONS))
    args = parser.parse_args()
    report = check(Path(args.root), Path(args.declarations))
    for failure in report["failures"]:
        print(f"FAIL {failure}")
    print("SC_DATA_SCOPE_RULE_COVERAGE=" + json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 1 if report["failures"] else 0


if __name__ == "__main__":
    sys.exit(main())
