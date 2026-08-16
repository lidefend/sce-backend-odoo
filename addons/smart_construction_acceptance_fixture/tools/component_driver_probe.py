# -*- coding: utf-8 -*-
"""Disposable non-payment entitlement for the component-driver browser probe."""

from .frontend_productization_fixture import MODULE, _guard_acceptance_scope, _ref


def apply_component_driver_probe(env, mode):
    _guard_acceptance_scope(env)
    mode = str(mode or "").strip()
    if mode not in ("setup", "cleanup"):
        raise RuntimeError("component driver probe mode must be setup or cleanup")
    plan_model = env["sc.subscription.plan"].sudo()
    subscription_model = env["sc.subscription"].sudo()
    plan = plan_model.search([("code", "=", "acceptance_component_driver_probe")])
    subscription_model.search([("plan_id", "in", plan.ids)]).unlink()
    plan.unlink()
    if mode == "cleanup":
        return None

    company = _ref(env, "%s.fe_company_a" % MODULE)
    menu = _ref(env, "smart_construction_core.menu_sc_project_project")
    model = str(menu.action.res_model or "").strip()
    if not model or "payment" in model:
        raise RuntimeError("component driver probe requires a non-payment action model")
    plan = plan_model.create({
        "code": "acceptance_component_driver_probe",
        "name": "Acceptance Component Driver Probe",
        "active": True,
        "sequence": 999,
        "feature_flags_json": {
            "scene_component_drivers_v1": {
                "enabled": True,
                "read_only_only": True,
                "models": [model],
                "allowed_kits": ["sc-native", "tdesign-modern"],
                "system_default_kit": "tdesign-modern",
                "locked_kit": "tdesign-modern",
                "allow_user_override": False,
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
        "menu_id": int(menu.id),
        "model": model,
        "record_id": int(record.id),
        "record_identity": str(record.display_name),
        "login": "fixture_role_pm",
    }
