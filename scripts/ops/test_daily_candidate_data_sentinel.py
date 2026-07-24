#!/usr/bin/env python3
from __future__ import annotations

import copy
import importlib.util
import json
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
OPS = ROOT / "scripts/ops"
sys.path.insert(0, str(OPS))
SPEC = importlib.util.spec_from_file_location(
    "daily_candidate_data_sentinel",
    OPS / "daily_candidate_data_sentinel.py",
)
assert SPEC and SPEC.loader
SENTINEL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SENTINEL)
CONTRACT_PATH = OPS / "daily_candidate_data_sentinel_contract_v1.json"


def capture_fixture() -> dict:
    return {
        "database_uuid": "uuid",
        "model_mappings": {
            "project.project": {
                "status": "MODEL_PRESENT",
                "table_present": True,
                "replacement_model": None,
            }
        },
        "companies": [
            {"id": 1, "partner_id": 1, "currency_id": 1, "active": True}
        ],
        "installed_core_modules": [{"module": "base", "version": "1"}],
        "aggregates": {
            "project.project": {
                "record_count": 10,
                "null_required_fields": {"company_id": 0},
                "write_date_max": "before",
            }
        },
        "samples": {
            "project.project": [
                {
                    "id": 1,
                    "company_id": 1,
                    "active": True,
                    "direct_attachment_count": 1,
                }
            ]
        },
        "relationships": {"project_project.company_id->res_company.id": 0},
        "attachments": {
            "filestore": {
                "missing_file_count": 0,
                "unreadable_file_count": 0,
                "readable_sample_attachment_ids": [10],
            }
        },
    }


