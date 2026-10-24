# -*- coding: utf-8 -*-
from __future__ import annotations

import datetime
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT / "scripts" / "ops"))

import acceptance_evolution_binding_guard as guard  # noqa: E402
import acceptance_evolution_record as recorder  # noqa: E402

HEAD = "a" * 40
OTHER = "b" * 40

PATH_NS_CHECKS = [
    "server_head_matches_expected",
    "server_worktree_clean",
    "server_applied_commit_in_history",
    "bare_root_requires_a_namespace",
    "bare_api_requires_namespace",
    "database_header_hint_refused",
    "database_query_hint_refused",
    "unknown_namespace_refused",
    "tenant_entry_binds_tenant_database",
    "platform_entry_binds_platform_database",
    "tenant_runtime_reports_deployed_revision",
    "platform_runtime_reports_deployed_revision",
    "demo_entry_admin_login_succeeds",
    "platform_entry_admin_login_succeeds",
    "tokens_are_independent",
    "demo_token_accepted_on_demo_entry",
    "platform_token_accepted_on_platform_entry",
    "demo_token_rejected_on_platform_entry",
    "platform_token_rejected_on_demo_entry",
    "demo_logout_succeeds",
    "demo_token_invalid_after_demo_logout",
    "platform_token_survives_demo_logout",
    "unauthorized_company_is_refused",
]

ENTRY_REQUIRED_CHECKS = [
    "entry_declares_one_serving_duty",
    "exactly_one_container_publishes_the_public_port",
    "bare_root_requires_a_namespace",
    "root_api_requires_a_namespace",
    "root_login_contract_requires_a_namespace",
    "client_database_hint_x_odoo_database_is_refused",
    "client_database_query_is_refused",
    "client_namespace_header_cannot_override_the_path",
    "unknown_namespace_is_refused",
    "unknown_namespace_page_shell_is_refused",
    "invalid_namespace_prefix_is_refused",
    "tenant_namespace_lands_on_the_serving_database",
    "platform_namespace_lands_on_the_platform_database",
    "tenant_runtime_publishes_the_deployed_revision",
    "platform_runtime_publishes_the_deployed_revision",
    "serving_application_reads_the_deployed_revision",
    "platform_application_reads_the_deployed_revision",
]


