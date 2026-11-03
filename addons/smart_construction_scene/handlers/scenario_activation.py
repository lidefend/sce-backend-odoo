# -*- coding: utf-8 -*-
from __future__ import annotations

from odoo.addons.smart_core.core.base_handler import BaseIntentHandler
from odoo.addons.smart_construction_scene.services.workspace_scenario_projection import (
    resolve_request_company,
    bind_company_context,
)


def _resolve_request_company(env, params):
    """Return the validated company id for a client request.

    A client-supplied company hint is never trusted: an explicitly requested
    company outside the principal's allowed set is rejected instead of silently
    falling back. An omitted hint resolves to the principal's default company
    through ``resolve_allowed_company_id``.
    """
    requested = params.get("company_id") if isinstance(params, dict) else None
    return resolve_request_company(requested, env.user.company_ids.ids, env.company.id or 0)


def _product_surface_index():
    from odoo.addons.smart_construction_core.services.scenario_surface_projection import (
        build_menu_index,
        load_surface,
    )

    return build_menu_index(load_surface())


def _catalog(env, company_id=0):
    from odoo.addons.smart_construction_scene.profiles.scene_registry_content import (
        list_scene_entries,
    )
    from odoo.addons.smart_construction_core.services.product_menu_source import (
        load_menu_release_states,
    )
    from odoo.addons.smart_construction_scene.services.scenario_activation_catalog import (
        build_scenario_activation_catalog,
    )

    entries = list_scene_entries()
    release_state_by_menu = load_menu_release_states()
    product_release_by_scene = {}
    scenes = env["sc.scene"].sudo().search([("active_version_id", "!=", False)])
    for scene in scenes:
        active = scene.active_version_id
        if active:
            product_release_by_scene[scene.code] = active.product_release_state or "PREVIEW"
    enablement = {}
    if company_id:
        rows = env["sc.scene.company.enablement"].search([("company_id", "=", company_id)])
        enablement = {row.scene_key: bool(row.enabled) for row in rows}
    from odoo.addons.smart_construction_core.services.scenario_surface_projection import load_surface
    from odoo.addons.smart_construction_scene.services.business_scene_enablement import business_catalog

    result = build_scenario_activation_catalog(
        entries=entries,
        release_state_by_menu=release_state_by_menu,
        product_release_by_scene=product_release_by_scene,
        tenant_enablement_by_scene=enablement,
        surface_index=_product_surface_index(),
    )
    enablement_model = env["sc.scene.company.enablement"]
    can_manage = (enablement_model.check_access_rights("write", raise_exception=False)
                  and enablement_model.check_access_rights("create", raise_exception=False))
    result["business_scenarios"] = business_catalog(
        load_surface(), release_state_by_menu, enablement, can_manage=bool(can_manage)
    )
    result["company_id"] = company_id
    return result


class ScenarioActivationCatalogGetHandler(BaseIntentHandler):
    INTENT_TYPE = "scenario.activation.catalog.get"
    DESCRIPTION = "企业场景接入目录"
    VERSION = "1.0.0"
    ETAG_ENABLED = False
    SOURCE_AUTHORITY = {
        "kind": "scenario_activation_projection",
        "authorities": ["sc.scene", "sc.scene.company.enablement", "product_menu_source"],
        "projection_only": True,
        "no_business_fact_authority": True,
    }

    def handle(self, payload=None, ctx=None):
        params = payload or self.params or {}
        company_id, error = _resolve_request_company(self.env, params)
        if error:
            return {"ok": False, "error": error}
        env = bind_company_context(self.env, company_id)
        return {"ok": True, "data": _catalog(env, company_id=company_id), "meta": {}}


