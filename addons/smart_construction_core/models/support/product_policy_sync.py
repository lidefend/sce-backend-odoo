# -*- coding: utf-8 -*-

from odoo import api, models
from odoo.addons.smart_core.utils.backend_contract_boundaries import (
    MENU_CONFIG_NAV_ENABLED_PARAM,
    NAV_USER_DATA_ACCEPTANCE_ONLY_PARAM,
)
from odoo.addons.smart_construction_core.services.locked_menu_policy_contract import (
    FORMAL_ACTION_ONLY_MENU_TARGETS,
    FORMAL_BUSINESS_DECISION_REQUIRED_TARGETS,
    LockedMenuPolicyContractError,
    assert_policy_matches_locked_contract,
    canonical_group_label,
    declared_scene_entry_key,
    load_locked_menu_policy_contract,
)


def _text(value):
    return str(value or "").strip()


class ScProductPolicy(models.Model):
    _inherit = "sc.product.policy"

    @api.model
    def synchronize_locked_formal_menu_policy(
        self,
        product_key,
        *,
        baseline_path=None,
        checksum_path=None,
    ):
        """Converge one formal construction policy without catalog fallback."""
        product_key = _text(product_key)
        contract = load_locked_menu_policy_contract(
            baseline_path=baseline_path,
            checksum_path=checksum_path,
        )
        product = contract["products"].get(product_key)
        if not isinstance(product, dict):
            raise LockedMenuPolicyContractError("LOCKED_MENU_BASELINE_PRODUCT_MISMATCH", product_key)

        menu_groups = []
        for group in product.get("menu_groups") or []:
            legacy_label = _text(group.get("group_label") or group.get("label") or group.get("title"))
            group_label = canonical_group_label(legacy_label)
            next_group = dict(group)
            next_group.update(
                {
                    "group_label": group_label,
                    "group_key": "construction.%s" % group_label,
                    "label": group_label,
                    "title": group_label,
                }
            )
            menus = []
            for menu in group.get("menus") or []:
                row = dict(menu)
                menu_xmlid = _text(row.get("menu_xmlid") or row.get("page_key") or row.get("menu_key"))
                # A declared scene entry carries no business action: its identity is
                # the native menu anchor plus the declared scene, and it is authorized
                # by the same (menu_id, action_id=0) pair as any other entry. It is
                # never routed through an action-only target.
                scene_key = declared_scene_entry_key(row)
                action_xmlid = "" if scene_key else (
                    _text(row.get("action_xmlid")) or FORMAL_ACTION_ONLY_MENU_TARGETS.get(menu_xmlid, "")
                )
                if FORMAL_BUSINESS_DECISION_REQUIRED_TARGETS.get(menu_xmlid) == action_xmlid:
                    raise LockedMenuPolicyContractError(
                        "BUSINESS_DECISION_REQUIRED",
                        f"{product_key} unresolved disposition {menu_xmlid} -> {action_xmlid}",
                    )
                menu_rec = self.env.ref(menu_xmlid, raise_if_not_found=False) if menu_xmlid else False
                if scene_key:
                    if not menu_rec:
                        raise LockedMenuPolicyContractError(
                            "LOCKED_MENU_BASELINE_NORMALIZATION_MISMATCH",
                            f"{product_key} declared scene entry requires a native menu anchor {menu_xmlid}",
                        )
                    action = False
                else:
                    action = menu_rec.action if menu_rec else (
                        self.env.ref(action_xmlid, raise_if_not_found=False) if action_xmlid else False
                    )
                if not menu_rec and not action_xmlid:
                    raise LockedMenuPolicyContractError(
                        "LOCKED_MENU_BASELINE_NORMALIZATION_MISMATCH",
                        f"{product_key} unresolved menu without stable action target {menu_xmlid}",
                    )
                if menu_rec and hasattr(menu_rec, "active") and not menu_rec.active:
                    raise LockedMenuPolicyContractError(
                        "LOCKED_MENU_NATIVE_FACT_MISMATCH", f"published native menu is inactive: {menu_xmlid}"
                    )
                if not action and not scene_key:
                    raise LockedMenuPolicyContractError(
                        "LOCKED_MENU_BASELINE_NORMALIZATION_MISMATCH",
                        f"{product_key} unresolved action {action_xmlid or menu_xmlid}",
                    )
                resolved_action_xmlid = (action.get_external_id().get(action.id, "") or "") if action else ""
                if action_xmlid and resolved_action_xmlid != action_xmlid:
                    raise LockedMenuPolicyContractError(
                        "LOCKED_MENU_BASELINE_NORMALIZATION_MISMATCH",
                        f"{product_key} action identity mismatch {menu_xmlid}",
                    )
                action_id = int(action.id or 0) if action else 0
                menu_id = int(menu_rec.id or 0) if menu_rec else 0
                action_res_model = _text(getattr(action, "res_model", "")) if action else ""
                locked_res_model = _text(row.get("res_model") or row.get("model"))
                if locked_res_model and action_res_model != locked_res_model:
                    raise LockedMenuPolicyContractError(
                        "LOCKED_MENU_BASELINE_NORMALIZATION_MISMATCH",
                        f"{product_key} action model mismatch {menu_xmlid}",
                    )
                if scene_key:
                    # A declared scene entry has no action route: the server owns the
                    # scene channel and the frontend never derives it.
                    res_model = ""
                    route = "/s/%s" % scene_key
                else:
                    res_model = action_res_model or locked_res_model
                    route = "/a/%s?menu_id=%s" % (action_id, menu_id) if menu_id else "/a/%s" % action_id
                row.update(
                    {
                        "menu_xmlid": menu_xmlid,
                        "menu_key": menu_xmlid,
                        "page_key": menu_xmlid,
                        "menu_id": menu_id,
                        "action_id": action_id,
                        "action_xmlid": resolved_action_xmlid,
                        "route": route,
                        "res_model": res_model,
                        "model": res_model,
                        "enabled": True,
                        "release_state": row["release_state"],
                        "access_level": "public",
                    }
                )
                row.pop("id", None)
                menus.append(row)
            next_group["menus"] = menus
            menu_groups.append(next_group)

        capabilities = self._capabilities_from_user_confirmed_menu_groups(menu_groups)

        values = {
            "active": True,
            "product_key": product_key,
            "base_product_key": _text(product.get("base_product_key")) or "construction",
            "edition_key": _text(product.get("edition_key")) or product_key.split(".", 1)[1],
            "state": _text(product.get("state")) or ("preview" if product_key.endswith(".preview") else "stable"),
            "access_level": "public",
            "allowed_role_codes": product.get("allowed_role_codes") if isinstance(product.get("allowed_role_codes"), list) else [],
            "label": _text(product.get("label")) or product_key,
            "version": _text(product.get("version")) or "v1",
            "scene_version_bindings": product.get("scene_version_bindings") if isinstance(product.get("scene_version_bindings"), dict) else {},
            "menu_groups": menu_groups,
            "scenes": product.get("scenes") if isinstance(product.get("scenes"), list) else [],
            "capabilities": capabilities,
            "note": "projected from P1 native product facts; release state is tracked separately",
        }
        rec = self.sudo().search([("product_key", "=", product_key)], limit=1)
        if rec:
            changed = any(rec[field_name] != field_value for field_name, field_value in values.items())
            if changed:
                rec.write(values)
        else:
            rec = self.sudo().create(values)
            changed = True
        match = assert_policy_matches_locked_contract(contract, product_key, rec.menu_groups)
        return {
            "policy": rec,
            "contract": contract,
            "changed": changed,
            "match": match,
        }

    @api.model
    def sync_construction_menu_product_policies(self):
        self._ensure_formal_product_navigation_runtime_params()
        for product_key in ("construction.standard", "construction.preview"):
            self.synchronize_locked_formal_menu_policy(product_key)
        return True

    @api.model
    def _ensure_formal_product_navigation_runtime_params(self):
        Param = self.env["ir.config_parameter"].sudo()
        Param.set_param(NAV_USER_DATA_ACCEPTANCE_ONLY_PARAM, "0")
        Param.set_param(MENU_CONFIG_NAV_ENABLED_PARAM, "1")
        return True






    @api.model
    def _capabilities_from_user_confirmed_menu_groups(self, menu_groups):
        capabilities = []
        seen = set()
        for group in menu_groups or []:
            if not isinstance(group, dict):
                continue
            group_key = _text(group.get("group_key")) or _text(group.get("group_label")) or "construction.locked"
            group_label = _text(group.get("group_label")) or group_key
            for menu in group.get("menus") or []:
                if not isinstance(menu, dict):
                    continue
                page_key = _text(menu.get("page_key") or menu.get("menu_xmlid") or menu.get("menu_key"))
                if not page_key or page_key in seen:
                    continue
                seen.add(page_key)
                capabilities.append(
                    {
                        "capability_key": _text(menu.get("capability_key")) or "construction.menu.%s" % page_key.replace(".", "_"),
                        "label": _text(menu.get("label") or menu.get("page_label")) or page_key,
                        "group_key": group_key,
                        "group_label": group_label,
                        "target_scene_key": _text(menu.get("target_scene_key")),
                        "target_page_key": page_key,
                        "product_key": _text(menu.get("product_key")),
                        "delivery_level": "exclusive",
                        "entry_kind": "user_visible_menu_page",
                        "visible_menu_path": _text(menu.get("visible_menu_path")),
                        "enabled": bool(menu.get("enabled", True)),
                        "release_state": _text(menu.get("release_state")) or "released",
                        "access_level": _text(menu.get("access_level")) or "public",
                        "control_object": _text(menu.get("control_object")),
                        "source_kind": _text(menu.get("source_kind")),
                        "menu_xmlid": _text(menu.get("menu_xmlid") or page_key),
                        "action_id": int(menu.get("action_id") or 0),
                        "res_model": _text(menu.get("res_model")),
                        "product_domain": _text(menu.get("product_domain")),
                        "entry_intent": _text(menu.get("entry_intent")),
                        "disposition_policy": _text(menu.get("disposition_policy")),
                        "integration_target": _text(menu.get("integration_target")),
                        "default_business_category_code": _text(menu.get("default_business_category_code")),
                        "allowed_business_category_codes": menu.get("allowed_business_category_codes") if isinstance(menu.get("allowed_business_category_codes"), list) else [],
                        "entry_target_policy": _text(menu.get("entry_target_policy")),
                    }
                )
        return capabilities
