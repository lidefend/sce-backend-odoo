#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import hashlib
import json
import os
from pathlib import Path
import re
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
    "contract_custody_bytes_persisted",
]


def contract_output() -> Path:
    """A live byte-custody target outside the repo, as a governed lane would write."""
    return Path(tempfile.mkdtemp(prefix="acceptance-contract-")) / "contract.json"


def resolved_custody_path(receipt_block):
    path = Path(receipt_block["custody"]["response_path"])
    return path if path.is_absolute() else ROOT / path


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
            "op": "action_open",
            "render_profile": "edit",
            "contract_surface": "user",
            "source_mode": "governance_pipeline",
            "view_type": "form",
            "delivery_profile": "full",
            "client_type": "web_pc",
            "context": {"lang": "zh_CN", "tz": "Asia/Shanghai"},
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
            return 200, json.dumps({"ok": True, "data": {"user": self.user, "role_surface": {"role_code": self.role_code}, "record_context": {"request_context": {"company_id": self.user["company_id"]}}}})
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
        contract_output=kwargs.pop("contract_output", None) or contract_output(),
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
            contract_output=contract_output(),
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

    def test_custody_bytes_are_persisted_and_re_derivable_offline(self):
        result = receipt()
        self.assertTrue(result["checks"]["contract_custody_bytes_persisted"])
        custody = result["custody"]
        raw = resolved_custody_path(result).read_bytes()
        self.assertEqual(len(raw), custody["response_bytes"])
        self.assertEqual(hashlib.sha256(raw).hexdigest(), custody["response_sha256"])
        # The persisted bytes, not the re-serialized snapshot, must reconstruct the contract.
        self.assertEqual(json.loads(raw.decode("utf-8"))["data"], result["snapshot"])

    def test_no_contract_output_cannot_claim_byte_custody(self):
        result = MODULE.probe_contract_acceptance(
            "https://daily.example.test",
            "sc_frontend_acceptance",
            declaration(),
            resolution(),
            served_sha=SHA,
            expected_sha=SHA,
            session=FakeSession(example_contract()),
        )
        self.assertEqual(result["status"], "FAIL")
        self.assertIs(result["checks"]["contract_custody_bytes_persisted"], False)
        self.assertIn("contract_custody_bytes_not_persisted", result["errors"])
        self.assertEqual(result["custody"]["response_path"], "")

    def test_resolved_record_id_drives_the_request_not_a_constant(self):
        first = receipt(res=resolution(record_id=4242))
        second = receipt(res=resolution(record_id=7777))
        self.assertEqual(first["request"]["params"]["record_id"], 4242)
        self.assertEqual(second["request"]["params"]["record_id"], 7777)
        self.assertNotEqual(first["request"]["fingerprint_sha256"], second["request"]["fingerprint_sha256"])

    def test_declared_request_context_is_sent_and_recorded_verbatim(self):
        # The sealed digest is a function of the localized projection, so the live
        # request must carry the declared context and the receipt must record it
        # unchanged; otherwise the approved request cannot be replayed verbatim.
        session = FakeSession(example_contract())
        result = receipt(session=session)
        self.assertEqual(result["status"], "PASS")
        sent = [payload for path, payload in session.requests if (payload or {}).get("intent") == "ui.contract.v2"]
        self.assertTrue(sent)
        self.assertEqual(sent[-1]["context"], {"lang": "zh_CN", "tz": "Asia/Shanghai"})
        self.assertEqual(result["request"]["context"], {"lang": "zh_CN", "tz": "Asia/Shanghai"})

    def test_request_context_changes_the_recorded_fingerprint(self):
        # Context is part of the declared request envelope, not ambient session
        # state: two different declared contexts can never share one fingerprint.
        base = receipt()
        other_decl = declaration()
        other_decl["request"]["context"] = {"lang": "en_US", "tz": "Asia/Shanghai"}
        other = receipt(decl=other_decl)
        self.assertNotEqual(base["request"]["fingerprint_sha256"], other["request"]["fingerprint_sha256"])

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
        self.assertEqual(detail["competing_identifiers"], [])
        self.assertEqual(detail["identifier_resolved_pairs"], 1)
        ambiguous = resolution()
        ambiguous["targets"]["duplicate_claim"] = {
            "model": "project.project",
            "record_id": 4242,
            "record_xmlid": "smart_construction_acceptance_fixture.some_other_record",
        }
        rejected = receipt(res=ambiguous)
        self.assertFalse(rejected["checks"]["resolution_unique_target"])
        self.assertIn("record_resolution_not_unique", rejected["errors"])

    def test_governed_aliases_of_one_record_are_not_ambiguous(self):
        # The shipped producer exposes the same payment request under the
        # payment_request target key and its journey_request alias, so the
        # receipt must be unique on the resolved identity, not on the alias count.
        aliased = resolution()
        aliased["targets"]["journey_request"] = dict(aliased["targets"]["payment_request"])
        result = receipt(res=aliased)
        self.assertTrue(result["checks"]["resolution_unique_target"])
        detail = result["check_detail"]["resolution_unique_target"]
        self.assertEqual(detail["matching_resolved_targets"], 2)
        self.assertEqual(detail["distinct_claiming_identifiers"], 1)
        self.assertEqual(detail["competing_identifiers"], [])
        self.assertEqual(detail["identifier_resolved_pairs"], 1)

    def test_one_identifier_spread_over_two_records_is_not_unique(self):
        spread = resolution()
        spread["targets"]["foreign_alias"] = {
            "model": "project.project",
            "record_id": 9999,
            "record_xmlid": "smart_construction_acceptance_fixture.fe_delivery_hardening_payment_request_a",
        }
        rejected = receipt(res=spread)
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

    def test_declaration_without_request_context_is_refused(self):
        for dropped in (None, {}, {"lang": "zh_CN"}):
            decl = declaration()
            if dropped is None:
                decl["request"].pop("context", None)
            else:
                decl["request"]["context"] = dropped
            errors = MODULE.validate_acceptance_declaration(decl)
            self.assertIn("contract_declaration_request_context_invalid", errors)
            loaded, load_errors = MODULE.load_acceptance_declaration(
                self._declaration_path(decl)
            )
            self.assertIsNone(loaded)
            self.assertIn("contract_declaration_request_context_invalid", load_errors)

    def _declaration_path(self, decl):
        folder = Path(tempfile.mkdtemp(prefix="acceptance-declaration-"))
        path = folder / "declaration.json"
        path.write_text(json.dumps(decl), encoding="utf-8")
        return path


    def test_declaration_without_negotiated_request_shape_is_refused(self):
        # The approved request has to be a request shape the released record page
        # actually issues; an unstated or unknown negotiation parameter is a
        # declaration defect, not a value the probe may invent.
        for dropped in ("op", "render_profile", "contract_surface", "source_mode"):
            decl = declaration()
            decl["request"].pop(dropped, None)
            self.assertIn(
                "contract_declaration_request_negotiation_invalid",
                MODULE.validate_acceptance_declaration(decl),
            )
        unknown = declaration()
        unknown["request"]["op"] = "read"
        self.assertIn(
            "contract_declaration_request_negotiation_invalid",
            MODULE.validate_acceptance_declaration(unknown),
        )


