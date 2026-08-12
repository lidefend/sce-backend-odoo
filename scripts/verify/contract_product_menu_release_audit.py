# -*- coding: utf-8 -*-
from __future__ import annotations

import json

from odoo import api
from odoo.addons.smart_core.delivery.final_menu_navigation_service import FinalMenuNavigationService
from odoo.addons.smart_construction_core.services.locked_menu_policy_contract import (
    load_locked_menu_policy_contract,
)


CONTRACT_CENTER_XMLID = "smart_construction_core.menu_sc_contract_center"
REQUIRED_CONTRACT_GROUP_XMLID = "smart_construction_core.group_sc_cap_contract_read"
REQUIRED_SETTLEMENT_GROUP_XMLID = "smart_construction_core.group_sc_cap_settlement_read"
REQUIRED_PRODUCT_ADMIN_GROUP_XMLID = "smart_construction_core.group_sc_cap_business_config_admin"
CONTRACT_CENTER_LABEL = "合同中心"
CONTRACT_ROADMAP_XMLID = "smart_construction_core.menu_sc_contract_performance_roadmap_v2"

USER_ACCEPTANCE_PRODUCT_MENU_XMLIDS = {
    "smart_construction_core.menu_sc_customer_partner",
    "smart_construction_core.menu_sc_supplier_partner",
}

USER_ACCEPTANCE_MENU_KEY_TOKENS = (
    "_acceptance",
    "user_acceptance",
)

VISIBLE_CHECK_USERS = (
    "wutao",
    "sc_fx_pm",
)


def _ref(xmlid):
    record = env.ref(xmlid, raise_if_not_found=False)  # noqa: F821
    if not record:
        raise AssertionError("missing xmlid: %s" % xmlid)
    return record


def _external_id(record):
    return record.get_external_id().get(record.id, "") if record else ""


def _is_user_acceptance_key(value):
    key = str(value or "").strip()
    return key in USER_ACCEPTANCE_PRODUCT_MENU_XMLIDS or any(token in key for token in USER_ACCEPTANCE_MENU_KEY_TOKENS)


def _assert_menu_has_any_group(menu_xmlid, group_xmlids):
    menu = _ref(menu_xmlid)
    expected_groups = [_ref(xmlid) for xmlid in group_xmlids]
    if not any(group in menu.groups_id for group in expected_groups):
        raise AssertionError(
            "%s missing one of %s; groups=%s"
            % (menu_xmlid, group_xmlids, sorted(_external_id(row) for row in menu.groups_id))
        )


def _locked_contract_menu_keys(product_key):
    contract = load_locked_menu_policy_contract()
    product = contract["products"].get(product_key) or {}
    for group in product.get("menu_groups") or []:
        label = str(group.get("group_label") or group.get("label") or "").strip()
        if label == CONTRACT_CENTER_LABEL:
            return tuple(
                str(row.get("menu_xmlid") or row.get("page_key") or row.get("menu_key") or "").strip()
                for row in group.get("menus") or []
                if isinstance(row, dict)
            )
    raise AssertionError("locked contract center is missing: %s" % product_key)


def _released_policy_menu_keys(product_key):
    policy = env["sc.product.policy"].sudo().search([("product_key", "=", product_key)], limit=1)  # noqa: F821
    if not policy:
        raise AssertionError("missing product policy: %s" % product_key)
    if not policy.active or policy.access_level != "public":
        raise AssertionError("%s must be active public" % product_key)

    keys = set()
    for group in policy.menu_groups or []:
        if not isinstance(group, dict):
            continue
        for menu in group.get("menus") or []:
            if not isinstance(menu, dict):
                continue
            if menu.get("enabled") and menu.get("release_state") == "released":
                keys.add(str(menu.get("page_key") or menu.get("menu_key") or ""))
    return keys


def _assert_user_reaches_released_targets(login, menu_xmlids):
    user = env["res.users"].sudo().search([("login", "=", login)], limit=1)  # noqa: F821
    if not user:
        raise AssertionError("missing verification user: %s" % login)
    user_env = api.Environment(env.cr, int(user.id), dict(env.context or {}))  # noqa: F821
    delivery = FinalMenuNavigationService(user_env).build()
    convergence = (delivery.get("meta") or {}).get("delivery_convergence") or {}
    if convergence.get("source") != "delivery_engine_v1":
        raise AssertionError("%s did not resolve navigation through delivery_engine_v1" % login)
    delivered_action_ids = {
        int(row.get("action_id") or 0)
        for row in ((delivery.get("nav_fact") or {}).get("flat") or [])
        if isinstance(row, dict) and int(row.get("action_id") or 0) > 0
    }
    missing = []
    for xmlid in menu_xmlids:
        menu = _ref(xmlid)
        action_id = int(getattr(menu.action, "id", 0) or 0)
        if action_id and action_id not in delivered_action_ids:
            missing.append(xmlid)
    if missing:
        raise AssertionError("%s cannot reach required released targets: %s" % (login, missing))


def main():
    _assert_menu_has_any_group(CONTRACT_CENTER_XMLID, (REQUIRED_CONTRACT_GROUP_XMLID,))

    product_results = {}
    locked_contract_menus = None
    for product_key in ("construction.standard", "construction.preview"):
        expected = _locked_contract_menu_keys(product_key)
        if locked_contract_menus is None:
            locked_contract_menus = expected
        elif expected != locked_contract_menus:
            raise AssertionError("standard and preview contract centers must be identical")
        keys = _released_policy_menu_keys(product_key)
        missing = [xmlid for xmlid in expected if xmlid not in keys]
        if missing:
            raise AssertionError("%s missing released formal pages: %s" % (product_key, missing))
        product_results[product_key] = len(keys)

    locked_contract_menus = locked_contract_menus or ()
    for menu_xmlid in locked_contract_menus:
        _assert_menu_has_any_group(
            menu_xmlid,
            (
                REQUIRED_CONTRACT_GROUP_XMLID,
                REQUIRED_SETTLEMENT_GROUP_XMLID,
                REQUIRED_PRODUCT_ADMIN_GROUP_XMLID,
            ),
        )
    user_visible_contract_menus = tuple(
        xmlid for xmlid in locked_contract_menus if xmlid != CONTRACT_ROADMAP_XMLID
    )
    for login in VISIBLE_CHECK_USERS:
        _assert_user_reaches_released_targets(login, (CONTRACT_CENTER_XMLID, *user_visible_contract_menus))

    print(
        json.dumps(
            {
                "status": "PASS",
                "db": env.cr.dbname,  # noqa: F821
                "contract_center": CONTRACT_CENTER_XMLID,
                "released_contract_pages": list(locked_contract_menus),
                "product_released_menu_counts": product_results,
                "visible_users": list(VISIBLE_CHECK_USERS),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


main()
