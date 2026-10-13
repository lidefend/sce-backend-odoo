#!/usr/bin/env python3
"""Fail-closed check that the money fact of every product model has one source.

The company ceiling guard owns the question "which rows may this caller read".
This guard owns the adjacent question "where does a record's money fact come
from" for every product-module model (config/tenant/module_sets.v1.json) that
declares a ``currency_id`` field. It reads source only and enforces:

* the set of models that default a new record to the tenant standard currency is
  declared once in fact_source_declarations.json; the derived set must equal it,
  so adding or removing an inline standard-currency default fails here instead of
  drifting silently. The runtime pin script must pin only declared models.
* a model whose money fact would come from the caller's environment company while
  its owning company is not that caller must be registered as a known open
  alignment with an issue id, an owning module and an actionable reason. The
  divergence is seen through three shapes, because each one was invisible before:
  the owning company is a ``related`` field; the model has no ``company_id``
  column at all; or the model inherits the caller-context ``currency_id`` from a
  mixin without declaring its own field.
* the places where a ``currency_id`` is written outside the field default are
  declared. A method assignment (``record.currency_id = ...``) is a second money
  fact source even when the field default looks correct, and it is invisible to a
  field-default-only scan. Extension classes (``_inherit`` without ``_name``)
  are attributed to the model they extend, so an override cannot hide there.
* a ``company_id``/``currency_id`` field defined by an extension class instead of
  the model's own class is declared, so a redefinition is a decision, not a
  silent override.
* the tenant standard currency is pinned onto the company by a named authority;
  the declaration must name the module and method that keeps
  ``res.company.currency_id`` at the standard currency, so the caller-context
  statement of the other models cannot quietly stop being true.
* no product source may hard-code a currency other than the tenant standard, and
  no ``currency_id`` field may carry both a ``related`` and a ``default``.

Absence is never an exemption: an undeclared inline currency fact fails closed.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sc_data_scope_rule_coverage_guard as scope_guard  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DECLARATIONS = ROOT / "scripts/verify/fact_source_declarations.json"
DEFAULT_MODULE_SETS = scope_guard.DEFAULT_MODULE_SETS
RUNTIME_PIN = ROOT / "scripts/verify/finance_p0_currency_default_audit.py"
STANDARD_CURRENCY = "CNY"
PLACEHOLDER_REASONS = scope_guard.PLACEHOLDER_REASONS

FIELD_START = r"^\s+{field}\s*=\s*fields\.\w+\("
HARD_CODED_REF = re.compile(r"env\.ref\(\s*[\"']base\.([A-Z]{3})[\"']")
PIN_MODELS = re.compile(r"^\s*MODELS\s*=\s*\[(.*?)\]", re.M | re.S)
METHOD_DEF = re.compile(r"^([ \t]+)def\s+(\w+)\s*\(", re.M)
CURRENCY_WRITE = re.compile(r"^[ \t]*[A-Za-z_][\w.]*\.currency_id\s*=", re.M)
OVERRIDE_FIELDS = ("currency_id", "company_id")


def field_assignment(block: str, field: str) -> str | None:
    """The raw ``field = fields.X(...)`` text, with balanced parentheses."""
    match = re.search(FIELD_START.format(field=re.escape(field)), block, re.M)
    if not match:
        return None
    opening = block.index("(", match.end() - 1)
    depth = 0
    for index in range(opening, len(block)):
        char = block[index]
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return block[match.start():index + 1]
    return None


inherit_names = scope_guard.inherit_names
target_models = scope_guard.target_models


def currency_write_methods(block: str) -> list[str]:
    """Methods in one class block that assign ``<expr>.currency_id = ...``.

    Only record attribute assignments: an SQL fragment inside a string, a
    migration script and a ``vals`` dict key are not a second field source, but
    an assignment on a record overwrites the money fact after the default ran.
    """
    matches = list(METHOD_DEF.finditer(block))
    if not matches:
        return []
    body_indent = min(len(match.group(1)) for match in matches)
    boundaries = [
        (match.start(), match.group(2))
        for match in matches
        if len(match.group(1)) == body_indent
    ]
    found: list[str] = []
    for index, (start, method) in enumerate(boundaries):
        end = boundaries[index + 1][0] if index + 1 < len(boundaries) else len(block)
        if CURRENCY_WRITE.search(block[start:end]):
            found.append(method)
    return found


def defaults_from_caller(text: str | None) -> bool:
    """The field defaults to the caller's environment company."""
    return bool(text) and "default=" in text and "env.company" in text


