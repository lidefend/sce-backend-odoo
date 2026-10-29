from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from scripts.ops.candidate_acceptance_profile import (
    ENVIRONMENTS,
    TOOL_MATRIX,
    CandidateProfileError,
    carrier_provision_command,
    provision_apply,
    provision_plan,
    resolve_candidate_profile,
    validate_candidate_sha,
)


SHA = "0ad215d5b636010e02413a04b49e13c64d9d6a92"


class CandidateProfileTest(unittest.TestCase):
    def test_resolves_valid_candidate_profile(self):
        resolved = resolve_candidate_profile()
        self.assertEqual(resolved["profile"], "candidate")
        self.assertEqual(resolved["resource_contract"]["compose_project"], "sc-fe-candidate-770")
        self.assertNotEqual(resolved["resource_contract"]["database"], "sc_frontend_acceptance")
        self.assertIn("sc_frontend_acceptance", resolved["isolation_guard"]["never_target"])

    def test_rejects_external_override_to_managed(self):
        data = copy.deepcopy(json.loads(ENVIRONMENTS.read_text()))
        data["profiles"]["candidate"]["target_mode"] = "managed"
        with tempfile.NamedTemporaryFile("w", suffix=".json") as handle:
            json.dump(data, handle)
            handle.flush()
            with self.assertRaises(CandidateProfileError):
                resolve_candidate_profile(environments_path=Path(handle.name), tool_matrix_path=TOOL_MATRIX)

    def test_rejects_shared_database(self):
        data = copy.deepcopy(json.loads(ENVIRONMENTS.read_text()))
        data["profiles"]["candidate"]["resource_contract"]["database"] = "sc_frontend_acceptance"
        with tempfile.NamedTemporaryFile("w", suffix=".json") as handle:
            json.dump(data, handle)
            handle.flush()
            with self.assertRaises(CandidateProfileError):
                resolve_candidate_profile(environments_path=Path(handle.name), tool_matrix_path=TOOL_MATRIX)

    def test_rejects_shared_compose_project(self):
        data = copy.deepcopy(json.loads(ENVIRONMENTS.read_text()))
        data["profiles"]["candidate"]["resource_contract"]["compose_project"] = "sc-fe-r2-p1-01"
        with tempfile.NamedTemporaryFile("w", suffix=".json") as handle:
            json.dump(data, handle)
            handle.flush()
            with self.assertRaises(CandidateProfileError):
                resolve_candidate_profile(environments_path=Path(handle.name), tool_matrix_path=TOOL_MATRIX)

    def test_rejects_shared_volume(self):
        data = copy.deepcopy(json.loads(ENVIRONMENTS.read_text()))
        data["profiles"]["candidate"]["resource_contract"]["volumes"]["database"] = "sc_fe_r2_p1_01_db"
        with tempfile.NamedTemporaryFile("w", suffix=".json") as handle:
            json.dump(data, handle)
            handle.flush()
            with self.assertRaises(CandidateProfileError):
                resolve_candidate_profile(environments_path=Path(handle.name), tool_matrix_path=TOOL_MATRIX)

    def test_rejects_shared_frontend_port(self):
        data = copy.deepcopy(json.loads(ENVIRONMENTS.read_text()))
        data["profiles"]["candidate"]["resource_contract"]["services"]["frontend_port"] = 5175
        with tempfile.NamedTemporaryFile("w", suffix=".json") as handle:
            json.dump(data, handle)
            handle.flush()
            with self.assertRaises(CandidateProfileError):
                resolve_candidate_profile(environments_path=Path(handle.name), tool_matrix_path=TOOL_MATRIX)

    def test_sha_must_be_full(self):
        with self.assertRaises(CandidateProfileError):
            validate_candidate_sha("0ad215d5")

    def test_plan_does_not_create_resources(self):
        plan = provision_plan(SHA)
        self.assertEqual(plan["candidate_sha"], SHA)
        self.assertFalse(plan["creates_resources"])
        self.assertIn("sc_frontend_acceptance", plan["shared_resources_forbidden"])

    def test_apply_refuses_without_confirmation(self):
        with self.assertRaises(CandidateProfileError):
            provision_apply(SHA, "", None)

    def test_apply_refuses_without_registration(self):
        with self.assertRaises(CandidateProfileError):
            provision_apply(SHA, "PROVISION_ISOLATED_CANDIDATE_ACCEPTANCE", None)

    def test_apply_refuses_on_head_mismatch(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json") as handle:
            json.dump({"registered": True}, handle)
            handle.flush()
            with self.assertRaises(CandidateProfileError):
                provision_apply(SHA, "PROVISION_ISOLATED_CANDIDATE_ACCEPTANCE", Path(handle.name))

    def test_rejects_managed_runtime_mismatch(self):
        data = copy.deepcopy(json.loads(ENVIRONMENTS.read_text()))
        data["profiles"]["candidate"]["managed_runtime"]["compose_project"] = "sc-fe-r2-p1-01"
        with tempfile.NamedTemporaryFile("w", suffix=".json") as handle:
            json.dump(data, handle)
            handle.flush()
            with self.assertRaises(CandidateProfileError):
                resolve_candidate_profile(environments_path=Path(handle.name), tool_matrix_path=TOOL_MATRIX)

    def test_rejects_base_url_mismatch(self):
        data = copy.deepcopy(json.loads(ENVIRONMENTS.read_text()))
        data["profiles"]["candidate"]["base_url"] = "http://127.0.0.1:5175"
        with tempfile.NamedTemporaryFile("w", suffix=".json") as handle:
            json.dump(data, handle)
            handle.flush()
            with self.assertRaises(CandidateProfileError):
                resolve_candidate_profile(environments_path=Path(handle.name), tool_matrix_path=TOOL_MATRIX)

    def test_carrier_provision_command(self):
        self.assertEqual(
            carrier_provision_command(),
            ["make", "acceptance.runtime.carrier.provision"],
        )


if __name__ == "__main__":
    unittest.main()
