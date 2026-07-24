# -*- coding: utf-8 -*-
import importlib.util
import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


def _load_lifecycle():
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        "sc_projection_relation_lifecycle",
        root / "models" / "projection_relation_lifecycle.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _LifecycleCursor:
    def __init__(
        self,
        lifecycle,
        relkind="r",
        signature=None,
        primary_key_count=1,
        view_definition="",
        dependent_count=0,
        row_count=12328,
        stage_validation=(12328, 0, 0, 0),
        invalid_project_count=0,
        fail_insert=False,
    ):
        self.lifecycle = lifecycle
        self.relkind = relkind
        self.signature = signature or lifecycle.AR_AP_COLUMNS
        self.primary_key_count = primary_key_count
        self.view_definition = view_definition
        self.dependent_count = dependent_count
        self.row_count = row_count
        self.stage_validation = stage_validation
        self.invalid_project_count = invalid_project_count
        self.fail_insert = fail_insert
        self.last_result = None
        self.statements = []

    def execute(self, statement, params=None):
        normalized = " ".join(statement.split())
        self.statements.append((normalized, params))
        if "FROM pg_class relation" in normalized:
            self.last_result = (
                (self.relkind, "public", "sc_ar_ap_project_summary")
                if self.relkind
                else None
            )
        elif "FROM pg_attribute attribute" in normalized:
            self.last_result = list(self.signature)
        elif "FROM pg_constraint" in normalized:
            self.last_result = (self.primary_key_count,)
        elif 'FROM "sc_ar_ap_project_summary_stage"' in normalized and (
            "count(*) FILTER" in normalized
        ):
            self.last_result = self.stage_validation
        elif 'LEFT JOIN project_project project' in normalized:
            self.last_result = (self.invalid_project_count,)
        elif normalized.startswith('CREATE TABLE "public"'):
            self.relkind = "r"
            self.signature = self.lifecycle.AR_AP_COLUMNS
            self.primary_key_count = 1
            self.row_count = 0
            self.last_result = None
        elif normalized.startswith(
            'DELETE FROM "public"."sc_ar_ap_project_summary" current WHERE NOT EXISTS'
        ):
            self.last_result = None
        elif normalized.startswith(
            'INSERT INTO "public"."sc_ar_ap_project_summary"'
        ):
            if self.fail_insert:
                raise RuntimeError("simulated insert failure")
            self.row_count = self.stage_validation[0]
            self.last_result = None
        else:
            self.last_result = None

    def fetchone(self):
        if isinstance(self.last_result, list):
            return self.last_result[0] if self.last_result else None
        return self.last_result

    def fetchall(self):
        if isinstance(self.last_result, list):
            return list(self.last_result)
        return []


class ArApProjectionRelationLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.lifecycle = _load_lifecycle()

    def test_known_populated_legacy_table_is_preserved_in_place(self):
        cursor = _LifecycleCursor(self.lifecycle, row_count=12328)
        before = cursor.row_count

        result = self.lifecycle.ensure_ar_ap_project_summary_provider(cursor)

        self.assertEqual(result, "preserved")
        self.assertEqual(cursor.relkind, "r")
        self.assertEqual(cursor.row_count, before)
        destructive = ("DROP TABLE", "ALTER TABLE", "TRUNCATE", "DELETE FROM")
        statements = "\n".join(item[0] for item in cursor.statements)
        self.assertFalse(any(token in statements for token in destructive))

    def test_second_upgrade_is_idempotent(self):
        cursor = _LifecycleCursor(self.lifecycle)
        self.assertEqual(
            self.lifecycle.ensure_ar_ap_project_summary_provider(cursor), "preserved"
        )
        first_statements = len(cursor.statements)
        self.assertEqual(
            self.lifecycle.ensure_ar_ap_project_summary_provider(cursor), "preserved"
        )
        self.assertGreater(len(cursor.statements), first_statements)
        self.assertEqual(cursor.relkind, "r")

    def test_unknown_table_structure_fails_closed(self):
        signature = list(self.lifecycle.AR_AP_COLUMNS)
        signature[-1] = ("actual_available_balance", "text", True)
        cursor = _LifecycleCursor(self.lifecycle, signature=tuple(signature))

        with self.assertRaisesRegex(
            RuntimeError, "AR_AP_PROJECTION_RELATION_INVALID.*stage=existing_table"
        ):
            self.lifecycle.ensure_ar_ap_project_summary_provider(cursor)

    def test_materialized_and_partitioned_relations_fail_closed(self):
        for relkind in ("m", "p", "f"):
            with self.subTest(relkind=relkind):
                cursor = _LifecycleCursor(self.lifecycle, relkind=relkind)
                with self.assertRaisesRegex(RuntimeError, "relkind=%s" % relkind):
                    self.lifecycle.ensure_ar_ap_project_summary_provider(cursor)

    def test_fresh_install_creates_core_owned_physical_provider(self):
        cursor = _LifecycleCursor(self.lifecycle, relkind=None)

        result = self.lifecycle.ensure_ar_ap_project_summary_provider(cursor)

        self.assertEqual(result, "created")
        self.assertEqual(cursor.relkind, "r")
        self.assertTrue(
            any(
                statement.startswith('CREATE TABLE "public"')
                for statement, _params in cursor.statements
            )
        )

    def test_typed_empty_view_is_never_silently_replaced(self):
        cursor = _LifecycleCursor(
            self.lifecycle,
            relkind="v",
            view_definition="SELECT NULL::integer AS id WHERE false",
        )

        with self.assertRaisesRegex(
            RuntimeError, "relkind=v.*stage=unsupported_relation_kind"
        ):
            self.lifecycle.ensure_ar_ap_project_summary_provider(cursor)
        self.assertEqual(cursor.relkind, "v")

    def test_nonempty_or_dependent_view_fails_closed(self):
        cursor = _LifecycleCursor(
            self.lifecycle, relkind="v", view_definition="SELECT 1 AS id"
        )
        with self.assertRaisesRegex(RuntimeError, "unsupported_relation_kind"):
            self.lifecycle.ensure_ar_ap_project_summary_provider(cursor)

        cursor = _LifecycleCursor(
            self.lifecycle,
            relkind="v",
            view_definition="SELECT NULL::integer AS id WHERE false",
            dependent_count=1,
        )
        with self.assertRaisesRegex(RuntimeError, "unsupported_relation_kind"):
            self.lifecycle.ensure_ar_ap_project_summary_provider(cursor)

    def test_refresh_rejects_non_select_input_before_database_write(self):
        cursor = _LifecycleCursor(self.lifecycle)
        with self.assertRaisesRegex(ValueError, "read-only SELECT/CTE"):
            self.lifecycle.refresh_ar_ap_project_summary(
                cursor, "DELETE FROM source_table"
            )
        self.assertEqual(cursor.statements, [])

    def test_safe_refresh_serializes_validates_and_preserves_relation_identity(self):
        cursor = _LifecycleCursor(
            self.lifecycle,
            stage_validation=(12328, 0, 0, 0),
        )

        refreshed = self.lifecycle.refresh_ar_ap_project_summary(
            cursor,
            "SELECT * FROM versioned_projection_source",
            minimum_row_count=12000,
        )

        self.assertEqual(refreshed, 12328)
        self.assertEqual(cursor.relkind, "r")
        self.assertEqual(cursor.row_count, 12328)
        statements = [item[0] for item in cursor.statements]
        self.assertTrue(statements[0].startswith("SELECT pg_advisory_xact_lock"))
        self.assertNotIn("DROP TABLE", "\n".join(statements))
        self.assertNotIn("TRUNCATE", "\n".join(statements))

    def test_refresh_validation_failure_occurs_before_official_table_write(self):
        cursor = _LifecycleCursor(
            self.lifecycle,
            stage_validation=(0, 0, 0, 0),
        )

        with self.assertRaisesRegex(RuntimeError, "stage=staging"):
            self.lifecycle.refresh_ar_ap_project_summary(
                cursor,
                "WITH source AS (SELECT 1) SELECT * FROM source",
                minimum_row_count=1,
            )

        statements = "\n".join(item[0] for item in cursor.statements)
        self.assertNotIn('ON CONFLICT (id) DO UPDATE', statements)
        self.assertEqual(cursor.row_count, 12328)

    def test_refresh_write_failure_is_not_swallowed(self):
        cursor = _LifecycleCursor(
            self.lifecycle,
            stage_validation=(12328, 0, 0, 0),
            fail_insert=True,
        )
        with self.assertRaisesRegex(RuntimeError, "simulated insert failure"):
            self.lifecycle.refresh_ar_ap_project_summary(
                cursor, "SELECT * FROM versioned_projection_source"
            )


