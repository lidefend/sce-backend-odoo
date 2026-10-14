# -*- coding: utf-8 -*-
"""Pure projections of P1-owned product menu metadata. No runtime/database reads."""
from __future__ import annotations

import ast
import copy
from xml.etree import ElementTree
import json
import re
from pathlib import Path

SOURCE_PATH = Path(__file__).resolve().parents[1] / "data/product_menu_source.json"

def load_source(path=SOURCE_PATH):
    source = json.loads(Path(path).read_text(encoding="utf-8"))
    if source.get("schema") != "construction.product_menu_source.v1":
        raise ValueError("invalid product menu source schema")
    return resolve_native_source(source)

def native_facts(module_root=None, _visiting=None, _loaded=None, _facts=None):
    """Resolve shipped Odoo XML in manifest order; never infer from labels."""
    root = Path(module_root) if module_root else SOURCE_PATH.parents[1]
    manifest = ast.literal_eval((root / "__manifest__.py").read_text(encoding="utf-8"))
    loaded = _loaded if _loaded is not None else set()
    facts = _facts if _facts is not None else {}
    if root.name in loaded:
        return facts
    visiting = set(_visiting or ())
    if root.name in visiting:
        raise ValueError("native module dependency cycle")
    visiting.add(root.name)
    for dependency in manifest.get("depends", []):
        dependency_root = root.parent / dependency
        if (dependency_root / "__manifest__.py").is_file():
            native_facts(dependency_root, visiting, loaded, facts)
    def qualified(value):
        return value if "." in value else root.name + "." + value
    for filename in manifest["data"]:
        path = root / filename
        if path.suffix != ".xml":
            continue
        for node in ElementTree.parse(path).getroot().iter():
            if node.tag not in ("menuitem", "record") or not node.get("id"):
                continue
            model = "ir.ui.menu" if node.tag == "menuitem" else node.get("model")
            if model not in ("ir.ui.menu", "ir.actions.act_window", "ir.actions.client", "ir.actions.server"):
                continue
            row = facts.setdefault(qualified(node.get("id")), {})
            row["type"] = model
            if node.tag == "menuitem":
                for key in ("name", "sequence", "active"):
                    if key in node.attrib:
                        row[key] = node.get(key)
                for key in ("parent", "action"):
                    if key in node.attrib:
                        row["parent_id" if key == "parent" else key] = qualified(node.get(key))
            for field in node.findall("field"):
                if field.get("name") not in ("name", "sequence", "active", "parent_id", "action", "res_model", "view_mode"):
                    continue
                if field.get("ref"):
                    row[field.get("name")] = qualified(field.get("ref"))
                elif field.text and field.text.strip():
                    row[field.get("name")] = field.text.strip()
                elif field.get("eval") in ("False", "True"):
                    row[field.get("name")] = field.get("eval")
                else:
                    match = re.fullmatch(r"'ir\.actions\.act_window,%d' % ref\('([a-zA-Z0-9_.]+)'\)", field.get("eval", ""))
                    if field.get("name") == "action" and match:
                        row["action"] = qualified(match.group(1))
                    else:
                        raise ValueError(f"unsupported native menu/action declaration: {filename}/{node.get('id')}/{field.get('name')}")
    loaded.add(root.name)
    return facts