def ancestors(model: str, fields: dict[str, dict]) -> set[str]:
    """Every model reachable through ``_inherit``, transitively."""
    seen: set[str] = set()
    pending = list(fields.get(model, {}).get("inherit") or [])
    while pending:
        parent = pending.pop()
        if parent in seen:
            continue
        seen.add(parent)
        pending.extend(fields.get(parent, {}).get("inherit") or [])
    return seen


def model_fields(root: Path, modules: list[str]) -> dict[str, dict]:
    """model -> {currency, company, file, inherit, definitions} in product modules.

    ``currency``/``company`` are the effective field definitions: a definition in
    an extension class (``_inherit`` without ``_name``) overrides the model's own
    class, which mirrors how Odoo merges such a class into the model, so a
    redefinition cannot hide from the money-fact classification.
    """
    constants = scope_guard.model_name_constants(root, modules)
    blocks: list[tuple[Path, str]] = []
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
            blocks.extend((path, block) for _match, block in scope_guard.class_blocks(text))

    known: set[str] = set()
    for _path, block in blocks:
        name, _unresolvable = scope_guard.resolve_model_name(block, constants)
        if name:
            known.add(name)

    found: dict[str, dict] = {}
    for path, block in blocks:
        owner = bool(
            scope_guard.resolve_model_name(block, constants)[0]
        )
        inherit = inherit_names(block)
        for model in target_models(block, constants, known):
            entry = found.setdefault(model, {})
            if inherit:
                entry["inherit"] = sorted(set(entry.get("inherit") or []) | set(inherit))
            for method in currency_write_methods(block):
                methods = entry.setdefault("write_methods", [])
                if method not in methods:
                    methods.append(method)
            for field, key in (("currency_id", "currency"), ("company_id", "company")):
                assignment = field_assignment(block, field)
                if not assignment:
                    continue
                relative = path.relative_to(root).as_posix()
                entry.setdefault("definitions", {}).setdefault(field, []).append(
                    {"file": relative, "extension": not owner}
                )
                if owner:
                    if not entry.get(key):
                        entry[key] = assignment
                        entry[f"{key}_file"] = relative
                else:
                    # An extension class redefines the field on the same model;
                    # Odoo applies that definition, so classify on it.
                    entry[key] = assignment
                    entry[f"{key}_file"] = relative
    for entry in found.values():
        entry["write_methods"] = sorted(entry.get("write_methods") or [])
        if entry.get("currency"):
            entry["file"] = entry.pop("currency_file", entry.get("file"))
        entry.pop("company_file", None)
    return found


def hard_coded_currencies(root: Path, modules: list[str]) -> list[str]:
    findings: list[str] = []
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
            for match in HARD_CODED_REF.finditer(text):
                if match.group(1) != STANDARD_CURRENCY:
                    findings.append(
                        f"{path.relative_to(root).as_posix()}: hard-codes base.{match.group(1)}"
                    )
    return sorted(set(findings))


def pinned_models(path: Path) -> list[str]:
    if not path.is_file():
        return []
    match = PIN_MODELS.search(path.read_text(encoding="utf-8"))
    if not match:
        return []
    return re.findall(r"[\"']([\w.]+)[\"']", match.group(1))


def caller_context_currency(fields: dict[str, dict]) -> tuple[set[str], dict[str, list[str]]]:
    """Models whose money fact is the caller's company instead of their own.

    Three shapes, all invisible to a field-default-only scan of derived companies:

    * ``company_id`` is a ``related`` field, so the owning company belongs to
      another relation;
    * the model has no ``company_id`` column at all, so the record carries no
      company of its own to own the currency;
    * the model inherits the caller-context ``currency_id`` from a mixin without
      declaring its own field.

    A model whose company fact and money fact both default from the same caller
    environment company is not a divergence: ``company_id`` and ``currency_id``
    agree, so the money fact has one source.
    """
    own: set[str] = set()
    for model, entry in fields.items():
        currency = entry.get("currency")
        if not currency:
            continue
        if "env.company.currency_id" not in currency:
            continue
        if f"base.{STANDARD_CURRENCY}" in currency:
            continue
        if "related=" in currency:
            continue
        company = entry.get("company")
        if company and "related=" not in company and defaults_from_caller(company):
            continue
        own.add(model)
    inherited: dict[str, list[str]] = {}
    for model, entry in fields.items():
        if model in own or entry.get("currency"):
            continue
        if defaults_from_caller(entry.get("company")):
            continue
        hits = sorted(carrier for carrier in ancestors(model, fields) if carrier in own)
        if hits:
            inherited[model] = hits
    return own, inherited


