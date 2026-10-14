#!/usr/bin/env python3
"""Generate the global company-scope ceilings from the data-scope declaration.

scripts/verify/data_scope_declarations.json is the single source: an ``enforced``
entry contributes its own anchor, a ``deferred`` group contributes its anchor for
every listed model. This script turns that declaration into the ir.rule records
that actually constrain access, so a new company ceiling is a one-line
declaration change instead of another hand-written near-duplicate record.

A ``source_bounded`` entry is deliberately *not* rendered: that model already
carries the named global ir.rule the declaration points at, and emitting a second
ceiling would duplicate one fact. The coverage guard verifies the named rule, so
the declaration stays the single source for both paths.

``--check`` regenerates in memory and fails when the committed file differs, so
the generated output can never drift from the declaration.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sc_data_scope_rule_coverage_guard as guard  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DECLARATIONS = ROOT / "scripts/verify/data_scope_declarations.json"
OWNER_MODULE = "smart_construction_core"
OUTPUT = ROOT / f"addons/{OWNER_MODULE}/security/sc_data_scope_ceiling_generated.xml"

HEADER = """<?xml version="1.0" encoding="UTF-8"?>
<odoo>
    <data noupdate="0">

        <!-- =========================================================
             Generated from scripts/verify/data_scope_declarations.json.
             Global rules: no group union can widen them. The owning company set
             is the intersection of the allowed-company selector ``company_ids``
             and the purpose-scoped authority ``user._sc_data_company_ids()``
             (``sc.tenant.company.registration``), so one ceiling covers both the
             company and the data-purpose dimension.

             An unset anchor stays visible as shared reference data by default
             (``unsetOwner: shared``), which covers Odoo global configuration
             (``company_id = False``). For a traversed anchor the unset branch
             is the union of "no parent" and "parent without an owning company",
             because Odoo compiles ``('a.b', '=', False)`` to ``a IN (SELECT id
             FROM a WHERE b IS NULL)``, which is NULL for a record whose ``a`` is
             NULL and would silently hide exactly the records the declaration
             keeps shared. An entry that declares ``unsetOwner:
             unknown`` renders a strict ceiling instead: a record without an
             owning company must not become public just because its owner
             relation is optional (the workbench/cockpit facts). The two forms
             share one shape, only the unset-owner branch differs.

             An ``enforced`` entry and every model of a ``deferred`` group are
             rendered here; a ``source_bounded`` entry is not, since it already
             names an existing global rule in a security file. Do not edit by
             hand; run `make verify.sc_data_scope.ceiling.sync` to regenerate.
        ========================================================== -->