def resolve_native_source(raw, facts=None):
    """Publication selects identities; Odoo declarations supply existing facts."""
    source = copy.deepcopy(raw)
    facts = native_facts() if facts is None else facts
    root_id = source["root_menu_xmlid"]
    root_label = facts[root_id]["name"]
    source["root_label"] = root_label
    centers = {}
    for center in source["product_contract"]["centers"]:
        xmlid = center.pop("native_menu_xmlid")
        native = facts[xmlid]
        if native.get("parent_id") != root_id or native.get("active") == "False":
            raise ValueError(f"invalid native product center: {xmlid}")
        center.update(name=native["name"], sequence=int(native["sequence"]), level_two=[])
        centers[xmlid] = center
    groups = {}
    seen = set()
    excluded = {row["menu_xmlid"] for row in source.get("excluded_entries", [])}
    for entry in source.pop("entries"):
        xmlid = entry["menu_xmlid"]
        if xmlid in excluded:
            raise ValueError("retired product entry cannot be republished without explicit disposition change")
        selection_keys = {"menu_xmlid", "delivery", "source_kind", "entry_target_policy", "target_scene_key", "external_presentation", "release_state"}
        if set(entry) - selection_keys:
            raise ValueError("product selection cannot redefine native facts")
        if xmlid in seen:
            raise ValueError(f"duplicate menu identity: {xmlid}")
        seen.add(xmlid)
        if entry.get("release_state") not in {"released", "preview"}:
            raise ValueError("product entry requires explicit release state")
        external = entry.get("external_presentation")
        if external:
            module = xmlid.split(".", 1)[0]
            module_source = SOURCE_PATH.parents[2] / module / "__manifest__.py"
            if xmlid in facts or module_source.is_file():
                raise ValueError("external presentation cannot override a module-owned native menu")
            if external.get("source_module") != module or not str(external.get("integration_reason") or "").strip():
                raise ValueError("external presentation requires source module and integration reason")
            center_id = external["center_xmlid"]
            if type(external.get("sequence")) is not int:
                raise ValueError("external presentation requires explicit product placement sequence")
            leaf = {"name": external["label"], "delivery": entry["delivery"], "binding": {"menu_xmlid":xmlid, "action_xmlid":external["action_xmlid"], "model":external["model"], "source_kind":external["source_kind"], "sequence":external["sequence"], "release_state":entry["release_state"]}}
            centers[center_id]["level_two"].append(leaf)
            continue
        native = facts[xmlid]
        if native["type"] != "ir.ui.menu" or native.get("active") == "False":
            raise ValueError(f"published native menu missing or inactive: {xmlid}")
        parent = native["parent_id"]
        group_id = None
        if parent not in centers:
            group_id = parent
            if facts[group_id].get("active") == "False":
                raise ValueError(f"published menu has inactive native parent: {xmlid}")
            parent = facts[parent]["parent_id"]
        if parent not in centers:
            raise ValueError(f"published native menu outside declared product centers: {xmlid}")
        binding = {"menu_xmlid":xmlid, "source_kind":entry["source_kind"], "sequence":int(native["sequence"]), "release_state":entry["release_state"]}
        leaf = {"name":native["name"], "delivery":entry["delivery"], "binding":binding}
        if entry.get("entry_target_policy") == "scene_entry":
            binding.update(entry_target_policy="scene_entry", target_scene_key=entry["target_scene_key"])
            leaf.update(entry_target_policy="scene_entry", target_scene_key=entry["target_scene_key"])
        else:
            action_id = native["action"]
            action = facts[action_id]
            binding.update(action_xmlid=action_id, model=action["res_model"], view_modes=[mode.strip() for mode in action["view_mode"].split(",") if mode.strip()])
        if group_id:
            if group_id not in groups:
                groups[group_id] = {"name":facts[group_id]["name"], "children":[]}
                centers[parent]["level_two"].append(groups[group_id])
            groups[group_id]["children"].append(leaf)
        else:
            centers[parent]["level_two"].append(leaf)
    return source


def _menu_row(center: str, label: str, menu_xmlid: str, action_xmlid: str, model: str, path: tuple[str, ...], *, maturity: str, source_kind: str = "p1_locked_menu_surface_projection") -> dict:
    capability_key = "construction.menu.%s" % menu_xmlid.replace(".", "_")
    domain_label = path[-2] if len(path) > 1 else center
    return {
        "access_level": "public", "action_xmlid": action_xmlid,
        "business_entry_contract_version": "business_entry_disposition.v1",
        "capability_key": capability_key, "capability_maturity": maturity,
        "control_granularity": "user_visible_menu_page",
        "control_object": "P1 施工行业正式产品入口", "disposition_policy": "keep_list_form",
        "enabled": True, "entry_intent": "handling", "entry_intent_label": "办理",
        "entry_target_policy": "keep_list_form", "group_key": f"construction.{center}",
        "group_label": center, "integration_target": f"{model} {label}", "label": label,
        "locked_data_policy": "odoo_model_acl_and_record_rules", "menu_key": menu_xmlid,
        "menu_xmlid": menu_xmlid, "model": model, "name": label, "page_key": menu_xmlid,
        "page_label": label, "policy_note": "locked_complete_product_menu_surface",
        "product_domain": center, "product_domain_label": domain_label, "product_key": center,
        "productization_source": source_kind, "release_domain": "construction",
        "release_state": "released", "res_model": model, "source_kind": source_kind,
        "target_scene_key": "", "title": label, "view_modes": ["tree", "form"],
        "visible_menu_path": " / ".join(("智慧施工管理平台", center, *path)),
    }


