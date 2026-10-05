# -*- coding: utf-8 -*-
"""Guard that formal product entries stay permission/contract driven.

Run through Odoo shell:
    DB_NAME=<db> make verify.formal_entry_capability_authority.guard

For every entry declared by the versioned formal product-menu policy baseline
the effective record capability must not be blocked *solely* by a view arch. If
a view denies an operation while the model right and the entry declaration both
allow it, then a presentation view owns the capability, which the architecture
forbids: read-only has to come from permissions (ACL / record rules), from an
entry-level declaration in the action context, or from the consumed render
profile, never from a dedicated read-only form.

This is a consumption check, not a text check: it reads the same
``statusContract.globalStatus`` authority split the frontend consumes.
"""

import json
import os
from pathlib import Path

import odoo.addons.smart_construction_core as _smart_construction_core

# This script runs through ``odoo shell`` (piped on stdin, so ``__file__`` is
# undefined). Locate the repository from the installed addon instead, and allow
# an explicit override for non-standard mounts.
ROOT = Path(_smart_construction_core.__file__).resolve().parents[2]
BASELINE = Path(
    os.environ.get(
        "FORMAL_MENU_POLICY_BASELINE",
        str(ROOT / "scripts/verify/baselines/formal_business_product_menu_policy_v1.json"),
    )
)
OPERATIONS = ("read", "write", "create", "unlink", "duplicate")


def _env():
    return globals()["env"]


def _formal_menu_xmlids():
    data = json.loads(BASELINE.read_text(encoding="utf-8"))
    keys = set()
    for product in data.get("products") or []:
        for capability in product.get("capabilities") or []:
            xmlid = capability.get("menu_xmlid")
            if xmlid and capability.get("enabled", True):
                keys.add(xmlid)
    return sorted(keys)


def _contract(user_env, action, menu):
    from odoo.addons.smart_core.handlers.ui_contract_v2 import UiContractV2Handler

    params = {
        "op": "action_open",
        "action_id": action.id,
        "menu_id": menu.id,
        "client_type": "web_pc",
        "delivery_profile": "full",
    }
    result = UiContractV2Handler(user_env, payload={"params": params}).handle(params, {})
    envelope = result.to_legacy_dict() if hasattr(result, "to_legacy_dict") else result
    if not envelope.get("ok", True):
        return None
    return envelope.get("data") or {}


def main():
    env = _env()
    errors = []
    checked = 0
    missing = []
    for xmlid in _formal_menu_xmlids():
        menu = env.ref(xmlid, raise_if_not_found=False)
        if not menu:
            missing.append(xmlid)
            continue
        action = menu.action
        if not action or action._name != "ir.actions.act_window":
            continue
        contract = _contract(env, action, menu)
        if contract is None:
            errors.append("%s: action_open contract did not succeed" % xmlid)
            continue
        status = (contract.get("statusContract") or {}).get("globalStatus") or {}
        view_caps = status.get("viewCapabilities") or {}
        model_rights = status.get("modelRights") or {}
        entry_caps = status.get("entryCapabilities") or {}
        checked += 1
        for operation in OPERATIONS:
            if view_caps.get(operation) is False and model_rights.get(operation) is True and entry_caps.get(operation) is True:
                errors.append(
                    "%s: view arch is the sole blocker of '%s' (model right and entry declaration both allow)"
                    % (xmlid, operation)
                )
    if missing:
        print("FORMAL_ENTRY_CAPABILITY_AUTHORITY_MISSING=%d" % len(missing))
    if errors:
        for error in errors:
            print("FORMAL_ENTRY_CAPABILITY_AUTHORITY_ERROR=%s" % error)
        raise AssertionError("; ".join(errors))
    print("FORMAL_ENTRY_CAPABILITY_AUTHORITY_OK entries=%d" % checked)


main()
