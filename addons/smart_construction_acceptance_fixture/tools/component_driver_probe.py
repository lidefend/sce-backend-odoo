# -*- coding: utf-8 -*-
"""Disposable non-payment entitlement for the component-driver browser probe."""

from .frontend_productization_fixture import MODULE, _guard_acceptance_scope, _ref


def apply_component_driver_probe(env, mode):
    _guard_acceptance_scope(env)
    mode = str(mode or "").strip()
    if mode not in ("setup", "cleanup"):
        raise RuntimeError("component driver probe mode must be setup or cleanup")
    menu = _ref(env, "smart_construction_core.menu_sc_project_project")
    action = menu.action
    model = str(action.res_model or "").strip()
    if not model or "payment" in model:
        raise RuntimeError("component driver probe requires a non-payment action model")
    form_view_id = next(
        (int(view_id or 0) for view_id, view_type in (action.views or []) if view_type == "form" and int(view_id or 0) > 0),
        0,
    )
    if form_view_id <= 0:
        raise RuntimeError("component driver probe requires an action-bound form view")
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
    preference_model = env["sc.user.view.preference"].sudo()
    preference_scope = preference_model.build_scope_key(
        preference_key="scene_ui_driver",
        view_type="form",
        action_id=int(menu.action.id),
        model_name=model,
    )
    preference_model.search([
        ("user_id", "=", probe_user.id),
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
                "models": [model],
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
    return {
        "action_id": int(menu.action.id),
        "view_id": form_view_id,
        "menu_id": int(menu.id),
        "model": model,
        "record_id": int(record.id),
        "record_identity": str(record.display_name),
        "create_probe_name": probe_record_name,
        "login": "fixture_role_pm",
    }
