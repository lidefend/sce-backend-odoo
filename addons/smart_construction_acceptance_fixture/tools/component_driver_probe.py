# -*- coding: utf-8 -*-
"""Disposable entitlement for generic and payment component-driver probes."""

from .frontend_productization_fixture import MODULE, _guard_acceptance_scope, _ref


def apply_component_driver_probe(env, mode):
    _guard_acceptance_scope(env)
    mode = str(mode or "").strip()
    if mode not in ("setup", "cleanup"):
        raise RuntimeError("component driver probe mode must be setup or cleanup")
    menu = _ref(env, "smart_construction_core.menu_sc_project_project")
    model = str(menu.action.res_model or "").strip()
    if not model or "payment" in model:
        raise RuntimeError("component driver probe requires a non-payment action model")
    payment_menu = _ref(env, "smart_construction_core.menu_sc_user_payment_apply")
    payment_action = _ref(env, "smart_construction_core.action_payment_request_user_payment_apply")
    payment_model = str(payment_action.res_model or "").strip()
    if payment_menu.action != payment_action or payment_model != "payment.request":
        raise RuntimeError("component driver probe payment action identity mismatch")
    company = _ref(env, "%s.fe_company_a" % MODULE)
    probe_record_name = "SC Component Driver Action Probe"
    probe_model = env[model].sudo()
    if "company_id" not in probe_model._fields:
        raise RuntimeError("component driver probe requires a company-owned target model")
    probe_model.search([
        ("name", "=", probe_record_name),
        ("company_id", "=", company.id),
    ]).unlink()
    probe_user = env["res.users"].sudo().search([("login", "=", "fixture_role_pm")], limit=1)
    payment_user = _ref(env, "%s.fe_user_finance" % MODULE)
    preference_model = env["sc.user.view.preference"].sudo()
    for user, action, model_name in (
        (probe_user, menu.action, model),
        (payment_user, payment_action, payment_model),
    ):
        preference_scope = preference_model.build_scope_key(
            preference_key="scene_ui_driver",
            view_type="form",
            action_id=int(action.id),
            model_name=model_name,
        )
        preference_model.search([
            ("user_id", "=", user.id),
            ("scope_key", "=", preference_scope),
        ]).unlink()
    plan_model = env["sc.subscription.plan"].sudo()
    subscription_model = env["sc.subscription"].sudo()
    plan = plan_model.search([("code", "=", "acceptance_component_driver_probe")])
    subscription_model.search([("plan_id", "in", plan.ids)]).unlink()
    plan.unlink()
    if mode == "cleanup":
        return None

    plan = plan_model.create({
        "code": "acceptance_component_driver_probe",
        "name": "Acceptance Component Driver Probe",
        "active": True,
        "sequence": 999,
        "feature_flags_json": {
            "scene_component_drivers_v1": {
                "enabled": True,
                "read_only_only": False,
                "form_modes": ["create", "edit", "readonly"],
                "models": [model, payment_model],
                "allowed_kits": ["sc-native", "tdesign-modern", "ui5-horizon"],
                "system_default_kit": "tdesign-modern",
                "allow_user_override": True,
                "allow_preview_override": False,
            },
        },
        "limits_json": {},
    })
    subscription_model.create({
        "company_id": company.id,
        "plan_id": plan.id,
        "state": "active",
        "is_trial": False,
    })
    record = _ref(env, "%s.fe_project_a" % MODULE)
    payment_record = _ref(env, "%s.fe_request_pfl035_001" % MODULE)
    payment_draft = _ref(env, "%s.fe_request_pfl035_002" % MODULE)
    return {
        "action_id": int(menu.action.id),
        "menu_id": int(menu.id),
        "model": model,
        "record_id": int(record.id),
        "record_identity": str(record.display_name),
        "create_probe_name": probe_record_name,
        "login": "fixture_role_pm",
        "payment_target": {
            "action_id": int(payment_action.id),
            "menu_id": int(payment_menu.id),
            "model": payment_model,
            "record_id": int(payment_record.id),
            "draft_record_id": int(payment_draft.id),
            "record_identity": str(payment_record.display_name),
            "draft_record_identity": str(payment_draft.display_name),
            "login": str(payment_user.login),
            "expected_primary_sections": {"readonly": 7, "edit": 6},
        },
    }
