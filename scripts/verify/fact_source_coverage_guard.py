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
  the model's own class fails closed, so the money fact cannot move into a second
  file that the owning declaration does not show.
* a field declared by more than one class block on the same model fails closed,
  because Odoo merges the two definitions attribute by attribute: the surviving
  field is a union of both, so neither file alone shows the real declaration.
  There is no registration escape hatch; consolidate into one declaration.
* every product source that writes ``res.company.currency_id`` -- an XML record, a
  method on the company model, or a bootstrap function that resolves the company
  model -- is declared, so the four shapes that carry the tenant standard
  currency cannot hide behind each other.
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
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import backend_model_field_declarations as field_declarations  # noqa: E402
import sc_data_scope_rule_coverage_guard as scope_guard  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DECLARATIONS = ROOT / "scripts/verify/fact_source_declarations.json"
DEFAULT_MODULE_SETS = scope_guard.DEFAULT_MODULE_SETS
RUNTIME_PIN = ROOT / "scripts/verify/finance_p0_currency_default_audit.py"
STANDARD_CURRENCY = "CNY"
PLACEHOLDER_REASONS = scope_guard.PLACEHOLDER_REASONS

FIELD_START = r"^\s+{field}\s*=\s*fields\.\w+\("
FIELD_DEFINITION = re.compile(r"^[ \t]+(\w+)\s*=\s*fields\.\w+\(", re.M)
CURRENCY_DICT_WRITE = re.compile(r"\.write\(\s*\{[^}]*[\"']currency_id[\"']", re.S)
COMPANY_MODEL_REF = re.compile(r"[\"']res\.company[\"']")
MODULE_FUNC_DEF = re.compile(r"^def\s+(\w+)\s*\(", re.M)
HARD_CODED_REF = re.compile(r"env\.ref\(\s*[\"']base\.([A-Z]{3})[\"']")
PIN_MODELS = re.compile(r"^\s*MODELS\s*=\s*\[(.*?)\]", re.M | re.S)
METHOD_DEF = re.compile(r"^([ \t]+)def\s+(\w+)\s*\(", re.M)
CURRENCY_WRITE = re.compile(r"^[ \t]*[A-Za-z_][\w.]*\.currency_id\s*=", re.M)
OVERRIDE_FIELDS = ("currency_id", "company_id")

# A business document number has exactly one generator: the ir.sequence record
# product data publishes for a code, read back through ``next_by_code(code)``.
# The shapes below let the scan see, per function, whether the value can become
# something other than that sequence: an ``or`` fallback on the call, a local
# that holds the sequence value and is then OR-ed or guarded, and a call whose
# code argument is not a literal.
NEXT_BY_CODE_CALL = re.compile(r"next_by_code\(([^()]*)\)")
NEXT_BY_CODE_OR = re.compile(r"next_by_code\([^()]*\)\s*or\s+([^\n]{0,80})")
SEQUENCE_LOCAL = re.compile(r"([A-Za-z_]\w*)\s*=\s*[^\n]*next_by_code\([^()]*\)")
ASSIGN_TAIL = re.compile(r'''([A-Za-z_][\w.]*(?:\[["'][\w]+["']\])?)\s*=\s*[^\n]*$''')
NAME_TARGET = re.compile(r'''(?:^|[.\[])[\"']?name[\"']?\]?$''')
SEQUENCE_MODEL = "ir.sequence"

# A fallback that only restores the field's own declared label is not a second
# authority: the name field already defaults to that label when the sequence is
# absent. Every other fallback class is a real second value and is registered.
BENIGN_SECOND_VALUE_CLASSES = ("name_label_fallback", "chained_sequence_then_label")
REGISTERED_SECOND_VALUE_CLASSES = (
    "derived_token",
    "unique_key_second_generator",
    "unique_key_from_label",
)


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


def class_source_blocks(root: Path, modules: list[str]) -> list[tuple[Path, str]]:
    """(file, class body) for every model class in the product modules."""
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
    return blocks


