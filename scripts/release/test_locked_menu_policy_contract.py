#!/usr/bin/env python3
from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
import json
import importlib.util
import sys
import tempfile
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "addons/smart_construction_core/services/locked_menu_policy_contract.py"
SPEC = importlib.util.spec_from_file_location("locked_menu_policy_contract", MODULE_PATH)
assert SPEC and SPEC.loader
CONTRACT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTRACT)


ROLE_SURFACE_MODULE_PATH = ROOT / "addons/smart_construction_core/services/role_surface_contract.py"
_ROLE_SURFACE_MODULE_CACHE: dict = {}


def _load_role_surface_contract_module():
    """Load the runtime overlay module without a live Odoo registry."""
    cached = _ROLE_SURFACE_MODULE_CACHE.get("module")
    if cached is not None:
        return cached
    for name in (
        "odoo",
        "odoo.addons",
        "odoo.addons.smart_construction_core",
        "odoo.addons.smart_construction_core.services",
    ):
        sys.modules.setdefault(name, types.ModuleType(name))
    sys.modules[
        "odoo.addons.smart_construction_core.services.locked_menu_policy_contract"
    ] = CONTRACT
    spec = importlib.util.spec_from_file_location("role_surface_contract", ROLE_SURFACE_MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _ROLE_SURFACE_MODULE_CACHE["module"] = module
    return module


def _code_map_landing(path: Path) -> dict:
    source = path.read_text(encoding="utf-8")
    start = source.index("ROLE_SURFACE_OVERRIDES")
    start = source.index("{", start)
    depth = 0
    end = start
    for index in range(start, len(source)):
        char = source[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                end = index
                break
    value = ast.literal_eval(source[start : end + 1])
    return {
        str(role): list((meta or {}).get("landing_scene_candidates") or [])
        for role, meta in value.items()
        if isinstance(meta, dict)
    }


POLICY_MAPS_PATH = ROOT / "addons/smart_construction_core/core_extension_policy_maps.py"
IDENTITY_MODULE_PATH = ROOT / "addons/smart_core/identity/identity_resolver.py"
_IDENTITY_MODULE_CACHE: dict = {}


def _load_policy_maps_module():
    spec = importlib.util.spec_from_file_location("sc_core_extension_policy_maps", POLICY_MAPS_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_identity_resolver_module():
    """Load the P0 identity resolver without a live Odoo registry."""
    cached = _IDENTITY_MODULE_CACHE.get("module")
    if cached is not None:
        return cached
    for name in (
        "odoo",
        "odoo.addons",
        "odoo.addons.smart_core",
        "odoo.addons.smart_core.core",
        "odoo.addons.smart_core.utils",
    ):
        sys.modules.setdefault(name, types.ModuleType(name))
    entry_target = types.ModuleType("odoo.addons.smart_core.core.navigation_entry_target")
    entry_target.build_scene_entry_target = lambda *args, **kwargs: None
    sys.modules["odoo.addons.smart_core.core.navigation_entry_target"] = entry_target
    hooks = types.ModuleType("odoo.addons.smart_core.utils.extension_hooks")
    hooks.call_extension_hook_first = lambda *args, **kwargs: None
    sys.modules["odoo.addons.smart_core.utils.extension_hooks"] = hooks
    spec = importlib.util.spec_from_file_location("sc_identity_resolver_under_test", IDENTITY_MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _IDENTITY_MODULE_CACHE["module"] = module
    return module


class LockedMenuPolicyContractTests(unittest.TestCase):
    def setUp(self):
        self.baseline = ROOT / "scripts/verify/baselines/formal_business_product_menu_policy_v1.json"
        self.checksum = ROOT / "scripts/verify/baselines/formal_business_product_menu_policy_v1.json.sha256"
        self.archive_views = (
            ROOT
            / "addons/smart_construction_core/views/core/fund_legacy_readonly_archive_views.xml"
        )
        self.module_manifest = ROOT / "addons/smart_construction_core/__manifest__.py"
        self.restore_script = ROOT / "scripts/ops/formal_product_menu_policy_restore.py"
        self.runtime_audit = ROOT / "scripts/verify/construction_product_menu_release_audit.py"
        self.contract_runtime_audit = ROOT / "scripts/verify/contract_product_menu_release_audit.py"

    def test_action_only_targets_use_stable_external_ids(self):
        self.assertEqual(
            CONTRACT.FORMAL_ACTION_ONLY_MENU_TARGETS[
                "smart_construction_core.menu_sc_material_rental_in_acceptance"
            ],
            "smart_construction_core.action_sc_material_rental_in_acceptance",
        )
        for menu_xmlid, action_xmlid in CONTRACT.FORMAL_ACTION_ONLY_MENU_TARGETS.items():
            self.assertTrue(menu_xmlid.startswith("smart_construction_core.menu_"))
            self.assertTrue(action_xmlid.startswith("smart_construction_core.action_"))

    def test_formal_restore_consumes_action_only_contract(self):
        source = self.restore_script.read_text(encoding="utf-8")
        self.assertIn("FORMAL_ACTION_ONLY_MENU_TARGETS", source)
        self.assertIn("def _resolve_runtime_target", source)
        self.assertIn('route = "/a/%s" % action_id', source)
        self.assertIn("_resolve_runtime_target(menu_xmlid, payload)", source)
        self.assertIn("PRESERVED_INACTIVE_MENU_XMLIDS", source)
        self.assertNotIn('menu_record.sudo().write({"active": True})', source)

    def test_runtime_release_audit_consumes_action_only_contract(self):
        source = self.runtime_audit.read_text(encoding="utf-8")
        self.assertIn("FORMAL_ACTION_ONLY_MENU_TARGETS", source)
        self.assertIn("FinalMenuNavigationService", source)
        self.assertIn('convergence.get("source") != "delivery_engine"', source)
        self.assertIn('"menu_id": int(menu.id) if menu else 0', source)

    def test_contract_runtime_audit_consumes_locked_product_contract(self):
        source = self.contract_runtime_audit.read_text(encoding="utf-8")
        self.assertIn("load_locked_menu_policy_contract", source)
        self.assertIn("def _locked_contract_menu_keys", source)
        self.assertNotIn("REQUIRED_RELEASED_SETTLEMENT_MENU_XMLIDS", source)

    def test_formal_initialization_action_specs_are_stable_and_complete(self):
        for action_xmlid, spec in CONTRACT.FORMAL_INITIALIZATION_ACTION_SPECS.items():
            self.assertIn(action_xmlid, CONTRACT.FORMAL_ACTION_ONLY_MENU_TARGETS.values())
            self.assertTrue(spec["name"])
            self.assertTrue(spec["res_model"])
            self.assertIn("domain", spec)
            self.assertIn("context", spec)

    def test_fund_archives_are_installed_xml_contracts_not_dynamic_fallbacks(self):
        xml = self.archive_views.read_text(encoding="utf-8")
        for action_xmlid in (
            "action_sc_fuel_card_registration_formal",
            "action_sc_fuel_card_recharge_formal",
        ):
            self.assertIn(f'id="{action_xmlid}"', xml)
            self.assertNotIn(
                f"smart_construction_core.{action_xmlid}",
                CONTRACT.FORMAL_INITIALIZATION_ACTION_SPECS,
            )
        self.assertIn("online_old_legacy_direct:direct_acceptance", xml)
        self.assertIn("direct_acceptance:油卡登记", xml)
        self.assertIn("direct_acceptance:充值登记", xml)
        self.assertIn('create="false" edit="false" delete="false" duplicate="false"', xml)

    def test_fund_archive_menu_loads_after_organization_parent_definition(self):
        manifest = ast.literal_eval(self.module_manifest.read_text(encoding="utf-8"))
        data_files = manifest["data"]
        self.assertLess(
            data_files.index("views/core/office_admin_document_views.xml"),
            data_files.index("views/core/fund_legacy_readonly_archive_views.xml"),
        )

    def test_tax_certificate_target_is_resolved_as_installed_menu(self):
        menu_xmlid = "smart_construction_core.menu_sc_tax_certificate_registration_user"
        action_xmlid = "smart_construction_core.action_sc_tax_certificate_registration_user"
        self.assertNotIn(menu_xmlid, CONTRACT.FORMAL_ACTION_ONLY_MENU_TARGETS)
        self.assertNotIn(menu_xmlid, CONTRACT.FORMAL_BUSINESS_DECISION_REQUIRED_TARGETS)
        self.assertNotIn(action_xmlid, CONTRACT.FORMAL_INITIALIZATION_ACTION_SPECS)
        self.assertNotEqual(action_xmlid, "smart_construction_core.action_sc_invoice_registration")

    def test_role_surface_contract_declares_platform_safe_landing_for_every_role(self):
        contract = CONTRACT.load_locked_menu_policy_contract(self.baseline, self.checksum)
        for product_key in CONTRACT.REQUIRED_PRODUCT_KEYS:
            surface = CONTRACT.product_role_surface(contract, product_key)
            self.assertEqual(surface.get("platform_safe_landing_scene"), "workspace.home")
            declared = CONTRACT.role_landing_candidates(contract, product_key)
            self.assertTrue(declared, f"{product_key} must declare role landing candidates")
            for role_code, candidates in declared.items():
                self.assertIn(
                    "workspace.home",
                    candidates,
                    f"{product_key}.{role_code} must be able to reach the platform-safe landing scene",
                )
                self.assertEqual(
                    candidates[0],
                    "workspace.home",
                    f"{product_key}.{role_code} first hop must be the role home surface",
                )
            # The released role landing must never send a role to a scene the
            # published surface does not grant, which is what caused the
            # login -> access-denied first hop.
            self.assertNotEqual(
                declared.get("business_config_admin", [None])[0],
                "projects.list",
            )

    def test_role_surface_declaration_must_include_platform_safe_landing(self):
        payload = json.loads(self.baseline.read_text(encoding="utf-8"))
        for product in payload["products"]:
            product["role_surface"]["roles"]["pm"]["landing_scene_candidates"] = ["projects.list"]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            baseline, checksum = self._write_contract(root, payload)
            with self.assertRaises(CONTRACT.LockedMenuPolicyContractError) as ctx:
                CONTRACT.load_locked_menu_policy_contract(baseline, checksum)
            self.assertEqual(ctx.exception.code, "LOCKED_MENU_ROLE_SURFACE_INVALID")

    def test_role_surface_declaration_must_be_non_empty_object(self):
        payload = json.loads(self.baseline.read_text(encoding="utf-8"))
        for product in payload["products"]:
            product["role_surface"]["roles"] = {}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            baseline, checksum = self._write_contract(root, payload)
            with self.assertRaises(CONTRACT.LockedMenuPolicyContractError) as ctx:
                CONTRACT.load_locked_menu_policy_contract(baseline, checksum)
            self.assertEqual(ctx.exception.code, "LOCKED_MENU_ROLE_SURFACE_INVALID")

    def test_contract_role_landing_overlay_uses_contract_as_authority(self):
        module = _load_role_surface_contract_module()
        module._CACHE.clear()
        contract = CONTRACT.load_locked_menu_policy_contract(self.baseline, self.checksum)
        sentinel = {
            "business_config_admin": {"label": "业务配置管理员"},
            "unknown_role_kept": {"landing_scene_candidates": ["custom.scene"]},
        }
        overrides, receipt = module.apply_contract_role_landing(sentinel)
        declared = {}
        for product_key in CONTRACT.REQUIRED_PRODUCT_KEYS:
            for role, candidates in CONTRACT.role_landing_candidates(contract, product_key).items():
                declared.setdefault(role, candidates)
        self.assertEqual(receipt["contract_status"], "ok", receipt)
        self.assertEqual(receipt["contract_sha256"], contract["sha256"])
        self.assertTrue(receipt["overlaid_roles"])
        for role, candidates in declared.items():
            self.assertEqual(overrides[role]["landing_scene_candidates"], candidates, role)
            self.assertEqual(candidates[0], "workspace.home", role)
        # A role the contract does not declare keeps its own declaration.
        self.assertEqual(overrides["unknown_role_kept"]["landing_scene_candidates"], ["custom.scene"])

    def test_role_landing_overlay_falls_back_safely_when_contract_unreadable(self):
        module = _load_role_surface_contract_module()
        original = module.load_locked_menu_policy_contract
        module._CACHE.clear()
        module.load_locked_menu_policy_contract = lambda *a, **k: (_ for _ in ()).throw(
            CONTRACT.LockedMenuPolicyContractError("LOCKED_MENU_BASELINE_MISSING", "test")
        )
        try:
            sentinel = {"pm": {"landing_scene_candidates": ["workspace.home", "portal.dashboard"]}}
            overrides, receipt = module.apply_contract_role_landing(sentinel)
        finally:
            module.load_locked_menu_policy_contract = original
            module._CACHE.clear()
        self.assertEqual(receipt["contract_status"], "unavailable")
        self.assertEqual(overrides["pm"]["landing_scene_candidates"], ["workspace.home", "portal.dashboard"])

    def test_code_role_surface_maps_mirror_the_released_contract(self):
        contract = CONTRACT.load_locked_menu_policy_contract(self.baseline, self.checksum)
        declared = {}
        for product_key in CONTRACT.REQUIRED_PRODUCT_KEYS:
            for role, candidates in CONTRACT.role_landing_candidates(contract, product_key).items():
                declared.setdefault(role, candidates)
                self.assertEqual(declared[role], candidates, role)
        for relative in (
            "addons/smart_construction_core/core_extension_policy_maps.py",
            "addons/smart_construction_scene/core_extension.py",
        ):
            code_map = _code_map_landing(ROOT / relative)
            self.assertTrue(code_map, relative)
            for role, candidates in code_map.items():
                self.assertIn(role, declared, f"{relative}: {role} is not declared by the contract")
                self.assertEqual(
                    candidates,
                    declared[role],
                    f"{relative}: {role} landing must mirror the released contract",
                )

    def test_role_catalog_matches_declared_code_role_maps(self):
        """The contract role catalog and the P1 code declarations cannot drift."""
        contract = CONTRACT.load_locked_menu_policy_contract(self.baseline, self.checksum)
        resolution = CONTRACT.role_catalog_resolution(contract)
        policy = _load_policy_maps_module()

        for role, groups in resolution["bindings"].items():
            with self.subTest(role=role):
                self.assertEqual(
                    sorted(policy.ROLE_GROUPS_EXPLICIT.get(role) or ()),
                    sorted(groups),
                    f"{role} group binding must be declared by the contract",
                )
        declared_order = [role for role in resolution["precedence"] if role in policy.ROLE_PRECEDENCE]
        self.assertEqual(
            declared_order,
            [role for role in policy.ROLE_PRECEDENCE if role in set(resolution["bindings"])],
            "role precedence must follow the contract catalog order, not a code literal",
        )
        for role, groups in resolution["capability_groups"].items():
            with self.subTest(role=f"capability:{role}"):
                self.assertEqual(
                    sorted(policy.ROLE_GROUPS_CAPABILITY_FALLBACK.get(role) or ()),
                    sorted(groups),
                    f"{role} capability fallback must be declared by the contract",
                )
        for role in resolution["synthetic_role_codes"]:
            self.assertNotIn(role, resolution["bindings"], f"{role} is synthetic and cannot be a delivered role")

    def test_declared_roles_are_pairwise_distinguishable(self):
        """Different roles must be genuinely different principals.

        Menus differ per role because the permission data differs: each role
        binds its own real group xmlids, so two roles that shared a binding
        would be indistinguishable at the menu/ACL layer and the per-role
        surface would silently collapse.  The role set stays a contract value;
        what is locked here is that every declared role is independently
        reachable and no two roles alias each other.
        """
        contract = CONTRACT.load_locked_menu_policy_contract(self.baseline, self.checksum)
        resolution = CONTRACT.role_catalog_resolution(contract)
        bindings = {role: tuple(groups) for role, groups in resolution["bindings"].items()}
        self.assertGreater(len(bindings), 1, "a product role set must declare more than one role")
        seen: dict[tuple, str] = {}
        for role, groups in bindings.items():
            with self.subTest(role=role):
                self.assertTrue(groups, f"{role} must bind at least one real group")
                self.assertNotIn(groups, seen, f"{role} aliases {seen.get(groups)}")
            seen[groups] = role
        # Menus differ per role because the permission data differs.  The
        # landing hop is deliberately shared (the platform-safe workspace
        # home), so role differentiation must be asserted on the declared
        # delivered menu surface, not on the landing candidate list.
        policy = _load_policy_maps_module()
        delivered: dict[str, frozenset] = {}
        for role in resolution["bindings"]:
            meta = policy.ROLE_SURFACE_OVERRIDES.get(role) or {}
            delivered[role] = frozenset(
                str(xmlid)
                for field in ("primary_menu_xmlids", "role_home_menu_xmlids", "menu_xmlids")
                for xmlid in meta.get(field) or []
            )
        self.assertGreater(
            len(set(delivered.values())),
            1,
            "declared roles must not all publish the same delivered menu surface",
        )
        restricted = policy.ROLE_SURFACE_OVERRIDES.get("restricted") or {}
        self.assertTrue(restricted.get("deny_all_navigation"), "the synthetic role must deny navigation")
        self.assertFalse(delivered.get("restricted"), "the synthetic role must deliver no menu")

    def test_role_catalog_drives_resolution_and_fails_closed(self):
        """Behaviour, not strings: declared roles resolve; unknown groups fail closed.

        The default role set is contract data, so a role added to the catalog
        (bound to real res.groups) resolves without a code change, while a
        principal whose real groups match no declared role always lands on the
        declared synthetic role.  A declaration never widens group visibility.
        """
        contract = CONTRACT.load_locked_menu_policy_contract(self.baseline, self.checksum)
        resolution = CONTRACT.role_catalog_resolution(contract)
        resolver = _load_identity_resolver_module().IdentityResolver()
        resolver._role_groups_explicit = {role: set(groups) for role, groups in resolution["bindings"].items()}
        resolver._role_precedence = tuple(resolution["precedence"])
        resolver._role_groups_capability_fallback = {
            role: set(groups) for role, groups in resolution["capability_groups"].items()
        }
        resolver._capability_role_codes = tuple(resolution["capability_role_codes"])
        resolver._capability_fallback_order = tuple(resolution["capability_fallback_order"])
        resolver._synthetic_role_codes = tuple(resolution["synthetic_role_codes"])
        resolver._role_meta = {role: dict(meta) for role, meta in resolution["metadata"].items()}

        for role, groups in resolution["bindings"].items():
            with self.subTest(role=role):
                self.assertEqual(resolver.resolve_role_codes_with_evidence({groups[0]})[0], [role])
                self.assertEqual(resolver.resolve_role_code(set(groups)), role)

        for role in resolution["capability_fallback_order"]:
            groups = sorted(resolution["capability_groups"].get(role) or ())
            self.assertTrue(groups, f"{role} declares no capability fallback group")
            with self.subTest(role=f"fallback:{role}"):
                self.assertEqual(resolver.resolve_role_code({groups[-1]}), role)

        terminal_codes, terminal_evidence = resolver.resolve_role_codes_with_evidence({"base.group_system"})
        self.assertEqual(terminal_codes, list(resolution["synthetic_role_codes"]))
        self.assertEqual(terminal_evidence["source"], "no_authoritative_role")

        declared_roles = set(resolution["bindings"]) | set(resolution["synthetic_role_codes"])
        known_roles = (
            set(resolver._role_precedence)
            | set(resolver._role_groups_explicit)
            | set(resolver._capability_role_codes)
        )
        self.assertLessEqual(
            known_roles,
            declared_roles,
            "the resolver must not know a role that the contract catalog does not declare",
        )

    def _write_contract(self, root: Path, payload) -> tuple[Path, Path]:
        baseline = root / CONTRACT.BASELINE_FILE
        checksum = root / CONTRACT.BASELINE_CHECKSUM_FILE
        raw = payload if isinstance(payload, bytes) else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        baseline.write_bytes(raw)
        checksum.write_text(f"{hashlib.sha256(raw).hexdigest()}  {CONTRACT.BASELINE_FILE}\n", encoding="utf-8")
        return baseline, checksum

    @staticmethod
    def _declared_menu_count(contract):
        """Menu count is a versioned contract value, never a frozen literal.

        The product surface is expected to iterate; the invariant the gate
        protects is that the declared, projected and accepted counts stay
        identical, not that the number is 89 forever.
        """
        return contract["payload"]["policy_strategy"]["effective_menu_count_per_product"]

    def test_versioned_locked_baseline_loads_and_contains_expected_contract(self):
        contract = CONTRACT.load_locked_menu_policy_contract(self.baseline, self.checksum)
        self.assertEqual(
            contract["sha256"],
            "bcefc90c4ef5bf61b32806fd75afea6eaaa93cb513c9d970d86dfb14bb5f0551",
        )
        declared = self._declared_menu_count(contract)
        for product_key in CONTRACT.REQUIRED_PRODUCT_KEYS:
            rows = CONTRACT.baseline_rows(contract, product_key)
            self.assertEqual(len(rows), declared)
            self.assertIn(
                (
                    "产品配置",
                    "表单配置",
                    "smart_construction_core.menu_sc_business_config_workbench",
                ),
                rows,
            )
            self.assertIn(
                (
                    "行政中心",
                    "人员档案",
                    "smart_construction_core.menu_sc_runtime_user_management",
                ),
                rows,
            )
            self.assertIn(
                (
                    "项目中心",
                    "新项目立项",
                    "smart_construction_core.menu_sc_project_initiation",
                ),
                rows,
            )
            self.assertIn(
                (
                    "成本中心",
                    "成本计划编制",
                    "smart_construction_core.menu_sc_p1_cost_plan",
                ),
                rows,
            )
            self.assertIn(
                (
                    "合同中心",
                    "日常合同",
                    "smart_construction_core.menu_sc_p1_daily_contract",
                ),
                rows,
            )
            self.assertNotIn("smart_construction_core.menu_sc_historical_payment_fact", {row[2] for row in rows})

    def test_missing_baseline_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaisesRegex(CONTRACT.LockedMenuPolicyContractError, "LOCKED_MENU_BASELINE_MISSING"):
                CONTRACT.load_locked_menu_policy_contract(root / "missing.json", root / "missing.sha256")

    def test_invalid_json_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            baseline, checksum = self._write_contract(Path(temp), b"{not-json")
            with self.assertRaisesRegex(CONTRACT.LockedMenuPolicyContractError, "LOCKED_MENU_BASELINE_INVALID"):
                CONTRACT.load_locked_menu_policy_contract(baseline, checksum)

    def test_checksum_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            baseline = root / CONTRACT.BASELINE_FILE
            checksum = root / CONTRACT.BASELINE_CHECKSUM_FILE
            baseline.write_text("{}", encoding="utf-8")
            checksum.write_text("0" * 64, encoding="utf-8")
            with self.assertRaisesRegex(CONTRACT.LockedMenuPolicyContractError, "sha256 mismatch"):
                CONTRACT.load_locked_menu_policy_contract(baseline, checksum)

    def test_product_key_mismatch_fails_closed(self):
        payload = json.loads(self.baseline.read_text(encoding="utf-8"))
        payload["products"] = [row for row in payload["products"] if row["product_key"] != "construction.preview"]
        with tempfile.TemporaryDirectory() as temp:
            baseline, checksum = self._write_contract(Path(temp), payload)
            with self.assertRaisesRegex(CONTRACT.LockedMenuPolicyContractError, "LOCKED_MENU_BASELINE_PRODUCT_MISMATCH"):
                CONTRACT.load_locked_menu_policy_contract(baseline, checksum)

    def test_duplicate_stable_identity_fails_normalization(self):
        payload = json.loads(self.baseline.read_text(encoding="utf-8"))
        product = payload["products"][0]
        product["menu_groups"][0]["menus"].append(copy.deepcopy(product["menu_groups"][0]["menus"][0]))
        with tempfile.TemporaryDirectory() as temp:
            baseline, checksum = self._write_contract(Path(temp), payload)
            with self.assertRaisesRegex(
                CONTRACT.LockedMenuPolicyContractError,
                "LOCKED_MENU_BASELINE_NORMALIZATION_MISMATCH",
            ):
                CONTRACT.load_locked_menu_policy_contract(baseline, checksum)

    def test_policy_comparison_uses_stable_identity_not_database_ids(self):
        contract = CONTRACT.load_locked_menu_policy_contract(self.baseline, self.checksum)
        groups = copy.deepcopy(contract["products"]["construction.standard"]["menu_groups"])
        for index, menu in enumerate((menu for group in groups for menu in group["menus"]), start=10000):
            menu["menu_id"] = index
            menu["action_id"] = index + 10000
        result = CONTRACT.assert_policy_matches_locked_contract(contract, "construction.standard", groups)
        self.assertEqual(result["menu_count"], self._declared_menu_count(contract))
        self.assertTrue(result["exact_match"])

    def test_full_baseline_rejects_every_out_of_band_addition(self):
        contract = CONTRACT.load_locked_menu_policy_contract(self.baseline, self.checksum)
        groups = copy.deepcopy(contract["products"]["construction.standard"]["menu_groups"])
        groups[0]["menus"].append(
            {
                "label": "未授权入口",
                "menu_xmlid": "smart_construction_core.menu_sc_unauthorized",
                "enabled": True,
                "release_state": "released",
            }
        )
        with self.assertRaisesRegex(
            CONTRACT.LockedMenuPolicyContractError, "LOCKED_MENU_POLICY_SYNCHRONIZATION_MISMATCH"
        ):
            CONTRACT.assert_policy_matches_locked_contract(contract, "construction.standard", groups)

    def test_snapshot_must_exactly_preserve_the_full_locked_baseline(self):
        contract = CONTRACT.load_locked_menu_policy_contract(self.baseline, self.checksum)
        rows = CONTRACT.baseline_rows(contract, "construction.standard")
        pages = [
            {"label": label, "menu_xmlid": menu_xmlid, "enabled": True, "release_state": "released"}
            for _group, label, menu_xmlid in rows
        ]
        self.assertEqual(
            CONTRACT.assert_snapshot_matches_locked_contract(contract, "construction.standard", pages)["menu_count"],
            self._declared_menu_count(contract),
        )
        pages.pop()
        with self.assertRaisesRegex(CONTRACT.LockedMenuPolicyContractError, "LOCKED_MENU_SNAPSHOT_MISMATCH"):
            CONTRACT.assert_snapshot_matches_locked_contract(contract, "construction.standard", pages)

    def test_standard_and_preview_contracts_are_independent_objects(self):
        contract = CONTRACT.load_locked_menu_policy_contract(self.baseline, self.checksum)
        standard = contract["products"]["construction.standard"]
        preview = contract["products"]["construction.preview"]
        self.assertIsNot(standard, preview)
        declared = self._declared_menu_count(contract)
        self.assertEqual(len(CONTRACT.baseline_rows(contract, "construction.standard")), declared)
        self.assertEqual(len(CONTRACT.baseline_rows(contract, "construction.preview")), declared)
        self.assertNotEqual(standard["product_key"], preview["product_key"])


# 过渡台账：契约尚未声明 scene 身份、而由代码常量承载的入口身份。
# 只允许随契约收敛而删除；新增即失败（新增一条 = 又出现一个声明点）。
TRANSITIONAL_UNDECLARED_SCENE_MENU_KEYS = (
    "smart_construction_core.menu_sc_project_initiation",
    "smart_construction_core.menu_sc_project_project",
    "smart_construction_core.menu_sc_project_management_scene",
    "smart_construction_core.menu_sc_project_cost_code",
    "smart_construction_core.menu_sc_project_dashboard",
    "smart_construction_core.menu_sc_operating_metrics_project",
    "smart_construction_core.menu_sc_dashboard_cost_cockpit_fact",
    "smart_construction_core.menu_sc_dictionary",
    "smart_construction_core.menu_payment_request",
)

# 过渡台账：契约当前声明的入口身份数量。只允许单调递增。
TRANSITIONAL_DECLARED_SCENE_ENTRY_COUNT = 1


class SceneEntryIdentityContractTests(unittest.TestCase):
    """Lock navigation_dual_track_contract_v1.md 2.7 / 2.8.

    入口身份必须由契约声明；代码常量只能镜像契约，不能自成事实源。
    断言声明消费与契约内部一致性，不以文本出现作为正确性证明。
    """

    def setUp(self):
        self.baseline = ROOT / "scripts/verify/baselines/formal_business_product_menu_policy_v1.json"
        self.payload = json.loads(self.baseline.read_text(encoding="utf-8"))

    def _menus(self):
        for product in self.payload["products"]:
            for group in product.get("menu_groups") or []:
                for menu in group.get("menus") or []:
                    yield product["product_key"], menu

    def _declared_scene_entries(self):
        return [
            (product_key, menu)
            for product_key, menu in self._menus()
            if str(menu.get("target_scene_key") or "").strip()
        ]

    def test_scene_declaration_fields_are_mutually_consistent(self):
        """契约内 scene 身份声明必须三处一致，不能只声明一半。"""
        for _product_key, menu in self._menus():
            with self.subTest(menu=menu.get("menu_xmlid")):
                declared = bool(str(menu.get("target_scene_key") or "").strip())
                self.assertEqual(declared, menu.get("entry_target_policy") == "scene_entry")
                self.assertEqual(declared, menu.get("disposition_policy") == "scene_entry")

    def test_declared_scene_route_consumes_the_declared_identity(self):
        """路由必须是契约声明的 scene 身份的投影，而不是另算一套。"""
        declared = self._declared_scene_entries()
        self.assertGreaterEqual(
            len({str(_menu["target_scene_key"]).strip() for _pk, _menu in declared}),
            TRANSITIONAL_DECLARED_SCENE_ENTRY_COUNT,
            "contract scene declaration must be a monotone ratchet; "
            "when a declaration lands, raise TRANSITIONAL_DECLARED_SCENE_ENTRY_COUNT",
        )
        seen = set()
        for _product_key, menu in declared:
            scene_key = str(menu["target_scene_key"]).strip()
            seen.add(scene_key)
            with self.subTest(menu=menu.get("menu_xmlid")):
                self.assertEqual(menu.get("route"), f"/s/{scene_key}")
                self.assertEqual(str(menu.get("scene_key") or "").strip(), scene_key)
        if declared:
            self.assertTrue(seen)

    def test_declared_scene_entries_keep_the_native_authorization_base(self):
        """R-A3: scene 不新开授权通道，授权仍由原生 model ACL + record rule 收口。"""
        for _product_key, menu in self._declared_scene_entries():
            with self.subTest(menu=menu.get("menu_xmlid")):
                self.assertEqual(menu.get("locked_data_policy"), "odoo_model_acl_and_record_rules")
                self.assertNotEqual(str(menu.get("target_scene_key") or "").strip(), "")
                self.assertFalse(
                    str(menu.get("target_scene_key") or "").strip()
                    and not str(menu.get("route") or "").startswith("/s/"),
                    "a declared scene entry must route through the scene channel",
                )

    def test_runtime_normalization_consumes_the_declared_scene_identity(self):
        """运行态策略同步必须按契约接受无动作的场景入口，普通菜单不得放行。"""
        declared = {
            str(menu.get("menu_xmlid") or "").strip(): str(menu.get("target_scene_key") or "").strip()
            for _product_key, menu in self._declared_scene_entries()
        }
        self.assertTrue(declared, "the contract must declare at least one scene entry")
        for _product_key, menu in self._menus():
            menu_xmlid = str(menu.get("menu_xmlid") or "").strip()
            with self.subTest(menu=menu_xmlid):
                self.assertEqual(CONTRACT.declared_scene_entry_key(menu), declared.get(menu_xmlid, ""))
        # A row is only a scene entry through its contract declaration. A menu
        # that merely lacks an action, or declares the policy without a scene
        # key, must never take the action-less branch.
        self.assertEqual(CONTRACT.declared_scene_entry_key({"menu_xmlid": "x.y"}), "")
        self.assertEqual(CONTRACT.declared_scene_entry_key({"action_xmlid": "x.y"}), "")
        self.assertEqual(CONTRACT.declared_scene_entry_key({"entry_target_policy": "scene_entry"}), "")
        self.assertEqual(CONTRACT.declared_scene_entry_key({"disposition_policy": "scene_entry"}), "")

    def test_code_scene_map_mirrors_the_released_contract(self):
        """代码常量只能镜像契约；不得承载契约未声明的入口身份。"""
        declared = {
            menu.get("menu_xmlid"): str(menu.get("target_scene_key") or "").strip()
            for _product_key, menu in self._menus()
        }
        policy = _load_policy_maps_module()
        code_map = dict(policy.NAV_MENU_SCENE_MAP)
        self.assertTrue(code_map, "NAV_MENU_SCENE_MAP must not be empty")
        undeclared = []
        for menu_xmlid, scene_key in code_map.items():
            contract_scene = declared.get(menu_xmlid)
            if contract_scene:
                self.assertEqual(
                    scene_key,
                    contract_scene,
                    f"{menu_xmlid} scene identity drifted from the released contract",
                )
                continue
            undeclared.append(menu_xmlid)
        self.assertEqual(
            sorted(undeclared),
            sorted(TRANSITIONAL_UNDECLARED_SCENE_MENU_KEYS),
            "code scene constants may only shrink as the contract converges; "
            "retire an entry by declaring it in the contract, never by adding a new code constant",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
