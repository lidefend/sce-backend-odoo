#!/usr/bin/env python3
"""Retire exact historical form mirrors; new mirror generation is forbidden.

Native model/action/view metadata is the product authority. This compatibility
entry only removes historical product semantics without touching user contracts.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
from pathlib import Path
import xml.etree.ElementTree as ET


ROOT = Path(os.environ.get("SC_REPO_ROOT") or Path.cwd()).resolve()
DEFAULT_OUTPUT = ROOT / "addons/smart_construction_core/data/view_orchestration_contract_generated_data.xml"
RETIREMENT_DECLARATION = ROOT / "addons/smart_construction_core/data/native_guidance_form_retirement.xml"


def retired_seed_ids(declaration: str) -> set[str]:
    """Read the native P1 write declaration without evaluating executable XML."""
    functions = ET.fromstring(declaration).findall("function")
    if len(functions) != 1:
        raise ValueError("Expected one exact seed retirement declaration")
    function = functions[0]
    values = function.findall("value")
    if (function.attrib != {"model": "ui.business.config.contract", "name": "write"}
            or len(values) != 2
            or ast.literal_eval(values[1].get("eval", "")) != {"active": False, "status": "draft"}):
        raise ValueError("Invalid seed retirement operation")
    expression = ast.parse(values[0].get("eval", ""), mode="eval").body
    if not isinstance(expression, ast.List) or not expression.elts:
        raise ValueError("Seed retirement requires exact XML identities")
    identities = set()
    for call in expression.elts:
        if (not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name)
                or call.func.id != "ref" or len(call.args) != 1 or call.keywords
                or not isinstance(call.args[0], ast.Constant) or not isinstance(call.args[0].value, str)):
            raise ValueError("Only literal ref identities are allowed")
        module, separator, identity = call.args[0].value.partition(".")
        if module != "smart_construction_core" or not separator or not identity.endswith("_form_structure_generated") or identity in identities:
            raise ValueError("Invalid or duplicate seed identity")
        identities.add(identity)
    return identities


def apply_declared_retirements(xml: str, declaration: str, *, require_all: bool = True) -> str:
    """Preserve unrelated generated records byte-for-byte; retain retired XMLIDs."""
    identities = retired_seed_ids(declaration)
    seen = set()

    def replace(match):
        record = ET.fromstring(match.group())
        identity = record.get("id")
        if identity not in identities:
            return match.group()
        if identity in seen or record.get("model") != "ui.business.config.contract":
            raise ValueError("Invalid generated seed identity")
        seen.add(identity)
        for name, attributes, value in (
            ("active", {"eval": "False"}, None),
            ("status", {}, "draft"),
            ("contract_json", {"eval": "{'view_orchestration': {'views': {}}}"}, None),
        ):
            fields = record.findall(f"field[@name='{name}']")
            if len(fields) != 1:
                raise ValueError(f"Missing or duplicate {identity}.{name}")
            fields[0].attrib = {"name": name, **attributes}
            fields[0].text = value
        return ET.tostring(record, encoding="unicode")

    result = re.sub(r"<record\b[^>]*>.*?</record>", replace, xml, flags=re.S)
    if require_all and seen != identities:
        raise ValueError("Missing generated retirement targets: " + ", ".join(sorted(identities - seen)))
    ET.fromstring(result)
    return result

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--retire-native-guidance", action="store_true")
    args = parser.parse_args(argv)

    if args.retire_native_guidance:
        output = Path(args.output)
        xml = apply_declared_retirements(output.read_text(), RETIREMENT_DECLARATION.read_text())
        output.write_text(xml)
        print(json.dumps({"retired": sorted(retired_seed_ids(RETIREMENT_DECLARATION.read_text())), "output": str(output)}))
        return 0

    print("Native form mirrors are retired; edit the owning native ir.ui.view declaration.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