def _load_optional_projection():
    odoo = types.ModuleType("odoo")
    odoo.models = types.SimpleNamespace(AbstractModel=object)
    odoo.tools = types.SimpleNamespace(drop_view_if_exists=lambda *_args: None)
    sys.modules["odoo"] = odoo
    spec = importlib.util.spec_from_file_location(
        "sc_optional_customer_projection",
        Path(__file__).resolve().parents[1]
        / "models"
        / "optional_customer_projection.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class OptionalProjectionHandoffContractTests(unittest.TestCase):
    def test_environment_flag_alone_never_proves_external_ownership(self):
        module = _load_optional_projection()
        with patch.dict(
            os.environ,
            {"SC_ALLOW_EXTERNAL_PROJECTION_HANDOFF": "1"},
            clear=True,
        ):
            with self.assertRaisesRegex(RuntimeError, "CONTRACT_MISSING"):
                module._load_handoff_contract("sc_ar_ap_project_summary")

    def test_incomplete_contract_fails_closed(self):
        module = _load_optional_projection()
        with patch.dict(
            os.environ,
            {
                "SC_EXTERNAL_PROJECTION_HANDOFF_CONTRACT": (
                    '{"sc_external_projection": {"readiness": true}}'
                )
            },
            clear=True,
        ):
            with self.assertRaisesRegex(RuntimeError, "CONTRACT_INCOMPLETE"):
                module._load_handoff_contract("sc_external_projection")

    def test_complete_contract_is_machine_readable(self):
        module = _load_optional_projection()
        contract = {
            "module_technical_name": "verified_external_provider",
            "minimum_version": "17.0.1.0",
            "provider_schema_version": "1",
            "owner_marker": "verified_external_provider",
            "relation_contract_version": "1",
            "expected_structure_fingerprint": "a" * 64,
            "readiness": True,
        }
        import json

        with patch.dict(
            os.environ,
            {
                "SC_EXTERNAL_PROJECTION_HANDOFF_CONTRACT": json.dumps(
                    {"sc_external_projection": contract}
                )
            },
            clear=True,
        ):
            self.assertEqual(
                module._load_handoff_contract("sc_external_projection"), contract
            )

        marker = {
            "module_technical_name": contract["module_technical_name"],
            "owner_marker": contract["owner_marker"],
            "provider_schema_version": contract["provider_schema_version"],
            "relation_contract_version": contract["relation_contract_version"],
            "readiness": True,
        }
        module._verify_relation_owner_marker(
            "sc_external_projection",
            module._HANDOFF_COMMENT_PREFIX + json.dumps(marker, sort_keys=True),
            contract,
        )

    def test_owner_marker_must_match_the_complete_contract(self):
        module = _load_optional_projection()
        contract = {
            "module_technical_name": "verified_external_provider",
            "minimum_version": "17.0.1.0",
            "provider_schema_version": "1",
            "owner_marker": "verified_external_provider",
            "relation_contract_version": "1",
            "expected_structure_fingerprint": "a" * 64,
            "readiness": True,
        }
        incomplete_marker = (
            module._HANDOFF_COMMENT_PREFIX
            + '{"owner_marker":"verified_external_provider"}'
        )
        with self.assertRaisesRegex(RuntimeError, "OWNER_MARKER_MISMATCH"):
            module._verify_relation_owner_marker(
                "sc_external_projection", incomplete_marker, contract
            )


if __name__ == "__main__":
    unittest.main()