class ParamsContextBindingTest(unittest.TestCase):
    """The approved instance must be the request the released record page issues.

    The page (frontend/apps/web/src/api/intents.ts, withCurrentRecordContext)
    replays the runtime-declared ``system.init.record_context.request_context``
    into ``params.context``, and the sealed contract echoes that business
    context, so the approved request has to carry it too. These cases lock the
    declaration's ``params_context_from`` binding to the probe's actual request
    shape: a declared source is consumed verbatim, an unresolvable source fails
    closed before any browser is launched, and a half-set binding is refused.
    """

    def _session(self, record_context):
        session = FakeSession(example_contract())
        base_post = session.post

        def post(path, payload):
            session.requests.append((path, payload))
            if (payload or {}).get("intent") == "system.init":
                data = {"user": session.user, "role_surface": {"role_code": session.role_code}}
                if record_context is not None:
                    data["record_context"] = record_context
                return 200, json.dumps({"ok": True, "data": data})
            if path.startswith("/web/session/authenticate"):
                return base_post(path, payload)
            if (payload or {}).get("intent") == "ui.contract.v2":
                return 200, json.dumps({"ok": True, "data": session.contract})
            return base_post(path, payload)

        session.post = post
        return session

    def _declaration_with_bound_context(self):
        decl = declaration()
        decl["request"]["params_context_from"] = "system.init.record_context.request_context"
        return decl

    def test_declared_runtime_record_context_is_sent_verbatim(self):
        runtime_context = {"company_id": 8}
        session = self._session({"request_context": runtime_context})
        result = MODULE.probe_contract_acceptance(
            "https://daily.example.test",
            "sc_frontend_acceptance",
            self._declaration_with_bound_context(),
            resolution(),
            served_sha=SHA,
            expected_sha=SHA,
            session=session,
            contract_output=contract_output(),
        )
        sent = [payload for path, payload in session.requests if (payload or {}).get("intent") == "ui.contract.v2"]
        self.assertTrue(sent)
        self.assertEqual(sent[-1]["params"]["context"], runtime_context)
        self.assertEqual(result["request"]["params"]["context"], runtime_context)
        self.assertEqual(result["status"], "PASS")

    def test_unavailable_declared_source_fails_closed_without_sending_the_request(self):
        session = self._session(None)
        result = MODULE.probe_contract_acceptance(
            "https://daily.example.test",
            "sc_frontend_acceptance",
            self._declaration_with_bound_context(),
            resolution(),
            served_sha=SHA,
            expected_sha=SHA,
            session=session,
            contract_output=contract_output(),
        )
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("contract_request_context_source_unavailable", result["errors"])
        self.assertFalse([payload for path, payload in session.requests if (payload or {}).get("intent") == "ui.contract.v2"])

    def test_non_mapping_declared_source_fails_closed(self):
        session = self._session({"request_context": "8"})
        result = MODULE.probe_contract_acceptance(
            "https://daily.example.test",
            "sc_frontend_acceptance",
            self._declaration_with_bound_context(),
            resolution(),
            served_sha=SHA,
            expected_sha=SHA,
            session=session,
            contract_output=contract_output(),
        )
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("contract_request_context_source_unavailable", result["errors"])

    def test_empty_declared_source_is_refused_by_the_shape_check(self):
        decl = declaration()
        decl["request"]["params_context_from"] = "   "
        self.assertIn("contract_declaration_request_context_source_invalid", MODULE.validate_acceptance_declaration(decl))

    def test_shipped_declarations_bind_the_runtime_record_context_path(self):
        for name in ("backend_contract_instance_v1.json", "backend_contract_instance_daily_v1.json"):
            with self.subTest(declaration=name):
                shipped = json.loads((ROOT / "config/acceptance" / name).read_text(encoding="utf-8"))
                declared = shipped["request"].get("params_context_from")
                self.assertEqual(declared, "system.init.record_context.request_context")
                self.assertEqual(MODULE.validate_acceptance_declaration(shipped), [])
                runtime_context = {"company_id": 21}
                # The declaration names the producing intent (system.init) plus the path
                # inside its payload, exactly as the probe consumes it.
                resolved = MODULE.resolve_declared_record_context(
                    declared, {"system.init": {"record_context": {"request_context": runtime_context}}}
                )
                self.assertEqual(resolved, runtime_context)
                params = MODULE.build_contract_request_params(shipped["request"], {"model": "payment.request", "record_id": 1}, resolved)
                self.assertEqual(params["context"], runtime_context)

    def test_shipped_declarations_consume_the_canonical_client_capabilities(self):
        client_source = (
            ROOT / "frontend/apps/web/src/app/contracts/v2/clientCapabilities.ts"
        ).read_text(encoding="utf-8")
        match = re.search(
            r"CONTRACT_V2_CLIENT_CAPABILITIES\s*=\s*\[(.*?)\]\s*as const",
            client_source,
            re.DOTALL,
        )
        self.assertIsNotNone(match)
        expected = re.findall(r"'([^']+)'", match.group(1))
        self.assertEqual(len(expected), 9)
        for name in ("backend_contract_instance_v1.json", "backend_contract_instance_daily_v1.json"):
            shipped = json.loads((ROOT / "config/acceptance" / name).read_text(encoding="utf-8"))
            self.assertEqual(shipped["request"]["client_contract_capabilities"], expected, name)

    def test_declaration_without_the_binding_keeps_the_declared_shape(self):
        # No binding declared: the runtime-declared record context is not injected,
        # so the approved request stays exactly the declared shape.
        session = self._session({"request_context": {"company_id": 8}})
        result = MODULE.probe_contract_acceptance(
            "https://daily.example.test",
            "sc_frontend_acceptance",
            declaration(),
            resolution(),
            served_sha=SHA,
            expected_sha=SHA,
            session=session,
            contract_output=contract_output(),
        )
        self.assertNotIn("context", result["request"]["params"])


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
            contract_output=contract_output(),
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

    def test_guard_rejects_pass_without_recorded_request_context(self):
        # A passing receipt whose recorded request drops the localized context
        # could not be replayed verbatim; the guard must refuse it.
        result = receipt()
        result["request"].pop("context", None)
        completed = self.run_guard(result)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("contract.request.context must record lang and tz when contract passes", completed.stdout)

    def test_guard_rejects_tampered_snapshot_behind_a_pass_claim(self):
        result = receipt()
        result["snapshot"]["pageInfo"]["pageName"] = "Tampered"
        completed = self.run_guard(result)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("must match the embedded snapshot semantics", completed.stdout)

    def test_guard_baseline_accepts_untampered_custody(self):
        # Negative-first: prove the persisted-bytes control passes before injection,
        # so a later failure can only be attributed to the injected change.
        result = receipt()
        baseline = self.run_guard(result)
        self.assertEqual(baseline.returncode, 0, baseline.stdout + baseline.stderr)

        tampered_bytes = resolved_custody_path(result).read_bytes().replace(b'"pageName"', b'"pageNam3"', 1)
        resolved_custody_path(result).write_bytes(tampered_bytes)
        mutated = self.run_guard(result)
        self.assertNotEqual(mutated.returncode, 0)
        self.assertIn("response_sha256 must equal the persisted byte digest", mutated.stdout)

    def test_guard_rejects_custody_bytes_that_are_not_persisted(self):
        result = receipt()
        resolved_custody_path(result).unlink()
        completed = self.run_guard(result)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("response_path must resolve to an existing file", completed.stdout)

    def test_guard_rejects_declared_byte_length_drift(self):
        result = receipt()
        result["custody"]["response_bytes"] = result["custody"]["response_bytes"] + 1
        completed = self.run_guard(result)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("response_bytes must equal the persisted byte length", completed.stdout)

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


