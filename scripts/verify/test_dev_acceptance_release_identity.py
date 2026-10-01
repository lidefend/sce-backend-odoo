#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
import tempfile
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("dev_acceptance_release_probe", ROOT / "scripts/ops/dev_acceptance_release_probe.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)
SHA = "a" * 40
SCHEMA_ASSET = "docs/architecture/unified_page_contract_v2/unified_page_contract_v2.schema.json"
DECLARATION_PATH = ROOT / "config/acceptance/backend_contract_instance_v1.json"
RESOLUTION_PRODUCER = "scripts/verify/frontend_delivery_hardening_runtime_ids.py"
EXAMPLE_CONTRACT = ROOT / "docs/architecture/unified_page_contract_v2/examples/form_project.json"
CONTRACT_CHECKS = [
    "identity_deployed_sha",
    "identity_actor_uid",
    "identity_role_code",
    "identity_company",
    "resolution_unique_target",
    "request_target_binding",
    "contract_integrity_self_consistent",
    "contract_schema_digest_bound",
    "contract_formal_schema_valid",
    "contract_custody_captured",
]


def declaration(required=None):
    return {
        "schema": "acceptance.backend_contract_instance.v1",
        "database": "sc_frontend_acceptance",
        "account": {"login": "fixture_role_finance", "role_code": "finance", "company_name": "FE Company A"},
        "resolution": {
            "governed_producer": RESOLUTION_PRODUCER,
            "producer_output_key": "FRONTEND_DELIVERY_HARDENING_TARGETS_JSON",
            "target_key": "payment_request",
            "company_key": "a",
            "stable_identifier_field": "record_xmlid",
            "requires_unique_match": True,
        },
        "request": {
            "intent": "ui.contract.v2",
            "view_type": "form",
            "delivery_profile": "full",
            "client_type": "web_pc",
            "accepted_contract_versions": ["2.2.x"],
            "client_contract_capabilities": ["status_contract.v2"],
        },
        "schema_asset": SCHEMA_ASSET,
        "required_checks": list(required if required is not None else CONTRACT_CHECKS),
    }


def resolution(sha=SHA, record_id=4242, model="project.project"):
    return {
        "schema": "acceptance.record_identity_resolution.v1",
        "producer": RESOLUTION_PRODUCER,
        "expected_sha": sha,
        "targets": {
            "payment_request": {
                "menu_id": 545,
                "menu_xmlid": "smart_construction_core.menu_sc_user_payment_apply",
                "action_id": 775,
                "model": model,
                "record_id": record_id,
                "record_xmlid": "smart_construction_acceptance_fixture.fe_delivery_hardening_payment_request_a",
                "record_identity": "FE-DELIVERY-HARDENING-001",
                "display_name": "FE-DELIVERY-HARDENING-001",
            },
            "companies": {"a": 8, "b": 9},
        },
    }


def example_contract():
    import copy

    return copy.deepcopy(json.loads(EXAMPLE_CONTRACT.read_text(encoding="utf-8")))


class FakeSession:
    def __init__(self, contract, uid=30, role_code="finance", company_name="FE Company A", init_uid=None):
        self.contract = contract
        self.uid = uid
        self.role_code = role_code
        self.requests = []
        self.user = {
            "id": uid if init_uid is None else init_uid,
            "name": "Acceptance Fixture Finance",
            "company_id": 8,
            "company_name": company_name,
            "allowed_company_ids": [8, 9],
            "lang": "zh_CN",
        }

    def post(self, path, payload):
        self.requests.append((path, payload))
        if path.startswith("/web/session/authenticate"):
            return 200, json.dumps({"result": {"uid": self.uid, "name": "Acceptance Fixture Finance"}})
        intent = (payload or {}).get("intent")
        if intent == "system.init":
            return 200, json.dumps({"ok": True, "data": {"user": self.user, "role_surface": {"role_code": self.role_code}}})
        if intent == "ui.contract.v2":
            return 200, json.dumps({"ok": True, "data": self.contract})
        return 200, json.dumps({"ok": False})


_UNSET = object()


def receipt(contract=None, decl=None, res=_UNSET, **kwargs):
    session = kwargs.pop("session", None) or FakeSession(contract if contract is not None else example_contract(), **kwargs)
    resolved = resolution() if res is _UNSET else res
    return MODULE.probe_contract_acceptance(
        "https://daily.example.test",
        "sc_frontend_acceptance",
        decl if decl is not None else declaration(),
        resolved,
        served_sha=SHA,
        expected_sha=SHA,
        session=session,
    )


class ContractAcceptanceTest(unittest.TestCase):
    def test_exact_instance_receipt_passes_and_binds_custody(self):
        session = FakeSession(example_contract())
        result = MODULE.probe_contract_acceptance(
            "https://daily.example.test",
            "sc_frontend_acceptance",
            declaration(),
            resolution(),
            served_sha=SHA,
            expected_sha=SHA,
            session=session,
        )
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["required_checks"], CONTRACT_CHECKS)
        self.assertEqual(result["not_run_checks"], [])
        self.assertTrue(all(result["checks"].values()))
        self.assertEqual(result["approved_semantic_sha256"], result["recomputed_semantic_sha256"])
        self.assertEqual(result["resolution"]["record_id"], 4242)
        self.assertEqual(result["request"]["params"]["record_id"], 4242)
        self.assertEqual(
            result["request"]["params"]["model"], "project.project"
        )
        self.assertTrue(result["request"]["fingerprint_sha256"])
        self.assertEqual(result["schema_asset"]["sha256"], result["schema_asset"]["declared_schema_sha256"])

    def test_resolved_record_id_drives_the_request_not_a_constant(self):
        first = receipt(res=resolution(record_id=4242))
        second = receipt(res=resolution(record_id=7777))
        self.assertEqual(first["request"]["params"]["record_id"], 4242)
        self.assertEqual(second["request"]["params"]["record_id"], 7777)
        self.assertNotEqual(first["request"]["fingerprint_sha256"], second["request"]["fingerprint_sha256"])

    def test_stale_schema_digest_fails_closed(self):
        contract = example_contract()
        contract["meta"]["lifecycle"]["definition"]["schemaSha256"] = "0b9be5e2" + "0" * 56
        result = receipt(contract=contract)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("contract_schema_digest_not_bound", result["errors"])
        self.assertIs(result["checks"]["contract_schema_digest_bound"], False)

    def test_tampered_semantics_fails_integrity(self):
        contract = example_contract()
        contract["pageInfo"]["pageName"] = "Tampered"
        result = receipt(contract=contract)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("contract_integrity_self_inconsistent", result["errors"])

    def test_contract_target_outside_declared_resolution_fails(self):
        contract = example_contract()
        contract["pageInfo"]["model"] = "res.partner"
        result = receipt(contract=contract)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("request_target_binding_mismatch", result["errors"])

    def test_wrong_role_or_company_fails(self):
        for kwargs, code in (
            ({"role_code": "admin"}, "identity_role_code_mismatch"),
            ({"company_name": "FE Company B"}, "identity_company_mismatch"),
            ({"init_uid": 31}, "identity_actor_uid_mismatch"),
        ):
            with self.subTest(**kwargs):
                session = FakeSession(example_contract(), **kwargs)
                result = MODULE.probe_contract_acceptance(
                    "https://daily.example.test",
                    "sc_frontend_acceptance",
                    declaration(),
                    resolution(),
                    served_sha=SHA,
                    expected_sha=SHA,
                    session=session,
                )
                self.assertEqual(result["status"], "FAIL")
                self.assertIn(code, result["errors"])

    def test_served_sha_drift_fails(self):
        result = MODULE.probe_contract_acceptance(
            "https://daily.example.test",
            "sc_frontend_acceptance",
            declaration(),
            resolution(),
            served_sha="b" * 40,
            expected_sha=SHA,
            session=FakeSession(example_contract()),
        )
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("identity_deployed_sha_mismatch", result["errors"])

    def test_resolution_sha_must_match_the_served_instance(self):
        result = MODULE.probe_contract_acceptance(
            "https://daily.example.test",
            "sc_frontend_acceptance",
            declaration(),
            resolution(sha="c" * 40),
            served_sha=SHA,
            expected_sha=SHA,
            session=FakeSession(example_contract()),
        )
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("record_resolution_served_sha_mismatch", result["errors"])
        self.assertIs(result["checks"]["resolution_unique_target"], False)

    def test_missing_resolution_cannot_pass_or_invent_a_record(self):
        result = receipt(res=None)
        self.assertNotEqual(result["status"], "PASS")
        self.assertIn("record_resolution_unavailable", result["errors"])
        self.assertNotIn("request", result)
        self.assertEqual(result["executed_checks"], [])
        self.assertEqual(result["not_run_checks"], CONTRACT_CHECKS)

    def test_unevaluated_required_check_is_not_run_and_never_a_silent_false(self):
        result = receipt(decl=declaration(required=CONTRACT_CHECKS + ["not_implemented_check"]))
        self.assertNotEqual(result["status"], "PASS")
        self.assertIn("not_implemented_check", result["not_run_checks"])
        self.assertNotIn("not_implemented_check", result["executed_checks"])
        self.assertNotIn("not_implemented_check", result["checks"])
        self.assertNotIn("contract_schema_digest_bound", result["not_run_checks"])

    def test_real_resolution_binds_the_declared_unique_identifier(self):
        result = receipt()
        self.assertTrue(result["checks"]["resolution_unique_target"])
        detail = result["check_detail"]["resolution_unique_target"]
        self.assertEqual(detail["record_xmlid"], detail["stable_identifier"])
        self.assertEqual(detail["matching_resolved_targets"], 1)
        ambiguous = resolution()
        ambiguous["targets"]["duplicate_claim"] = {
            "model": "project.project",
            "record_id": 4242,
            "record_xmlid": "smart_construction_acceptance_fixture.some_other_record",
        }
        rejected = receipt(res=ambiguous)
        self.assertFalse(rejected["checks"]["resolution_unique_target"])
        self.assertIn("record_resolution_not_unique", rejected["errors"])

    def test_foreign_producer_resolution_is_not_unique(self):
        foreign = resolution()
        foreign["producer"] = "scripts/verify/some_other.py"
        rejected = receipt(res=foreign)
        self.assertFalse(rejected["checks"]["resolution_unique_target"])

    def test_malformed_declaration_cannot_pass(self):
        result = receipt(decl=declaration(required=[]))
        self.assertNotEqual(result["status"], "PASS")
        self.assertIn("contract_declaration_required_checks_invalid", result["errors"])


