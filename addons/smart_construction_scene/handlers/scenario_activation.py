# -*- coding: utf-8 -*-
from __future__ import annotations

from odoo.addons.smart_core.core.base_handler import BaseIntentHandler
from odoo.addons.smart_construction_scene.services.workspace_scenario_projection import (
    resolve_request_company,
    bind_company_context,
)
from odoo.addons.smart_construction_scene.services.tenant_scene_activation import (
    ENABLEMENT_STORAGE_SOURCE,
    enablement_param_key,
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


def _product_surface_index(env=None):
    from odoo.addons.smart_construction_core.services.scenario_surface_projection import runtime_menu_scope
    return runtime_menu_scope(env)[0]


def _actor_fact(env) -> dict:
    user = getattr(env, "user", None)
    can_manage = bool(
        getattr(user, "has_group", lambda _group: False)(
            "smart_construction_core.group_sc_cap_business_config_admin"
        )
    )
    try:
        from odoo.addons.smart_core.security.platform_admin import (
            user_is_platform_control_admin,
        )

        platform_admin = bool(user_is_platform_control_admin(user))
    except Exception:
        platform_admin = False
    return {
        "user_id": int(getattr(user, "id", 0) or 0),
        "login": str(getattr(user, "login", "") or "").strip(),
        "name": str(getattr(user, "name", "") or "").strip(),
        "can_manage_enterprise_configuration": can_manage,
        "platform_admin": platform_admin,
        "source": "res.users + smart_construction_core.group_sc_cap_business_config_admin",
    }


def _target_scope(env, company_id: int) -> dict:
    company = getattr(env, "company", None)
    company_name = (
        str(getattr(company, "name", "") or "").strip()
        if int(getattr(company, "id", 0) or 0) == int(company_id)
        else ""
    )
    return {
        "kind": "enterprise_scenario_enablement",
        "company_id": int(company_id),
        "company_name": company_name,
        "target_role_scope": {
            "mode": "not_role_scoped",
            "target_role_key": "",
            "reason_code": "SCENARIO_ENABLEMENT_COMPANY_SCOPED",
            "meaning": "enablement exposes an eligible scenario for this company; user permission is evaluated separately",
        },
        "is_global_product_release": False,
        "source": "res.company + ir.config_parameter",
    }


def _release_evidence_by_menu(release_projection: dict) -> dict:
    snapshots = {
        str(row.get("product_key") or "").strip(): row
        for row in release_projection.get("snapshots") or []
        if isinstance(row, dict)
    }
    states_by_product = release_projection.get("menu_release_states_by_product") or {}
    menu_xmlids = {
        str(menu_xmlid)
        for states in states_by_product.values()
        for menu_xmlid in (states or {})
        if str(menu_xmlid).strip()
    }
    result = {}
    for menu_xmlid in sorted(menu_xmlids):
        evidence = []
        for product_key in ("construction.standard", "construction.preview"):
            snapshot = snapshots.get(product_key) or {}
            release_state = str(
                (states_by_product.get(product_key) or {}).get(menu_xmlid) or ""
            ).strip()
            evidence.append(
                {
                    "product_key": product_key,
                    "qualified": release_state == "released"
                    and bool(snapshot.get("applied")),
                    "release_state": release_state,
                    "snapshot_id": int(snapshot.get("snapshot_id") or 0),
                    "version": str(snapshot.get("version") or "").strip(),
                    "fingerprint": str(snapshot.get("fingerprint") or "").strip(),
                    "applied": bool(snapshot.get("applied")),
                    "source": "sc.edition.release.snapshot",
                }
            )
        result[menu_xmlid] = {
            "qualification_authority": "published_product_release",
            "products": evidence,
        }
    return result


def _catalog(env, company_id=0):
    from odoo.addons.smart_construction_scene.profiles.scene_registry_content import (
        list_scene_entries,
    )
    from odoo.addons.smart_construction_core.services.product_menu_source import (
        load_published_menu_release_projection,
    )
    from odoo.addons.smart_construction_scene.services.scenario_activation_catalog import (
        build_scenario_activation_catalog,
    )
    entries = list_scene_entries()
    release_projection = load_published_menu_release_projection(env)
    release_state_by_menu = release_projection.get("menu_release_states") or {}
    release_evidence_by_menu = _release_evidence_by_menu(release_projection)
    from odoo.addons.smart_construction_core.services.scenario_surface_projection import load_runtime_surface
    from odoo.addons.smart_construction_scene.services.business_scene_enablement import business_catalog, business_key
    from odoo.addons.smart_construction_scene.services.tenant_scene_activation import read_tenant_enablement

    product_release_by_scene = {}
    scenes = env["sc.scene"].sudo().search([("active_version_id", "!=", False)])
    for scene in scenes:
        active = scene.active_version_id
        if active:
            product_release_by_scene[scene.code] = active.product_release_state or "PREVIEW"
    enablement = {}
    if company_id:
        scene_keys = {str(e.get("code") or e.get("key") or "").strip() for e in entries if str(e.get("code") or e.get("key") or "").strip()}
        for s in (load_runtime_surface(env).get("scenarios") or []):
            key = str(s.get("key") or "").strip()
            if key:
                scene_keys.add(business_key(key))
        enablement = {key: read_tenant_enablement(env, company_id, key) for key in scene_keys}

    result = build_scenario_activation_catalog(
        entries=entries,
        release_state_by_menu=release_state_by_menu,
        product_release_by_scene=product_release_by_scene,
        tenant_enablement_by_scene=enablement,
        surface_index=_product_surface_index(env),
        product_release_evidence_by_menu=release_evidence_by_menu,
    )
    can_manage = bool(env.user.has_group("smart_construction_core.group_sc_cap_business_config_admin"))
    business_scenarios = business_catalog(
        load_runtime_surface(env), release_state_by_menu, enablement, can_manage=bool(can_manage)
    )
    standard_snapshot = next(
        (
            row
            for row in release_projection.get("snapshots") or []
            if isinstance(row, dict)
            and row.get("product_key") == "construction.standard"
        ),
        {},
    )
    business_evidence = {
        "product_key": "construction.standard",
        "qualified": bool(standard_snapshot.get("applied")),
        "snapshot_id": int(standard_snapshot.get("snapshot_id") or 0),
        "version": str(standard_snapshot.get("version") or "").strip(),
        "fingerprint": str(standard_snapshot.get("fingerprint") or "").strip(),
        "source": "sc.edition.release.snapshot",
    }
    for row in business_scenarios:
        row["product_qualification"] = {
            "status": "qualified" if row.get("product_released") else "not_qualified",
            "reason_code": (
                "PRODUCT_QUALIFIED"
                if row.get("product_released")
                else "PRODUCT_NOT_RELEASED"
            ),
            "evidence": business_evidence,
        }
        row["enablement_blockers"] = (
            [] if row.get("product_released") else ["PRODUCT_NOT_RELEASED"]
        )
        row["enable_allowed"] = bool(row.get("product_released"))
    result["business_scenarios"] = business_scenarios
    result["company_id"] = company_id
    result["actor"] = _actor_fact(env)
    result["target_scope"] = _target_scope(env, company_id) if company_id else {}
    return result


class ScenarioActivationCatalogGetHandler(BaseIntentHandler):
    INTENT_TYPE = "scenario.activation.catalog.get"
    DESCRIPTION = "企业场景接入目录"
    VERSION = "1.0.0"
    ETAG_ENABLED = False
    SOURCE_AUTHORITY = {
        "kind": "scenario_activation_projection",
        "authorities": [
            "sc.scene",
            "sc.product.scenario",
            "ir.config_parameter",
            "sc.scene.company.enablement.legacy_read",
            "product_menu_source",
        ],
        "projection_only": True,
        "no_business_fact_authority": True,
    }

    def handle(self, params=None, ctx=None):
        params = params if params is not None else self.params or {}
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
        "authorities": [
            "ir.config_parameter",
            "sc.scene.company.enablement.legacy_read",
            "product_menu_source",
        ],
        "projection_only": False,
        "no_business_fact_authority": True,
    }

    def handle(self, params=None, ctx=None):
        params = params if params is not None else self.params
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
        from odoo.addons.smart_construction_scene.services.tenant_scene_activation import (
            read_tenant_enablement,
            write_tenant_enablement,
        )

        write_tenant_enablement(env, company.id, stored_key, enabled)
        persisted_enabled = read_tenant_enablement(env, company.id, stored_key)
        if persisted_enabled is not enabled:
            return {
                "ok": False,
                "error": {
                    "code": 409,
                    "message": "enablement readback does not match the requested state",
                    "details": {
                        "company_id": int(company.id),
                        "scene_key": scene_key,
                        "requested": enabled,
                        "readback": persisted_enabled,
                    },
                },
            }
        return {
            "ok": True,
            "data": {
                "scene_key": scene_key,
                "stored_scene_key": stored_key,
                "enablement_scope": scope,
                "enabled": enabled,
                "actor": _actor_fact(env),
                "target_scope": _target_scope(env, company.id),
                "readback": {
                    "enabled": persisted_enabled,
                    "company_id": int(company.id),
                    "requested_scene_key": scene_key,
                    "stored_scene_key": stored_key,
                    "enablement_scope": scope,
                    "target_state": enabled,
                    "source": ENABLEMENT_STORAGE_SOURCE,
                    "storage_key": enablement_param_key(company.id, stored_key),
                    "write_committed": True,
                    "access_granted": False,
                },
            },
            "meta": {},
        }