class EntryBoundContractSessionTest(unittest.TestCase):
    def test_root_and_prefixed_entries_use_intent_without_database_hints(self):
        for base in ('https://example.test', 'https://example.test/t/demo'):
            session = MODULE._HttpSession(base, 'synthetic_db')
            body = json.dumps({'ok': True, 'data': {'session': {'token': 'synthetic-token'}, 'user': {'id': 7}}})
            with mock.patch.object(session, 'post', return_value=(200, body)) as post:
                status, result = session.login('reader', 'synthetic')
            self.assertEqual(status, 200)
            self.assertEqual(post.call_args.args[0], '/api/v1/intent')
            self.assertNotIn('db', post.call_args.args[1]['params'])
            self.assertEqual(session._headers(), {'Content-Type': 'application/json', 'Authorization': 'Bearer synthetic-token'})
            self.assertEqual(json.loads(result)['result']['uid'], 7)

    def test_contract_only_stops_before_auth_on_bad_runtime(self):
        with tempfile.TemporaryDirectory() as folder, \
             mock.patch.object(MODULE.sys, 'argv', ['probe', '--contract-only', '--base-url', 'https://example.test', '--db-name', 'synthetic', '--expected-sha', SHA, '--output', folder+'/receipt.json']), \
             mock.patch.object(MODULE, 'probe_runtime_identity', return_value={'status': 'FAIL'}), \
             mock.patch.object(MODULE, 'probe_contract_acceptance') as contract, \
             mock.patch.object(MODULE, 'probe_frontend') as frontend, \
             mock.patch.object(MODULE, 'probe_login') as login, mock.patch('builtins.print'):
            self.assertEqual(MODULE.main(), 1)
            contract.assert_not_called(); frontend.assert_not_called(); login.assert_not_called()
            self.assertEqual(json.loads(Path(folder+'/receipt.json').read_text())['status'], 'FAIL')

    def test_contract_only_never_implies_release_or_navigation_pass(self):
        for status in ('PASS', 'FAIL'):
            with tempfile.TemporaryDirectory() as folder, \
                 mock.patch.object(MODULE.sys, 'argv', ['probe', '--contract-only', '--base-url', 'https://example.test', '--db-name', 'synthetic', '--expected-sha', SHA, '--output', folder+'/receipt.json', '--contract-output', folder+'/explicit-contract.json']), \
                 mock.patch.object(MODULE, 'probe_runtime_identity', return_value={'status': 'PASS', 'served_sha': SHA}), \
                 mock.patch.object(MODULE, 'probe_contract_acceptance', return_value={'status': status}) as contract, \
                 mock.patch.object(MODULE, 'probe_frontend') as frontend, \
                 mock.patch.object(MODULE, 'probe_login') as login, mock.patch('builtins.print'):
                self.assertEqual(MODULE.main(), 0 if status == 'PASS' else 1)
                self.assertEqual(json.loads(Path(folder+'/receipt.json').read_text()), {'status': status})
                self.assertEqual(contract.call_args.kwargs['expected_sha'], SHA)
                self.assertEqual(contract.call_args.kwargs['contract_output'], Path(folder)/'explicit-contract.json')
                frontend.assert_not_called(); login.assert_not_called()


