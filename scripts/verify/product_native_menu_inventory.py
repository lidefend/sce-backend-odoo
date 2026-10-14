#!/usr/bin/env python3
"""Read-only native declaration inventory; never an automatic publication list.

Source evidence is deliberately distinguished from effective ORM ACL/view proof.
No menu is classified as usable merely because a model or view file exists.
"""
import argparse
import ast
import csv
import json
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET

from scripts.ops.promote_product_ten_center_policy import SOURCE_PATH, native_facts


def blocked_ancestors(key, facts):
    blocked, seen = [], {key}
    parent = facts[key].get("parent_id")
    while parent and parent not in {"False", ""}:
        if parent in seen:
            raise ValueError("native menu parent cycle: " + key)
        seen.add(parent)
        row = facts.get(parent, {})
        if row.get("active") == "False":
            blocked.append(parent)
        parent = row.get("parent_id")
    return blocked


def action_identity(row):
    value = row.get("action")
    return value if value and value != "False" else None


def inventory():
    root = SOURCE_PATH.parents[3]
    module = SOURCE_PATH.parents[1]
    facts = native_facts()
    source = json.loads(SOURCE_PATH.read_text())
    selected = {row["menu_xmlid"]: row for row in source["entries"]}
    published_actions = {}
    for key in selected:
        action = action_identity(facts.get(key, {}))
        if action:
            published_actions.setdefault(action, []).append(key)
    declarations, views, access, rules, models = {}, {}, {}, {}, {}
    manifest = ast.literal_eval((module / "__manifest__.py").read_text())
    for filename in manifest["data"]:
        path = module / filename
        relative = str(path.relative_to(root))
        if path.suffix == ".csv" and path.name == "ir.model.access.csv":
            for row in csv.DictReader(path.open()):
                access.setdefault(row["model_id:id"].split(".")[-1], []).append({"source": relative, **row})
        if path.suffix != ".xml":
            continue
        for node in ET.parse(path).getroot().iter():
            if node.tag not in {"record", "menuitem"} or not node.get("id"):
                continue
            key = node.get("id")
            key = key if "." in key else module.name + "." + key
            fields = {field.get("name"): field.get("ref") or field.get("eval") or (field.text or "").strip() for field in node.findall("field") if field.get("name") != "arch"}
            declarations.setdefault(key, []).append({"source": relative, "attributes": dict(node.attrib), "fields": fields})
            if node.get("model") == "ir.ui.view" and fields.get("model"):
                views.setdefault(fields["model"], []).append({"xmlid": key, "source": relative, "inherit_id": fields.get("inherit_id"), "groups": fields.get("groups_id"), "arch_roots": [child.tag for field in node.findall("field") if field.get("name") == "arch" for child in field]})
            if node.get("model") == "ir.rule" and fields.get("model_id"):
                rules.setdefault(fields["model_id"].split(".")[-1], []).append({"xmlid": key, "source": relative, "fields": fields})
    for path in (module / "models").rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if not isinstance(node, ast.ClassDef):
                continue
            for assignment in node.body:
                if isinstance(assignment, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "_name" for t in assignment.targets):
                    if isinstance(assignment.value, ast.Constant) and isinstance(assignment.value.value, str):
                        models.setdefault(assignment.value.value, []).append(str(path.relative_to(root)))
    rows = []
    for key, fact in facts.items():
        if fact["type"] != "ir.ui.menu" or not key.startswith(module.name + "."):
            continue
        action = action_identity(fact)
        target = facts.get(action, {})
        model = target.get("res_model")
        model_id = "model_" + model.replace(".", "_") if model else ""
        disabled_parents = blocked_ancestors(key, facts)
        duplicates = [identity for identity in published_actions.get(action, []) if identity != key]
        classification = (
            "registered_product" if key in selected else
            "structure_only" if not action else
            "same_action_as_registered_entry" if duplicates else
            "roadmap_carrier" if model == "sc.project.capability.roadmap" else
            "native_action_requires_review"
        )
        rows.append({"xmlid": key, "name": fact.get("name"), "classification": classification,
                     "release_state": selected.get(key, {}).get("release_state"),
                     "inactive": fact.get("active") == "False", "inactive_ancestors": disabled_parents,
                     "action_xmlid": action, "action_type": target.get("type"), "model": model,
                     "view_modes": target.get("view_mode"), "same_action_entries": duplicates,
                     "menu_declarations": declarations.get(key, []), "action_declarations": declarations.get(action, []),
                     "model_sources": models.get(model, []), "view_declarations": views.get(model, []),
                     "acl_declarations": access.get(model_id, []), "record_rule_declarations": rules.get(model_id, []),
                     "effective_runtime_validation": "not_run"})
    return {"schema": "native_menu_fact_inventory.v1", "authority": "read-only source evidence; no publication authority", "scope": module.name,
            "limitations": ["Source declarations are not proof of installed ORM model, effective inherited view, ACL or business usability.", "Same action does not alone prove duplicate product intent; menu context and native permissions still need review.", "External module model/views/permissions are not absent merely because this P1-local source inventory has no records."],
            "counts": dict(Counter(row["classification"] for row in rows)), "rows": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = inventory()
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"scope": result["scope"], "counts": result["counts"]}, ensure_ascii=False))
