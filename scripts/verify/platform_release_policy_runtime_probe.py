# -*- coding: utf-8 -*-
"""Runtime probe for platform product release policy effectiveness.

Run through Odoo shell:
  ENV=dev ENV_FILE=.env.dev DB_NAME=sc_demo make verify.platform.release_policy.runtime

The probe is read-only. It validates that construction product editions resolve
to a non-empty platform release policy surface and that delivery navigation is
filtered by the current user's native authorized menu facts.
"""

from __future__ import annotations

import json
from pathlib import Path

from odoo import api
from odoo.addons.smart_core.delivery.delivery_engine import DeliveryEngine
from odoo.addons.smart_core.delivery.menu_service import MenuService
from odoo.addons.smart_core.delivery.product_policy_catalog_sync_service import ProductPolicyCatalogSyncService
from odoo.addons.smart_core.delivery.product_policy_service import ProductPolicyService
from odoo.addons.smart_core.utils.extension_hooks import call_extension_hook_first


PRODUCT_KEYS = ("construction.standard", "construction.preview")
REPORT_JSON = Path("/tmp/platform_release_policy_runtime_probe.json")
REPORT_MD = Path("/tmp/platform_release_policy_runtime_probe.md")
RUNTIME_USER_ROLE_SURFACE = {
    "role_code": "runtime_user",
    "is_platform_admin": False,
    "is_business_config_admin": False,
    "exposure_policy_declared": True,
    "discover_installed_capabilities": True,
}


def _env():
    return globals()["env"]


def _text(value) -> str:
    return str(value or "").strip()


def _to_int(value) -> int:
    try:
        parsed = int(value or 0)
    except Exception:
        return 0
    return parsed if parsed > 0 else 0


def _leaf_count(nodes) -> int:
    count = 0
    for node in nodes or []:
        if not isinstance(node, dict):
            continue
        children = node.get("children") if isinstance(node.get("children"), list) else []
        if children:
            count += _leaf_count(children)
        else:
            count += 1
    return count


def _menu_xmlid(menu) -> str:
    try:
        return _text(menu.get_external_id().get(menu.id))
    except Exception:
        return ""


def _action_model(action) -> str:
    try:
        model = _text(getattr(action, "res_model", ""))
        if model:
            return model
        model = _text(getattr(action, "model_name", ""))
        if model:
            return model
        model_id = getattr(action, "model_id", None)
        model = _text(getattr(model_id, "model", ""))
        if model:
            return model
        binding_model_id = getattr(action, "binding_model_id", None)
        return _text(getattr(binding_model_id, "model", ""))
    except Exception:
        return ""


def _menu_action_id(menu) -> int:
    try:
        return _to_int(getattr(menu.action, "id", 0))
    except Exception:
        return 0


def _visible_menu_ids(user_env) -> list[int]:
    menu_model = user_env["ir.ui.menu"]
    try:
        ids = menu_model._visible_menu_ids(debug=False)
    except TypeError:
        ids = menu_model._visible_menu_ids()
    except Exception:
        ids = menu_model.search([]).ids
    return sorted({_to_int(item) for item in ids if _to_int(item)})


def _native_nav_for_user(user_env, *, limit: int | None = None) -> list[dict]:
    ids = _visible_menu_ids(user_env)
    menus = user_env["ir.ui.menu"].browse(ids).exists()
    leaves = []
    for menu in menus:
        if hasattr(menu, "active") and not bool(menu.active):
            continue
        action_id = _menu_action_id(menu)
        if action_id <= 0:
            continue
        xmlid = _menu_xmlid(menu)
        model = _action_model(menu.action)
        route = "/a/%s?menu_id=%s" % (action_id, int(menu.id))
        leaves.append(
            {
                "label": _text(menu.name),
                "menu_id": int(menu.id),
                "route": route,
                "scene_key": "",
                "menu_xmlid": xmlid,
                "meta": {
                    "menu_id": int(menu.id),
                    "menu_xmlid": xmlid,
                    "route": route,
                    "action_id": action_id,
                    "model": model,
                    "scene_key": "",
                },
            }
        )
    leaves.sort(key=lambda row: (_text(row.get("label")), int(row.get("menu_id") or 0)))
    if limit is not None:
        leaves = leaves[: max(0, int(limit))]
    return leaves


