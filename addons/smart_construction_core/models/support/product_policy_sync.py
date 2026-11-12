# -*- coding: utf-8 -*-

from copy import deepcopy

from odoo import api, models
from odoo.exceptions import ValidationError
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

    def _normalize_locked_menu_row(self, product_key, menu):
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
            # Actionless scene entries keep the native menu as their
            # authorization carrier; the route is derived later.
            res_model = ""
        else:
            res_model = action_res_model or locked_res_model
        row.update(
            {
                "menu_xmlid": menu_xmlid,
                "menu_key": menu_xmlid,
                "page_key": menu_xmlid,
                "menu_id": menu_id,
                "action_id": action_id,
                "action_xmlid": resolved_action_xmlid,
                "res_model": res_model,
                "model": res_model,
                "scene_key": scene_key,
                "target_scene_key": scene_key,
                "enabled": True,
                "release_state": row["release_state"],
                "access_level": "public",
            }
        )
        row.pop("id", None)
        return row

    @api.model
    def merge_locked_formal_menu_additions(self, product_key, *, menu_xmlids):
        """Add newly shipped formal menu rows without replacing maintained policy.

        Existing rows and operator edits win. This migration seam only adds
        identities that are absent from the persisted policy but present in the
        versioned P1 contract.
        """
        product_key = _text(product_key)
        targets = {_text(value) for value in menu_xmlids or [] if _text(value)}
        rec = self.sudo().with_context(active_test=False).search([
            ("product_key", "=", product_key),
        ], limit=1)
        if not rec:
            return {"policy": self.browse(), "added": [], "skipped": sorted(targets)}
        contract = load_locked_menu_policy_contract()
        product = contract["products"].get(product_key)
        if not isinstance(product, dict):
            raise LockedMenuPolicyContractError("LOCKED_MENU_BASELINE_PRODUCT_MISMATCH", product_key)
        groups = [dict(group) for group in rec.menu_groups or [] if isinstance(group, dict)]
        existing = {
            _text(menu.get("menu_xmlid") or menu.get("page_key") or menu.get("menu_key"))
            for group in groups
            for menu in group.get("menus") or []
            if isinstance(menu, dict)
        }
        source_rows = {}
        for group in product.get("menu_groups") or []:
            for menu in group.get("menus") or []:
                menu_xmlid = _text(
                    menu.get("menu_xmlid") or menu.get("page_key") or menu.get("menu_key")
                )
                if menu_xmlid in targets:
                    source_rows[menu_xmlid] = (group, menu)
        added, skipped = [], []
        for menu_xmlid in sorted(targets):
            if menu_xmlid in existing:
                skipped.append(menu_xmlid)
                continue
            source = source_rows.get(menu_xmlid)
            if not source:
                raise LockedMenuPolicyContractError(
                    "LOCKED_MENU_BASELINE_MENU_MISMATCH", f"{product_key} {menu_xmlid}"
                )
            source_group, source_menu = source
            group_label = canonical_group_label(
                _text(source_group.get("group_label") or source_group.get("label") or source_group.get("title"))
            )
            group_key = "construction.%s" % group_label
            destination = next(
                (
                    group for group in groups
                    if _text(group.get("group_key")) == group_key
                    or canonical_group_label(_text(group.get("group_label") or group.get("label")))
                    == group_label
                ),
                None,
            )
            if destination is None:
                destination = {
                    **source_group,
                    "group_label": group_label,
                    "group_key": group_key,
                    "label": group_label,
                    "title": group_label,
                    "menus": [],
                }
                groups.append(destination)
            destination.setdefault("menus", []).append(
                self._normalize_locked_menu_row(product_key, source_menu)
            )
            existing.add(menu_xmlid)
            added.append(menu_xmlid)
        if added:
            rec.write({
                "menu_groups": groups,
                "capabilities": self._capabilities_from_user_confirmed_menu_groups(groups),
            })
        return {"policy": rec, "added": sorted(added), "skipped": sorted(skipped)}

    def set_native_menu_publication(self, menu_id, group_key, release_state="preview"):
        """Maintain an entry in the existing policy draft; never publish it.

        Same model ACL as the formal product-policy form. Native IDs and action
        references are resolved here, not copied from a file or another database.
        """
        self.ensure_one()
        self.check_access_rights("write")
        self.check_access_rule("write")
        if release_state not in {"released", "preview", "hidden", "retired"}:
            raise ValidationError("Unsupported native entry release state")
        menu = self.env["ir.ui.menu"].browse(int(menu_id)).exists()
        if not menu or not menu.action or menu.action._name != "ir.actions.act_window":
            raise ValidationError("Select one native window-action menu")
        menu.ensure_one()
        menu.check_access_rights("read")
        menu.check_access_rule("read")
        xmlid = menu.get_external_id().get(menu.id)
        action = menu.action
        action_xmlid = action.get_external_id().get(action.id)
        if not xmlid or not action_xmlid or not action.res_model or action.res_model not in self.env:
            raise ValidationError("Stable menu/action identities and an installed model are required")
        groups = deepcopy(self.menu_groups or [])
        matches = [group for group in groups if group.get("group_key") == group_key]
        if len(matches) != 1:
            raise ValidationError("Select one existing product policy group")
        target = matches[0]
        for group in groups:
            group["menus"] = [row for row in group.get("menus", []) if row.get("menu_xmlid") != xmlid]
        target["menus"].append({
            "menu_xmlid": xmlid, "menu_key": xmlid, "page_key": xmlid,
            "menu_id": menu.id, "action_id": action.id, "action_xmlid": action_xmlid,
            "label": menu.name, "page_label": menu.name, "sequence": menu.sequence,
            "res_model": action.res_model, "model": action.res_model,
            "enabled": release_state in {"released", "preview"}, "release_state": release_state,
            "access_level": "public", "source_kind": "native_menu", "entry_target_policy": "native_action",
        })
        self.write({"menu_groups": groups})
        return True

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
        rec = self.sudo().with_context(active_test=False).search([("product_key", "=", product_key)], limit=1)
        if rec:
            # An existing record, including an archived/empty one, is maintained
            # authority. Seed files are not a prerequisite for using it.
            return {"policy": rec, "contract": None, "changed": False, "match": None}
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
            menus = [
                self._normalize_locked_menu_row(product_key, menu)
                for menu in group.get("menus") or []
            ]
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
        rec = self.sudo().create(values)
        match = assert_policy_matches_locked_contract(contract, product_key, rec.menu_groups)
        return {
            "policy": rec,
            "contract": contract,
            "changed": True,
            "match": match,
        }

    @api.model
    def sync_construction_menu_product_policies(self):
        self._ensure_formal_product_navigation_runtime_params()
        for product_key in ("construction.standard", "construction.preview"):
            self.synchronize_locked_formal_menu_policy(product_key)
        return True

    @api.model
    def apply_entry_group_rebinding(self):
        """Rebind the 68 cross-domain menus to their entry exposure groups.

        Idempotent: if a menu already carries exactly its target entry group,
        it is skipped. Replaces the previous broad capability groups with the
        single reusable entry group; it never grants data permissions.
        """
        import json
        from pathlib import Path

        mapping_path = Path(__file__).resolve().parents[2] / "data" / "menu_entry_group_rebinding.json"
        mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
        applied = 0
        skipped = 0
        for menu_xmlid, entry_key in mapping.items():
            menu = self.env.ref(menu_xmlid, raise_if_not_found=False)
            entry = self.env.ref(f"smart_construction_core.group_sc_{entry_key}", raise_if_not_found=False)
            if not menu or not entry:
                raise ValueError(f"unresolved menu rebinding {menu_xmlid} -> {entry_key}")
            current = set(menu.groups_id.ids)
            if current == {entry.id}:
                skipped += 1
                continue
            menu.write({"groups_id": [(6, 0, [entry.id])]})
            applied += 1
        return {"applied": applied, "skipped": skipped, "total": len(mapping)}

    @api.model
    def protect_product_menu_records(self):
        """Mark the maintainable product menu XMLIDs noupdate on every upgrade.

        This is the persistent complement to the one-time 17.0.0.173
        pre-migration: menus added in a later release are still loaded with
        noupdate=False, and this function (wired through a data-file function
        that runs on install and upgrade) marks them after load so operator
        edits survive the *next* upgrade. Only ``ir.ui.menu`` records of this
        module are touched; actions, views and security records are untouched.
        """
        Data = self.env["ir.model.data"].sudo()
        marked = 0
        for row in Data.search([
            ("model", "=", "ir.ui.menu"),
            ("module", "=", "smart_construction_core"),
            ("name", "=like", "menu_sc_%"),
        ]):
            if not row.noupdate:
                row.write({"noupdate": True})
                marked += 1
        return {"marked_noupdate": marked}

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
                        "identity_kind": "entry_compatibility_alias",
                        "business_capability": False,
                        "identity_contract_version": "capability.identity.v1",
                        "qualification_authority": "published_product_release",
                        "provider_authority": "native_menu_action_entry",
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