def model_fields(root: Path, modules: list[str]) -> dict[str, dict]:
    """model -> {currency, company, file, inherit, definitions} in product modules.

    ``currency``/``company`` are the effective field definitions: a definition in
    an extension class (``_inherit`` without ``_name``) overrides the model's own
    class, which mirrors how Odoo merges such a class into the model, so a
    redefinition cannot hide from the money-fact classification.
    """
    constants = scope_guard.model_name_constants(root, modules)
    blocks = class_source_blocks(root, modules)

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


def function_bodies(
    text: str, definition: re.Pattern, name_group: int, indent_group: int | None
) -> list[tuple[str, str]]:
    """``(name, body)`` for the functions one scan should read.

    ``indent_group`` names the capture that holds indentation when only one
    nesting level is wanted (methods inside a class body); ``None`` keeps every
    match, which is right for module-level ``def`` at column zero.
    """
    matches = list(definition.finditer(text))
    if not matches:
        return []
    if indent_group is None:
        boundaries = [(match.start(), match.group(name_group)) for match in matches]
    else:
        indent = min(len(match.group(indent_group)) for match in matches)
        boundaries = [
            (match.start(), match.group(name_group))
            for match in matches
            if len(match.group(indent_group)) == indent
        ]
    bodies: list[tuple[str, str]] = []
    for index, (start, name) in enumerate(boundaries):
        end = boundaries[index + 1][0] if index + 1 < len(boundaries) else len(text)
        bodies.append((name, text[start:end]))
    return bodies


def company_currency_write_sites(root: Path, modules: list[str]) -> list[tuple[str, str, str]]:
    """``(file, kind, site)`` for every product source that writes the company currency.

    ``res.company.currency_id`` is the carrier of the tenant standard currency,
    and it is written through three shapes that no single scan sees together: an
    XML record on ``res.company``, a method on a class that extends the company
    model, and a module-level bootstrap function that resolves ``res.company``
    and writes the field through a ``vals`` dict. Reading one shape hid the
    others, so all of them are named and compared as one set.
    """
    sites: set[tuple[str, str, str]] = set()
    for module in modules:
        base = root / "addons" / module
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.xml")):
            try:
                tree = ET.parse(path)
            except ET.ParseError:
                continue
            for record in tree.iter("record"):
                if record.get("model") != "res.company":
                    continue
                if any(field.get("name") == "currency_id" for field in record.findall("field")):
                    sites.add(
                        (
                            path.relative_to(root).as_posix(),
                            "xml_record",
                            record.get("id") or "",
                        )
                    )
        for path in sorted(base.rglob("*.py")):
            if "tests" in path.parts:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            relative = path.relative_to(root).as_posix()
            for _match, source in scope_guard.class_blocks(text):
                name, _unresolvable = scope_guard.resolve_model_name(source, {})
                if "res.company" not in set(inherit_names(source)) and name != "res.company":
                    continue
                for method, body in function_bodies(source, METHOD_DEF, 2, 1):
                    if CURRENCY_WRITE.search(body) or CURRENCY_DICT_WRITE.search(body):
                        sites.add((relative, "function", method))
            for function, body in function_bodies(text, MODULE_FUNC_DEF, 1, None):
                if COMPANY_MODEL_REF.search(body) and (
                    CURRENCY_WRITE.search(body) or CURRENCY_DICT_WRITE.search(body)
                ):
                    sites.add((relative, "function", function))
    return sorted(sites)


def duplicate_field_declarations(root: Path, modules: list[str]) -> dict[str, list[dict]]:
    """``model.field`` declared by more than one class block, with its files.

    The strict declaration guard owns the pass/fail decision; this wrapper keeps
    the money-fact report's historical shape while sharing the scanner. A
    duplicate has no registration escape hatch: it is a hidden union of two
    declarations and must be consolidated.
    """
    return field_declarations.duplicate_fields(root, modules)


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


