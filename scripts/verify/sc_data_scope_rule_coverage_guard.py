#!/usr/bin/env python3
"""Fail-closed check that every product-owned company model is accounted for.

The registered 744-model registry is inspection scope, not a rewrite list. This
guard reads source only (offline lane) and enforces two things:

* the explicit declaration in data_scope_declarations.json is internally sound:
  every ``enforced`` model has a *global* ir.rule (no groups, so no group union
  can widen it) whose domain constrains the declared company anchor path; every
  ``exempt`` model names one isolation dimension and its owning module; every
  ``deferred`` model belongs to a group with an issue id, an anchor, an owner
  and an actionable reason *and* carries the same global ceiling an enforced
  model does (deferred records the delivery order, never the isolation), so the
  rule set can be regenerated from the declaration and deleting it cannot hide;
  every ``source_bounded`` model names the existing global ir.rule (id and file)
  that bounds it, that named rule is verified instead of inferred, and it must
  carry both isolation facts on the declared anchor - the allowed-company
  selector *and* the purpose authority ``user._sc_data_company_ids()``, exactly
  as the generated ceiling for an ``enforced`` model does; rule xml ids stay
  unique across security files.
* the declaration *covers* the product model surface exactly: every model
  defined by a product module (config/tenant/module_sets.v1.json) that declares a
  ``company_id`` field carries one explicit declaration - enforced, deferred,
  exempt (including ``transient``) or source_bounded. Coverage is never inferred
  from a rule that merely mentions a company column, so a model whose isolation
  is group-scoped cannot pass by accident and an undeclared company model fails
  here instead of surfacing as a silent isolation hole.
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
NAME_EXPR = re.compile(r"^\s*_name\s*=\s*([^\s#]+)\s*$", re.M)
CONST_DEF = re.compile(r"^\s*([A-Z][A-Z0-9_]{2,})\s*=\s*[\"']([\w.]+)[\"']\s*$", re.M)
COMPANY_FIELD = re.compile(r"^\s+company_id\s*=\s*fields\.Many2one", re.M)
INHERIT_LINE = re.compile(r"^[ \t]*_inherit\s*=\s*(.+?)\s*$", re.M)
INHERIT_LITERAL = re.compile(r"[\"']([\w.]+)[\"']")
INHERIT_TOKEN = re.compile(r"[A-Za-z_][\w.]*")
# ``groups`` is an x2many, so "no group" can be declared by an ORM command as
# well as by an empty literal: ``(5, 0, 0)`` unlinks every existing link and
# ``(6, 0, [])`` replaces the set with nothing. Both leave the rule global.
GROUPS_CLEAR_COMMAND = re.compile(r"\(5\s*,\s*0\s*,\s*0\)|\(6\s*,\s*0\s*,\s*\[\s*\]\)")
ORM_SYNTAX = re.compile(r"[\s,\[\]()]")


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
    """A rule is global when it ends up carrying no group.

    ``[(5, 0, 0)]`` (unlink all) and ``[(6, 0, [])]`` (replace with nothing)
    are the ORM's two ways of saying "no groups"; reading them as a group scope
    under-reported the global rules and could report a fully global rule set as
    if a group union were able to widen it.
    """
    for field in record.findall("field"):
        if field.get("name") == "groups":
            expression = (field.get("eval") or "").strip()
            text = "".join(field.itertext()).strip()
            if not expression:
                return not text
            remainder = GROUPS_CLEAR_COMMAND.sub("", expression)
            return not ORM_SYNTAX.sub("", remainder)
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
            constants = model_name_constants(root, sorted(modules))
            for _match, block in class_blocks(text):
                name, _unresolvable = resolve_model_name(block, constants)
                if name:
                    names.add(name)
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


_CONSTANT_CACHE: dict[tuple[str, tuple[str, ...]], dict[str, str]] = {}


def model_name_constants(root: Path, modules: list[str]) -> dict[str, str]:
    """``CONST = "a.b"`` assignments, so ``_name = CONST`` still names a model.

    A model that names itself through a module constant is a real model; without
    this table its identity, and therefore its company scope, would be invisible
    to the coverage universe. A name mapping to more than one value is dropped,
    so such a model has to fall back to a literal ``_name``.
    """
    key = (str(root), tuple(sorted(modules)))
    cached = _CONSTANT_CACHE.get(key)
    if cached is not None:
        return cached
    table: dict[str, set[str]] = {}
    for module in sorted(modules):
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
            for match in CONST_DEF.finditer(text):
                table.setdefault(match.group(1), set()).add(match.group(2))
    resolved = {
        name: next(iter(values)) for name, values in table.items() if len(values) == 1
    }
    _CONSTANT_CACHE[key] = resolved
    return resolved


def class_blocks(text: str):
    """(match, body) for every ``class X(models.Y):`` block in one source text."""
    for match in CLASS_BLOCK.finditer(text):
        end = text.find("\nclass ", match.end())
        yield match, text[match.end():end if end > 0 else len(text)]


def resolve_model_name(block: str, constants: dict[str, str]) -> tuple[str | None, bool]:
    """``(model name, unresolvable)`` for one class body.

    A literal ``_name`` is used directly and a bare identifier is resolved
    through the module constant table. A class without any ``_name`` extends an
    existing model and owns no new identity. Any other expression is
    unresolvable: the caller must fail closed instead of dropping the class out
    of the universe, which is exactly how a company-bearing model escapes
    coverage unnoticed.
    """
    literal = NAME_LINE.search(block)
    if literal:
        return literal.group(1), False
    expression = NAME_EXPR.search(block)
    if not expression:
        return None, False
    value = constants.get(expression.group(1).split(".")[-1])
    return value, value is None


def inherit_names(block: str) -> list[str]:
    """Literal model names an ``_inherit`` line extends."""
    match = INHERIT_LINE.search(block)
    if not match:
        return []
    quoted = INHERIT_LITERAL.findall(match.group(1))
    if quoted:
        return quoted
    raw = match.group(1).strip()
    return [
        token.strip().split(".")[-1]
        for token in raw.strip("[]").split(",")
        if token.strip()
    ]


def inherit_constant_tokens(block: str) -> list[str]:
    """Bare expressions an ``_inherit`` line uses instead of a literal name."""
    match = INHERIT_LINE.search(block)
    if not match:
        return []
    without_literals = INHERIT_LITERAL.sub(" ", match.group(1))
    return [token for token in INHERIT_TOKEN.findall(without_literals) if token != "_inherit"]


def target_models(block: str, constants: dict[str, str], known: set[str]) -> list[str]:
    """Models one class block belongs to.

    A class with ``_name`` owns that identity. A class that only extends others
    (``_inherit`` without ``_name``) belongs to every extended model, so a field
    it declares is attributed to the model instead of being skipped. Skipping
    such a class is exactly how a company-bearing model escapes the universe.
    """
    name, _unresolvable = resolve_model_name(block, constants)
    if name:
        return [name]
    return [parent for parent in inherit_names(block) if parent in known]


def unresolved_model_names(root: Path, modules: list[str]) -> list[str]:
    """Source locations whose declared ``_name`` cannot be resolved to a model."""
    constants = model_name_constants(root, modules)
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
            for match, block in class_blocks(text):
                line = text[:match.start()].count("\n") + 1
                expression = NAME_EXPR.search(block)
                if expression:
                    _name, unresolvable = resolve_model_name(block, constants)
                    if unresolvable:
                        findings.append(
                            f"{path.relative_to(root).as_posix()}:{line}: _name = "
                            f"{expression.group(1)} does not resolve to a model name"
                        )
                    continue
                if not COMPANY_FIELD.search(block):
                    continue
                for token in inherit_constant_tokens(block):
                    if token.split(".")[-1] not in constants:
                        findings.append(
                            f"{path.relative_to(root).as_posix()}:{line}: class declaring "
                            f"company_id extends {token}, which does not resolve to a model name"
                        )
    return sorted(findings)


def company_field_models(root: Path, modules: list[str]) -> dict[str, bool]:
    """Product-module models declaring a ``company_id`` field -> transient flag.

    A ``company_id`` declared by an extension class belongs to the model the class
    extends, so the universe follows the same inheritance resolution as the
    money-fact guard instead of only reading classes that own a ``_name``.
    """
    found: dict[str, bool] = {}
    constants = model_name_constants(root, modules)
    known: set[str] = set()
    for names in defined_models(root, set(modules)).values():
        known |= names
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
            for match, block in class_blocks(text):
                if not COMPANY_FIELD.search(block):
                    continue
                transient = "TransientModel" in text[match.start():match.end()]
                for name in target_models(block, constants, known):
                    if transient or name not in found:
                        found[name] = transient
    return found


def rules_for(by_ref: dict[str, list[dict]], model: str) -> list[dict]:
    return by_ref.get("model_" + model.replace(".", "_"), [])


def declared_source_rule(
    by_ref: dict[str, list[dict]], model: str, anchor: str, rule_id: str
) -> dict | None:
    """The named source rule, when it is global and carries both isolation facts.

    A model bounded by an existing native ir.rule must name that rule in the
    declaration. The guard then verifies the named rule rather than accepting any
    rule that happens to mention a company column, so a group-scoped rule can
    never stand in for a ceiling and the declaration stays the single source for
    *why* a model is bounded.

    The named rule must also carry the purpose authority
    ``user._sc_data_company_ids()`` on the same anchor as the company selector.
    A company-only ceiling is not the same fact as the generated ceiling an
    ``enforced`` model gets: it lets a customer principal read a demo/test
    company's rows, which is exactly the data-purpose isolation hole that
    "the named rule is verified instead of inferred" used to hide behind.
    """
    purpose = f"('{anchor}', 'in', user._sc_data_company_ids())"
    for rule in rules_for(by_ref, model):
        if (
            rule["xmlid"] == rule_id
            and rule["global"]
            and f"('{anchor}'" in rule["domain"]
            and purpose in rule["domain"]
        ):
            return rule
    return None


def check(root: Path, declarations_path: Path, module_sets_path: str = DEFAULT_MODULE_SETS) -> dict:
    declaration = json.loads(declarations_path.read_text(encoding="utf-8"))
    enforced = declaration.get("enforced") or []
    exempt = declaration.get("exempt") or []
    deferred = declaration.get("deferred") or []
    modules = product_modules(root, module_sets_path)
    universe = company_field_models(root, modules)
    by_ref, ids = scan_security_files(root)

    failures: list[str] = []
    unresolved_names = unresolved_model_names(root, modules)
    for finding in unresolved_names:
        failures.append(
            f"{finding}; name the model with a literal _name so its company scope "
            "can be derived instead of escaping the coverage universe"
        )
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

    def ceiling(model: str, anchor: str, note: str = "") -> list[dict]:
        """Require one global rule whose domain constrains ``anchor``.

        The same requirement holds for an enforced declaration and for every
        model inside a deferred group: a deferred ceiling is still a ceiling the
        runtime must carry, it is only recorded as deferred delivery. Without
        this, deleting the generated ceiling file would leave the guard green
        and the isolation hole silent.
        """
        suffix = f" (deferred {note})" if note else ""
        expected = "model_" + model.replace(".", "_")
        candidates = by_ref.get(expected, [])
        if not candidates:
            failures.append(f"{model}: no ir.rule references {expected}{suffix}")
            return []
        needle = f"('{anchor}'"
        scoped = [r for r in candidates if r["global"] and needle in r["domain"]]
        if not scoped:
            global_rules = [r for r in candidates if r["global"]]
            detail = (
                f"{len(global_rules)} global rule(s) but none constrains {anchor}"
                if global_rules
                else "every matching rule is group-scoped (group union could widen it)"
            )
            failures.append(f"{model}: {detail}{suffix}")
            return []
        for owner in {r["owner_module"] for r in scoped}:
            if owner not in owners:
                owners.update(defined_models(root, {owner}))
            if model not in owners[owner]:
                failures.append(
                    f"{model}: rule in {owner} cannot resolve; {owner} does not define it"
                )
        return scoped

    unset_owner_values = {"shared", "unknown"}

    def check_unset_owner(entry: dict, label: str) -> None:
        """An unset-owner branch must be declared, never inferred.

        The default is the shared-reference reading, so a model whose anchor is
        its only optional ownership path has to state that explicitly instead of
        passing a fail-open ceiling off as complete attribution.
        """
        value = entry.get("unsetOwner")
        if value is None:
            return
        if value not in unset_owner_values:
            failures.append(
                f"{label}: unsetOwner must be one of {sorted(unset_owner_values)}, "
                f"got {value!r}"
            )
            return
        reason = (entry.get("reason") or "").strip()
        if not reason:
            failures.append(f"{label}: unsetOwner={value} requires a reason")
        elif any(token in reason.lower() for token in PLACEHOLDER_REASONS):
            failures.append(f"{label}: placeholder reason for unsetOwner={value}")

    for entry in enforced:
        model = entry["model"]
        anchor = entry["anchor"]
        if model in seen:
            failures.append(f"duplicate enforced entry: {model}")
        seen.add(model)
        ceiling(model, anchor)
        check_unset_owner(entry, model)

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
        check_unset_owner(group, f"deferred {issue or '<no issue>'}")
        for model in models:
            if model in deferred_models:
                failures.append(f"{model}: listed in two deferred groups")
            deferred_models[model] = issue
            if model in seen:
                failures.append(f"{model}: declared enforced and deferred")
            if model in exempt_models:
                failures.append(f"{model}: declared exempt and deferred")
            if anchor:
                ceiling(model, anchor, note=issue)
            if model not in universe:
                failures.append(f"{model}: deferred but no product module declares company_id")

    # A source_bounded entry names the existing global ir.rule that owns the
    # company scope, so it is legitimate for a relation-anchored model that has
    # no company_id column of its own (for example a *line model bounded through
    # its parent's company anchor). Such a model is outside the company_id-based
    # coverage universe by construction; it still has to resolve to a product
    # module and to a real global rule below, which is checked for every entry.
    bounded_models: set[str] = set()
    for entry in declaration.get("source_bounded") or []:
        model = entry.get("model")
        anchor = (entry.get("anchor") or "company_id").strip()
        rule_id = (entry.get("rule") or "").strip()
        file_hint = (entry.get("file") or "").strip()
        reason = (entry.get("reason") or "").strip()
        if model in bounded_models:
            failures.append(f"{model}: listed in source_bounded twice")
        bounded_models.add(model)
        if model in seen:
            failures.append(f"{model}: declared enforced and source_bounded")
        if model in exempt_models:
            failures.append(f"{model}: declared exempt and source_bounded")
        if model in deferred_models:
            failures.append(f"{model}: declared deferred and source_bounded")
        if not reason or any(token in reason.lower() for token in PLACEHOLDER_REASONS):
            failures.append(
                f"{model}: source_bounded reason is missing or a placeholder"
            )
        if not rule_id:
            failures.append(f"{model}: source_bounded without the source rule id")
            continue
        matched = declared_source_rule(by_ref, model, anchor, rule_id)
        if not matched:
            failures.append(
                f"{model}: source_bounded rule {rule_id} is missing, group-scoped or "
                f"does not constrain {anchor} with user._sc_data_company_ids()"
            )
            continue
        if file_hint and file_hint != matched["file"]:
            failures.append(
                f"{model}: source_bounded rule {rule_id} lives in {matched['file']}, "
                f"not the declared {file_hint}"
            )
        owner = matched["owner_module"]
        if owner not in owners:
            owners.update(defined_models(root, {owner}))
        if model not in owners[owner]:
            failures.append(
                f"{model}: source rule {rule_id} in {owner} cannot resolve; "
                f"{owner} does not define it"
            )

    uncovered: list[str] = []
    for model in sorted(universe):
        if (
            model in seen
            or model in exempt_models
            or model in deferred_models
            or model in bounded_models
        ):
            continue
        uncovered.append(model)
    for model in uncovered:
        failures.append(
            f"{model}: product module declares company_id but carries no enforced, "
            "deferred, exempt or source_bounded declaration; declare the isolation "
            "fact in data_scope_declarations.json instead of leaving it inferred"
        )

    enforced_in_universe = sum(1 for model in universe if model in seen)
    exempt_in_universe = sum(1 for model in universe if model in exempt_models)
    deferred_in_universe = sum(1 for model in universe if model in deferred_models)
    source_bounded_in_universe = sum(1 for model in universe if model in bounded_models)
    declared_total = (
        enforced_in_universe
        + exempt_in_universe
        + deferred_in_universe
        + source_bounded_in_universe
        + len(uncovered)
    )
    if declared_total != len(universe):
        failures.append(
            f"coverage accounting is inconsistent: {declared_total} decisions for "
            f"{len(universe)} universe models"
        )

    return {
        "status": "failed" if failures else "passed",
        "enforced": len(enforced),
        "exempt": len(exempt),
        "deferred": len(deferred_models),
        "deferred_issues": sorted({issue for issue in deferred_models.values()}),
        "universe": len(universe),
        "enforced_in_universe": enforced_in_universe,
        "exempt_in_universe": exempt_in_universe,
        "deferred_in_universe": deferred_in_universe,
        "source_bounded": sorted(bounded_models),
        "source_bounded_count": len(bounded_models),
        "source_bounded_in_universe": source_bounded_in_universe,
        "source_bounded_out_of_universe": sorted(
            model for model in bounded_models if model not in universe
        ),
        "transient": sum(1 for transient in universe.values() if transient),
        "uncovered": sorted(uncovered),
        "unresolved_model_names": unresolved_names,
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