"""

FOOTER = """    </data>
</odoo>
"""


UNSET_OWNERS = ("shared", "unknown")


def entries(declaration: dict) -> list[tuple[str, str, str | None]]:
    """(model, anchor, unset_owner) triples, deduplicated, in a stable order.

    ``unset_owner`` is ``None`` when the entry does not declare one, which keeps
    the rendered rule at the shared-reference default instead of inferring a
    stricter reading than the declaration states.
    """
    pairs: dict[str, tuple[str, str | None]] = {}
    for entry in declaration.get("enforced") or []:
        pairs[entry["model"]] = (entry["anchor"], entry.get("unsetOwner"))
    for group in declaration.get("deferred") or []:
        for model in group.get("models") or []:
            pairs.setdefault(model, (group["anchor"], group.get("unsetOwner")))
    return sorted((model, anchor, unset) for model, (anchor, unset) in pairs.items())


def ceiling_domain(anchor: str, unset_owner: str | None = None) -> str:
    """The one company ceiling for a declared anchor.

    Two facts are intersected, never inferred:

    * ``company_ids`` is the principal's allowed-company selector;
    * ``user._sc_data_company_ids()`` is the persisted data-purpose authority
      (``sc.tenant.company.registration``): a demo/test principal and a
      customer principal never share a company realm. The purpose dimension is
      resolved once, in this method, instead of a second predicate per model.

    ``unsetOwner`` decides only the unset-owner branch, because an unset anchor
    is not one fact for every model:

    * ``shared`` (default) - the anchor unset means shared reference data
      (Odoo global configuration, a dictionary entry with no policy). The record
      stays visible, and the purpose scope still bounds the records that do name
      an owning company.
    * ``unknown`` - the anchor is the model's only ownership path and it is
      optional, so an unset anchor is incomplete attribution rather than shared
      data. The ceiling is strict and never exposes it.

    The branch is written with an explicit ``&`` because Odoo ANDs an implicit
    trailing term onto the whole disjunction, which would silently drop the
    ``= False`` pass-through instead of keeping it.
    """
    if unset_owner is not None and unset_owner not in UNSET_OWNERS:
        raise SystemExit(
            f"{anchor}: unsetOwner must be one of {UNSET_OWNERS}, got {unset_owner!r}"
        )
    allowed = f"('{anchor}', 'in', company_ids)"
    purpose = f"('{anchor}', 'in', user._sc_data_company_ids())"
    if unset_owner == "unknown":
        return f"[{allowed}, {purpose}]"
    unset = unset_branch_terms(anchor)
    if len(unset) == 1:
        return f"['|', {unset[0]}, '&', {allowed}, {purpose}]"
    return f"['|', '|', {unset[0]}, {unset[1]}, '&', {allowed}, {purpose}]"


def unset_branch_terms(anchor: str) -> list[str]:
    """The terms that mean "the declared anchor carries no owning company".

    An own column (``company_id``) is one exact term: Odoo compiles
    ``('company_id', '=', False)`` to ``company_id IS NULL``.

    A traversed anchor (``project_id.company_id``) is not: Odoo compiles
    ``('project_id.company_id', '=', False)`` to ``project_id IN (SELECT id FROM
    project_project WHERE company_id IS NULL)``, which evaluates to NULL - never
    true - for a record whose ``project_id`` is NULL. The declared shared reading
    therefore vanished for exactly the records that name no parent at all, and
    the ceiling silently became stricter than the declaration.

    The unset reading is the union of the two facts the declaration covers: the
    record names no parent, or the parent names no owning company. Both terms are
    read from the anchor text; nothing is inferred from data.
    """
    if "." not in anchor:
        return [f"('{anchor}', '=', False)"]
    parent = anchor.split(".", 1)[0]
    return [f"('{parent}', '=', False)", f"('{anchor}', '=', False)"]


def record_xml(model: str, anchor: str, owner_module: str,
               unset_owner: str | None = None) -> str:
    ident = model.replace(".", "_")
    ref = f"model_{ident}" if owner_module == OWNER_MODULE else f"{owner_module}.model_{ident}"
    # The domain uses the prefix '&'; XML text must escape it.
    domain = ceiling_domain(anchor, unset_owner).replace("&", "&amp;")
    return (
        f'        <record id="rule_sc_data_scope_{ident}" model="ir.rule">\n'
        f'            <field name="name">SC Data Scope - {model} by allowed companies</field>\n'
        f'            <field name="model_id" ref="{ref}"/>\n'
        f'            <field name="domain_force">{domain}</field>\n'
        f'            <field name="perm_read" eval="True"/>\n'
        f'            <field name="perm_write" eval="True"/>\n'
        f'            <field name="perm_create" eval="True"/>\n'
        f'            <field name="perm_unlink" eval="True"/>\n'
        f"        </record>\n"
    )


def render(root: Path, declaration: dict, module_sets: str = guard.DEFAULT_MODULE_SETS) -> str:
    modules = guard.product_modules(root, module_sets)
    owners = guard.defined_models(root, set(modules))
    owner_of: dict[str, str] = {}
    for module, names in owners.items():
        for name in names:
            owner_of.setdefault(name, module)

    body = HEADER
    for model, anchor, unset_owner in entries(declaration):
        owner_module = owner_of.get(model)
        if owner_module is None:
            raise SystemExit(f"{model}: no product module defines this model")
        body += record_xml(model, anchor, owner_module, unset_owner)
    return body + "\n" + FOOTER


def display(path: Path, root: Path) -> str:
    """A readable path for the receipt, whether or not it sits under the root."""
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--declarations", default=str(DECLARATIONS))
    parser.add_argument("--output", default=None)
    parser.add_argument("--module-sets", default=guard.DEFAULT_MODULE_SETS)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    root = Path(args.root)
    declaration = json.loads(Path(args.declarations).read_text(encoding="utf-8"))
    expected = render(root, declaration, args.module_sets)
    output = Path(args.output) if args.output else root / f"addons/{OWNER_MODULE}/security/sc_data_scope_ceiling_generated.xml"

    if args.check:
        actual = output.read_text(encoding="utf-8") if output.is_file() else ""
        if actual != expected:
            print(
                f"FAIL {display(output, root)} differs from the declaration; "
                "run make verify.sc_data_scope.ceiling.sync"
            )
            return 1
        print(f"SC_DATA_SCOPE_CEILING=connected rules={expected.count('model=\"ir.rule\"')}")
        return 0

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(expected, encoding="utf-8")
    print(
        "SC_DATA_SCOPE_CEILING=written "
        f"rules={expected.count('model=\"ir.rule\"')} path={display(output, root)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