STATE_MACHINE_REL = "models/support/state_machine.py"
CLASS_CONSTANT = re.compile(
    r"^\s{4}([A-Z][A-Z0-9_]*)\s*=\s*[\"']([a-z][a-z0-9_.]*)[\"']\s*$", re.M
)
REGISTRY_BLOCK = re.compile(r"_REGISTRY\s*=\s*\{(?P<body>.*?)\n\s{4}\}", re.S)
REGISTRY_KEY = re.compile(r"^\s{8}([A-Z][A-Z0-9_]*)\s*:", re.M)
TRANSITION_ATTR = re.compile(
    r"^[ \t]+(?P<name>_?[A-Za-z0-9_]*TRANSITIONS[A-Za-z0-9_]*)\s*=", re.M
)
SELECTION_CONSUMER = re.compile(
    r"ScStateMachine\.selection\(\s*ScStateMachine\.(?P<key>[A-Z][A-Z0-9_]*)\s*\)"
)
BYPASS_SITE = re.compile(r"allow_transition\s*=\s*True")


def state_machine_path(root: Path, modules: list[str]) -> Path | None:
    """The one file that owns the declared lifecycle tables."""
    for module in modules:
        candidate = root / "addons" / module / STATE_MACHINE_REL
        if candidate.is_file():
            return candidate
    return None


def state_registry(text: str) -> dict[str, str]:
    """``REGISTRY_KEY -> model name`` for every model the tables cover."""
    constants = {match.group(1): match.group(2) for match in CLASS_CONSTANT.finditer(text)}
    block = REGISTRY_BLOCK.search(text)
    if not block:
        return {}
    return {
        key: constants[key]
        for key in REGISTRY_KEY.findall(block.group("body"))
        if key in constants
    }


def product_sources(root: Path, modules: list[str]):
    """Every non-test Python file of the product modules."""
    for module in sorted(modules):
        base = root / "addons" / module
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.py")):
            if "tests" in path.parts:
                continue
            yield path


def enclosing_method(text: str, offset: int) -> str:
    """The method a byte offset sits in, for a stable site label."""
    name = "<module>"
    for match in METHOD_DEF.finditer(text):
        if match.start() > offset:
            break
        name = match.group(2)
    return name