def _policy_surface_counts(policy: dict) -> dict:
    return {
        "menu_group_count": len(policy.get("menu_groups") or []),
        "menu_count": sum(
            len(group.get("menus") or [])
            for group in policy.get("menu_groups") or []
            if isinstance(group, dict)
        ),
        "scene_count": len(policy.get("scenes") or []),
        "capability_count": len(policy.get("capabilities") or []),
    }


def _delivery_summary(user_env, *, product_key: str, native_nav: list[dict], role_surface: dict) -> dict:
    delivery = DeliveryEngine(user_env).build(
        data={"role_surface": dict(role_surface or {})},
        product_key=product_key,
        native_nav=native_nav,
    )
    product_policy = delivery.get("product_policy") if isinstance(delivery.get("product_policy"), dict) else {}
    meta = delivery.get("meta") if isinstance(delivery.get("meta"), dict) else {}
    nav = delivery.get("nav") if isinstance(delivery.get("nav"), list) else []
    return {
        "product_key": _text(delivery.get("product_key")),
        "policy_source_kind": _text(product_policy.get("policy_source_kind")),
        "policy_empty": bool(product_policy.get("policy_empty")),
        "menu_key_count": len(product_policy.get("menu_keys") or []),
        "scene_key_count": len(product_policy.get("scene_keys") or []),
        "capability_key_count": len(product_policy.get("capability_keys") or []),
        "nav_leaf_count": _leaf_count(nav),
        "stable_leaf_count": int(meta.get("stable_leaf_count") or 0),
        "native_preview_leaf_count": int(meta.get("native_preview_leaf_count") or 0),
        "delivered_menu_leaf_count": int(meta.get("stable_leaf_count") or 0)
        + int(meta.get("native_preview_leaf_count") or 0),
        "nav_source_authority_kind": _text((meta.get("nav_source_authority") or {}).get("kind")),
        "capability_source_authority_kind": _text((meta.get("capability_source_authority") or {}).get("kind")),
        "group_count": int(meta.get("group_count") or 0),
    }


def _find_probe_user():
    env = _env()
    for login in ("wutao", "caisiqi", "chenshuai"):
        user = env["res.users"].sudo().search([("login", "=", login), ("active", "=", True)], limit=1)
        if user:
            return user
    return env.user


def _customer_specific_product_views(env):
    xmlids = env["ir.model.data"].sudo().search(
        [
            ("module", "=", "smart_construction_core"),
            ("model", "=", "ir.ui.view"),
        ]
    )
    views = env["ir.ui.view"].sudo().with_context(active_test=False).browse(xmlids.mapped("res_id")).exists()
    forbidden_tokens = ("用户确认数据",)
    contaminated = []
    external_ids = views.get_external_id()
    for view in views:
        arch = _text(getattr(view, "arch_db", ""))
        if any(token in arch for token in forbidden_tokens):
            contaminated.append(_text(external_ids.get(view.id)) or "ir.ui.view:%s" % view.id)
    return sorted(set(contaminated))


def _customer_field_boundary(env, *, model_name, table_name):
    legacy_fields = ["legacy_acceptance_label", "legacy_acceptance_sort_id"] + [
        "legacy_visible_%02d" % index for index in range(1, 61)
    ]
    registered = sorted(set(legacy_fields) & set(env[model_name]._fields))
    env.cr.execute(
        """
        SELECT column_name
          FROM information_schema.columns
         WHERE table_schema = 'public'
           AND table_name = %s
           AND column_name = ANY(%s)
         ORDER BY column_name
        """,
        [table_name, legacy_fields],
    )
    retained_columns = [row[0] for row in env.cr.fetchall()]
    return {
        "registered_fields": registered,
        "registered_field_count": len(registered),
        "remaining_physical_columns": retained_columns,
        "remaining_physical_column_count": len(retained_columns),
    }