class WorkspaceScenarioProjectionGetHandler(BaseIntentHandler):
    INTENT_TYPE = "workspace.scenario.projection.get"
    DESCRIPTION = "当前用户工作空间场景投影"
    VERSION = "1.0.0"
    ETAG_ENABLED = False
    SOURCE_AUTHORITY = {
        "kind": "workspace_scenario_projection",
        "authorities": [
            "ir.config_parameter",
            "sc.scene.company.enablement.legacy_read",
            "sc.edition.release.snapshot",
            "published_route_authority",
        ],
        "projection_only": True,
        "no_business_fact_authority": True,
    }

    def handle(self, params=None, ctx=None):
        from odoo.addons.smart_construction_scene.profiles.scene_registry_content import (
            list_scene_entries,
        )
        from odoo.addons.smart_construction_core.services.product_menu_source import (
            load_published_menu_release_states,
        )
        from odoo.addons.smart_construction_scene.services.workspace_scenario_projection import (
            project_workspace_scenes,
        )

        params = params if params is not None else self.params or {}
        company_id, error = _resolve_request_company(self.env, params)
        if error:
            return {"ok": False, "error": error}
        env = bind_company_context(self.env, company_id)
        entries = list_scene_entries()
        role_scene_candidates = self._resolve_authorized_scene_candidates(entries, company_id)
        release_state_by_menu = load_published_menu_release_states(env)
        enablement = {}
        if company_id:
            from odoo.addons.smart_construction_core.services.scenario_surface_projection import load_runtime_surface
            from odoo.addons.smart_construction_scene.services.business_scene_enablement import business_key
            from odoo.addons.smart_construction_scene.services.tenant_scene_activation import read_tenant_enablement
            for entry in entries:
                key = str(entry.get("code") or entry.get("key") or "").strip()
                if key:
                    enablement[key] = read_tenant_enablement(env, company_id, key)
            for scene in (load_runtime_surface(env).get("scenarios") or []):
                key = str(scene.get("key") or "").strip()
                if key:
                    enablement[business_key(key)] = read_tenant_enablement(env, company_id, business_key(key))
        from odoo.addons.smart_construction_scene.services.business_scene_enablement import business_states
        data = project_workspace_scenes(
            entries=entries,
            release_state_by_menu=release_state_by_menu,
            tenant_enabled_by_scene=enablement,
            business_enabled_by_scene=business_states(enablement),
            role_scene_candidates=role_scene_candidates,
            surface_index=_product_surface_index(env),
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