def state_fact(root: Path, modules: list[str], declares: dict) -> tuple[list[str], dict]:
    """The declared lifecycle must be the one fact every writer obeys.

    Three ways a second state fact used to appear silently: a registered model
    whose ``write`` never consults its table, a model that declares its own
    transition table next to the canonical one, and a model that borrows a
    lifecycle ``Selection`` without belonging to it. Each is derived here and
    must equal the declaration; absence is never an exemption.
    """
    declared = declares.get("state_fact") or {}
    failures: list[str] = []
    source = state_machine_path(root, modules)
    if source is None:
        if declared.get("enforcements"):
            return [
                "state_fact: an enforcement is declared but no product module owns the "
                "state-machine source"
            ], {}
        return [], {"status": "not_applicable"}
    registry = state_registry(source.read_text(encoding="utf-8", errors="replace"))
    if not registry:
        return ["state_fact: the state registry could not be read"], {}

    entries = declared.get("enforcements") or []
    by_model: dict[str, dict] = {}
    for entry in entries:
        model = entry.get("model")
        if not model:
            failures.append("state_fact: an enforcement entry has no model")
            continue
        if model in by_model:
            failures.append(f"state_fact: {model} is declared twice")
        by_model[model] = entry
    for model in sorted(set(registry.values()) - set(by_model)):
        failures.append(f"state_fact: {model} is registered but has no declared enforcement")
    for model in sorted(set(by_model) - set(registry.values())):
        failures.append(f"state_fact: {model} declares an enforcement but is not registered")

    enforced_models: list[str] = []
    for model in sorted(set(registry.values()) & set(by_model)):
        entry = by_model[model]
        if entry.get("enforced"):
            rel = entry.get("file")
            token = entry.get("token")
            if not rel or not token:
                failures.append(f"state_fact: {model} is enforced without a file and token")
                continue
            path = root / rel
            if not path.is_file():
                failures.append(f"state_fact: {model} enforcement file is missing: {rel}")
                continue
            if token not in path.read_text(encoding="utf-8", errors="replace"):
                failures.append(
                    f"state_fact: {model} enforcement token {token!r} is absent from {rel}"
                )
                continue
            enforced_models.append(model)
            continue
        if not (entry.get("reason") or "").strip():
            failures.append(f"state_fact: {model} is unenforced without a reason")
        if not (entry.get("next_exact_step") or "").strip():
            failures.append(f"state_fact: {model} is unenforced without a next step")

    canonical = source.relative_to(root).as_posix()
    derived_tables: dict[tuple[str, str], int] = {}
    for path in product_sources(root, modules):
        rel = path.relative_to(root).as_posix()
        if rel == canonical:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in TRANSITION_ATTR.finditer(text):
            key = (rel, match.group("name"))
            derived_tables[key] = derived_tables.get(key, 0) + 1
    declared_tables = {
        (entry.get("file"), entry.get("name"))
        for entry in declared.get("transition_tables") or []
    }
    for key in sorted(set(derived_tables) - declared_tables):
        failures.append(f"state_fact: {key[0]} declares a second transition table {key[1]}")
    for key in sorted(declared_tables - set(derived_tables)):
        failures.append(f"state_fact: declared transition table {key[0]}:{key[1]} is gone")
    for key, count in sorted(derived_tables.items()):
        if count > 1:
            failures.append(
                f"state_fact: {key[0]} declares {key[1]} {count} times"
            )

    constants = scope_guard.model_name_constants(root, modules)
    known = set(registry.values())
    for names in scope_guard.defined_models(root, set(modules)).values():
        known.update(names)
    declared_stage = {
        (entry.get("model"), entry.get("key"))
        for entry in declared.get("selection_stage_references") or []
    }
    derived_stage: set[tuple[str, str]] = set()
    for path in product_sources(root, modules):
        text = path.read_text(encoding="utf-8", errors="replace")
        if "ScStateMachine.selection(" not in text:
            continue
        if path == source:
            continue
        for match in SELECTION_CONSUMER.finditer(text):
            block = None
            for candidate, body in scope_guard.class_blocks(text):
                if candidate.start() > match.start():
                    break
                block = body
            if block is None:
                failures.append(
                    f"state_fact: a {match.group('key')} selection consumer outside any class: "
                    f"{path.relative_to(root).as_posix()}"
                )
                continue
            for model in scope_guard.target_models(block, constants, known):
                derived_stage.add((model, match.group("key")))
    for model, key in sorted(derived_stage):
        if model in registry.values():
            continue
        if (model, key) in declared_stage:
            continue
        failures.append(f"state_fact: {model} borrows the {key} lifecycle selection undeclared")
    for model, key in sorted(declared_stage - derived_stage):
        failures.append(f"state_fact: declared stage reference {model}:{key} is gone")

    derived_bypass: dict[tuple[str, str], int] = {}
    for model in sorted(set(registry.values()) & set(by_model)):
        entry = by_model[model]
        rel = entry.get("file")
        if not rel:
            continue
        path = root / rel
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in BYPASS_SITE.finditer(text):
            key = (rel, enclosing_method(text, match.start()))
            derived_bypass[key] = derived_bypass.get(key, 0) + 1
    declared_bypass = {
        (entry.get("file"), entry.get("method"))
        for entry in declared.get("bypass_sites") or []
    }
    for key in sorted(set(derived_bypass) - declared_bypass):
        failures.append(
            f"state_fact: {key[0]} bypasses the declared table in {key[1]} undeclared"
        )
    for key in sorted(declared_bypass - set(derived_bypass)):
        failures.append(f"state_fact: declared bypass site {key[0]}:{key[1]} is gone")

    return failures, {
        "registry_models": sorted(registry.values()),
        "enforced_models": sorted(enforced_models),
        "unenforced_models": sorted(set(registry.values()) - set(enforced_models)),
        "transition_tables": sorted(f"{rel}:{name}" for rel, name in derived_tables),
        "selection_consumers": sorted(f"{model}:{key}" for model, key in derived_stage),
        "bypass_sites": sorted(f"{rel}:{method}" for rel, method in derived_bypass),
    }