class NamespaceEntryProbeTest(unittest.TestCase):
    """Batch C: the path prefix is the only database selector."""

    BASE = "http://daily.example.test/t/demo"

    def test_entry_namespace_detection(self):
        self.assertEqual(MODULE.entry_namespace(self.BASE), "demo")
        self.assertEqual(MODULE.entry_namespace(self.BASE + "/"), "demo")
        self.assertEqual(MODULE.entry_namespace("https://daily.example.test/platform-admin"), "platform")
        self.assertEqual(MODULE.entry_namespace("https://daily.example.test"), "")

    def test_frontend_has_no_embedded_db_and_asserts_explicit_refusals(self):
        seen = []

        def requester(url, method="GET", data=None, headers=None, cookie_jar=None, timeout=20):
            seen.append((url, method, dict(headers or {})))
            if url.endswith("/t/demo/"):
                return 200, '<script type="module" src="/assets/index-test.js"></script>', {"Content-Type": "text/html"}
            if url.endswith("/assets/index-test.js"):
                return 200, 'const APP_ENV="dev".trim()||"default"', {}
            if "?db=" in url:
                return 409, '{"error":"NS_DATABASE_HINT_CONFLICT"}', {}
            if headers and "X-Odoo-DB" in headers:
                return 409, '{"error":"NS_DATABASE_HINT_CONFLICT"}', {}
            if url.endswith("/t/demo/api/v1/intent"):
                return (204, "", {}) if method == "OPTIONS" else (405, "", {})
            if url == "http://daily.example.test/api/v1/intent":
                return 400, '{"error":"NS_NAMESPACE_REQUIRED"}', {}
            if "namespace-probe-unknown" in url:
                return 404, '{"error":"NS_UNKNOWN_NAMESPACE"}', {}
            return 500, "", {}

        with mock.patch.object(MODULE, "http_request", side_effect=requester):
            result = MODULE.probe_frontend(self.BASE, "sc_demo", "dev", "sc_prod_sim")

        self.assertEqual(result["status"], "PASS", result)
        self.assertFalse(result["checks"]["asset_has_db"])
        self.assertEqual(result["checks"]["db_query_conflict_status"], 409)
        self.assertEqual(result["checks"]["db_header_conflict_status"], 409)
        self.assertEqual(result["checks"]["missing_namespace_status"], 400)
        self.assertEqual(result["checks"]["unknown_namespace_status"], 404)
        clean_calls = [row for row in seen if row[0] == self.BASE + "/api/v1/intent" and not row[2]]
        self.assertEqual(len(clean_calls), 2, clean_calls)
        self.assertEqual(sorted(row[1] for row in clean_calls), ["GET", "OPTIONS"])

    def test_namespace_login_uses_login_intent_and_binds_session_database(self):
        class Response:
            status = 200

            def __init__(self, payload):
                self.payload = payload

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return None

            def read(self):
                return json.dumps(self.payload).encode()

        opener = mock.Mock()
        opener.open.side_effect = [
            Response(
                {
                    "ok": True,
                    "data": {
                        "session": {"token": "token", "db": "sc_demo", "entry_kind": "tenant"},
                        "user": {"id": 16, "name": "Reader"},
                    },
                }
            ),
            Response(
                {
                    "ok": True,
                    "data": {
                        "role_surface": {"role_code": "reader"},
                        "navigation": {"nav": [{"name": "Canonical", "action_id": 5}]},
                    },
                }
            ),
        ]
        with mock.patch.object(MODULE.urllib.request, "build_opener", return_value=opener):
            result = MODULE.probe_login(self.BASE, "sc_demo", "test-reader", "synthetic-test-secret", nav_min_actions=1)

        self.assertEqual(result["status"], "PASS", result)
        self.assertEqual(result["checks"]["session_database"], "sc_demo")
        requests = [call.args[0] for call in opener.open.call_args_list]
        self.assertTrue(requests[0].full_url.endswith("/t/demo/api/v1/intent"))
        login_payload = json.loads(requests[0].data.decode())
        self.assertEqual(login_payload["intent"], "login")
        self.assertNotIn("db", login_payload["params"])
        self.assertEqual(requests[1].get_header("Authorization"), "Bearer token")
        self.assertIsNone(requests[1].get_header("X-odoo-db"))

    def test_namespace_login_database_drift_fails(self):
        class Response:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return None

            def read(self):
                return json.dumps(
                    {
                        "ok": True,
                        "data": {
                            "session": {"token": "token", "db": "sc_other", "entry_kind": "tenant"},
                            "user": {"id": 16, "name": "Reader"},
                        },
                    }
                ).encode()

        opener = mock.Mock()
        opener.open.return_value = Response()
        with mock.patch.object(MODULE.urllib.request, "build_opener", return_value=opener):
            result = MODULE.probe_login(self.BASE, "sc_demo", "test-reader", "synthetic-test-secret")

        self.assertEqual(result["status"], "FAIL")
        self.assertIn("login_session_database_mismatch", result["errors"])