def currency_write_paths(fields: dict[str, dict], declares: dict) -> tuple[list[str], list[str]]:
    """``model.method`` write paths outside the field default, derived vs declared."""
    derived = sorted(
        f"{model}.{method}"
        for model, entry in fields.items()
        for method in entry.get("write_methods") or []
    )
    declared = sorted(
        f"{entry['model']}.{method}"
        for entry in ((declares.get("currency_write_paths") or {}).get("models") or [])
        if isinstance(entry, dict)
        for method in entry.get("methods") or []
    )
    return derived, declared


def company_field_overrides(fields: dict[str, dict]) -> set[str]:
    """Models whose company_id/currency_id is defined by an extension class."""
    overrides: set[str] = set()
    for model, entry in fields.items():
        for field, definitions in (entry.get("definitions") or {}).items():
            if any(definition.get("extension") for definition in definitions):
                overrides.add(model)
    return overrides


def company_currency_authority(
    root: Path, modules: list[str], declares: dict, standard: dict
) -> tuple[list[str], dict]:
    """The named pin that keeps ``res.company.currency_id`` at the standard currency."""
    failures: list[str] = []
    authority = declares.get("company_currency_authority") or {}
    declared = {
        "model": (authority.get("model") or "").strip(),
        "module": (authority.get("module") or "").strip(),
        "method": (authority.get("method") or "").strip(),
        "currency": (authority.get("currency") or "").strip(),
    }
    if not declared["model"] and not declared["method"]:
        if standard.get("models"):
            failures.append(
                "standard_currency is declared but the company-currency authority is not "
                "registered, so nothing keeps res.company.currency_id at the standard currency"
            )
        return failures, {"status": "not_declared"}
    for key in ("model", "module", "method"):
        if not declared[key]:
            failures.append(f"company_currency_authority without a {key}")
    if declared["currency"] and declared["currency"] != STANDARD_CURRENCY:
        failures.append("company_currency_authority does not pin the standard currency")
    if declared["model"] and declared["model"] != "res.company":
        failures.append("company_currency_authority must pin res.company.currency_id")
    module_dir = root / "addons" / declared["module"]
    if declared["module"] in modules and module_dir.is_dir():
        text = "\n".join(
            path.read_text(encoding="utf-8", errors="replace")
            for path in module_dir.rglob("*.py")
            if "tests" not in path.parts
        )
        if f"def {declared['method']}" not in text:
            failures.append(
                f"company_currency_authority {declared['method']} is not defined in "
                f"{declared['module']}"
            )
        if f"base.{STANDARD_CURRENCY}" not in text:
            failures.append(
                "company_currency_authority no longer references the standard currency"
            )
    return failures, {"status": "failed" if failures else "verified", **declared}