class ContractTests(unittest.TestCase):
    def test_fixed_contract_loads_and_unknown_origin_is_protected(self):
        contract = SENTINEL._load_contract(CONTRACT_PATH)
        self.assertEqual(
            contract["environment"]["database_uuid"],
            "c838b4b6-4cd6-11f1-9590-82245e4e7b62",
        )
        self.assertFalse(
            contract["classification"]["unknown_origin_delete_allowed"]
        )

    def test_unknown_database_uuid_is_rejected(self):
        payload = json.loads(CONTRACT_PATH.read_text())
        payload["environment"]["database_uuid"] = "unknown"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "contract.json"
            path.write_text(json.dumps(payload))
            with self.assertRaisesRegex(SENTINEL.SentinelError, "database_uuid"):
                SENTINEL._load_contract(path)

    def test_model_absent_and_replaced_semantics_are_versioned(self):
        contract = SENTINEL._load_contract(CONTRACT_PATH)
        statuses = {row["expected"] for row in contract["models"]}
        self.assertEqual(
            statuses, {"MODEL_PRESENT", "MODEL_ABSENT", "MODEL_REPLACED_BY"}
        )

    def test_snapshot_sql_is_read_only_repeatable_and_bounded(self):
        contract = SENTINEL._load_contract(CONTRACT_PATH)
        columns = {}
        mapping = {}
        for row in contract["models"]:
            mapping[row["model"]] = {"status": row["expected"]}
            if row["expected"] == "MODEL_PRESENT":
                columns[row["table"]] = {
                    "id",
                    "create_date",
                    "write_date",
                    *row.get("required_fields", []),
                    *row.get("sample_fields", []),
                    *row.get("amount_fields", []),
                }
        sql = SENTINEL._build_snapshot_sql(contract, columns, mapping)
        self.assertIn("REPEATABLE READ READ ONLY", sql)
        self.assertIn("SET LOCAL statement_timeout='30s'", sql)
        self.assertIn("SET LOCAL lock_timeout='1s'", sql)
        self.assertTrue(sql.rstrip().endswith("ROLLBACK;"))
        self.assertNotIn("CREATE TABLE", sql)
        self.assertNotIn("INSERT INTO", sql)
        self.assertNotIn("UPDATE ", sql)
        self.assertNotIn("DELETE FROM", sql)

    def test_sample_selection_is_deterministic(self):
        contract = SENTINEL._load_contract(CONTRACT_PATH)
        model = next(
            row for row in contract["models"] if row["model"] == "project.project"
        )
        sql = SENTINEL._sample_sql(model)
        self.assertIn("row_number() OVER", sql)
        self.assertIn("attachment_score DESC", sql)
        self.assertIn("relationship_score DESC", sql)
        self.assertNotIn("random()", sql)

    def test_all_sample_order_constants_are_typed_not_positions(self):
        contract = SENTINEL._load_contract(CONTRACT_PATH)
        for model in contract["models"]:
            sql = SENTINEL._sample_sql(model)
            if sql:
                self.assertNotIn("ORDER BY 0,", sql, model["model"])
                self.assertNotIn("PARTITION BY 0,", sql, model["model"])

    def test_sensitive_output_key_is_rejected(self):
        contract = SENTINEL._load_contract(CONTRACT_PATH)
        with self.assertRaisesRegex(SENTINEL.SentinelError, "sensitive"):
            SENTINEL._assert_no_sensitive_output(
                contract, {"records": [{"login": "redacted-is-still-forbidden"}]}
            )

    def test_atomic_evidence_mode_is_0600(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "sentinels"
            root.mkdir(mode=0o700)
            target = root / "capture.json"
            digest = SENTINEL._atomic_write(target, {"pass": True})
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)
            self.assertEqual(len(digest), 64)


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.contract = SENTINEL._load_contract(CONTRACT_PATH)
        self.baseline = capture_fixture()

    def compare(self, candidate, **kwargs):
        return SENTINEL.compare(
            self.contract, self.baseline, candidate, **kwargs
        )

    def test_identical_capture_passes(self):
        self.assertTrue(self.compare(copy.deepcopy(self.baseline))["pass"])

    def test_fixed_sample_missing_fails(self):
        candidate = copy.deepcopy(self.baseline)
        candidate["samples"]["project.project"] = []
        result = self.compare(candidate)
        self.assertIn(
            "FIXED_SAMPLE_MISSING:project.project:1", result["failures"]
        )

    def test_relationship_change_fails(self):
        candidate = copy.deepcopy(self.baseline)
        candidate["samples"]["project.project"][0]["company_id"] = 2
        result = self.compare(candidate)
        self.assertTrue(
            any(item.startswith("FIXED_SAMPLE_RELATION_CHANGED") for item in result["failures"])
        )

    def test_attachment_missing_increase_fails(self):
        candidate = copy.deepcopy(self.baseline)
        candidate["attachments"]["filestore"]["missing_file_count"] = 1
        self.assertIn(
            "ATTACHMENT_MISSING_COUNT_INCREASED",
            self.compare(candidate)["failures"],
        )

    def test_orphan_increase_fails(self):
        candidate = copy.deepcopy(self.baseline)
        candidate["relationships"][
            "project_project.company_id->res_company.id"
        ] = 1
        self.assertTrue(
            any(item.startswith("ORPHAN_COUNT_INCREASED") for item in self.compare(candidate)["failures"])
        )

    def test_normal_record_addition_warns_but_passes(self):
        candidate = copy.deepcopy(self.baseline)
        candidate["aggregates"]["project.project"]["record_count"] = 11
        result = self.compare(candidate)
        self.assertTrue(result["pass"])
        self.assertIn(
            "RECORD_COUNT_INCREASED:project.project", result["warnings"]
        )

    def test_write_date_drift_is_ignored(self):
        candidate = copy.deepcopy(self.baseline)
        candidate["aggregates"]["project.project"]["write_date_max"] = "after"
        self.assertTrue(self.compare(candidate)["pass"])

    def test_restore_snapshot_count_difference_is_warning(self):
        candidate = copy.deepcopy(self.baseline)
        candidate["aggregates"]["project.project"]["record_count"] = 9
        result = self.compare(candidate, restore_equivalence=True)
        self.assertTrue(result["pass"])
        self.assertTrue(
            any(item.startswith("RESTORE_SNAPSHOT_PRECEDES_BASELINE") for item in result["warnings"])
        )

    def test_verify_requires_confirmation_before_runtime_access(self):
        with (
            mock.patch.dict("os.environ", {}, clear=True),
            mock.patch.object(SENTINEL, "_runtime_identity") as runtime,
        ):
            with self.assertRaisesRegex(SENTINEL.SentinelError, "confirmation"):
                SENTINEL.verify(
                    self.contract,
                    Path(
                        self.contract["environment"]["continuity_backup_root"]
                    ),
                )
        runtime.assert_not_called()

    def test_make_temp_cleanup_requires_exact_scoped_path(self):
        makefile = (ROOT / "make/daily_candidate.mk").read_text()
        target = makefile.split(
            "daily.candidate.sentinel.remote_cleanup_temp:", 1
        )[1]
        self.assertIn(
            "^/tmp/daily-candidate-data-sentinel-[0-9]{8}T[0-9]{6}Z[.]json",
            target,
        )
        self.assertIn('rm -- "$(DAILY_SENTINEL_TEMP_FILE)"', target)


if __name__ == "__main__":
    unittest.main(verbosity=2)
