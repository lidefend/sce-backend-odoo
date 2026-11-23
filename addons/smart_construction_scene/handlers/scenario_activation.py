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
from odoo.addons.smart_construction_core.services.scenario_product_declarations import (
    SCENARIO_OWNER_CENTER_BY_KEY,
)

CATALOG_VERSION = "scenario_activation_catalog.v3"
CENTER_ACTIVATION_VERSION = "scenario_center_activation.v1"
PRODUCT_CONFIGURATION_CENTER_KEY = "construction.center.product_configuration"
BUSINESS_CENTER_KEYS = (
    "workspace.home.workbench",
    "construction.center.project",
    "construction.center.contract",
    "construction.center.cost",
    "construction.center.supply_chain",
    "construction.center.finance",
    "construction.center.tax",
    "construction.center.accounting",
    "construction.center.reporting",
    "construction.center.administration",
)
RECOMMENDED_CENTER_KEYS = (
    "workspace.home.workbench",
    "construction.center.project",
    "construction.center.contract",
    "construction.center.cost",
    "construction.center.finance",
    "construction.center.reporting",
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


def _business_center_catalog(surface, business_scenarios):
    rows_by_key = {
        str(row.get("scene_key") or "").strip(): row
        for row in business_scenarios
        if isinstance(row, dict) and str(row.get("scene_key") or "").strip()
    }
    scenes_by_owner = {}
    for scene in surface.get("scenarios") or []:
        if not isinstance(scene, dict):
            continue
        scene_key = str(scene.get("key") or "").strip()
        owner_center = str(
            SCENARIO_OWNER_CENTER_BY_KEY.get(scene_key, "")
        ).strip()
        if scene_key and owner_center:
            scenes_by_owner.setdefault(owner_center, []).append(scene_key)
    rows = []
    for sequence, center_key in enumerate(BUSINESS_CENTER_KEYS, start=1):
        center = next(
            (
                row for row in (surface.get("centers") or [])
                if isinstance(row, dict) and str(row.get("key") or "").strip() == center_key
            ),
            {},
        )
        scene_keys = [
            str(scene_key or "").strip()
            for scene_key in scenes_by_owner.get(center_key, [])
            if str(scene_key or "").strip() in rows_by_key
        ]
        scene_rows = [rows_by_key[scene_key] for scene_key in scene_keys]
        enabled_scene_count = sum(bool(row.get("tenant_enabled")) for row in scene_rows)
        released = bool(scene_rows) and all(
            bool(row.get("product_released")) and bool(row.get("enable_allowed"))
            for row in scene_rows
        )
        if not scene_rows or not released:
            state = "blocked"
            state_label = "产品未就绪"
        elif enabled_scene_count == len(scene_rows):
            state = "enabled"
            state_label = "已启用"
        elif enabled_scene_count:
            state = "partial"
            state_label = "部分启用"
        else:
            state = "not_enabled"
            state_label = "未启用"
        rows.append({
            "key": center_key,
            "name": str(center.get("name") or center_key).strip(),
            "sequence": int(center.get("sequence") or sequence),
            "scene_keys": scene_keys,
            "scene_count": len(scene_keys),
            "enabled_scene_count": enabled_scene_count,
            "status": state,
            "status_label": state_label,
            "default_selected": center_key in RECOMMENDED_CENTER_KEYS,
            "enable_allowed": released,
        })
    return rows


def _catalog(env, company_id=0):
    from odoo.addons.smart_construction_core.services.product_menu_source import (
        load_published_menu_release_projection,
    )
    release_projection = load_published_menu_release_projection(env)
    release_state_by_menu = release_projection.get("menu_release_states") or {}
    from odoo.addons.smart_construction_core.services.scenario_surface_projection import load_runtime_surface
    from odoo.addons.smart_construction_scene.services.business_scene_enablement import business_catalog, business_key
    from odoo.addons.smart_construction_scene.services.tenant_scene_activation import read_tenant_enablement

    surface = load_runtime_surface(env)
    enablement = {}
    if company_id:
        scene_keys = set()
        for s in (surface.get("scenarios") or []):
            key = str(s.get("key") or "").strip()
            if key:
                scene_keys.add(business_key(key))
        enablement = {key: read_tenant_enablement(env, company_id, key) for key in scene_keys}

    can_manage = bool(env.user.has_group("smart_construction_core.group_sc_cap_business_config_admin"))
    business_scenarios = business_catalog(
        surface, release_state_by_menu, enablement, can_manage=bool(can_manage)
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
        qualification_status = (
            "qualified" if row.get("product_released") else "not_qualified"
        )
        row["product_qualification"] = {
            "status": qualification_status,
            "label": "成立" if qualification_status == "qualified" else "不成立",
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
    from odoo.addons.smart_construction_core.services.scenario_surface_projection import build_menu_index

    published_menu_keys = set(release_state_by_menu)
    scenario_menu_keys = {
        menu_key
        for menu_key, location in build_menu_index(surface).items()
        if any(
            candidate.get("location") == "scenario"
            for candidate in (
                location.get("scenario_locations")
                if isinstance(location.get("scenario_locations"), list)
                else [location]
            )
            if isinstance(candidate, dict)
        )
    }
    scenario_bound_page_keys = published_menu_keys & scenario_menu_keys
    standard_snapshot = next(
        (
            row
            for row in release_projection.get("snapshots") or []
            if isinstance(row, dict)
            and row.get("product_key") == "construction.standard"
        ),
        {},
    )
    blockers = []
    if not standard_snapshot.get("applied"):
        blockers.append(
            str(standard_snapshot.get("reason") or "PRODUCT_RELEASE_UNVERIFIED")
        )
    if not business_scenarios:
        blockers.append("SCENARIO_COMPOSITION_EMPTY")
    business_centers = _business_center_catalog(surface, business_scenarios)
    center_count = len(surface.get("centers") or [])
    business_center_count = len(business_centers)
    unassigned_page_count = len(published_menu_keys - scenario_menu_keys)
    if not published_menu_keys:
        catalog_summary = "当前没有已发布的正式产品页面"
    elif unassigned_page_count:
        catalog_summary = (
            f"已发布产品页面 {len(published_menu_keys)} 项 · 可选业务中心 {business_center_count} 个"
            f" · {unassigned_page_count} 个页面尚未纳入办理场景"
        )
    else:
        catalog_summary = (
            f"已发布产品页面 {len(published_menu_keys)} 项 · 可选业务中心 {business_center_count} 个"
            " · 页面均已纳入办理场景"
        )
    blocker_text = " · ".join(blockers) if blockers else "当前没有可启停业务场景"
    return {
        "contract_version": CATALOG_VERSION,
        "published_page_count": len(published_menu_keys),
        "published_snapshot": {
            "snapshot_id": int(standard_snapshot.get("snapshot_id") or 0),
            "version": str(standard_snapshot.get("version") or ""),
            "fingerprint": str(standard_snapshot.get("fingerprint") or ""),
            "applied": bool(standard_snapshot.get("applied")),
        },
        "catalog_status": "ready" if not blockers else "blocked",
        "catalog_blockers": blockers,
        "catalog_presentation": {
            "title": "企业业务中心启用",
            "summary": catalog_summary,
            "empty_label": f"{catalog_summary}，{blocker_text}。",
        },
        "catalog_cardinality": {
            "published_page_count": len(published_menu_keys),
            "scenario_bound_page_count": len(scenario_bound_page_keys),
            "unscenarioized_published_page_count": unassigned_page_count,
            "center_count": center_count,
            "business_scenario_count": len(business_scenarios),
            "actionable_business_scenario_count": len(
                [row for row in business_scenarios if row.get("actions")]
            ),
        },
        "business_scenarios": business_scenarios,
        "business_centers": business_centers,
        "center_activation": {
            "contract_version": CENTER_ACTIVATION_VERSION,
            "title": "最后一步：选择企业业务中心",
            "description": "请先完成企业信息、部门、岗位、人员与账号、业务角色与允许公司。推荐选中仅代表提交前的建议，不代表已经启用。",
            "selection_label": "已选择业务中心",
            "selection_count_label": "个业务中心",
            "scene_count_label": "个业务场景",
            "apply_label": "启用所选业务中心",
            "advanced_label": "高级：单独选择业务场景",
            "intent": "scenario.activation.centers.set",
            "recommended_center_keys": [
                center["key"]
                for center in business_centers
                if center["default_selected"]
            ],
        },
        "company_id": company_id,
        "actor": _actor_fact(env),
        "target_scope": _target_scope(env, company_id) if company_id else {},
    }


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


class ScenarioCenterActivationSetHandler(BaseIntentHandler):
    INTENT_TYPE = "scenario.activation.centers.set"
    REQUIRED_GROUPS = ["smart_construction_core.group_sc_cap_business_config_admin"]
    DESCRIPTION = "企业业务中心启用"
    VERSION = "1.0.0"
    ETAG_ENABLED = False
    SOURCE_AUTHORITY = {
        "kind": "enterprise_center_activation_mutation",
        "authorities": [
            "sc.product.scenario",
            "ir.config_parameter",
            "sc.edition.release.snapshot",
        ],
        "projection_only": False,
        "no_business_fact_authority": True,
    }

    def handle(self, params=None, ctx=None):
        params = params if params is not None else self.params
        if not isinstance(params, dict):
            return {"ok": False, "error": {"code": 400, "message": "invalid center activation parameters"}}
        center_keys = params.get("center_keys")
        if (
            not isinstance(center_keys, list)
            or not center_keys
            or any(not isinstance(key, str) or not key.strip() for key in center_keys)
        ):
            return {"ok": False, "error": {"code": 400, "message": "center_keys must be a nonempty string list"}}
        center_keys = list(dict.fromkeys(key.strip() for key in center_keys))
        company_id, error = _resolve_request_company(self.env, params)
        if error:
            return {"ok": False, "error": error}
        env = bind_company_context(self.env, company_id)
        catalog = _catalog(env, company_id=company_id)
        centers = {
            center["key"]: center
            for center in ((catalog.get("business_centers") or []))
            if isinstance(center, dict)
        }
        unknown = sorted(set(center_keys) - set(centers))
        if unknown:
            return {"ok": False, "error": {"code": 400, "message": "unknown business center", "details": unknown}}
        selected = [centers[key] for key in center_keys]
        blocked = [
            center["key"]
            for center in selected
            if not center.get("enable_allowed") or not center.get("scene_keys")
        ]
        if blocked:
            return {"ok": False, "error": {"code": 409, "message": "business center not released", "details": blocked}}
        scene_keys = sorted({
            scene_key
            for center in selected
            for scene_key in (center.get("scene_keys") or [])
        })
        scenes = {
            row["scene_key"]: row
            for row in (catalog.get("business_scenarios") or [])
            if isinstance(row, dict) and row.get("scene_key") in scene_keys
        }
        missing = sorted(set(scene_keys) - set(scenes))
        if missing:
            return {"ok": False, "error": {"code": 409, "message": "business center scenario missing", "details": missing}}
        from odoo.addons.smart_construction_scene.services.business_scene_enablement import business_key
        from odoo.addons.smart_construction_scene.services.tenant_scene_activation import (
            read_tenant_enablement,
            write_tenant_enablement,
        )
        try:
            with env.cr.savepoint():
                for scene_key in scene_keys:
                    write_tenant_enablement(env, company_id, business_key(scene_key), True)
                enabled_scene_keys = [
                    scene_key
                    for scene_key in scene_keys
                    if read_tenant_enablement(env, company_id, business_key(scene_key))
                ]
                if enabled_scene_keys != scene_keys:
                    raise RuntimeError("business center enablement readback mismatch")
        except Exception:
            return {
                "ok": False,
                "error": {
                    "code": 409,
                    "message": "business center enablement was rolled back",
                },
            }
        return {
            "ok": True,
            "data": {
                "contract_version": CENTER_ACTIVATION_VERSION,
                "company_id": company_id,
                "center_keys": center_keys,
                "scene_keys": scene_keys,
                "enabled_scene_count": len(enabled_scene_keys),
                "actor": _actor_fact(env),
                "target_scope": _target_scope(env, company_id),
                "readback": {
                    "company_id": company_id,
                    "center_keys": center_keys,
                    "scene_keys": enabled_scene_keys,
                    "source": ENABLEMENT_STORAGE_SOURCE,
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
        from odoo.addons.smart_core.delivery.runtime_route_authority import published_route_authority
        from odoo.addons.smart_construction_core.services.scenario_surface_projection import (
            load_runtime_surface,
            runtime_menu_scope,
        )
        from odoo.addons.smart_construction_scene.services.business_scene_enablement import (
            business_catalog,
            business_key,
        )
        from odoo.addons.smart_construction_scene.services.tenant_scene_activation import (
            read_tenant_enablement,
        )

        params = params if params is not None else self.params or {}
        company_id, error = _resolve_request_company(self.env, params)
        if error:
            return {"ok": False, "error": error}
        env = bind_company_context(self.env, company_id)
        surface = load_runtime_surface(env)
        release_states = {
            str(menu_key): str(location.get("release_state") or "released")
            for menu_key, location in (runtime_menu_scope(env, surface)[0] or {}).items()
        }
        enablement = {
            business_key(scene_key): read_tenant_enablement(
                env, company_id, business_key(scene_key)
            )
            for scene_key in (
                str(scene.get("key") or "").strip()
                for scene in (surface.get("scenarios") or [])
            )
            if scene_key
        }
        rows = business_catalog(
            surface,
            release_states,
            enablement,
            can_manage=False,
        )
        authority = published_route_authority(env)
        allowed_menu_xmlids = {
            str(row.get("menu_xmlid") or "").strip()
            for bucket in (
                "primary_actions",
                "role_home_actions",
                "contextual_actions",
                "admin_actions",
            )
            for row in (authority.get(bucket) or [])
            if isinstance(row, dict)
            and row.get("allowed") is not False
            and row.get("allowed_operation") != "none"
            and str(row.get("menu_xmlid") or "").strip()
        }
        index = runtime_menu_scope(env, surface)[0] or {}
        scenario_menu_keys = {}
        for menu_xmlid, location in index.items():
            for placement in (
                location.get("scenario_locations")
                if isinstance(location.get("scenario_locations"), list)
                else [location]
            ):
                if not isinstance(placement, dict):
                    continue
                scenario_key = str(placement.get("scenario_key") or "").strip()
                if scenario_key:
                    scenario_menu_keys.setdefault(scenario_key, set()).add(menu_xmlid)
        projected_rows = []
        for row in rows:
            role_assigned = bool(
                scenario_menu_keys.get(row["scene_key"], set())
                & allowed_menu_xmlids
            )
            projected_rows.append({
                **row,
                "role_assigned": role_assigned,
                "workspace_candidate": bool(
                    row["product_released"]
                    and row["tenant_enabled"]
                    and role_assigned
                ),
            })
        return {
            "ok": True,
            "data": {
                "contract_version": "workspace_scenario_projection.v2",
                "rows": projected_rows,
                "row_count": len(projected_rows),
                "workspace_candidate_count": len([
                    row for row in projected_rows if row["workspace_candidate"]
                ]),
            },
            "meta": {},
        }