class ScenarioActivationSetHandler(BaseIntentHandler):
    INTENT_TYPE = "scenario.activation.set"
    REQUIRED_GROUPS = ["smart_construction_core.group_sc_cap_business_config_admin"]
    DESCRIPTION = "企业场景启用/停用"
    VERSION = "1.0.0"
    ETAG_ENABLED = False
    SOURCE_AUTHORITY = {
        "kind": "scenario_activation_mutation",
        "authorities": ["sc.scene.company.enablement", "product_menu_source"],
        "projection_only": False,
        "no_business_fact_authority": True,
    }

    def handle(self, payload=None, ctx=None):
        params = payload if payload is not None else self.params
        if not isinstance(params, dict):
            return {"ok": False, "error": {"code": 400, "message": "invalid activation parameters"}}
        # Mutations require explicit JSON booleans. In particular, "false" is
        # truthy in Python and an omitted value must never mean "disable".
        enabled = params.get("enabled")
        if not isinstance(enabled, bool):
            return {"ok": False, "error": {"code": 400, "message": "enabled must be a boolean"}}
        scene_key = params.get("scene_key")
        if not isinstance(scene_key, str) or not scene_key.strip():
            return {"ok": False, "error": {"code": 400, "message": "scene_key must be a nonempty string"}}
        scene_key = scene_key.strip()
        company_id, error = _resolve_request_company(self.env, params)
        if error:
            return {"ok": False, "error": error}
        env = bind_company_context(self.env, company_id)
        from odoo.addons.smart_construction_scene.services.business_scene_enablement import BUSINESS_SCOPE, business_key
        scope = params.get("enablement_scope", "scene_entry.v1")
        if scope not in ("scene_entry.v1", BUSINESS_SCOPE):
            return {"ok": False, "error": {"code": 400, "message": "invalid enablement_scope"}}
        if scope == BUSINESS_SCOPE:
            candidates = _catalog(env, company_id)["business_scenarios"]
            candidate = next((row for row in candidates if row["scene_key"] == scene_key), None)
            if candidate is None:
                return {"ok": False, "error": {"code": 404, "message": "unknown business scenario"}}
            if enabled and not candidate["product_released"]:
                return {"ok": False, "error": {"code": 409, "message": "business scenario not released"}}
            stored_key = business_key(scene_key)
        else:
            # Reserved namespace is only writable through the explicit business contract.
            if scene_key.startswith("business."):
                return {"ok": False, "error": {"code": 400, "message": "explicit business scope required"}}
            stored_key = scene_key
        company = env["res.company"].browse(company_id).exists()
        if not company:
            return {"ok": False, "error": {"code": 404, "message": "company not found"}}
        record = env["sc.scene.company.enablement"].search(
            [("company_id", "=", company.id), ("scene_key", "=", stored_key)], limit=1
        )
        if enabled and scope == "scene_entry.v1":
            from odoo.addons.smart_construction_scene.services.scenario_dependency_diagnosis import (
                diagnose_scenario_dependencies,
            )

            diagnosis = diagnose_scenario_dependencies(
                env, scene_key=scene_key, company_id=company.id
            )
            if not diagnosis.get("enable_allowed"):
                return {
                    "ok": False,
                    "error": {
                        "code": 409,
                        "message": "enablement blocked",
                        "details": diagnosis.get("blocking_dependencies") or [],
                    },
                }
        if not record:
            record = env["sc.scene.company.enablement"].create(
                {"company_id": company.id, "scene_key": stored_key, "enabled": False}
            )
        record.set_enabled(enabled)
        return {"ok": True, "data": {"scene_key": scene_key, "enablement_scope": scope, "enabled": bool(record.enabled)}, "meta": {}}


class WorkspaceScenarioProjectionGetHandler(BaseIntentHandler):
    INTENT_TYPE = "workspace.scenario.projection.get"
    DESCRIPTION = "当前用户工作空间场景投影"
    VERSION = "1.0.0"
    ETAG_ENABLED = False
    SOURCE_AUTHORITY = {
        "kind": "workspace_scenario_projection",
        "authorities": ["sc.scene.company.enablement", "product_menu_source", "published_route_authority"],
        "projection_only": True,
        "no_business_fact_authority": True,
    }

    def handle(self, payload=None, ctx=None):
        from odoo.addons.smart_construction_scene.profiles.scene_registry_content import (
            list_scene_entries,
        )
        from odoo.addons.smart_construction_core.services.product_menu_source import (
            load_menu_release_states,
        )
        from odoo.addons.smart_construction_scene.services.workspace_scenario_projection import (
            project_workspace_scenes,
        )

        params = payload or self.params or {}
        company_id, error = _resolve_request_company(self.env, params)
        if error:
            return {"ok": False, "error": error}
        entries = list_scene_entries()
        role_scene_candidates = self._resolve_authorized_scene_candidates(entries, company_id)
        release_state_by_menu = load_menu_release_states()
        enablement = {}
        if company_id:
            rows = bind_company_context(self.env, company_id)["sc.scene.company.enablement"].search(
                [("company_id", "=", company_id)]
            )
            enablement = {row.scene_key: bool(row.enabled) for row in rows}
        from odoo.addons.smart_construction_scene.services.business_scene_enablement import business_states
        data = project_workspace_scenes(
            entries=entries,
            release_state_by_menu=release_state_by_menu,
            tenant_enabled_by_scene=enablement,
            business_enabled_by_scene=business_states(enablement),
            role_scene_candidates=role_scene_candidates,
            surface_index=_product_surface_index(),
        )
        return {"ok": True, "data": data, "meta": {}}

    def _resolve_authorized_scene_candidates(self, entries, company_id) -> list[str]:
        from odoo.addons.smart_core.delivery.runtime_route_authority import published_route_authority
        from odoo.addons.smart_construction_scene.services.workspace_scenario_projection import (
            authorized_scene_candidates,
        )

        # Preserve the principal and bind both authority and XML-id resolution to
        # the explicitly validated company. Never elevate the user for projection.
        env = self.env["sc.product.policy"].with_context(allowed_company_ids=[company_id]).env
        return authorized_scene_candidates(
            entries=entries,
            authority=published_route_authority(env),
            resolve_ref=env.ref,
        )
