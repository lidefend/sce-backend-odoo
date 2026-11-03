"""Project scene handling entries from an authorized native form view.

The scene stores one source reference. Labels, ordering, actions and groups
remain in native declarations; this reader never creates records or grants ACL.
"""
from __future__ import annotations


def _groups_allowed(env, groups):
    tokens = [value.strip() for value in str(groups or "").split(",") if value.strip()]
    positive = [value for value in tokens if not value.startswith("!")]
    negative = [value[1:] for value in tokens if value.startswith("!")]
    return (not positive or any(env.user.has_group(value) for value in positive)) and not any(
        env.user.has_group(value) for value in negative)


def _node_allowed(env, node, parents):
    ancestor = node
    while ancestor is not None:
        if not _groups_allowed(env, ancestor.get("groups")):
            return False
        if ancestor.get("attrs") or ancestor.get("states"):
            raise ValueError("NATIVE_HANDLING_RECORD_MODIFIER_UNSUPPORTED")
        invisible = ancestor.get("invisible")
        if invisible in ("1", "True", "true"):
            return False
        if invisible not in (None, "0", "False", "false"):
            raise ValueError("NATIVE_HANDLING_RECORD_MODIFIER_UNSUPPORTED")
        ancestor = parents.get(ancestor)
    return True


def project_native_handling_catalog(env, scene):
    """Return None for legacy scenes, or the complete native projection.

    Missing/invalid declared sources raise instead of restoring a historical
    provider whitelist. A denied source returns an empty authorized catalog.
    """
    extensions = scene.get("extensions") or {}
    if not isinstance(extensions, dict):
        raise ValueError("NATIVE_HANDLING_EXTENSIONS_INVALID")
    source = extensions.get("native_handling_entry_source")
    if source is None:
        return None
    if not isinstance(source, dict) or not isinstance(source.get("view_xmlid"), str):
        raise ValueError("NATIVE_HANDLING_SOURCE_INVALID")
    if env is None:
        raise ValueError("NATIVE_HANDLING_ENV_REQUIRED")
    view = env.ref(source["view_xmlid"], raise_if_not_found=False)
    if not view or view._name != "ir.ui.view" or view.type != "form" or not view.active:
        raise ValueError("NATIVE_HANDLING_VIEW_UNAVAILABLE")
    catalog = {"contract_version": "handling_entry_catalog.v1",
               "domain": str(scene.get("code") or scene.get("key") or ""),
               "entry_mode": "integrated_handling", "source_authority": "ir.ui.view + ir.actions.act_window",
               "source_view_xmlid": source["view_xmlid"], "groups": [], "group_count": 0, "item_count": 0}
    if view.groups_id and not (view.groups_id & env.user.groups_id):
        return catalog
    if not env[view.model].check_access_rights("read", raise_exception=False):
        return catalog
    arch = view._get_combined_arch()
    parents = {child: parent for parent in arch.iter() for child in parent}
    seen = set()
    for group in arch.iter("group"):
        buttons = group.findall("button")
        if not buttons or not _node_allowed(env, group, parents):
            continue
        key, title = group.get("name"), group.get("string")
        if not key or not title:
            raise ValueError("NATIVE_HANDLING_GROUP_IDENTITY_MISSING")
        items = []
        for button in buttons:
            if not _node_allowed(env, button, parents):
                continue
            if button.get("context"):
                raise ValueError("NATIVE_HANDLING_BUTTON_CONTEXT_UNSUPPORTED")
            if button.get("type") != "action":
                raise ValueError("NATIVE_HANDLING_BUTTON_REQUIRES_ACTION")
            reference = str(button.get("name") or "")
            action = (env["ir.actions.act_window"].browse(int(reference)).exists()
                      if reference.isdigit() else env.ref(reference, raise_if_not_found=False))
            if not action or action._name != "ir.actions.act_window":
                raise ValueError("NATIVE_HANDLING_ACTION_UNAVAILABLE")
            if action.groups_id and not (action.groups_id & env.user.groups_id):
                continue
            if not env[action.res_model].check_access_rights("read", raise_exception=False):
                continue
            xmlid = action.get_external_id().get(action.id)
            if not xmlid or xmlid in seen:
                raise ValueError("NATIVE_HANDLING_ACTION_IDENTITY_INVALID")
            seen.add(xmlid)
            label = button.get("string") or action.name
            items.append({"key": xmlid, "label": label, "model": action.res_model,
                          "action_xmlid": xmlid, "target": {"type": "action", "action_xmlid": xmlid},
                          "remediation_keys": [key.strip() for key in (button.get("data-sc-remediation") or "").split(",") if key.strip()]})
        if items:
            catalog["groups"].append({"key": key, "title": title, "items": items})
    catalog["group_count"] = len(catalog["groups"])
    catalog["item_count"] = sum(len(group["items"]) for group in catalog["groups"])
    return catalog