class ContractDeclarationConsumptionTest(unittest.TestCase):
    def test_shipped_declaration_is_consumed_verbatim_and_fully_executed(self):
        loaded, errors = MODULE.load_acceptance_declaration(DECLARATION_PATH)
        self.assertEqual(errors, [])
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["required_checks"], CONTRACT_CHECKS)
        result = MODULE.probe_contract_acceptance(
            "https://daily.example.test",
            "sc_frontend_acceptance",
            loaded,
            resolution(),
            served_sha=SHA,
            expected_sha=SHA,
            session=FakeSession(example_contract()),
        )
        self.assertEqual(result["required_checks"], loaded["required_checks"])
        self.assertEqual(result["not_run_checks"], [])
        self.assertEqual(result["status"], "PASS")

    def test_record_resolution_is_loaded_from_the_governed_producer_shape(self):
        payload = resolution()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "resolution.json"
            path.write_text(json.dumps({"schema": "acceptance.record_identity_resolution.v1",
                                        "producer": RESOLUTION_PRODUCER,
                                        "expected_sha": SHA,
                                        "targets": payload["targets"]}), encoding="utf-8")
            loaded, errors = MODULE.load_record_resolution(path, declaration())
        self.assertEqual(errors, [])
        self.assertEqual(loaded["targets"]["payment_request"]["record_id"], 4242)

    def test_record_resolution_rejects_foreign_producer_and_missing_company(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "resolution.json"
            path.write_text(json.dumps({"schema": "acceptance.record_identity_resolution.v1",
                                        "producer": "scripts/verify/some_other.py",
                                        "expected_sha": SHA,
                                        "targets": {"payment_request": {"model": "project.project"}}}), encoding="utf-8")
            loaded, errors = MODULE.load_record_resolution(path, declaration())
        self.assertIsNone(loaded)
        self.assertIn("record_resolution_producer_mismatch", errors)
        self.assertIn("record_resolution_company_missing", errors)


class ReceiptSchemaGuardTest(unittest.TestCase):
    def run_guard(self, contract_block, report_status="FAIL"):
        with tempfile.TemporaryDirectory() as folder:
            report = {
                "mode": "dev_acceptance_release_probe",
                "status": report_status,
                "db_name": "sc_frontend_acceptance",
                "base_url": "https://daily.example.test",
                "app_env": "acceptance",
                "runtime_identity": {
                    "status": "PASS",
                    "enabled": True,
                    "expected_sha": SHA,
                    "served_sha": SHA,
                    "http_status": 200,
                },
                "backup": {"enabled": False, "status": "PASS"},
                "frontend": {
                    "status": "FAIL",
                    "base_url": "https://daily.example.test",
                    "checks": {},
                    "errors": ["synthetic_frontend_failure"],
                },
                "login": {"enabled": False, "status": "PASS"},
                "contract": contract_block,
            }
            path = Path(folder) / "report.json"
            path.write_text(json.dumps(report), encoding="utf-8")
            env = dict(os.environ, ACCEPTANCE_PROBE_OUTPUT=str(path))
            return subprocess.run(
                [sys.executable, str(ROOT / "scripts/verify/dev_acceptance_release_probe_schema_guard.py")],
                capture_output=True,
                text=True,
                env=env,
                cwd=str(ROOT),
            )

    def test_guard_accepts_a_bound_receipt(self):
        result = receipt()
        completed = self.run_guard(result)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_guard_rejects_receipt_without_executed_checks(self):
        completed = self.run_guard(
            {"enabled": True, "status": "PASS", "required_checks": CONTRACT_CHECKS, "checks": {}, "errors": []}
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("contract.status=PASS requires at least one executed required check", completed.stdout)
        self.assertIn("contract.checks.contract_schema_digest_bound must be true when contract passes", completed.stdout)

    def test_guard_rejects_tampered_snapshot_behind_a_pass_claim(self):
        result = receipt()
        result["snapshot"]["pageInfo"]["pageName"] = "Tampered"
        completed = self.run_guard(result)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("must match the embedded snapshot semantics", completed.stdout)

    def test_guard_rejects_failed_contract_marked_as_aggregate_pass(self):
        result = receipt()
        result["status"] = "FAIL"
        result["errors"] = ["contract_schema_digest_not_bound"]
        result["checks"]["contract_schema_digest_bound"] = False
        completed = self.run_guard(result, report_status="PASS")
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("aggregate status", completed.stdout)


class RuntimeIdentityTest(unittest.TestCase):
    def test_exact_identity_passes(self):
        def requester(_url):
            return 200, json.dumps({"git_sha": SHA, "database": "sc_demo", "frontend_build_sha256": "f" * 64}), {}

        result = MODULE.probe_runtime_identity("https://daily.example.test", "sc_demo", SHA, requester)
        self.assertEqual(result["status"], "PASS")

    def test_sha_and_database_drift_fail(self):
        def requester(_url):
            return 200, json.dumps({"git_sha": "b" * 40, "database": "other"}), {}

        result = MODULE.probe_runtime_identity("https://daily.example.test", "sc_demo", SHA, requester)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("runtime_identity_sha_mismatch", result["errors"])
        self.assertIn("runtime_identity_database_mismatch", result["errors"])

    def test_invalid_expected_sha_fails_before_network(self):
        calls = []
        result = MODULE.probe_runtime_identity("https://daily.example.test", "sc_demo", "short", lambda url: calls.append(url))
        self.assertEqual(result["errors"], ["expected_sha_invalid"])
        self.assertEqual(calls, [])


class CanonicalNavigationTest(unittest.TestCase):
    def probe(self, data):
        class Response:
            status = 200
            def __init__(self, payload): self.payload = payload
            def __enter__(self): return self
            def __exit__(self, *_): pass
            def read(self): return json.dumps(self.payload).encode()
        opener = mock.Mock()
        opener.open.side_effect = [Response({'result': {'uid': 16}}), Response({'ok': True, 'data': data})]
        with mock.patch.object(MODULE.urllib.request, 'build_opener', return_value=opener):
            return MODULE.probe_login('https://daily.example.test', 'sc_demo', 'test-reader', 'synthetic-test-secret', nav_min_actions=1)

    def test_canonical_navigation_ignores_legacy_conflicts(self):
        result = self.probe({'role_surface': {'role_code': 'reader'}, 'navigation': {'nav': [{'name': 'Canonical', 'action_id': 5}]}, 'nav': [{'name': 'Wrong', 'action_id': 8}]})
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['checks']['nav_paths_sample'], ['Canonical'])

    def test_missing_invalid_or_empty_canonical_cannot_fall_back(self):
        for navigation in (None, {}, {'nav': None}, {'nav': {}}, {'nav': []}):
            with self.subTest(navigation=navigation):
                result = self.probe({'role_surface': {'role_code': 'reader'}, 'navigation': navigation, 'nav': [{'name': 'Legacy', 'action_id': 5}], 'menus': [{'name': 'Legacy', 'action_id': 5}]})
                self.assertEqual(result['status'], 'FAIL')
                self.assertEqual(result['checks']['nav_node_count'], 0)

    def test_main_never_sends_credentials_after_identity_failure(self):
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(MODULE.sys, 'argv', ['probe', '--base-url', 'https://daily.example.test', '--db-name', 'sc_demo', '--expected-sha', SHA, '--login', 'reader', '--password', 'synthetic-test-secret', '--output', folder + '/report.json']), mock.patch.object(MODULE, 'probe_runtime_identity', return_value={'status': 'FAIL'}), mock.patch.object(MODULE, 'probe_backup', return_value={'status': 'PASS'}), mock.patch.object(MODULE, 'probe_frontend', return_value={'status': 'PASS'}), mock.patch.object(MODULE, 'probe_login') as login, mock.patch('builtins.print'):
            self.assertEqual(MODULE.main(), 1)
            login.assert_not_called()
            self.assertEqual(json.loads(Path(folder + '/report.json').read_text())['login']['status'], 'NOT_RUN')

    def test_external_readonly_make_entry_preserves_release_head_binding(self):
        source = (ROOT / 'make/dev.mk').read_text()
        release = source.split('verify.dev.acceptance.release:')[1].split('.PHONY:')[0]
        self.assertIn('SC_ACCEPTANCE_EXPECTED_SHA="$$(git rev-parse HEAD)"', release)
        readonly = source.split('.PHONY: verify.daily_dev.acceptance.readonly.probe')[1].split('.PHONY:')[0]
        self.assertIn('--login "$(ACCEPTANCE_LOGIN)" --api-url "$(ACCEPTANCE_BASE_URL)"', readonly)
        self.assertIn('SC_ACCEPTANCE_EXPECTED_SHA="$(ACCEPTANCE_TARGET_SHA)"', readonly)
        self.assertIn('$(DAILY_ACCEPTANCE_NAV_REQUIRED_PATHS)', readonly)
        self.assertIn('dev_acceptance_release_probe_schema_guard.py', readonly)
        self.assertNotIn('$(RUN_ENV)', readonly)
        self.assertIn('ACCEPTANCE_PROBE_OUTPUT := $(DAILY_ACCEPTANCE_PROBE_OUTPUT)', readonly)
        self.assertIn('DAILY_ACCEPTANCE_PROBE_OUTPUT ?= artifacts/backend/daily_dev_acceptance_probe.json', source)

    def test_missing_data_fails_closed(self):
        self.assertIn('canonical_navigation_nav_missing_or_invalid', self.probe(None)['errors'])


if __name__ == "__main__":
    unittest.main()