def _scene_entry_row(center: str, label: str, menu_xmlid: str, scene_key: str, path: tuple[str, ...], *, maturity: str) -> dict:
    """Contracted navigation entry whose identity is a declared scene.

    It deliberately carries no action_xmlid/res_model: the entry is authorized
    by the same native (menu_id, action_id=0) pair as any other entry, and the
    backend owns the route/entry_target projection so the tree cannot drift.
    """
    capability_key = "construction.menu.%s" % menu_xmlid.replace(".", "_")
    domain_label = path[-2] if len(path) > 1 else center
    route = "/s/%s" % scene_key
    return {
        "access_level": "public", "action_xmlid": "",
        "business_entry_contract_version": "business_entry_disposition.v1",
        "capability_key": capability_key, "capability_maturity": maturity,
        "control_granularity": "user_visible_menu_page",
        "control_object": "P1 施工行业正式产品入口", "disposition_policy": "scene_entry",
        "enabled": True, "entry_intent": "handling", "entry_intent_label": "办理",
        "entry_target_policy": "scene_entry", "group_key": f"construction.{center}",
        "group_label": center, "integration_target": f"{scene_key} {label}", "label": label,
        "locked_data_policy": "odoo_model_acl_and_record_rules", "menu_key": menu_xmlid,
        "menu_xmlid": menu_xmlid, "model": "", "name": label, "page_key": menu_xmlid,
        "page_label": label, "policy_note": "locked_complete_product_menu_surface",
        "product_domain": center, "product_domain_label": domain_label, "product_key": center,
        "productization_source": "p1_locked_menu_surface_projection",
        "release_domain": "construction",
        "release_state": "released", "res_model": "", "route": route, "scene_key": scene_key,
        "source_kind": "p1_locked_menu_surface_projection",
        "target_scene_key": scene_key, "title": label, "view_modes": [],
        "visible_menu_path": " / ".join(("智慧施工管理平台", center, *path)),
    }


def _capability_from_menu(row: dict) -> dict:
    keys = ("access_level", "capability_key", "capability_maturity", "control_object", "disposition_policy", "enabled", "entry_intent", "entry_intent_label", "entry_target_policy", "group_key", "group_label", "integration_target", "label", "menu_xmlid", "product_domain", "product_domain_label", "product_key", "release_state", "res_model", "source_kind", "target_scene_key", "visible_menu_path")
    capability = {key: row[key] for key in keys if key in row}
    capability["entry_kind"] = "user_visible_menu_page"
    capability["target_page_key"] = row["page_key"]
    return capability



def project(source):
    contract = copy.deepcopy(source["product_contract"])
    publication = copy.deepcopy(source["product_policy_profiles"])
    groups = []
    seen = set()
    paths = set()
    for center in contract["centers"]:
        center_name = center["name"]
        rows = []
        for item in center["level_two"]:
            for leaf in item.get("children") or [item]:
                binding = leaf.pop("binding")
                menu_xmlid = binding["menu_xmlid"]
                path = (item["name"], leaf["name"]) if item.get("children") else (leaf["name"],)
                full_path = (center_name, *path)
                if not menu_xmlid or menu_xmlid in seen or full_path in paths:
                    raise ValueError("duplicate or empty product menu identity")
                seen.add(menu_xmlid)
                paths.add(full_path)
                if binding.get("entry_target_policy") == "scene_entry":
                    if not binding.get("target_scene_key") or binding.get("action_xmlid") or binding.get("model"):
                        raise ValueError("scene entry must declare only a scene target")
                    row = _scene_entry_row(center_name, leaf["name"], menu_xmlid, binding["target_scene_key"], path, maturity=leaf["delivery"])
                else:
                    if not binding.get("action_xmlid") or not binding.get("model"):
                        raise ValueError("native entry must declare action and model")
                    row = _menu_row(center_name, leaf["name"], menu_xmlid, binding["action_xmlid"], binding["model"], path, maturity=leaf["delivery"], source_kind=binding["source_kind"])
                if "sequence" in binding:
                    row["sequence"] = binding["sequence"]
                if "view_modes" in binding:
                    row["view_modes"] = binding["view_modes"]
                row["release_state"] = binding["release_state"]
                leaf["release_state"] = binding["release_state"]
                row["visible_menu_path"] = " / ".join((source["root_label"], center_name, *path))
                rows.append(row)
        groups.append({"category":"user_visible_menu", "group_key":f"construction.{center_name}", "group_label":center_name, "label":center_name, "title":center_name, "menus":rows})
    if not seen:
        raise ValueError("empty formal menu source")
    counts = {}
    for product in publication["products"]:
        if "menu_groups" in product or "capabilities" in product:
            raise ValueError("publication template cannot redefine menu facts")
        included = product.get("included_release_states")
        expected = {"standard": ["released"], "preview": ["released", "preview"]}.get(product.get("edition_key"))
        if included != expected or expected is None:
            raise ValueError("invalid edition release scope")
        selected = [{**copy.deepcopy(group), "menus": [copy.deepcopy(row) for row in group["menus"] if row["release_state"] in included]} for group in groups]
        product["menu_groups"] = selected
        product["capabilities"] = [_capability_from_menu(row) for group in selected for row in group["menus"]]
        counts[product["product_key"]] = len(product["capabilities"])
    released_count = sum(row["release_state"] == "released" for group in groups for row in group["menus"])
    publication["policy_strategy"]["effective_menu_count_per_product"] = released_count
    publication["policy_strategy"]["effective_capability_count_per_product"] = released_count
    publication["policy_strategy"]["menu_count_by_product"] = counts
    publication["policy_strategy"]["full_product_entry_count"] = len(seen)
    return contract, publication
