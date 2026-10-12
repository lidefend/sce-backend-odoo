# -*- coding: utf-8 -*-
"""Collection capability declaration — the single source of list-surface actions.

A governed list surface declares the actions it may offer in exactly one place:
``surface_policies.collection_capabilities.actions``.  Every declared action
carries the two facts a consumer must not invent for itself:

* ``scope`` — where the action belongs.  ``selection`` actions operate on the
  chosen rows and are only reachable once rows are selected; ``collection``
  actions operate on the collection itself and are therefore reachable with an
  empty selection (today: ``import``).
* ``intent`` — the backend intent the action executes through.

Encoding the scope in the *data* instead of in a container key name is what lets
the frontend route an action to the right surface and look up an executor
without deciding the action's scope, availability or business rules itself.
``batch_policy`` remains published as the ``selection`` projection of this same
list so existing consumers and evidence stay valid; it is a projection of this
fact, never an independent derivation.

Availability is decided here from facts the contract already carries (the
caller's effective rights, the model field map, the declared delete policy and
active flag).  A model the caller may create on but that cannot be imported is
rejected by the governed ``api.data.import`` intent, which reports the reason
code it refused with; the importability rule below mirrors the kernel's own so
declaration and executor agree on the same facts.
"""

from typing import Any, Dict, Iterable, List

MAGIC_COLUMNS = ("id", "create_uid", "create_date", "write_uid", "write_date", "__last_update")

SELECTION_SCOPE = "selection"
COLLECTION_SCOPE = "collection"

IMPORT_ACTION = "import"
IMPORT_INTENT = "api.data.import"

# The intent each selection-scope action executes through.  Declared here so the
# projection and any consumer agree on one table instead of repeating it.
SELECTION_SCOPE_INTENTS = {
    "export": "api.data",
    "archive": "api.data.batch",
    "activate": "api.data.batch",
    "delete": "api.data.unlink",
}


def importable_field_names(fields_map: Any) -> List[str]:
    """Field names the import kernel would accept, per its own rule."""

    names: List[str] = []
    if not isinstance(fields_map, dict):
        return names
    for name, row in fields_map.items():
        field_name = str(name or "").strip()
        if not field_name or field_name in MAGIC_COLUMNS:
            continue
        if not isinstance(row, dict):
            continue
        if row.get("deprecated", False) is not False:
            continue
        if row.get("readonly"):
            continue
        names.append(field_name)
    return names


def build_collection_capabilities(
    *,
    selection_actions: Iterable[str],
    rights: Any,
    fields_map: Any,
    has_list_view: bool,
) -> Dict[str, Any]:
    """The single declared action list for a governed collection surface.

    ``selection_actions`` is the already-governed selection-scope set; it is
    tagged with its scope here rather than restated, and the collection-scope
    facts are derived from the same payload.
    """

    actions: List[Dict[str, str]] = []
    for action in selection_actions:
        name = str(action or "").strip().lower()
        intent = SELECTION_SCOPE_INTENTS.get(name)
        if not name or not intent:
            continue
        actions.append({"action": name, "scope": SELECTION_SCOPE, "intent": intent, "available": True})
    resolved_rights = rights if isinstance(rights, dict) else {}
    # Declared, not coerced: a right that is not literally true is not a granted
    # right, matching how ``available`` is read back below.  A truthy string or
    # number must not promote a capability the ACL never granted.
    create_allowed = resolved_rights.get("create") is True
    if has_list_view and create_allowed and importable_field_names(fields_map):
        actions.append({"action": IMPORT_ACTION, "scope": COLLECTION_SCOPE, "intent": IMPORT_INTENT, "available": True})
    return {"enabled": bool(actions), "actions": actions}


def project_scope_actions(capabilities: Any, scope: str) -> List[Dict[str, str]]:
    """The declared actions of one scope, in declared order."""

    rows = capabilities.get("actions") if isinstance(capabilities, dict) else None
    if not isinstance(rows, list):
        return []
    wanted = str(scope or "").strip()
    return [
        {
            "action": str(row.get("action") or ""),
            "scope": str(row.get("scope") or ""),
            "intent": str(row.get("intent") or ""),
            # Availability is declared, never inferred: a row that does not
            # declare it is unavailable rather than assumed usable.
            "available": row.get("available") is True,
        }
        for row in rows
        if isinstance(row, dict) and str(row.get("scope") or "") == wanted and str(row.get("action") or "")
    ]


def project_selection_policy(capabilities: Any) -> Dict[str, Any]:
    """``batch_policy``'s action fields, projected from the single declared list.

    Shape and order match the historic ``batch_policy`` derivation exactly, so
    the projection replaces a second derivation rather than adding a channel.
    """

    declared = project_scope_actions(capabilities, SELECTION_SCOPE)
    available_actions = [row["action"] for row in declared]
    return {
        "available_actions": available_actions,
        "execution_intents": {row["action"]: row["intent"] for row in declared},
        "execution_operations": {row["action"]: "export_csv" for row in declared if row["action"] == "export"},
    }