def sequence_codes_published(root: Path, modules: list[str]) -> dict[str, str]:
    """code -> the product-module data file that publishes the ir.sequence."""
    published: dict[str, str] = {}
    for module in modules:
        base = root / "addons" / module
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.xml")):
            try:
                tree = ET.parse(path)
            except ET.ParseError:
                continue
            for record in tree.getroot().iter("record"):
                if record.get("model") != SEQUENCE_MODEL:
                    continue
                code = None
                for field in record.findall("field"):
                    if field.get("name") == "code":
                        code = (field.text or "").strip()
                if code:
                    published.setdefault(code, str(path.relative_to(root)))
    return published


def sequence_read_sites(root: Path, modules: list[str]) -> dict:
    """Every product-module read of a business-number sequence.

    Returns the reader files with the codes they read, the calls whose code is
    not a literal, and the functions where the value can become a second fact.
    """
    readers: dict[str, set[str]] = {}
    dynamic: set[tuple[str, str, str]] = set()
    second_value: set[tuple[str, str]] = set()
    for module in modules:
        base = root / "addons" / module
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.py")):
            if "tests" in path.parts:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if "next_by_code" not in text:
                continue
            relative = str(path.relative_to(root))
            for match in NEXT_BY_CODE_CALL.finditer(text):
                argument = match.group(1).strip()
                if argument[:1] in ("\"", "'"):
                    readers.setdefault(relative, set()).add(argument.strip("\"'"))
            functions = function_bodies(text, MODULE_FUNC_DEF, 1, None)
            functions += function_bodies(text, METHOD_DEF, 2, 1)
            for name, body in functions:
                if "next_by_code" not in body:
                    continue
                for match in NEXT_BY_CODE_CALL.finditer(body):
                    argument = match.group(1).strip()
                    if argument[:1] not in ("\"", "'"):
                        dynamic.add((relative, name, argument))
                second = False
                for match in NEXT_BY_CODE_OR.finditer(body):
                    head = body[: match.start()].rsplit("\n", 1)[-1]
                    targets = ASSIGN_TAIL.findall(head)
                    target = targets[-1] if targets else ""
                    fallback = match.group(1).strip()
                    label = fallback.startswith("_(") or fallback[:1] in ("\"", "'")
                    if not (target and NAME_TARGET.search(target) and label):
                        second = True
                for match in SEQUENCE_LOCAL.finditer(body):
                    local = match.group(1)
                    tail = body[match.end():]
                    guarded = re.search(r"if\s+not\s+%s\s*:" % re.escape(local), tail)
                    ored = re.search(r"(?<![\w.])%s\s+or\s+" % re.escape(local), tail)
                    if (guarded or ored) and not NAME_TARGET.search(local):
                        second = True
                if second:
                    second_value.add((relative, name))
    return {
        "readers": {file: sorted(codes) for file, codes in readers.items()},
        "dynamic": sorted(dynamic),
        "second_value": sorted(second_value),
    }