class DailyAcceptanceLaneSelfConsistencyTest(unittest.TestCase):
    """The daily publication lane quotes the governed release probe artifact."""

    def test_daily_publication_keeps_the_governed_probe_artifact(self):
        source = (ROOT / 'make/dev.mk').read_text()
        publish = source.split('release.daily_dev.acceptance.publish:')[1].split(
            'release.daily_product_navigation.snapshot')[0]
        self.assertNotIn('ACCEPTANCE_PROBE_OUTPUT', publish)
        self.assertIn('ACCEPTANCE_PROBE_OUTPUT ?= artifacts/backend/dev_acceptance_release_probe.json', source)
        readonly = source.split('.PHONY: verify.daily_dev.acceptance.readonly.probe')[1].split('.PHONY:')[0]
        self.assertIn('ACCEPTANCE_PROBE_OUTPUT := $(DAILY_ACCEPTANCE_PROBE_OUTPUT)', readonly)

    def test_guards_bind_the_same_release_probe_artifact(self):
        env_guard = (ROOT / 'scripts/verify/daily_dev_acceptance_env_guard.py').read_text()
        self.assertIn('"ACCEPTANCE_PROBE_OUTPUT": "artifacts/backend/dev_acceptance_release_probe.json"', env_guard)
        topology = (ROOT / 'scripts/verify/environment_topology_guard.py').read_text()
        self.assertIn('ACCEPTANCE_PROBE_OUTPUT=artifacts/backend/dev_acceptance_release_probe.json', topology)

    def test_topology_guard_token_matches_the_shipped_prerequisite_list(self):
        source = (ROOT / 'make/dev.mk').read_text()
        header = source.split('release.daily_dev.acceptance.publish: guard.prod.forbid')[1].split('\n')[0]
        self.assertIn('daily.runtime.entry.verify', header)
        self.assertIn('verify.daily_dev.acceptance.formal_surface', header)
        self.assertIn('verify.daily_dev.acceptance.release', header)
        self.assertNotIn('release.dev.acceptance.publish', header)
        self.assertNotIn('verify.frontend.build', header)
        topology = (ROOT / 'scripts/verify/environment_topology_guard.py').read_text()
        self.assertIn(
            'release.daily_dev.acceptance.publish: guard.prod.forbid verify.daily_dev.acceptance.env.guard '
            'env.matrix.check verify.daily_dev.runtime_repo.clean verify.daily_dev.product_menu_release_gate.guard '
            'daily.runtime.entry.verify verify.daily_dev.acceptance.formal_surface '
            'verify.daily_dev.acceptance.release',
            topology,
        )

    def test_daily_formal_surface_uses_the_declared_serving_duty(self):
        source = (ROOT / 'make/dev.mk').read_text()
        target = source.split('verify.daily_dev.acceptance.formal_surface:', 1)[1].split(
            'verify.daily_dev.acceptance.release:', 1
        )[0]
        self.assertIn('scripts/ops/daily_runtime_duty_odoo_shell.py', target)
        self.assertIn('--duty "$(DAILY_ACCEPTANCE_BUSINESS_DUTY)"', target)
        self.assertNotIn('odoo_shell_exec.sh', target)
        self.assertNotIn('check-compose-project', target)
        self.assertNotIn('verify.frontend.build', target)
        self.assertNotIn('formal_entry_metadata_audit.py', target)
        self.assertNotIn('engineering_progress_income_visible_contract_audit.py', target)

    def test_daily_business_duty_and_database_come_from_the_entry_declaration(self):
        source = (ROOT / 'make/dev.mk').read_text()
        self.assertIn(
            '"config/ops/daily_runtime_entry.v1.json"',
            source.split('DAILY_ACCEPTANCE_BUSINESS_DUTY ?=', 1)[1].split('\n', 1)[0],
        )
        self.assertIn(
            '"config/ops/daily_runtime_database_duties.v1.json"',
            source.split('DAILY_DEV_ACCEPTANCE_DB ?=', 1)[1].split('\n', 1)[0],
        )


if __name__ == "__main__":
    unittest.main()
