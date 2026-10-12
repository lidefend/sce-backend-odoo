#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Falsifiable, container-free assertions for the collection-capability rule.

The list surface publishes one declared action list; ``import`` may only appear
there when the caller's *effective rights* allow ``create`` on a model that has
a list view and at least one importable field.  A README cannot prove that, and
a runtime census only samples the models that happen to be reachable, so the
rule is locked here against the pure function that implements it.

What is asserted is the mechanism, not the presence of a string:

* ``import`` is declared exactly when ``rights.create`` is true (a biconditional
  sweep, so a future "just add import for this model" cannot pass);
* absence of rights never promotes a capability (fail-closed, not inferred);
* the declaration is a pure function of (selection_actions, rights, fields_map,
  has_list_view) — it has no model/surface/action parameter, so a per-model
  special case is not expressible;
* ``batch_policy`` is the ``selection`` projection of that same declaration, so
  an empty declaration yields an empty policy instead of a second derivation.
"""

from __future__ import annotations

import importlib.util
import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CAPABILITY_PATH = ROOT / "addons/smart_core/utils/collection_action_capability.py"

_spec = importlib.util.spec_from_file_location("collection_action_capability", CAPABILITY_PATH)
if _spec is None or _spec.loader is None:  # pragma: no cover - defensive
    raise SystemExit(f"cannot load {CAPABILITY_PATH}")
capability = importlib.util.module_from_spec(_spec)
sys.modules["collection_action_capability"] = capability
_spec.loader.exec_module(capability)

build_collection_capabilities = capability.build_collection_capabilities
project_scope_actions = capability.project_scope_actions
project_selection_policy = capability.project_selection_policy
IMPORT_ACTION = capability.IMPORT_ACTION
IMPORT_INTENT = capability.IMPORT_INTENT
COLLECTION_SCOPE = capability.COLLECTION_SCOPE
SELECTION_SCOPE = capability.SELECTION_SCOPE

cases = 0


def check(actual, expected, label):
    global cases
    if actual != expected:
        raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")
    cases += 1


def actions_of(caps, scope):
    return [row["action"] for row in project_scope_actions(caps, scope)]


# A model the caller may create on, with a list view and one importable field.
OPEN_RIGHTS = {"read": True, "write": True, "create": True, "unlink": True}
READONLY_RIGHTS = {"read": True, "write": False, "create": False, "unlink": False}
IMPORTABLE_FIELDS = {"id": {}, "name": {"readonly": False}, "note": {"readonly": False}}
NO_IMPORTABLE_FIELDS = {"id": {}, "name": {"readonly": True}, "create_date": {"readonly": False}}
SELECTION = ["export", "delete"]


def build(rights, fields_map, has_list_view=True, selection=SELECTION):
    return build_collection_capabilities(
        selection_actions=selection,
        rights=rights,
        fields_map=fields_map,
        has_list_view=has_list_view,
    )


# --- the positive path: create right + list view + importable field ---
open_caps = build(OPEN_RIGHTS, IMPORTABLE_FIELDS)
check(IMPORT_ACTION in actions_of(open_caps, COLLECTION_SCOPE), True,
      "a caller with create rights on a list model with importable fields gets import")
import_row = next(row for row in project_scope_actions(open_caps, COLLECTION_SCOPE) if row["action"] == IMPORT_ACTION)
check(import_row["intent"], IMPORT_INTENT, "the declared import carries the governed import intent")
check(import_row["available"], True, "a declared available row stays declared available")
check(actions_of(open_caps, SELECTION_SCOPE), SELECTION, "selection actions are published unchanged")
check(open_caps["enabled"], True, "enabled reflects having declared actions")

# --- the negative path: the create right is the gate, nothing else promotes it ---
check(actions_of(build(READONLY_RIGHTS, IMPORTABLE_FIELDS), COLLECTION_SCOPE), [],
      "a read-only role gets no import even though the model is importable")
check(actions_of(build(READONLY_RIGHTS, IMPORTABLE_FIELDS), SELECTION_SCOPE), SELECTION,
      "a read-only role still gets the selection actions it was granted")
check(actions_of(build(OPEN_RIGHTS, IMPORTABLE_FIELDS, has_list_view=False), COLLECTION_SCOPE), [],
      "create rights without a list view declare no collection action")
check(actions_of(build(OPEN_RIGHTS, NO_IMPORTABLE_FIELDS), COLLECTION_SCOPE), [],
      "create rights on a model with no importable field declare no import")

# --- absence is not a permission: no rights / empty rights / wrong shape ---
for missing in (None, {}, {"read": True}, {"create": "yes"}, [], ""):
    check(actions_of(build(missing, IMPORTABLE_FIELDS), COLLECTION_SCOPE), [],
          f"an undeclared or non-boolean create right ({missing!r}) declares no import")

# --- the biconditional sweep: import present == (create and list view and importable) ---
for rights_create in (True, False):
    for has_list_view in (True, False):
        for fields_map in (IMPORTABLE_FIELDS, NO_IMPORTABLE_FIELDS):
            rights = {"read": True, "create": rights_create}
            declared = IMPORT_ACTION in actions_of(build(rights, fields_map, has_list_view), COLLECTION_SCOPE)
            expected = rights_create and has_list_view and bool(capability.importable_field_names(fields_map))
            check(declared, expected,
                  f"import declared={declared} must equal create/list-view/importable={expected}")

# --- availability is declared, never inferred from a row's presence ---
undeclared = {"actions": [{"action": "import", "scope": COLLECTION_SCOPE, "intent": IMPORT_INTENT}]}
check(project_scope_actions(undeclared, COLLECTION_SCOPE)[0]["available"], False,
      "a declared row that does not declare availability is not assumed usable")
check(project_scope_actions(undeclared, SELECTION_SCOPE), [],
      "a collection-scope row never leaks into the selection scope")

# --- batch_policy is the projection of the same declaration, not a second derivation ---
policy = project_selection_policy(open_caps)
check(policy["available_actions"], SELECTION, "the selection policy mirrors the declared selection actions")
check(policy["execution_intents"], {"export": "api.data", "delete": "api.data.unlink"},
      "the selection policy carries each declared action's declared intent")
check(project_selection_policy({"actions": []})["available_actions"], [],
      "an empty declaration yields an empty selection policy instead of a fallback")
check(IMPORT_ACTION in policy["available_actions"], False,
      "the collection action is not advertised as a selection action")

# --- no per-model special case is expressible: the rule has no model/surface input ---
params = set(inspect.signature(build_collection_capabilities).parameters)
check(params, {"selection_actions", "rights", "fields_map", "has_list_view"},
      "the capability rule takes only facts, so model/surface name-casing cannot exist")
for forbidden in ("model", "surface", "action_id", "context", "menu"):
    check(forbidden in params, False, f"the capability rule must not accept {forbidden!r}")

print(f"[collection_capability_rights_projection_test] PASS cases={cases}")