def _write(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _entry_verify(head: str = HEAD, passed: bool = True) -> dict:
    checks = [{"name": name, "passed": True} for name in ENTRY_REQUIRED_CHECKS]
    while len(checks) < 40:
        checks.append({"name": f"extra_{len(checks):02d}", "passed": True})
    if not passed:
        checks[-1]["passed"] = False
    return {
        "status": "PASS" if passed else "FAIL",
        "expected_sha": head,
        "head": head,
        "checks": checks,
    }


def _path_ns(head: str = HEAD) -> dict:
    return {
        "schema": "path-ns-c.acceptance.v1",
        "provenance": {"expected_sha": head, "head": head},
        "target": {"expected_sha": head},
        "summary": {"total": 23, "passed": 23, "failed": 0, "status": "PASS"},
        "checks": [{"name": name, "status": "pass"} for name in PATH_NS_CHECKS],
    }


def _list_surface(head: str = HEAD) -> dict:
    return {
        "schema": "frontend_list_surface_structure_browser.v1",
        "passed": True,
        "failures": [],
        "summary": {
            "observations": 6,
            "records": {"passed": 8, "total": 8, "complete": True},
            "gated": {"passed": 108, "total": 108, "failed": 0},
            "negative_fixtures": {"detected": 5, "total": 5},
            "runtime_errors": 0,
        },
        "source": {"acceptance": {"provenance": {"expectedSha": head}}},
    }


def _presentation(head: str = HEAD, *, passed: bool = True) -> dict:
    return {
        "schema": "frontend_product_page_header_browser.v1",
        "passed": passed,
        "provenance": {"expected_sha": head},
        "console": [],
        "pageerror": [],
        "http": [],
        "mutations": [],
        "mutationCount": 0,
        "targets": [{
            "key": "project-form",
            "headerCount": 1,
            "h1Count": 1,
            "unresolvedComponentCount": 0,
            "pagePattern": "workspace-form",
            "mobileOverflow": False,
        }],
    }


def _relation(head: str = HEAD) -> dict:
    fields = ["user_id", "manager_id", "partner_id"]
    declared = {"can_read": True, "can_open": True, "action_id": 807, "menu_id": 430}
    comparison = [
        {
            "field": field,
            "contract": {
                "can_read": True,
                "can_open": True,
                "visible": True,
                "readonly": True,
                "required": False,
                "label": field,
            },
            "rendered": {
                "visible": True,
                "readonly": True,
                "required": False,
                "has_value": True,
                "has_open_control": True,
                "label": field,
            },
            "differences": [],
        }
        for field in fields
    ]
    comparison.append({
        "field": "owner_id",
        "contract": {
            "can_read": True,
            "can_open": True,
            "visible": False,
            "readonly": True,
            "required": False,
            "label": "owner_id",
        },
        "rendered": {
            "visible": False,
            "readonly": None,
            "required": None,
            "has_value": False,
            "has_open_control": False,
            "label": "",
        },
        "differences": [],
    })
    return {
        "schema": "record-relation-roundtrip-acceptance.v1",
        "status": "pass",
        "expected_sha": head,
        "served_revision": head,
        "failures": [],
        "console_errors": [],
        "denied_requests": [],
        "declared_entry_count": 13,
        "declared_openable": [
            {"field": field, "declared": dict(declared)} for field in fields
        ],
        "controls": [{"field": field, "label": field} for field in fields],
        "attempts": [
            {"field": field, "outcome": "opened"} for field in fields
        ],
        "contract_openable_fields": [*fields, "owner_id"],
        "visible_openable_fields": fields,
        "populated_openable_fields": fields,
        "empty_value_openable_fields": [],
        "not_visible_openable_fields": ["owner_id"],
        "visible_relation_control_fields": fields,
        "contract_render_comparison": comparison,
        "contract_render_comparison_summary": {
            "complete": True,
            "contract_field_count": 4,
            "compared_field_count": 4,
            "fields_with_differences": 0,
            "difference_count": 0,
            "blocking_count": 0,
            "non_blocking_count": 0,
        },
        "roundtrip": {
            "field": "user_id",
            "restored": {
                "path_restored": True,
                "title_restored": True,
                "statusbar_restored": True,
                "tabs_restored": True,
                "actions_restored": True,
                "error_free": True,
            },
        },
    }


class TestGlobAndPlan(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = guard.load_registry(
            ROOT / "config" / "acceptance" / "evolution_binding.v1.json"
        )

    def test_stage_selection_is_shared_and_never_marks_deferred_suites_passed(self):
        plan = {"required_evidence_suites": ["daily_runtime_entry", "path_namespace_identity", "list_surface_structure", "relation_roundtrip"], "status": "PASS"}
        merge = guard.plan_for_stage(self.registry, plan, "merge")
        self.assertEqual(merge["required_evidence_suites"], ["list_surface_structure", "relation_roundtrip"])
        self.assertEqual(merge["deferred_evidence_suites"], ["daily_runtime_entry", "path_namespace_identity"])
        self.assertEqual(guard.plan_for_stage(self.registry, plan)["required_evidence_suites"], plan["required_evidence_suites"])
        self.assertEqual(guard.plan_for_stage(self.registry, plan, "deployment")["required_evidence_suites"], plan["required_evidence_suites"])
        self.assertEqual(len(plan["required_evidence_suites"]), 4)
        with self.assertRaises(guard.BindingError):
            guard.plan_for_stage(self.registry, plan, "skip")

    def test_runtime_suite_inputs_are_target_scoped_not_repository_wide(self):
        self.assertEqual(guard.GLOBAL_SUITE_INPUTS, ())
        for suite_id in ("frontend_presentation", "list_surface_structure", "relation_roundtrip"):
            suite = self.registry["suites"][suite_id]
            self.assertTrue(suite["make_inputs"], suite_id)
            self.assertNotIn("make/**", suite["inputs"], suite_id)
            self.assertNotIn("make/ci.mk", {item["path"] for item in suite["make_inputs"]})

    def test_make_target_material_ignores_other_rules_but_tracks_the_selected_rule(self):
        original = (
            "target-one:\n"
            "\t@echo one\n"
            "\n"
            "target-two:\n"
            "\t@echo two\n"
        )
        changed_other = original.replace("@echo one", "@echo changed")
        changed_target = original.replace("@echo two", "@echo changed")
        selected = guard._make_target_material(original, "target-two", "Makefile")
        self.assertEqual(selected, guard._make_target_material(changed_other, "target-two", "Makefile"))
        self.assertNotEqual(selected, guard._make_target_material(changed_target, "target-two", "Makefile"))
        self.assertEqual(
            guard._make_variable_material("UNRELATED := 1\n", "UNRELATED", "Makefile"),
            "UNRELATED := 1\n",
        )

    def test_glob_semantics(self):
        self.assertTrue(guard.path_matches("addons/**", "addons/a.py"))
        self.assertTrue(guard.path_matches("addons/**", "addons/a/b.py"))
        self.assertFalse(guard.path_matches("addons/**", "addons_other/a.py"))
        self.assertTrue(guard.path_matches("**/*.md", "README.md"))
        self.assertTrue(guard.path_matches("**/*.md", "docs/a/b.md"))
        self.assertTrue(guard.path_matches("docker-compose*.yml", "docker-compose.ci.yml"))
        self.assertFalse(guard.path_matches("docker-compose*.yml", "nested/docker-compose.yml"))

    def test_plan_maps_runtime_changes_to_acceptance_suites(self):
        plan = guard.build_plan(
            self.registry,
            ["addons/smart_core/app_config_engine/models/app_nav_config.py"],
            "base",
            HEAD,
        )
        self.assertEqual(plan["status"], "PASS")
        self.assertEqual(plan["required_suites"], ["backend_contract", "daily_runtime_entry"])
        self.assertEqual(plan["required_evidence_suites"], ["daily_runtime_entry"])

    def test_plan_keeps_docs_only_changes_out_of_runtime_evidence(self):
        plan = guard.build_plan(self.registry, ["docs/ops/readme.md"], "base", HEAD)
        self.assertEqual(plan["status"], "PASS")
        self.assertEqual(plan["required_suites"], [])
        self.assertEqual(plan["required_evidence_suites"], [])

    def test_governance_markdown_is_not_absorbed_by_the_docs_rule(self):
        plan = guard.build_plan(self.registry, ["AGENTS.md"], "base", HEAD)
        self.assertEqual(plan["status"], "PASS")
        self.assertEqual(plan["required_suites"], ["governance_static"])
        self.assertEqual(plan["required_evidence_suites"], [])

    def test_presentation_owned_frontend_files_use_the_lightweight_lane(self):
        for path in (
            "frontend/apps/web/src/components/product-page-header/ProductPageHeader.vue",
            "frontend/apps/web/src/components/template/FormSection.vue",
            "frontend/apps/web/src/pages/contractForm/ContractFormProductHeader.vue",
        ):
            plan = guard.build_plan(self.registry, [path], "base", HEAD)
            self.assertEqual(plan["matched_rules"][path], "frontend-presentation")
            self.assertEqual(
                plan["required_suites"],
                ["frontend_contract", "frontend_presentation"],
            )
            self.assertEqual(plan["required_evidence_suites"], ["frontend_presentation"])

        runtime_path = "frontend/apps/web/src/api/businessConfig.ts"
        plan = guard.build_plan(self.registry, [runtime_path], "base", HEAD)
        self.assertEqual(plan["matched_rules"][runtime_path], "frontend-runtime")
        self.assertEqual(
            plan["required_suites"],
            ["frontend_contract", "list_surface_structure"],
        )

    def test_presentation_lane_is_wired_into_the_frontend_quick_gate(self):
        makefile = (ROOT / "make" / "frontend.mk").read_text(encoding="utf-8")
        self.assertIn(
            "verify.frontend.quick.gate: verify.frontend.presentation.lane.unit",
            makefile,
        )

    def test_acceptance_runners_require_their_own_runtime_evidence(self):
        plan = guard.build_plan(
            self.registry,
            ["scripts/verify/record_relation_roundtrip_acceptance.js"],
            "base",
            HEAD,
        )
        self.assertEqual(plan["required_suites"], ["governance_static", "relation_roundtrip"])
        self.assertEqual(plan["required_evidence_suites"], ["relation_roundtrip"])

        plan = guard.build_plan(
            self.registry,
            ["scripts/verify/lib/frontend_acceptance_environment.mjs"],
            "base",
            HEAD,
        )
        self.assertEqual(
            plan["required_suites"],
            ["governance_static", "list_surface_structure", "relation_roundtrip"],
        )
        self.assertEqual(
            plan["required_evidence_suites"],
            ["list_surface_structure", "relation_roundtrip"],
        )

    def test_isolated_acceptance_entry_changes_require_identity_evidence(self):
        for path in (
            "config/acceptance/isolated_entry_identity.v1.env",
            "scripts/dev/frontend_acceptance_up.sh",
            "scripts/verify/frontend_acceptance_login_probe.py",
        ):
            plan = guard.build_plan(self.registry, [path], "base", HEAD)
            self.assertEqual(plan["status"], "PASS", path)
            self.assertIn("path_namespace_identity", plan["required_suites"], path)
            self.assertIn("path_namespace_identity", plan["required_evidence_suites"], path)

    def test_exact_governance_tools_do_not_require_runtime(self):
        paths = ['scripts/ops/agent_run_context.py', 'scripts/ops/evidence_scope.py',
                 'scripts/ops/test_evidence_scope.py', 'scripts/ops/validation_delivery_plan.py',
                 'config/acceptance/evolution_binding.v1.json']
        for path in paths:
            plan = guard.build_plan(self.registry, [path], 'base', HEAD)
            self.assertEqual(plan['required_suites'], ['governance_static'], path)
            self.assertEqual(plan['required_evidence_suites'], [], path)

    def test_runtime_tools_and_mixed_changes_keep_runtime_requirements(self):
        for path in ('scripts/ops/daily_runtime_database_duty.py', 'scripts/ops/path_ns_c_acceptance.py',
                     'scripts/ops/new_unclassified_runtime.py'):
            plan = guard.build_plan(self.registry, ['scripts/ops/evidence_scope.py', path], 'base', HEAD)
            self.assertEqual(set(plan['required_suites']),
                             {'governance_static', 'daily_runtime_entry', 'path_namespace_identity'})

    def test_explicit_dependencies_override_first_match(self):
        self.assertFalse(guard.suite_owns_path(self.registry, 'daily_runtime_entry',
                                             'config/acceptance/evolution_binding.v1.json'))
        self.assertFalse(guard.suite_owns_path(self.registry, 'daily_runtime_entry',
                                             'scripts/ops/evidence_scope.py'))
        registry = json.loads(json.dumps(self.registry))
        registry['suites']['daily_runtime_entry']['inputs'] = ['scripts/ops/evidence_scope.py']
        self.assertTrue(guard.suite_owns_path(registry, 'daily_runtime_entry', 'scripts/ops/evidence_scope.py'))

    def test_plan_fails_closed_for_unclassified_paths(self):
        plan = guard.build_plan(self.registry, ["new_surface/unknown.txt"], "base", HEAD)
        self.assertEqual(plan["status"], "FAIL")
        self.assertEqual(plan["unclassified"], ["new_surface/unknown.txt"])

    def test_every_declared_suite_is_reachable_from_a_rule(self):
        referenced = {
            suite_id
            for rule in self.registry["rules"]
            for suite_id in rule["suites"]
        }
        self.assertEqual(set(self.registry["suites"]), referenced)

    def test_carry_forward_policy_rejects_an_unknown_mode(self):
        registry = json.loads(json.dumps(self.registry))
        registry["policy"]["evidence_carry_forward"]["mode"] = "whole_manifest"
        with self.assertRaisesRegex(guard.BindingError, "suite_input_fingerprint"):
            guard.carry_forward_policy(registry)

    def test_evidence_contracts_are_non_vacuous(self):
        for suite_id, suite in self.registry["suites"].items():
            contract = suite.get("evidence")
            if not contract:
                continue
            with self.subTest(suite=suite_id):
                self.assertTrue(
                    contract.get("required_checks")
                    or contract.get("min_counts")
                    or contract.get("min_checks"),
                    f"{suite_id} evidence contract has no non-empty assertion",
                )

    def test_remote_quality_lane_runs_the_binding_gate_unconditionally(self):
        workflow = (
            ROOT / ".github" / "workflows" / "professional_quality_gate.yml"
        ).read_text(encoding="utf-8")
        marker = "make verify.acceptance.evolution.binding"
        self.assertEqual(workflow.count(marker), 1)
        index = workflow.index(marker)
        start = workflow.rfind("      - name:", 0, index)
        self.assertNotEqual(start, -1)
        block = workflow[start:index]
        self.assertNotIn("if:", block)
        self.assertLess(index, workflow.index("Run full professional quality gate"))

    def test_zero_base_sha_is_treated_as_absent(self):
        head = guard._git("rev-parse", "HEAD")
        base = guard.resolve_base(guard.ZERO_SHA, head)
        self.assertRegex(base, r"^[0-9a-f]{40}$")

    def test_record_target_always_refreshes_the_manifest(self):
        makefile = (ROOT / "make" / "guards.mk").read_text(encoding="utf-8")
        start = makefile.index("acceptance.evolution.record:")
        block = makefile[start : start + 500]
        self.assertIn("acceptance_evolution_record.py", block)
        self.assertNotIn("if [ -n", block)


class TestAdapters(unittest.TestCase):
    def test_entry_verify_adapter(self):
        counts = guard.validate_evidence_file
        self.assertEqual(
            guard._adapter_entry_verify(_entry_verify(), HEAD)["counts"]["passed"], 40
        )
        contract = {
            "required_checks": ["entry_declares_one_serving_duty", "bare_root_requires_a_namespace"],
            "min_checks": 40,
        }
        self.assertEqual(
            guard._adapter_entry_verify(_entry_verify(), HEAD, contract)["counts"]["total"], 40
        )
        with self.assertRaises(guard.BindingError):
            guard._adapter_entry_verify(_entry_verify(OTHER), HEAD)
        with self.assertRaises(guard.BindingError):
            guard._adapter_entry_verify(_entry_verify(passed=False), HEAD)
        broken = _entry_verify()
        broken["checks"] = [
            check
            for check in broken["checks"]
            if check["name"] != "bare_root_requires_a_namespace"
        ]
        with self.assertRaises(guard.BindingError):
            guard._adapter_entry_verify(broken, HEAD, contract)
        self.assertIs(counts, guard.validate_evidence_file)

    def test_path_namespace_adapter(self):
        result = guard._adapter_path_ns_c(_path_ns(), HEAD)
        self.assertEqual(result["counts"], {"total": 23, "passed": 23, "failed": 0})
        with self.assertRaises(guard.BindingError):
            guard._adapter_path_ns_c(_path_ns(OTHER), HEAD)
        broken = _path_ns()
        broken["checks"][0]["status"] = "fail"
        with self.assertRaises(guard.BindingError):
            guard._adapter_path_ns_c(broken, HEAD)
        broken = _path_ns()
        broken["checks"].pop()
        with self.assertRaises(guard.BindingError):
            guard._adapter_path_ns_c(broken, HEAD)

    def test_list_surface_adapter(self):
        result = guard._adapter_list_surface(_list_surface(), HEAD)
        self.assertEqual(result["counts"]["failures"], 0)
        broken = _list_surface()
        broken["passed"] = False
        with self.assertRaises(guard.BindingError):
            guard._adapter_list_surface(broken, HEAD)

    def test_presentation_adapter(self):
        result = guard._adapter_presentation_header(_presentation(), HEAD)
        self.assertEqual(result["counts"]["targets"], 1)
        self.assertEqual(result["counts"]["mutations"], 0)
        with self.assertRaisesRegex(guard.BindingError, "did not pass"):
            guard._adapter_presentation_header(_presentation(passed=False), HEAD)
        with self.assertRaisesRegex(guard.BindingError, "bound to"):
            guard._adapter_presentation_header(_presentation(OTHER), HEAD)
        broken = _presentation()
        broken["mutations"] = [{"intent": "api.data.write"}]
        with self.assertRaisesRegex(guard.BindingError, "mutations"):
            guard._adapter_presentation_header(broken, HEAD)
        broken = _presentation()
        broken["targets"][0]["mobileOverflow"] = True
        with self.assertRaisesRegex(guard.BindingError, "mobile overflow"):
            guard._adapter_presentation_header(broken, HEAD)
        with self.assertRaises(guard.BindingError):
            guard._adapter_list_surface(_list_surface(OTHER), HEAD)
        broken = _list_surface()
        broken["summary"]["records"] = {"passed": 0, "total": 0, "complete": True}
        with self.assertRaises(guard.BindingError):
            guard._adapter_list_surface(broken, HEAD)
        broken = _list_surface()
        broken["summary"]["negative_fixtures"] = {"detected": 4, "total": 5}
        with self.assertRaises(guard.BindingError):
            guard._adapter_list_surface(broken, HEAD)
        broken = _list_surface()
        broken["failures"] = [{"check": "x"}]
        with self.assertRaises(guard.BindingError):
            guard._adapter_list_surface(broken, HEAD)

    def test_relation_roundtrip_adapter(self):
        relation_contract = {
            "allowed_non_blocking_difference_kinds": [
                "CONTRACT_LABEL_RENDER_DIFF",
                "OPENABLE_EMPTY_VALUE_HAS_NO_TARGET",
            ]
        }
        result = guard._adapter_relation_roundtrip(_relation(), HEAD, relation_contract)
        self.assertEqual(result["counts"]["openable_entries"], 3)
        self.assertEqual(result["counts"]["opened_entries"], 3)
        broken = _relation()
        broken["failures"] = ["x"]
        with self.assertRaises(guard.BindingError):
            guard._adapter_relation_roundtrip(broken, HEAD)
        broken = _relation()
        broken["served_revision"] = OTHER
        with self.assertRaises(guard.BindingError):
            guard._adapter_relation_roundtrip(broken, HEAD)
        broken = _relation()
        broken["roundtrip"]["restored"]["error_free"] = False
        with self.assertRaises(guard.BindingError):
            guard._adapter_relation_roundtrip(broken, HEAD)
        broken = _relation()
        broken["console_errors"] = ["boom"]
        with self.assertRaises(guard.BindingError):
            guard._adapter_relation_roundtrip(broken, HEAD)
        broken = _relation()
        broken["visible_relation_control_fields"] = ["user_id", "manager_id"]
        with self.assertRaisesRegex(guard.BindingError, "diverge"):
            guard._adapter_relation_roundtrip(broken, HEAD)
        broken = _relation()
        broken["attempts"].pop()
        with self.assertRaisesRegex(guard.BindingError, "every contract-openable"):
            guard._adapter_relation_roundtrip(broken, HEAD)
        broken = _relation()
        broken["declared_openable"][0]["declared"]["action_id"] = None
        with self.assertRaisesRegex(guard.BindingError, "action/menu"):
            guard._adapter_relation_roundtrip(broken, HEAD)
        broken = _relation()
        broken["not_visible_openable_fields"] = []
        with self.assertRaisesRegex(guard.BindingError, "partition"):
            guard._adapter_relation_roundtrip(broken, HEAD)
        broken = _relation()
        del broken["contract_render_comparison"]
        with self.assertRaisesRegex(guard.BindingError, "comparison is missing"):
            guard._adapter_relation_roundtrip(broken, HEAD, relation_contract)
        broken = _relation()
        broken["contract_render_comparison"][0]["differences"] = [{
            "kind": "CONTRACT_LABEL_RENDER_DIFF",
            "blocking": False,
            "reason": "label copy differs",
            "contract": "负责人",
            "rendered": "项目经理",
        }]
        broken["contract_render_comparison_summary"]["difference_count"] = 1
        broken["contract_render_comparison_summary"]["non_blocking_count"] = 1
        broken["contract_render_comparison_summary"]["fields_with_differences"] = 1
        guard._adapter_relation_roundtrip(broken, HEAD, relation_contract)
        broken = _relation()
        broken["contract_render_comparison"][0]["differences"] = [{
            "kind": "CONTRACT_VISIBILITY_MISMATCH",
            "blocking": True,
            "reason": "declared visible but rendered hidden",
            "contract": True,
            "rendered": False,
        }]
        broken["contract_render_comparison_summary"]["difference_count"] = 1
        broken["contract_render_comparison_summary"]["blocking_count"] = 1
        broken["contract_render_comparison_summary"]["fields_with_differences"] = 1
        with self.assertRaisesRegex(guard.BindingError, "blocking differences"):
            guard._adapter_relation_roundtrip(broken, HEAD, relation_contract)
        broken = _relation()
        broken["contract_render_comparison"][0]["differences"] = [{
            "kind": "UNREVIEWED_DIFFERENCE",
            "blocking": False,
            "reason": "unclassified",
            "contract": True,
            "rendered": False,
        }]
        broken["contract_render_comparison_summary"]["difference_count"] = 1
        broken["contract_render_comparison_summary"]["non_blocking_count"] = 1
        broken["contract_render_comparison_summary"]["fields_with_differences"] = 1
        with self.assertRaisesRegex(guard.BindingError, "not declared in policy"):
            guard._adapter_relation_roundtrip(broken, HEAD, relation_contract)


class TestManifest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = guard.load_registry(
            ROOT / "config" / "acceptance" / "evolution_binding.v1.json"
        )
        cls.plan = {
            "required_evidence_suites": ["daily_runtime_entry"],
        }

    def _manifest(self, directory: Path, head: str = HEAD) -> Path:
        evidence = _write(directory / "entry.json", _entry_verify(head))
        payload = {
            "schema": guard.EVIDENCE_SCHEMA,
            "head_sha": head,
            "base_sha": "c" * 40,
            "recorded_at": datetime.datetime.now(datetime.timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z"),
            "suites": {
                "daily_runtime_entry": {
                    "status": "pass",
                    "evidence": [
                        {
                            "path": str(evidence),
                            "sha256": hashlib.sha256(evidence.read_bytes()).hexdigest(),
                        }
                    ],
                }
            },
        }
        return _write(directory / "manifest.json", payload)

    def test_exact_head_manifest_passes(self):
        with tempfile.TemporaryDirectory() as raw:
            result = guard.validate_manifest(
                self.registry, self.plan, self._manifest(Path(raw)), HEAD
            )
            self.assertEqual(result["status"], "PASS")
            self.assertIn("daily_runtime_entry", result["suites"])

    def test_manifest_head_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as raw:
            with self.assertRaises(guard.BindingError):
                guard.validate_manifest(
                    self.registry, self.plan, self._manifest(Path(raw), OTHER), HEAD
                )

    def test_missing_required_suite_fails(self):
        with tempfile.TemporaryDirectory() as raw:
            manifest = self._manifest(Path(raw))
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            payload["suites"] = {}
            manifest.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(guard.BindingError):
                guard.validate_manifest(self.registry, self.plan, manifest, HEAD)

    def test_evidence_tampering_fails(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            manifest = self._manifest(directory)
            _write(directory / "entry.json", _entry_verify(OTHER))
            with self.assertRaises(guard.BindingError):
                guard.validate_manifest(self.registry, self.plan, manifest, HEAD)

    def test_stale_manifest_fails(self):
        with tempfile.TemporaryDirectory() as raw:
            manifest = self._manifest(Path(raw))
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            payload["recorded_at"] = "2000-01-01T00:00:00Z"
            manifest.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(guard.BindingError):
                guard.validate_manifest(self.registry, self.plan, manifest, HEAD)

    def test_future_manifest_fails(self):
        with tempfile.TemporaryDirectory() as raw:
            manifest = self._manifest(Path(raw))
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            payload["recorded_at"] = "2999-01-01T00:00:00Z"
            manifest.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(guard.BindingError):
                guard.validate_manifest(self.registry, self.plan, manifest, HEAD)


class TestCarryForwardPolicy(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.repo = Path(self.temporary.name)
        self.registry = guard.load_registry(
            ROOT / "config" / "acceptance" / "evolution_binding.v1.json"
        )
        self.original_root = guard.ROOT
        guard.ROOT = self.repo
        self.addCleanup(setattr, guard, "ROOT", self.original_root)
        self.addCleanup(self.temporary.cleanup)
        self._git("init", "-q")
        self._write("runtime.py", "VERSION = 1\n")
        self._commit("baseline")

    def _git(self, *args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(self.repo), *args],
            text=True,
            capture_output=True,
            check=True,
        )
        return result.stdout.strip()

    def _write(self, path: str, content: str) -> None:
        target = self.repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def _commit(self, message: str) -> str:
        self._git("add", ".")
        self._git(
            "-c",
            "user.name=Codex Test",
            "-c",
            "user.email=codex-test@example.invalid",
            "commit",
            "-q",
            "-m",
            message,
        )
        return self._git("rev-parse", "HEAD")

    def _write_json(self, path: Path, payload: dict) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def _manifest(self, head: str, bound_head: str, evidence: Path, directory: Path) -> Path:
        now = (
            datetime.datetime.now(datetime.timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )
        payload = {
            "schema": guard.EVIDENCE_SCHEMA,
            "head_sha": head,
            "base_sha": bound_head,
            "recorded_at": now,
            "suites": {
                "daily_runtime_entry": {
                    "status": "pass",
                    "evidence": [
                        {
                            "path": str(evidence),
                            "sha256": hashlib.sha256(evidence.read_bytes()).hexdigest(),
                        }
                    ],
                    "bound_head": bound_head,
                    "input_sha256": guard.suite_input_sha256(
                        self.registry, "daily_runtime_entry", bound_head
                    ),
                    "verified_at": now,
                }
            },
        }
        return self._write_json(directory / "manifest.json", payload)

    def test_suite_digest_changes_only_for_the_affected_layer(self):
        base = self._git("rev-parse", "HEAD")
        self._write("frontend/app.ts", "export const value = 1;\n")
        head = self._commit("frontend")
        self.assertEqual(
            guard.suite_input_sha256(self.registry, "backend_contract", base),
            guard.suite_input_sha256(self.registry, "backend_contract", head),
        )
        self.assertNotEqual(
            guard.suite_input_sha256(self.registry, "frontend_contract", base),
            guard.suite_input_sha256(self.registry, "frontend_contract", head),
        )

    def test_governance_tool_change_preserves_runtime_fingerprint(self):
        base = self._git('rev-parse', 'HEAD')
        self._write('scripts/ops/evidence_scope.py', 'offline ledger change')
        head = self._commit('governance only')
        for suite in ('daily_runtime_entry', 'path_namespace_identity'):
            self.assertEqual(guard.suite_input_sha256(self.registry, suite, base),
                             guard.suite_input_sha256(self.registry, suite, head))
        self._write('scripts/ops/daily_runtime_database_duty.py', 'runtime change')
        runtime = self._commit('runtime')
        self.assertNotEqual(guard.suite_input_sha256(self.registry, 'daily_runtime_entry', head),
                            guard.suite_input_sha256(self.registry, 'daily_runtime_entry', runtime))

    def test_unrelated_make_change_preserves_runtime_fingerprint(self):
        registry = {
            "suites": {
                "runtime_probe": {
                    "description": "runtime probe",
                    "entrypoints": ["make verify.runtime.probe"],
                    "evidence": None,
                    "stages": ["merge"],
                    "inputs": [],
                    "make_inputs": [
                        {
                            "path": "make/runtime.mk",
                            "targets": ["verify.runtime.probe"],
                            "variables": ["RUNTIME_PROBE_MODE"],
                        }
                    ],
                }
            },
            "rules": [],
        }
        self._write(
            "make/runtime.mk",
            "RUNTIME_PROBE_MODE ?= readonly\n"
            "verify.runtime.probe:\n"
            "\t@echo runtime\n"
            "verify.runtime.other:\n"
            "\t@echo other\n",
        )
        self._write("make/ci.mk", "ci-unrelated:\n\t@echo ci\n")
        base = self._commit("runtime probe baseline")
        self._write("make/ci.mk", "ci-unrelated:\n\t@echo changed-ci\n")
        ci_only = self._commit("unrelated CI orchestration")
        self.assertEqual(
            guard.suite_input_sha256(registry, "runtime_probe", base),
            guard.suite_input_sha256(registry, "runtime_probe", ci_only),
        )
        self._write(
            "make/runtime.mk",
            "RUNTIME_PROBE_MODE ?= readonly\n"
            "verify.runtime.probe:\n"
            "\t@echo runtime\n"
            "verify.runtime.other:\n"
            "\t@echo changed-other\n",
        )
        other_target = self._commit("unrelated target")
        self.assertEqual(
            guard.suite_input_sha256(registry, "runtime_probe", ci_only),
            guard.suite_input_sha256(registry, "runtime_probe", other_target),
        )
        self._write(
            "make/runtime.mk",
            "RUNTIME_PROBE_MODE ?= write\n"
            "verify.runtime.probe:\n"
            "\t@echo runtime-changed\n"
            "verify.runtime.other:\n"
            "\t@echo changed-other\n",
        )
        changed = self._commit("owned target")
        self.assertNotEqual(
            guard.suite_input_sha256(registry, "runtime_probe", other_target),
            guard.suite_input_sha256(registry, "runtime_probe", changed),
        )

    def test_unchanged_suite_inputs_can_be_carried_across_head(self):
        base = self._git("rev-parse", "HEAD")
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            evidence = self._write_json(directory / "entry.json", _entry_verify(base))
            self._write("frontend/app.ts", "export const value = 1;\n")
            head = self._commit("frontend-only")
            manifest = self._manifest(head, base, evidence, directory)
            result = guard.validate_manifest(
                self.registry,
                {"required_evidence_suites": ["daily_runtime_entry"]},
                manifest,
                head,
            )
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["suites"]["daily_runtime_entry"]["bound_head"], base)

    def test_reviewed_input_policy_migration_reanchors_identical_suite_inputs(self):
        head = self._git("rev-parse", "HEAD")
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            evidence = self._write_json(directory / "entry.json", _entry_verify(head))
            now = (
                datetime.datetime.now(datetime.timezone.utc)
                .replace(microsecond=0)
                .isoformat()
                .replace("+00:00", "Z")
            )
            current_input = guard.suite_input_sha256(
                self.registry, "daily_runtime_entry", head
            )
            previous = {
                "schema": guard.EVIDENCE_SCHEMA,
                "head_sha": head,
                "base_sha": head,
                "recorded_at": now,
                "suites": {
                    "daily_runtime_entry": {
                        "status": "pass",
                        "evidence": [
                            {
                                "path": str(evidence),
                                "sha256": hashlib.sha256(evidence.read_bytes()).hexdigest(),
                            }
                        ],
                        "bound_head": head,
                        "input_sha256": "f" * 64,
                        "verified_at": now,
                    }
                },
            }
            candidate = recorder._reuse_suite_record(
                self.registry, previous, "daily_runtime_entry", head
            )
            self.assertIsNotNone(candidate)
            self.assertEqual(candidate["input_sha256"], current_input)
            self.assertEqual(candidate["input_policy_reanchored_from"], "f" * 64)

    def test_changed_suite_inputs_refuse_carried_evidence(self):
        base = self._git("rev-parse", "HEAD")
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            evidence = self._write_json(directory / "entry.json", _entry_verify(base))
            self._write("addons/smart_core/runtime.py", "VERSION = 2\n")
            head = self._commit("backend-runtime")
            manifest = self._manifest(head, base, evidence, directory)
            with self.assertRaisesRegex(guard.BindingError, "inputs changed"):
                guard.validate_manifest(
                    self.registry,
                    {"required_evidence_suites": ["daily_runtime_entry"]},
                    manifest,
                    head,
                )

    def test_recorder_reuses_only_unchanged_suite_layers(self):
        base = self._git("rev-parse", "HEAD")
        original_record_root = recorder.ROOT
        recorder.ROOT = self.repo
        self.addCleanup(setattr, recorder, "ROOT", original_record_root)
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            entry_base = self._write_json(directory / "entry-base.json", _entry_verify(base))
            path_ns_base = self._write_json(directory / "path-ns-base.json", _path_ns(base))
            manifest = directory / "manifest.json"
            plan = {"base_sha": base, "required_evidence_suites": ["daily_runtime_entry"]}
            recorder.record_manifest(
                self.registry,
                plan,
                manifest,
                base,
                {
                    "daily_runtime_entry": [entry_base],
                    "path_namespace_identity": [path_ns_base],
                },
            )
            self._write("addons/smart_core/runtime.py", "VERSION = 2\n")
            head = self._commit("backend-runtime")
            entry_head = self._write_json(directory / "entry-head.json", _entry_verify(head))
            _manifest, recorded, carried = recorder.record_manifest(
                self.registry,
                plan,
                manifest,
                head,
                {"daily_runtime_entry": [entry_head]},
            )
            self.assertEqual(recorded, ["daily_runtime_entry"])
            self.assertEqual(carried, ["path_namespace_identity"])
            self.assertEqual(
                guard.validate_manifest(
                    self.registry, plan, manifest, head
                )["status"],
                "PASS",
            )

if __name__ == "__main__":
    unittest.main()