def check(root: Path, declarations_path: Path, module_sets_path: str = DEFAULT_MODULE_SETS,
          runtime_pin: Path | None = None) -> dict:
    declaration = json.loads(declarations_path.read_text(encoding="utf-8"))
    declares = declaration
    standard = declaration.get("standard_currency") or {}
    caller = declaration.get("caller_context_currency") or {}
    modules = scope_guard.product_modules(root, module_sets_path)
    fields = model_fields(root, modules)

    failures: list[str] = []

    declared_standard = [entry["model"] for entry in standard.get("models") or []]
    for entry in standard.get("models") or []:
        if not (entry.get("reason") or "").strip():
            failures.append(f"{entry['model']}: standard currency without a reason")
    derived_standard = sorted(
        model
        for model, entry in fields.items()
        if entry.get("currency") and f'base.{STANDARD_CURRENCY}' in entry["currency"]
    )
    if sorted(set(declared_standard)) != derived_standard:
        missing = sorted(set(derived_standard) - set(declared_standard))
        extra = sorted(set(declared_standard) - set(derived_standard))
        if missing:
            failures.append(
                "undeclared standard-currency default (declare it or derive the currency "
                f"from the owning fact): {', '.join(missing)}"
            )
        if extra:
            failures.append(
                "declared standard-currency model has no inline standard-currency fact; "
                f"the declaration drifted from source: {', '.join(extra)}"
            )
    if len(declared_standard) != len(set(declared_standard)):
        failures.append("standard_currency lists a model twice")

    undeclared_pins = sorted(set(pinned_models(runtime_pin or RUNTIME_PIN)) - set(declared_standard))
    if undeclared_pins:
        failures.append(
            "runtime pin script asserts standard currency for undeclared models: "
            f"{', '.join(undeclared_pins)}"
        )

    issue = (caller.get("issue") or "").strip()
    owner_module = (caller.get("owner_module") or "").strip()
    reason = (caller.get("reason") or "").strip()
    declared_caller = [
        entry["model"] if isinstance(entry, dict) else entry
        for entry in (caller.get("models") or [])
    ]
    if declared_caller:
        if not issue:
            failures.append("caller_context_currency without an issue id")
        if not owner_module:
            failures.append("caller_context_currency without an owning module")
        if not reason or any(token in reason.lower() for token in PLACEHOLDER_REASONS):
            failures.append("caller_context_currency reason is missing or a placeholder")
        owners = scope_guard.defined_models(root, {owner_module}) if owner_module else {}
        for model in declared_caller:
            if owner_module and owner_module in modules and model not in owners.get(owner_module, set()):
                failures.append(
                    f"{model}: caller_context_currency owner {owner_module} does not define it"
                )
    derived_own, derived_inherited = caller_context_currency(fields)
    derived_caller = sorted(set(derived_own) | set(derived_inherited))
    if derived_caller != sorted(set(declared_caller)):
        missing = sorted(set(derived_caller) - set(declared_caller))
        extra = sorted(set(declared_caller) - set(derived_caller))
        if missing:
            failures.append(
                "currency comes from the caller's environment company while the owning "
                "company is not that caller (derived company, no company column, or an "
                f"inherited field); register it or derive the currency: {', '.join(missing)}"
            )
        if extra:
            failures.append(
                "caller_context_currency lists models whose source no longer matches: "
                f"{', '.join(extra)}"
            )

    write_paths, declared_paths = currency_write_paths(fields, declares)
    if write_paths != declared_paths:
        missing = sorted(set(write_paths) - set(declared_paths))
        extra = sorted(set(declared_paths) - set(write_paths))
        if missing:
            failures.append(
                "currency_id is written outside the field default and is not declared; "
                f"the money fact has a second source: {', '.join(missing)}"
            )
        if extra:
            failures.append(
                "declared currency write path no longer matches source: "
                f"{', '.join(extra)}"
            )

    for entry in (declares.get("currency_write_paths") or {}).get("models") or []:
        if not isinstance(entry, dict):
            continue
        if not (entry.get("source") or "").strip():
            failures.append(
                f"{entry.get('model')}: currency write path without the source relation it copies"
            )
        if not (entry.get("reason") or "").strip():
            failures.append(f"{entry.get('model')}: currency write path without a reason")

    overrides = company_field_overrides(fields)
    declared_overrides = {
        (entry["model"] if isinstance(entry, dict) else entry)
        for entry in ((declares.get("company_field_overrides") or {}).get("models") or [])
    }
    if overrides and overrides != declared_overrides:
        missing = sorted(overrides - declared_overrides)
        extra = sorted(declared_overrides - overrides)
        if missing:
            failures.append(
                "an extension class redefines company_id/currency_id on a product model "
                f"without a declaration: {', '.join(missing)}"
            )
        if extra:
            failures.append(
                "declared field override no longer matches source: " f"{', '.join(extra)}"
            )
    for entry in ((declares.get("company_field_overrides") or {}).get("models") or []):
        if isinstance(entry, dict) and not (entry.get("reason") or "").strip():
            failures.append(f"{entry.get('model')}: field override without a reason")

    authority_failures, authority = company_currency_authority(root, modules, declares, standard)
    failures.extend(authority_failures)

    contradictions = sorted(
        model
        for model, entry in fields.items()
        if entry.get("currency")
        and "related=" in entry["currency"]
        and "default=" in entry["currency"]
    )
    for model in contradictions:
        failures.append(f"{model}: currency_id is both related and defaulted")

    for finding in hard_coded_currencies(root, modules):
        failures.append(finding)

    return {
        "status": "failed" if failures else "passed",
        "standard_currency": STANDARD_CURRENCY,
        "standard_currency_models": derived_standard,
        "caller_context_currency_models": derived_caller,
        "caller_context_inherited_models": sorted(derived_inherited),
        "currency_write_paths": write_paths,
        "company_field_overrides": sorted(overrides),
        "company_currency_authority": authority,
        "currency_models": len([m for m, e in fields.items() if e.get("currency")]),
        "ownership_derived_currency": len(
            [m for m, e in fields.items() if e.get("currency") and "related=" in e["currency"]]
        ),
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--declarations", default=str(DEFAULT_DECLARATIONS))
    parser.add_argument("--module-sets", default=DEFAULT_MODULE_SETS)
    parser.add_argument("--runtime-pin", default=str(RUNTIME_PIN))
    args = parser.parse_args()
    report = check(
        Path(args.root), Path(args.declarations), args.module_sets, Path(args.runtime_pin)
    )
    for failure in report["failures"]:
        print(f"FAIL {failure}")
    print("FACT_SOURCE_COVERAGE=" + json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 1 if report["failures"] else 0


if __name__ == "__main__":
    sys.exit(main())