def _write_report(payload: dict):
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    try:
        REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "# Platform Release Policy Runtime Probe",
            "",
            "- ok: `%s`" % payload.get("ok"),
            "- db: `%s`" % payload.get("db"),
            "- probe_user: `%s`" % payload.get("probe_user_login"),
            "- failure_count: `%s`" % len(payload.get("failures") or []),
            "",
            "## Products",
            "",
            "| product_key | source | menus | scenes | capabilities | user_leaf | no_native_leaf | admin_leaf |",
            "|---|---|---:|---:|---:|---:|---:|---:|",
        ]
        for product in payload.get("products") or []:
            counts = product.get("policy_counts") or {}
            runtime = product.get("runtime") or {}
            user_delivery = runtime.get("user_delivery") or {}
            no_native_delivery = runtime.get("no_native_delivery") or {}
            admin_delivery = runtime.get("admin_delivery") or {}
            lines.append(
                "| {product_key} | {source} | {menus} | {scenes} | {capabilities} | {user_leaf} | {no_native_leaf} | {admin_leaf} |".format(
                    product_key=product.get("product_key"),
                    source=product.get("policy_source_kind"),
                    menus=counts.get("menu_count"),
                    scenes=counts.get("scene_count"),
                    capabilities=counts.get("capability_count"),
                    user_leaf=user_delivery.get("delivered_menu_leaf_count"),
                    no_native_leaf=no_native_delivery.get("delivered_menu_leaf_count"),
                    admin_leaf=admin_delivery.get("delivered_menu_leaf_count"),
                )
            )
        lines.extend(["", "## Failures", ""])
        failures = payload.get("failures") or []
        if failures:
            lines.extend("- `%s`" % item for item in failures)
        else:
            lines.append("- none")
        REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except Exception as exc:
        payload.setdefault("report_warnings", []).append("MD_WRITE_FAILED:%s" % exc)