def business_number_authority(root: Path, modules: list[str], declares: dict) -> tuple[list[str], dict]:
    """One published ir.sequence is the single generator of a business number.

    Every product-module read has to name the code it reads, the published set
    has to match what the declaration says, and every site where the value can
    become a second fact has to be registered with its class. A code that no
    product data publishes is a declaration gap, not a silent fallback.
    """
    declared = declares.get("business_number_authority") or {}
    failures: list[str] = []
    measured = sequence_read_sites(root, modules)
    published = sequence_codes_published(root, modules)

    if not declared:
        if measured["readers"] or published:
            failures.append(
                "product modules read ir.sequence business numbers but "
                "business_number_authority is not declared"
            )
        return failures, {"readers": 0, "codes": 0}

    issue = (declared.get("issue") or "").strip()
    reason = (declared.get("reason") or "").strip()
    if not issue:
        failures.append("business_number_authority without an issue id")
    if not reason or any(token in reason.lower() for token in PLACEHOLDER_REASONS):
        failures.append("business_number_authority reason is missing or a placeholder")

    declared_readers = {
        entry.get("file"): set(entry.get("codes") or [])
        for entry in (declared.get("reader_files") or [])
    }
    if len(declared_readers) != len(declared.get("reader_files") or []):
        failures.append("business_number_authority lists a reader file twice")
    measured_readers = measured["readers"]
    for file in sorted(set(measured_readers) - set(declared_readers)):
        failures.append(
            f"{file}: reads an ir.sequence business number without naming it in "
            "business_number_authority.reader_files"
        )
    for file in sorted(set(declared_readers) - set(measured_readers)):
        failures.append(
            f"{file}: declared as a business-number reader but no longer reads one"
        )
    for file in sorted(set(measured_readers) & set(declared_readers)):
        codes = measured_readers[file]
        if codes != sorted(declared_readers[file]):
            failures.append(
                f"{file}: business-number codes changed to {codes}; the declaration "
                f"still says {sorted(declared_readers[file])}"
            )

    read_codes = {code for codes in measured_readers.values() for code in codes}
    published_codes = set(published)
    # ``codes`` is an exception registry: the reader files already name every
    # code a product module reads, so repeating the published-and-read set here
    # would create a second place to keep in sync. Only the two mismatches are
    # registered, each with the reason it is tolerated.
    exception_codes = (published_codes - read_codes) | (read_codes - published_codes)
    declared_code_list = [entry.get("code") for entry in (declared.get("codes") or [])]
    for code in declared_code_list:
        if not code:
            failures.append("business_number_authority lists a code without an id")
    for code in sorted({code for code in declared_code_list if declared_code_list.count(code) > 1}):
        failures.append(f"{code}: business_number_authority lists this code twice")
    declared_codes = set(declared_code_list)
    for code in sorted(published_codes - read_codes):
        if code not in declared_codes:
            failures.append(
                f"{code}: product data publishes this business-number rule but no "
                "product code reads it; register it as an unread published rule"
            )
    for code in sorted(read_codes - published_codes):
        if code not in declared_codes:
            failures.append(
                f"{code}: a product module reads this business-number code but no "
                "product data publishes it; publish the ir.sequence or register the gap"
            )
    for entry in declared.get("codes") or []:
        code = entry.get("code")
        if not code:
            continue
        if code not in exception_codes:
            failures.append(
                f"{code}: registered as a business-number exception but source has no "
                "publication/read mismatch for it"
            )
        if not (entry.get("reason") or "").strip():
            failures.append(f"{code}: business-number exception without a reason")

    for entry in declared.get("dynamic_reads") or []:
        site = (entry.get("file"), entry.get("function"), entry.get("argument"))
        if site not in set(measured["dynamic"]):
            failures.append(
                f"{entry.get('file')}:{entry.get('function')}: registered dynamic "
                "business-number read no longer matches source"
            )
        if not (entry.get("reason") or "").strip():
            failures.append(
                f"{entry.get('file')}:{entry.get('function')}: dynamic business-number "
                "read without a reason"
            )
    for site in sorted(set(measured["dynamic"])):
        if site not in {
            (e.get("file"), e.get("function"), e.get("argument"))
            for e in (declared.get("dynamic_reads") or [])
        }:
            failures.append(
                f"{site[0]}:{site[1]}: reads the business-number sequence through the "
                f"non-literal code {site[2]!r} without a registration"
            )

    declared_second = {
        (entry.get("file"), entry.get("function")): entry
        for entry in (declared.get("second_value_sites") or [])
    }
    for site in sorted(set(measured["second_value"])):
        if site not in declared_second:
            failures.append(
                f"{site[0]}:{site[1]}: a business-number read can fall back to a second "
                "fact without a registered class"
            )
    for site in sorted(set(declared_second) - set(measured["second_value"])):
        failures.append(
            f"{site[0]}:{site[1]}: registered business-number fallback site no longer "
            "matches source"
        )
    for site, entry in sorted(declared_second.items()):
        klass = (entry.get("class") or "").strip()
        if klass not in BENIGN_SECOND_VALUE_CLASSES + REGISTERED_SECOND_VALUE_CLASSES:
            failures.append(
                f"{site[0]}:{site[1]}: unknown business-number fallback class {klass!r}"
            )
        if klass in REGISTERED_SECOND_VALUE_CLASSES and not (entry.get("issue") or "").strip():
            failures.append(
                f"{site[0]}:{site[1]}: a {klass} fallback still needs the owning issue"
            )
        if not (entry.get("reason") or "").strip():
            failures.append(f"{site[0]}:{site[1]}: fallback site without a reason")

    return failures, {
        "issue": issue,
        "reader_files": len(measured_readers),
        "codes": len(read_codes),
        "published_codes": len(published),
        "unpublished_codes": sorted(read_codes - set(published)),
        "unread_published_codes": sorted(set(published) - read_codes),
        "dynamic_reads": [":".join(site) for site in measured["dynamic"]],
        "second_value_sites": [":".join(site) for site in measured["second_value"]],
    }


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
    if overrides:
        failures.append(
            "an extension class declares company_id/currency_id on a product model; "
            "Odoo merges the declaration into the model, so the money fact has a "
            "second source that the owning file cannot show. Consolidate it into the "
            f"owning declaration: {', '.join(sorted(overrides))}"
        )

    scanned_fields = field_declarations.scan(root, modules)
    duplicates, same_class_duplicates = field_declarations.conflicts(scanned_fields)
    for key, items in duplicates.items():
        failures.append(
            f"{key}: a field is declared by more than one class on the same model; "
            "Odoo merges the definitions attribute by attribute, so the real field is "
            "a union of both and must be consolidated into one declaration: "
            + ", ".join(
                f"{item['file']}:{item['line']} ({item['class_name']}, {item['role']})"
                for item in items
            )
        )
    for item in same_class_duplicates:
        failures.append(
            f"{item['model']}.{item['field']}: declared more than once in one class; "
            "only the last assignment survives: "
            + ", ".join(
                f"{declaration['file']}:{declaration['line']} ({declaration['class_name']})"
                for declaration in item["declarations"]
            )
        )

    company_sites = company_currency_write_sites(root, modules)
    declared_sites = sorted(
        (
            entry.get("file"),
            entry.get("kind"),
            entry.get("site"),
        )
        for entry in ((declares.get("company_currency_write_sites") or {}).get("sites") or [])
        if isinstance(entry, dict)
    )
    measured_sites = sorted(company_sites)
    missing_sites = [site for site in measured_sites if site not in declared_sites]
    extra_sites = [site for site in declared_sites if site not in measured_sites]
    if missing_sites:
        failures.append(
            "a product source writes res.company.currency_id, the carrier of the tenant "
            "standard currency, without a registration: "
            + ", ".join(":".join(site) for site in missing_sites)
        )
    if extra_sites:
        failures.append(
            "registered company-currency write site no longer matches source: "
            + ", ".join(":".join(site) for site in extra_sites)
        )
    for entry in ((declares.get("company_currency_write_sites") or {}).get("sites") or []):
        if isinstance(entry, dict) and not (entry.get("reason") or "").strip():
            failures.append(
                f"{entry.get('file')}:{entry.get('site')}: company-currency write site "
                "without a reason"
            )

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

    state_failures, state_report = state_fact(root, modules, declares)
    failures.extend(state_failures)

    number_failures, number_report = business_number_authority(root, modules, declares)
    failures.extend(number_failures)

    return {
        "status": "failed" if failures else "passed",
        "state_fact": state_report,
        "business_number_authority": number_report,
        "standard_currency": STANDARD_CURRENCY,
        "standard_currency_models": derived_standard,
        "caller_context_currency_models": derived_caller,
        "caller_context_inherited_models": sorted(derived_inherited),
        "currency_write_paths": write_paths,
        "company_field_overrides": sorted(overrides),
        "duplicate_field_declarations": sorted(duplicates),
        "company_currency_authority": authority,
        "company_currency_write_sites": [":".join(site) for site in measured_sites],
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
