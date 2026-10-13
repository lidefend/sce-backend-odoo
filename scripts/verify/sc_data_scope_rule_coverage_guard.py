#!/usr/bin/env python3
"""Fail-closed check that every product-owned company model is accounted for.

The registered 744-model registry is inspection scope, not a rewrite list. This
guard reads source only (offline lane) and enforces two things:

* the explicit declaration in data_scope_declarations.json is internally sound:
  every ``enforced`` model has a *global* ir.rule (no groups, so no group union
  can widen it) whose domain constrains the declared company anchor path; every
  ``exempt`` model names one isolation dimension and its owning module; every
  ``deferred`` model belongs to a group with an issue id, an anchor, an owner
  and an actionable reason; rule xml ids stay unique across security files.
* the declaration *covers* the product model surface: every model defined by a
  product module (config/tenant/module_sets.v1.json) that declares a
  ``company_id`` field is either enforced, exempt, deferred, transient, or
  already carries a company-constraining ir.rule in source. Absence is never an
  exemption, so an undeclared company model fails here instead of surfacing as
  a silent isolation hole.
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
DEFAULT_MODULE_SETS = "config/tenant/module_sets.v1.json"

# Isolation dimensions are deliberately not duplicated onto every model. A
# non-enforced declaration states which single dimension (or which ownership
# fact) carries the model, so no reader has to infer a ceiling from an absence.
DIMENSIONS = {
    "platform_state",
    "identity_registry",
    "master_data",
    "role_scope",
    "scope_ref",
    "audit_trail",
    "delivery_orchestration",
    "technical_state",
    "transient",
    "parent_inherited",
}
PLATFORM_OWNER = "odoo_base"
PLACEHOLDER_REASONS = (
    "needs an ownership anchor",
    "record as an anchor gap",
    "anchor gap",
    "todo",
    "tbd",
    "unknown reason",
)

CLASS_BLOCK = re.compile(r"class\s+\w+\s*\([^)]*models\.\w+[^)]*\)\s*:")
NAME_LINE = re.compile(r"^\s*_name\s*=\s*[\"']([\w.]+)[\"']", re.M)
COMPANY_FIELD = re.compile(r"^\s+company_id\s*=\s*fields\.Many2one", re.M)


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
            names.update(NAME_LINE.findall(text))
        found[module] = names
    return found


def product_modules(root: Path, module_sets_path: str) -> list[str]:
    path = root / module_sets_path
    if path.is_file():
        data = json.loads(path.read_text(encoding="utf-8"))
        modules = data.get("product_modules") or []
        if modules:
            return sorted(set(modules))
    addons = root / "addons"
    return sorted(p.name for p in addons.iterdir() if p.is_dir()) if addons.is_dir() else []


def company_field_models(root: Path, modules: list[str]) -> dict[str, bool]:
    """Product-module models declaring a ``company_id`` field -> transient flag."""
    found: dict[str, bool] = {}
    for module in modules:
        base = root / "addons" / module
        if not base.is_dir():
            continue
        for path in base.rglob("*.py"):
            if "tests" in path.parts:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for match in CLASS_BLOCK.finditer(text):
                header = text[match.start():match.end()]
                end = text.find("\nclass ", match.end())
                block = text[match.end():end if end > 0 else len(text)]
                name = NAME_LINE.search(block)
                if not name or not COMPANY_FIELD.search(block):
                    continue
                found[name.group(1)] = "TransientModel" in header
    return found


def rules_for(by_ref: dict[str, list[dict]], model: str) -> list[dict]:
    return by_ref.get("model_" + model.replace(".", "_"), [])


def covers_company(rules: list[dict]) -> bool:
    return any("company_id" in rule["domain"] for rule in rules)


def check(root: Path, declarations_path: Path, module_sets_path: str = DEFAULT_MODULE_SETS) -> dict:
    declaration = json.loads(declarations_path.read_text(encoding="utf-8"))
    enforced = declaration.get("enforced") or []
    exempt = declaration.get("exempt") or []
    deferred = declaration.get("deferred") or []
    modules = product_modules(root, module_sets_path)
    universe = company_field_models(root, modules)
    by_ref, ids = scan_security_files(root)

    failures: list[str] = []
    seen: set[str] = set()
    owners: dict[str, set[str]] = {}

    def owner_defines(owner_module: str, model: str) -> bool:
        if owner_module == PLATFORM_OWNER:
            return True
        if owner_module not in modules:
            return False
        if owner_module not in owners:
            owners.update(defined_models(root, {owner_module}))
        return model in owners[owner_module]

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

    exempt_models: set[str] = set()
    for entry in exempt:
        model = entry.get("model")
        exempt_models.add(model)
        reason = (entry.get("reason") or "").strip()
        if not reason:
            failures.append(f"{model}: exemption without a reason")
        elif any(token in reason.lower() for token in PLACEHOLDER_REASONS):
            failures.append(f"{model}: exemption reason is a placeholder, not a decision")
        dimension = entry.get("dimension")
        if dimension not in DIMENSIONS:
            failures.append(
                f"{model}: exemption must name one dimension from {sorted(DIMENSIONS)}"
            )
        owner_module = entry.get("owner_module")
        if not owner_module:
            failures.append(f"{model}: exemption without an owning module")
        elif not owner_defines(owner_module, model):
            failures.append(f"{model}: {owner_module} does not define this model")
        if dimension == "transient" and model in universe and not universe[model]:
            failures.append(f"{model}: declared transient but the model is not a TransientModel")

    overlap = sorted(seen & exempt_models)
    if overlap:
        failures.append(f"model declared enforced and exempt: {', '.join(overlap)}")
    duplicates = sorted({xml_id for xml_id in ids if ids.count(xml_id) > 1})
    if duplicates:
        failures.append(f"duplicate ir.rule xml ids: {', '.join(duplicates)}")

    deferred_models: dict[str, str] = {}
    for group in deferred:
        issue = (group.get("issue") or "").strip()
        anchor = (group.get("anchor") or "").strip()
        owner_module = (group.get("owner_module") or "").strip()
        reason = (group.get("reason") or "").strip()
        models = group.get("models") or []
        if not issue:
            failures.append("deferred group without an issue id")
        if not anchor:
            failures.append(f"deferred {issue or '<no issue>'}: missing company anchor")
        if not reason or any(token in reason.lower() for token in PLACEHOLDER_REASONS):
            failures.append(f"deferred {issue or '<no issue>'}: reason is missing or a placeholder")
        if not owner_module:
            failures.append(f"deferred {issue or '<no issue>'}: missing owning module")
        if not models:
            failures.append(f"deferred {issue or '<no issue>'}: empty model list")
        for model in models:
            if model in deferred_models:
                failures.append(f"{model}: listed in two deferred groups")
            deferred_models[model] = issue
            if model in seen:
                failures.append(f"{model}: declared enforced and deferred")
            if model in exempt_models:
                failures.append(f"{model}: declared exempt and deferred")
            if covers_company(rules_for(by_ref, model)):
                failures.append(f"{model}: deferred but a company-constraining rule already exists")
            if model not in universe:
                failures.append(f"{model}: deferred but no product module declares company_id")

    source_covered: list[str] = []
    uncovered: list[str] = []
    for model, transient in sorted(universe.items()):
        if model in seen or model in exempt_models or model in deferred_models:
            continue
        if transient:
            continue
        if covers_company(rules_for(by_ref, model)):
            source_covered.append(model)
            continue
        uncovered.append(model)
    for model in uncovered:
        failures.append(
            f"{model}: product module declares company_id but has no company ceiling, "
            "exemption or deferred decision"
        )

    return {
        "status": "failed" if failures else "passed",
        "enforced": len(enforced),
        "exempt": len(exempt),
        "deferred": len(deferred_models),
        "deferred_issues": sorted({issue for issue in deferred_models.values()}),
        "universe": len(universe),
        "source_company_rule": len(source_covered),
        "uncovered": sorted(uncovered),
        "global_rules_seen": sum(1 for rules in by_ref.values() for r in rules if r["global"]),
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--declarations", default=str(DEFAULT_DECLARATIONS))
    parser.add_argument("--module-sets", default=DEFAULT_MODULE_SETS)
    args = parser.parse_args()
    report = check(Path(args.root), Path(args.declarations), args.module_sets)
    for failure in report["failures"]:
        print(f"FAIL {failure}")
    print("SC_DATA_SCOPE_RULE_COVERAGE=" + json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 1 if report["failures"] else 0


if __name__ == "__main__":
    sys.exit(main())