def main():
    env = _env()
    failures = []
    policy_service = ProductPolicyService(env)
    catalog_service = ProductPolicyCatalogSyncService(env)
    probe_user = _find_probe_user()
    user_env = api.Environment(env.cr, int(probe_user.id), dict(env.context or {}))
    native_nav = _native_nav_for_user(user_env)
    native_leaf_count = _leaf_count(native_nav)
    native_subset = _native_nav_for_user(user_env, limit=1)
    native_navigation_authoritative = bool(
        call_extension_hook_first(
            user_env,
            "smart_core_native_navigation_authority",
            user_env,
            {},
            RUNTIME_USER_ROLE_SURFACE,
        )
    )
    customer_specific_product_views = _customer_specific_product_views(env)
    if customer_specific_product_views:
        failures.append(
            "smart_construction_core: customer-specific form views remain active in P1: %s"
            % ",".join(customer_specific_product_views)
        )
    material_plan_customer_field_boundary = _customer_field_boundary(
        env, model_name="project.material.plan", table_name="project_material_plan"
    )
    if material_plan_customer_field_boundary["registered_fields"]:
        failures.append(
            "project.material.plan: P2 legacy-visible fields remain registered in P1: %s"
            % ",".join(material_plan_customer_field_boundary["registered_fields"])
        )
    if material_plan_customer_field_boundary["remaining_physical_columns"]:
        failures.append(
            "project.material.plan: P2 legacy-visible physical columns remain after guarded extraction: %s"
            % ",".join(material_plan_customer_field_boundary["remaining_physical_columns"])
        )
    material_rfq_customer_field_boundary = _customer_field_boundary(
        env, model_name="sc.material.rfq", table_name="sc_material_rfq"
    )
    if material_rfq_customer_field_boundary["registered_fields"]:
        failures.append(
            "sc.material.rfq: P2 legacy-visible fields remain registered in P1: %s"
            % ",".join(material_rfq_customer_field_boundary["registered_fields"])
        )
    if material_rfq_customer_field_boundary["remaining_physical_columns"]:
        failures.append(
            "sc.material.rfq: P2 legacy-visible physical columns remain after guarded extraction: %s"
            % ",".join(material_rfq_customer_field_boundary["remaining_physical_columns"])
        )
    material_inbound_customer_field_boundary = _customer_field_boundary(
        env, model_name="sc.material.inbound", table_name="sc_material_inbound"
    )
    if material_inbound_customer_field_boundary["registered_fields"]:
        failures.append(
            "sc.material.inbound: P2 legacy-visible fields remain registered in P1: %s"
            % ",".join(material_inbound_customer_field_boundary["registered_fields"])
        )
    if material_inbound_customer_field_boundary["remaining_physical_columns"]:
        failures.append(
            "sc.material.inbound: P2 legacy-visible physical columns remain after guarded extraction: %s"
            % ",".join(material_inbound_customer_field_boundary["remaining_physical_columns"])
        )
    subcontract_request_customer_field_boundary = _customer_field_boundary(
        env, model_name="sc.subcontract.request", table_name="sc_subcontract_request"
    )
    if subcontract_request_customer_field_boundary["registered_fields"]:
        failures.append(
            "sc.subcontract.request: P2 legacy-visible fields remain registered in P1: %s"
            % ",".join(subcontract_request_customer_field_boundary["registered_fields"])
        )
    if subcontract_request_customer_field_boundary["remaining_physical_columns"]:
        failures.append(
            "sc.subcontract.request: P2 legacy-visible physical columns remain after guarded extraction: %s"
            % ",".join(subcontract_request_customer_field_boundary["remaining_physical_columns"])
        )
    construction_diary_customer_field_boundary = _customer_field_boundary(
        env, model_name="sc.construction.diary", table_name="sc_construction_diary"
    )
    if construction_diary_customer_field_boundary["registered_fields"] or construction_diary_customer_field_boundary["remaining_physical_columns"]:
        failures.append("sc.construction.diary: P2 legacy-visible boundary remains registered or physical")
    settlement_order_customer_field_boundary = _customer_field_boundary(
        env, model_name="sc.settlement.order", table_name="sc_settlement_order"
    )
    if settlement_order_customer_field_boundary["registered_fields"] or settlement_order_customer_field_boundary["remaining_physical_columns"]:
        failures.append("sc.settlement.order: P2 legacy-visible boundary remains registered or physical")
    equipment_usage_customer_field_boundary = _customer_field_boundary(
        env, model_name="sc.equipment.usage", table_name="sc_equipment_usage"
    )
    if equipment_usage_customer_field_boundary["registered_fields"] or equipment_usage_customer_field_boundary["remaining_physical_columns"]:
        failures.append("sc.equipment.usage: P2 legacy-visible boundary remains registered or physical")
    labor_usage_customer_field_boundary = _customer_field_boundary(
        env, model_name="sc.labor.usage", table_name="sc_labor_usage"
    )
    if labor_usage_customer_field_boundary["registered_fields"] or labor_usage_customer_field_boundary["remaining_physical_columns"]:
        failures.append("sc.labor.usage: P2 legacy-visible boundary remains registered or physical")
    material_rental_order_customer_field_boundary = _customer_field_boundary(
        env, model_name="sc.material.rental.order", table_name="sc_material_rental_order"
    )
    if material_rental_order_customer_field_boundary["registered_fields"] or material_rental_order_customer_field_boundary["remaining_physical_columns"]:
        failures.append("sc.material.rental.order: P2 legacy-visible boundary remains registered or physical")
    hr_payroll_document_customer_field_boundary = _customer_field_boundary(
        env, model_name="sc.hr.payroll.document", table_name="sc_hr_payroll_document"
    )
    if hr_payroll_document_customer_field_boundary["registered_fields"] or hr_payroll_document_customer_field_boundary["remaining_physical_columns"]:
        failures.append("sc.hr.payroll.document: P2 legacy-visible boundary remains registered or physical")
    pass_through_customer_field_boundaries = {}
    for model_name, table_name in (
        ("sc.fund.account.operation", "sc_fund_account_operation"),
        ("sc.receipt.income", "sc_receipt_income"),
        ("sc.invoice.registration", "sc_invoice_registration"),
        ("construction.contract.expense", "construction_contract_expense"),
    ):
        boundary = _customer_field_boundary(env, model_name=model_name, table_name=table_name)
        pass_through_customer_field_boundaries[model_name] = boundary
        if boundary["registered_fields"] or boundary["remaining_physical_columns"]:
            failures.append(
                "%s: pass-through P2 legacy-visible boundary remains registered or physical"
                % model_name
            )

    products = []
    allowed_policy_sources = {
        "delivery_product_policy_projection",
        "platform_product_policy_projection",
        "product_policy_catalog_sync",
    }
    for product_key in PRODUCT_KEYS:
        policy = policy_service.get_policy(product_key=product_key, enforce_release=True, enforce_access=True)
        source_kind = _text((policy.get("policy_source_authority") or {}).get("kind"))
        counts = _policy_surface_counts(policy)
        catalog = catalog_service.build_catalog_policy_payload(product_key=product_key)
        catalog_counts = _policy_surface_counts(catalog)

        user_delivery = _delivery_summary(
            user_env,
            product_key=product_key,
            native_nav=native_nav,
            role_surface=RUNTIME_USER_ROLE_SURFACE,
        )
        no_native_delivery = _delivery_summary(
            user_env,
            product_key=product_key,
            native_nav=[],
            role_surface=RUNTIME_USER_ROLE_SURFACE,
        )
        subset_delivery = _delivery_summary(
            user_env,
            product_key=product_key,
            native_nav=native_subset,
            role_surface=RUNTIME_USER_ROLE_SURFACE,
        )
        admin_delivery = _delivery_summary(
            user_env,
            product_key=product_key,
            native_nav=native_nav,
            role_surface={
                "role_code": "platform_admin",
                "is_platform_admin": True,
                "exposure_policy_declared": True,
                "discover_installed_capabilities": True,
            },
        )

        if source_kind not in allowed_policy_sources:
            failures.append("%s: unexpected policy_source_kind=%s" % (product_key, source_kind))
        if counts["menu_count"] <= 0:
            failures.append("%s: policy menu_count is empty" % product_key)
        if catalog_counts["menu_count"] <= 0:
            failures.append("%s: catalog projection menu_count is empty" % product_key)
        if user_delivery["policy_empty"]:
            failures.append("%s: delivery product_policy is empty" % product_key)
        if user_delivery["menu_key_count"] <= 0:
            failures.append("%s: delivery product_policy menu keys empty" % product_key)
        if user_delivery["delivered_menu_leaf_count"] <= 0:
            failures.append("%s: user delivery nav leaf count is empty" % product_key)
        if native_navigation_authoritative:
            # The industry product owns its active ACL-visible native tree, so
            # caller-supplied native candidates are deliberately ignored. The
            # probe must prove deterministic recomputation from current-user
            # facts instead of treating an injected empty/subset tree as an
            # authorization boundary.
            if no_native_delivery["delivered_menu_leaf_count"] != user_delivery["delivered_menu_leaf_count"]:
                failures.append("%s: authoritative native tree changed for empty caller candidate" % product_key)
            if subset_delivery["delivered_menu_leaf_count"] != user_delivery["delivered_menu_leaf_count"]:
                failures.append("%s: authoritative native tree changed for subset caller candidate" % product_key)
        else:
            if no_native_delivery["delivered_menu_leaf_count"] != 0:
                failures.append("%s: non-admin without native authorization still sees policy menus" % product_key)
            if subset_delivery["delivered_menu_leaf_count"] > 1:
                failures.append("%s: native subset authorization leaked extra menus" % product_key)
        if admin_delivery["stable_leaf_count"] < user_delivery["stable_leaf_count"]:
            failures.append("%s: platform admin policy surface smaller than user surface" % product_key)
        if user_delivery["nav_source_authority_kind"] != MenuService.SOURCE_KIND:
            failures.append("%s: nav source authority is not MenuService" % product_key)

        products.append(
            {
                "product_key": product_key,
                "policy_source_kind": source_kind,
                "policy_counts": counts,
                "catalog_counts": catalog_counts,
                "runtime": {
                    "user_delivery": user_delivery,
                    "no_native_delivery": no_native_delivery,
                    "subset_delivery": subset_delivery,
                    "admin_delivery": admin_delivery,
                },
            }
        )

    payload = {
        "ok": not failures,
        "db": _text(env.cr.dbname),
        "probe_user_login": _text(probe_user.login),
        "native_authorized_leaf_count": native_leaf_count,
        "native_navigation_authoritative": native_navigation_authoritative,
        "customer_specific_product_view_count": len(customer_specific_product_views),
        "customer_specific_product_view_xmlids": customer_specific_product_views,
        "material_plan_customer_field_boundary": material_plan_customer_field_boundary,
        "material_rfq_customer_field_boundary": material_rfq_customer_field_boundary,
        "material_inbound_customer_field_boundary": material_inbound_customer_field_boundary,
        "subcontract_request_customer_field_boundary": subcontract_request_customer_field_boundary,
        "construction_diary_customer_field_boundary": construction_diary_customer_field_boundary,
        "settlement_order_customer_field_boundary": settlement_order_customer_field_boundary,
        "equipment_usage_customer_field_boundary": equipment_usage_customer_field_boundary,
        "labor_usage_customer_field_boundary": labor_usage_customer_field_boundary,
        "material_rental_order_customer_field_boundary": material_rental_order_customer_field_boundary,
        "hr_payroll_document_customer_field_boundary": hr_payroll_document_customer_field_boundary,
        "pass_through_customer_field_boundaries": pass_through_customer_field_boundaries,
        "products": products,
        "failures": failures,
        "artifacts": {
            "json": str(REPORT_JSON),
            "markdown": str(REPORT_MD),
        },
    }
    _write_report(payload)
    print("PLATFORM_RELEASE_POLICY_RUNTIME_PROBE=%s" % json.dumps(payload, ensure_ascii=False, sort_keys=True))
    if failures:
        raise AssertionError("; ".join(failures))


main()
