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
             Global rules: no group union can widen them, and the anchor is
             the owning business relation, so company_id = False stays
             visible. An ``enforced`` entry and every model of a ``deferred``
             group are rendered here; a ``source_bounded`` entry is not, since
             it already names an existing global rule in a security file. Do
             not edit by hand; run
             `make verify.sc_data_scope.ceiling.sync` to regenerate.
        ========================================================== -->
"""

FOOTER = """    </data>
</odoo>
"""


def entries(declaration: dict) -> list[tuple[str, str]]:
    """(model, anchor) pairs, deduplicated, in a stable order."""
    pairs: dict[str, str] = {}
    for entry in declaration.get("enforced") or []:
        pairs[entry["model"]] = entry["anchor"]
    for group in declaration.get("deferred") or []:
        for model in group.get("models") or []:
            pairs.setdefault(model, group["anchor"])
    return sorted(pairs.items())


def record_xml(model: str, anchor: str, owner_module: str) -> str:
    ident = model.replace(".", "_")
    ref = f"model_{ident}" if owner_module == OWNER_MODULE else f"{owner_module}.model_{ident}"
    return (
        f'        <record id="rule_sc_data_scope_{ident}" model="ir.rule">\n'
        f'            <field name="name">SC Data Scope - {model} by allowed companies</field>\n'
        f'            <field name="model_id" ref="{ref}"/>\n'
        f"            <field name=\"domain_force\">['|', ('{anchor}', '=', False), "
        f"('{anchor}', 'in', company_ids)]</field>\n"
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
    for model, anchor in entries(declaration):
        owner_module = owner_of.get(model)
        if owner_module is None:
            raise SystemExit(f"{model}: no product module defines this model")
        body += record_xml(model, anchor, owner_module)
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
