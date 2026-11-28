# -*- coding: utf-8 -*-

import hashlib
import json
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
from odoo.addons.smart_construction_core.services.product_capability_admission import (
    merge_admitted_menu_entry,
    merge_admission_capability,
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
    def _merge_locked_formal_menu_additions(self, product_key, *, menu_xmlids):
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
        capabilities = [
            dict(capability)
            for capability in rec.capabilities or []
            if isinstance(capability, dict)
        ]
        capability_keys = {
            _text(capability.get("capability_key"))
            for capability in capabilities
            if _text(capability.get("capability_key"))
        }
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
            added_capabilities = self._capabilities_from_user_confirmed_menu_groups(groups)
            for capability in added_capabilities:
                if _text(capability.get("menu_xmlid")) not in added:
                    continue
                capability_key = _text(capability.get("capability_key"))
                if capability_key and capability_key in capability_keys:
                    continue
                capabilities.append(capability)
                if capability_key:
                    capability_keys.add(capability_key)
            rec.write({
                "menu_groups": groups,
                "capabilities": capabilities,
            })
        return {"policy": rec, "added": sorted(added), "skipped": sorted(skipped)}

    @staticmethod
    def _policy_menu_row(policy, menu_xmlid):
        for group in policy.get("menu_groups") or []:
            for menu in group.get("menus") or []:
                if _text(menu.get("menu_xmlid") or menu.get("menu_key") or menu.get("page_key")) == menu_xmlid:
                    return group, menu
        return None, None

    @staticmethod
    def _release_version_for_policy(version, policy):
        digest = hashlib.sha256(
            json.dumps(
                policy,
                ensure_ascii=False,
                sort_keys=True,
                default=str,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()[:12]
        return "%s-%s" % (_text(version), digest)

    @api.model
    def reconcile_locked_formal_menu_surface(self, product_key, *, version):
        """Converge every shipped formal menu row into one policy release delta."""
        product_key = _text(product_key)
        contract = load_locked_menu_policy_contract()
        product = contract["products"].get(product_key)
        if not isinstance(product, dict):
            raise LockedMenuPolicyContractError(
                "LOCKED_MENU_BASELINE_PRODUCT_MISMATCH", product_key
            )
        menu_xmlids = [
            _text(menu.get("menu_xmlid") or menu.get("menu_key") or menu.get("page_key"))
            for group in product.get("menu_groups") or []
            for menu in group.get("menus") or []
            if isinstance(menu, dict)
            and _text(menu.get("menu_xmlid") or menu.get("menu_key") or menu.get("page_key"))
        ]
        return self._reconcile_locked_menu_releases(
            product_key,
            menu_xmlids=menu_xmlids,
            version=version,
        )

    @api.model
    def _reconcile_locked_menu_release(
        self,
        product_key,
        *,
        menu_xmlid,
        version,
    ):
        """Apply one formal menu delta on top of the active released snapshot.

        Maintained policy edits unrelated to this menu remain drafts. If the
        active snapshot already contains the menu's native anchor, its existing
        release decision is preserved and no snapshot is created.
        """
        product_key = _text(product_key)
        menu_xmlid = _text(menu_xmlid)
        version = _text(version)
        rec = self.sudo().with_context(active_test=False).search([
            ("product_key", "=", product_key),
        ], limit=1)
        if not rec or not menu_xmlid or not version:
            raise LockedMenuPolicyContractError(
                "LOCKED_MENU_RELEASE_RECONCILIATION_INVALID", product_key
            )
        return self._reconcile_locked_menu_releases(
            product_key,
            menu_xmlids=[menu_xmlid],
            version=version,
        )

    @api.model
    def _reconcile_locked_menu_releases(
        self,
        product_key,
        *,
        menu_xmlids,
        version,
    ):
        """Publish all newly shipped formal rows in one release snapshot."""
        product_key = _text(product_key)
        version = _text(version)
        menu_xmlids = list(dict.fromkeys(
            _text(menu_xmlid)
            for menu_xmlid in menu_xmlids or []
            if _text(menu_xmlid)
        ))
        if not product_key or not menu_xmlids or not version:
            raise LockedMenuPolicyContractError(
                "LOCKED_MENU_RELEASE_RECONCILIATION_INVALID", product_key
            )
        merge = self._merge_locked_formal_menu_additions(
            product_key,
            menu_xmlids=menu_xmlids,
        )
        rec = merge["policy"]
        if not rec:
            raise LockedMenuPolicyContractError(
                "LOCKED_MENU_RELEASE_RECONCILIATION_INVALID", product_key
            )
        snapshot_model = self.env["sc.edition.release.snapshot"].sudo()
        active = snapshot_model.search([
            ("product_key", "=", product_key),
            ("state", "=", "released"),
            ("is_active", "=", True),
            ("active", "=", True),
        ], order="released_at desc, activated_at desc, id desc", limit=1)
        active_policy = (
            dict(active.snapshot_json.get("policy") or {})
            if active and isinstance(active.snapshot_json, dict)
            else {}
        )
        missing_xmlids = [
            menu_xmlid
            for menu_xmlid in menu_xmlids
            if not self._policy_menu_row(active_policy, menu_xmlid)[1]
        ]
        if not missing_xmlids:
            return {
                "policy": rec,
                "added": merge["added"],
                "snapshot_id": int(active.id),
                "snapshot_created": False,
                "release_present": True,
            }
        target_policy = deepcopy(active_policy) if active_policy else rec.to_runtime_dict()
        source_policy = rec.to_runtime_dict()
        groups = [deepcopy(item) for item in target_policy.get("menu_groups") or []]
        target_policy["menu_groups"] = groups
        capabilities = [
            deepcopy(item)
            for item in target_policy.get("capabilities") or []
            if isinstance(item, dict)
        ]
        for menu_xmlid in missing_xmlids:
            if self._policy_menu_row(target_policy, menu_xmlid)[1]:
                continue
            group, row = self._policy_menu_row(source_policy, menu_xmlid)
            if not group or not row:
                raise LockedMenuPolicyContractError(
                    "LOCKED_MENU_RELEASE_MENU_MISSING",
                    f"{product_key} {menu_xmlid}",
                )
            group_key = _text(group.get("group_key"))
            target_group = next(
                (
                    item
                    for item in groups
                    if _text(item.get("group_key")) == group_key
                    or (
                        _text(item.get("group_label") or item.get("label"))
                        == _text(group.get("group_label") or group.get("label"))
                    )
                ),
                None,
            )
            if target_group is None:
                target_group = {**deepcopy(group), "menus": []}
                groups.append(target_group)
            target_group.setdefault("menus", []).append(deepcopy(row))
        for menu_xmlid in missing_xmlids:
            if any(_text(item.get("menu_xmlid")) == menu_xmlid for item in capabilities):
                continue
            declared = next(
                (
                    item for item in rec.capabilities or []
                    if isinstance(item, dict) and _text(item.get("menu_xmlid")) == menu_xmlid
                ),
                None,
            )
            if declared:
                capabilities.append(deepcopy(declared))
        target_policy["capabilities"] = capabilities
        release_version = self._release_version_for_policy(version, target_policy)
        existing_versions = snapshot_model.search([
            ("product_key", "=", product_key),
            ("version", "=", release_version),
            ("active", "=", True),
        ], order="id")
        if existing_versions:
            current = next(
                (
                    item for item in existing_versions
                    if item.state == "released" and item.is_active
                ),
                None,
            )
            if current:
                return {
                    "policy": rec,
                    "added": merge["added"],
                    "snapshot_id": int(current.id),
                    "snapshot_created": False,
                    "release_present": True,
                }
            suffix = len(existing_versions) + 1
            while snapshot_model.search_count([
                ("product_key", "=", product_key),
                ("version", "=", "%s-r%s" % (release_version, suffix)),
                ("active", "=", True),
            ]):
                suffix += 1
            release_version = "%s-r%s" % (release_version, suffix)
        from odoo.addons.smart_core.delivery.edition_release_snapshot_service import (
            EditionReleaseSnapshotService,
        )
        snapshot = EditionReleaseSnapshotService(self.env).freeze_release_surface(
            product_key=product_key,
            version=release_version,
            replace_active=True,
            note="reconcile formal menu surface %s" % version,
            policy_override=target_policy,
        )
        return {
            "policy": rec,
            "added": merge["added"],
            "snapshot_id": int(snapshot.get("id") or 0),
            "snapshot_created": True,
            "release_present": True,
        }

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
        existing_entry = next(
            (
                deepcopy(row)
                for group in self.menu_groups or []
                if isinstance(group, dict)
                for row in group.get("menus") or []
                if isinstance(row, dict)
                and _text(
                    row.get("menu_xmlid")
                    or row.get("menu_key")
                    or row.get("page_key")
                )
                == xmlid
            ),
            None,
        )
        groups = deepcopy(self.menu_groups or [])
        matches = [group for group in groups if group.get("group_key") == group_key]
        if len(matches) != 1:
            raise ValidationError("Select one existing product policy group")
        target = matches[0]
        for group in groups:
            group["menus"] = [row for row in group.get("menus", []) if row.get("menu_xmlid") != xmlid]
        generated_entry = {
                "menu_xmlid": xmlid, "menu_key": xmlid, "page_key": xmlid,
                "menu_id": menu.id, "action_id": action.id, "action_xmlid": action_xmlid,
                "label": menu.name, "page_label": menu.name, "sequence": menu.sequence,
                "res_model": action.res_model, "model": action.res_model,
                "enabled": release_state in {"released", "preview"}, "release_state": release_state,
                "access_level": "public", "source_kind": "native_menu", "entry_target_policy": "native_action",
        }
        entry = merge_admitted_menu_entry(existing_entry, generated_entry)
        target["menus"].append(entry)
        generated_rows = self._capabilities_from_user_confirmed_menu_groups(
            [{**target, "menus": [entry]}]
        )
        if not generated_rows:
            raise ValidationError("Native entry capability projection is unavailable")
        generated_target = generated_rows[0]
        capabilities = merge_admission_capability(
            self.capabilities,
            generated_target,
            menu_xmlid=xmlid,
        )
        self.write({"menu_groups": groups, "capabilities": capabilities})
        entry_capability = next(
            (
                capability
                for capability in capabilities
                if _text(capability.get("menu_xmlid")) == xmlid
            ),
            {},
        )
        return {
            "policy": self.to_runtime_dict(),
            "entry": entry,
            "capability": entry_capability,
            "product_key": _text(self.product_key),
            "group_key": group_key,
            "readback": {
                "menu_xmlid": xmlid,
                "action_xmlid": action_xmlid,
                "menu_id": int(menu.id),
                "action_id": int(action.id),
                "res_model": _text(action.res_model),
                "enabled": bool(entry["enabled"]),
                "release_state": release_state,
            },
        }

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
    def ensure_system_product_release_snapshots(self):
        """Materialize the shipped product release on a new or reset database.

        Installation loads product policies, but a policy is a maintained
        source and is not itself the runtime release. Fresh installs do not run
        upgrade migrations, so they must explicitly freeze the shipped policy
        into the active release snapshot consumed by navigation and business
        scene activation. An already valid active system release is reused.
        """
        from odoo.addons.smart_core.delivery.edition_release_snapshot_service import (
            EditionReleaseSnapshotService,
        )
        from odoo.addons.smart_core.delivery.product_scene_composition import (
            compose_product_policy,
        )

        current_db = _text(getattr(self.env.cr, "dbname", ""))
        if not current_db:
            raise LockedMenuPolicyContractError(
                "SYSTEM_PRODUCT_RELEASE_DATABASE_MISSING", ""
            )
        params = self.env["ir.config_parameter"].sudo()
        catalog_source_key = "smart_core.release_operator.catalog_source_db"
        catalog_source_db = _text(params.get_param(catalog_source_key, ""))
        if not catalog_source_db:
            params.set_param(catalog_source_key, current_db)
            catalog_source_db = current_db
        release_env = self.env(
            context={
                **self.env.context,
                "sc_release_catalog_source_db": catalog_source_db,
            }
        )
        Snapshot = release_env["sc.edition.release.snapshot"].sudo()
        service = EditionReleaseSnapshotService(release_env)
        policy_model = release_env["sc.product.policy"].sudo()
        results = []
        for product_key in ("construction.standard", "construction.preview"):
            policy = policy_model.with_context(active_test=False).search([
                ("product_key", "=", product_key),
                ("active", "=", True),
            ], limit=1)
            if not policy:
                raise LockedMenuPolicyContractError(
                    "SYSTEM_PRODUCT_RELEASE_POLICY_MISSING", product_key
                )
            active = Snapshot.search([
                ("product_key", "=", product_key),
                ("state", "=", "released"),
                ("is_active", "=", True),
                ("active", "=", True),
            ], order="released_at desc, activated_at desc, id desc", limit=1)
            valid = False
            if active:
                try:
                    integrity = service.assert_frozen_release_integrity(active)
                    payload = active.snapshot_json if isinstance(active.snapshot_json, dict) else {}
                    frozen_policy = payload.get("policy") if isinstance(payload.get("policy"), dict) else {}
                    composition = frozen_policy.get("business_scene_composition")
                    scenarios = composition.get("scenarios") if isinstance(composition, dict) else None
                    valid = bool(
                        payload.get("policy_snapshot_schema") == "maintained_product_policy.v1"
                        and active.source_policy_id == policy
                        and integrity.get("exact_match")
                        and isinstance(scenarios, list)
                        and scenarios
                    )
                except Exception:
                    valid = False
            if valid:
                results.append({
                    "product_key": product_key,
                    "snapshot_id": int(active.id),
                    "version": str(active.version or ""),
                    "reused": True,
                    "business_scenario_count": len(scenarios),
                    "released_page_count": int(integrity.get("released_count") or 0),
                })
                continue
            source_policy = compose_product_policy(
                release_env,
                policy.to_runtime_dict(),
            )
            draft = service.build_policy_draft_contract(
                product_key=product_key,
                policy_override=source_policy,
            )
            if int(draft.get("blocking_issue_count") or 0):
                blocking = [
                    "%s[%s]" % (
                        _text(row.get("key")),
                        ",".join(
                            _text(issue.get("code"))
                            for issue in (row.get("issues") or [])
                            if isinstance(issue, dict) and _text(issue.get("code"))
                        ),
                    )
                    for row in (draft.get("preflight_checks") or [])
                    if isinstance(row, dict) and row.get("blocking")
                ]
                raise LockedMenuPolicyContractError(
                    "SYSTEM_PRODUCT_RELEASE_PREFLIGHT_BLOCKED",
                    "%s:%s" % (product_key, ",".join(blocking)),
                )
            fingerprint = _text(draft.get("fingerprint"))
            if not fingerprint:
                raise LockedMenuPolicyContractError(
                    "SYSTEM_PRODUCT_RELEASE_FINGERPRINT_MISSING", product_key
                )
            frozen = service.freeze_release_surface(
                product_key=product_key,
                version="system-baseline-%s" % fingerprint[:12],
                note="system product baseline materialized from the shipped industry contract",
                replace_active=True,
                policy_override=source_policy,
            )
            active = Snapshot.browse(int(frozen.get("id") or 0)).exists()
            if not active:
                raise LockedMenuPolicyContractError(
                    "SYSTEM_PRODUCT_RELEASE_SNAPSHOT_MISSING", product_key
                )
            integrity = service.assert_frozen_release_integrity(active)
            payload = active.snapshot_json if isinstance(active.snapshot_json, dict) else {}
            composition = (payload.get("policy") or {}).get("business_scene_composition") or {}
            scenarios = composition.get("scenarios") if isinstance(composition, dict) else []
            if not isinstance(scenarios, list) or not scenarios:
                raise LockedMenuPolicyContractError(
                    "SYSTEM_PRODUCT_RELEASE_SCENARIOS_MISSING", product_key
                )
            results.append({
                "product_key": product_key,
                "snapshot_id": int(active.id),
                "version": str(active.version or ""),
                "reused": False,
                "business_scenario_count": len(scenarios),
                "released_page_count": int(integrity.get("released_count") or 0),
            })
        self.env.registry.clear_cache()
        return {"products": results}

    @api.model
    def promote_preview_entries_to_standard_release(self):
        """Converge persisted policies after the 2026-11-19 preview promotion.

        Existing maintained policies intentionally do not follow source-file
        rewrites. This migration seam adds only missing formal menu identities,
        then promotes rows explicitly classified as preview. Existing rows that
        are already released or hidden, and unrelated operator edits, remain
        untouched.
        """
        contract = load_locked_menu_policy_contract()
        standard = contract["products"].get("construction.standard")
        if not isinstance(standard, dict):
            raise LockedMenuPolicyContractError(
                "LOCKED_MENU_BASELINE_PRODUCT_MISMATCH",
                "construction.standard",
            )
        standard_targets = [
            _text(menu.get("menu_xmlid") or menu.get("menu_key") or menu.get("page_key"))
            for group in standard.get("menu_groups") or []
            for menu in group.get("menus") or []
            if isinstance(menu, dict)
        ]
        merge = self._merge_locked_formal_menu_additions(
            "construction.standard",
            menu_xmlids=standard_targets,
        )
        promoted = set(merge["added"])
        changed_by_product = {
            "construction.standard": set(merge["added"]),
            "construction.preview": set(),
        }
        for product_key in ("construction.standard", "construction.preview"):
            product = contract["products"].get(product_key)
            if not isinstance(product, dict):
                raise LockedMenuPolicyContractError(
                    "LOCKED_MENU_BASELINE_PRODUCT_MISMATCH",
                    product_key,
                )
            desired = {}
            for group in product.get("menu_groups") or []:
                for menu in group.get("menus") or []:
                    if not isinstance(menu, dict):
                        continue
                    menu_xmlid = _text(
                        menu.get("menu_xmlid") or menu.get("menu_key") or menu.get("page_key")
                    )
                    if menu_xmlid:
                        desired[menu_xmlid] = menu
            rec = self.sudo().with_context(active_test=False).search([
                ("product_key", "=", product_key),
            ], limit=1)
            if not rec:
                continue
            groups = deepcopy(rec.menu_groups or [])
            capabilities = deepcopy(rec.capabilities or [])
            changed = 0
            for group in groups:
                if not isinstance(group, dict):
                    continue
                for menu in group.get("menus") or []:
                    if not isinstance(menu, dict):
                        continue
                    menu_xmlid = _text(
                        menu.get("menu_xmlid") or menu.get("menu_key") or menu.get("page_key")
                    )
                    release = desired.get(menu_xmlid)
                    if not release or _text(release.get("release_state")) != "released":
                        continue
                    current_release = _text(menu.get("release_state"))
                    if current_release not in {"preview", "released"}:
                        continue
                    target_maturity = _text(
                        release.get("capability_maturity")
                    ) or "RELEASED_FOUNDATION"
                    if current_release == "released" and _text(
                        menu.get("capability_maturity")
                    ) == target_maturity:
                        continue
                    if current_release == "preview":
                        promoted.add(menu_xmlid)
                    changed_by_product[product_key].add(menu_xmlid)
                    menu["release_state"] = "released"
                    menu["enabled"] = True
                    menu["capability_maturity"] = target_maturity
                    changed += 1
            menu_by_xmlid = {
                _text(
                    menu.get("menu_xmlid")
                    or menu.get("menu_key")
                    or menu.get("page_key")
                ): menu
                for group in groups
                if isinstance(group, dict)
                for menu in group.get("menus") or []
                if isinstance(menu, dict)
            }
            for capability in capabilities:
                if not isinstance(capability, dict):
                    continue
                menu_xmlid = _text(capability.get("menu_xmlid"))
                release = desired.get(menu_xmlid)
                if not release or _text(release.get("release_state")) != "released":
                    continue
                menu = menu_by_xmlid.get(menu_xmlid) or {}
                if _text(menu.get("release_state")) != "released":
                    continue
                current_release = _text(capability.get("release_state"))
                if current_release not in {"preview", "released"}:
                    continue
                target_maturity = _text(
                    release.get("capability_maturity")
                ) or "RELEASED_FOUNDATION"
                if current_release == "released" and _text(
                    capability.get("capability_maturity")
                ) == target_maturity:
                    continue
                if current_release == "preview":
                    promoted.add(menu_xmlid)
                changed_by_product[product_key].add(menu_xmlid)
                capability["release_state"] = "released"
                capability["capability_maturity"] = target_maturity
                changed += 1
            if changed:
                rec.write({
                    "menu_groups": groups,
                    "capabilities": capabilities,
                })
        self.env.registry.clear_cache()
        return {
            "standard_added": list(merge["added"]),
            "promoted_entry_count": len(promoted),
            "promoted_entry_xmlids": sorted(promoted),
            "changed_entry_xmlids": {
                product_key: sorted(menu_xmlids)
                for product_key, menu_xmlids in changed_by_product.items()
            },
        }

    @api.model
    def preview_entry_policy_snapshot(self):
        """Capture maintained menu and capability rows before promotion."""
        snapshot = {}
        for product_key in ("construction.standard", "construction.preview"):
            rec = self.sudo().with_context(active_test=False).search([
                ("product_key", "=", product_key),
            ], limit=1)
            menus = {}
            capabilities = {}
            if rec:
                for group in rec.menu_groups or []:
                    for menu in group.get("menus") or []:
                        if not isinstance(menu, dict):
                            continue
                        menu_xmlid = _text(
                            menu.get("menu_xmlid")
                            or menu.get("menu_key")
                            or menu.get("page_key")
                        )
                        if menu_xmlid:
                            menus[menu_xmlid] = deepcopy(menu)
                for capability in rec.capabilities or []:
                    if not isinstance(capability, dict):
                        continue
                    menu_xmlid = _text(capability.get("menu_xmlid"))
                    if menu_xmlid:
                        capabilities[menu_xmlid] = deepcopy(capability)
            snapshot[product_key] = {
                "menus": menus,
                "capabilities": capabilities,
            }
        return snapshot

    @api.model
    def validate_preview_entry_promotion(self, result, previous=None):
        """Validate only the identities changed by this migration pass."""
        contract = load_locked_menu_policy_contract()
        changed_by_product = result.get("changed_entry_xmlids") or {}
        summary = {}
        failures = []
        for product_key in ("construction.standard", "construction.preview"):
            product = contract["products"].get(product_key)
            if not isinstance(product, dict):
                failures.append("%s source product is missing" % product_key)
                continue
            desired = {}
            for group in product.get("menu_groups") or []:
                for menu in group.get("menus") or []:
                    if not isinstance(menu, dict):
                        continue
                    menu_xmlid = _text(
                        menu.get("menu_xmlid") or menu.get("menu_key") or menu.get("page_key")
                    )
                    if menu_xmlid:
                        desired[menu_xmlid] = menu
            changed = set(changed_by_product.get(product_key) or [])
            rec = self.sudo().with_context(active_test=False).search([
                ("product_key", "=", product_key),
            ], limit=1)
            if not rec:
                failures.append("%s persisted product is missing" % product_key)
                continue
            rows = [
                row
                for group in rec.menu_groups or []
                for row in group.get("menus") or []
                if isinstance(row, dict)
            ]
            by_xmlid = {
                _text(row.get("menu_xmlid") or row.get("menu_key") or row.get("page_key")): row
                for row in rows
                if _text(row.get("menu_xmlid") or row.get("menu_key") or row.get("page_key"))
            }
            capabilities = {
                _text(capability.get("menu_xmlid")): capability
                for capability in rec.capabilities or []
                if isinstance(capability, dict) and _text(capability.get("menu_xmlid"))
            }
            missing_changed = sorted(changed - set(by_xmlid))
            wrong_release = sorted(
                menu_xmlid
                for menu_xmlid in changed
                if menu_xmlid in by_xmlid
                and _text(by_xmlid[menu_xmlid].get("release_state")) != "released"
            )
            wrong_maturity = sorted(
                menu_xmlid
                for menu_xmlid in changed
                if menu_xmlid in by_xmlid
                and _text(by_xmlid[menu_xmlid].get("capability_maturity"))
                != (
                    _text((desired.get(menu_xmlid) or {}).get("capability_maturity"))
                    or "RELEASED_FOUNDATION"
                )
            )
            missing_capabilities = sorted(changed - set(capabilities))
            wrong_capability_release = sorted(
                menu_xmlid
                for menu_xmlid in changed
                if menu_xmlid in capabilities
                and _text(capabilities[menu_xmlid].get("release_state")) != "released"
            )
            wrong_capability_maturity = sorted(
                menu_xmlid
                for menu_xmlid in changed
                if menu_xmlid in capabilities
                and _text(capabilities[menu_xmlid].get("capability_maturity"))
                != (
                    _text((desired.get(menu_xmlid) or {}).get("capability_maturity"))
                    or "RELEASED_FOUNDATION"
                )
            )
            previous_product = (previous or {}).get(product_key) or {}
            previous_menus = previous_product.get("menus") or {}
            previous_capabilities = previous_product.get("capabilities") or {}
            changed_menu_drift = sorted(
                menu_xmlid
                for menu_xmlid, old_row in previous_menus.items()
                if menu_xmlid not in changed and by_xmlid.get(menu_xmlid) != old_row
            )
            changed_capability_drift = sorted(
                menu_xmlid
                for menu_xmlid, old_capability in previous_capabilities.items()
                if menu_xmlid not in changed
                and capabilities.get(menu_xmlid) != old_capability
            )
            if missing_changed:
                failures.append(
                    "%s changed entries are missing: %s" % (product_key, missing_changed)
                )
            if wrong_release:
                failures.append(
                    "%s changed entries are not released: %s" % (product_key, wrong_release)
                )
            if wrong_maturity:
                failures.append(
                    "%s changed entries have stale maturity: %s"
                    % (product_key, wrong_maturity)
                )
            if missing_capabilities:
                failures.append(
                    "%s changed capabilities are missing: %s"
                    % (product_key, missing_capabilities)
                )
            if wrong_capability_release:
                failures.append(
                    "%s changed capabilities are not released: %s"
                    % (product_key, wrong_capability_release)
                )
            if wrong_capability_maturity:
                failures.append(
                    "%s changed capabilities have stale maturity: %s"
                    % (product_key, wrong_capability_maturity)
                )
            if changed_menu_drift:
                failures.append(
                    "%s unchanged maintained menus drifted: %s"
                    % (product_key, changed_menu_drift)
                )
            if changed_capability_drift:
                failures.append(
                    "%s unchanged maintained capabilities drifted: %s"
                    % (product_key, changed_capability_drift)
                )
            summary[product_key] = {
                "changed_count": len(changed),
                "persisted_count": len(by_xmlid),
                "capability_count": len(capabilities),
                "diagnostics": {
                    "standard_added": (
                        list(result.get("standard_added") or [])
                        if product_key == "construction.standard"
                        else []
                    ),
                    "changed_entry_xmlids": sorted(changed),
                    "promoted_entry_xmlids": list(result.get("promoted_entry_xmlids") or []),
                },
                "missing_xmlids": missing_changed,
                "wrong_release_xmlids": wrong_release,
                "wrong_maturity_xmlids": wrong_maturity,
                "missing_capability_xmlids": missing_capabilities,
                "wrong_capability_release_xmlids": wrong_capability_release,
                "wrong_capability_maturity_xmlids": wrong_capability_maturity,
                "unchanged_menu_drift_xmlids": changed_menu_drift,
                "unchanged_capability_drift_xmlids": changed_capability_drift,
            }
        if failures:
            raise LockedMenuPolicyContractError(
                "CLOSE03_PREVIEW_PROMOTION_INCOMPLETE",
                "; ".join(failures),
            )
        return summary

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
