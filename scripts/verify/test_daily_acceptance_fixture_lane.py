# -*- coding: utf-8 -*-
"""Locks the daily development acceptance fixture lane.

The daily runtime is a separate declared profile from the isolated acceptance
database, so the fixture scope must be declared, not inferred. These tests prove
the declaration is consumed by the code that acts on it: the fixture scope
resolver, the daily contract declaration and the daily probe/ensure wiring.
They deliberately assert on behaviour and on declaration consumption, never on a
selector, a pixel value or a literal string that merely appears in the tree.
"""

from __future__ import annotations

import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from addons.smart_construction_acceptance_fixture.tools.frontend_productization_fixture import (
    DAILY_DEV_DB,
    FIXTURE_SCOPES,
    FIXTURE_SCOPE_ENV,
    FRONTEND_ACCEPTANCE_DB,
    _guard_acceptance_scope,
)
from scripts.ops.dev_acceptance_release_probe import (
    CONTRACT_PASSWORD_ENV,
    _contract_credential,
    validate_acceptance_declaration,
)

ROOT = Path(__file__).resolve().parents[2]
MAKE_DEV = ROOT / "make" / "dev.mk"
ACCEPTANCE_DECLARATION = ROOT / "config" / "acceptance" / "backend_contract_instance_v1.json"
DAILY_DECLARATION = ROOT / "config" / "acceptance" / "backend_contract_instance_daily_v1.json"


class _Cursor:
    def __init__(self, dbname: str) -> None:
        self.dbname = dbname


class _NoOrmEnvironment:
    """Expose only the database name and fail if a guard reaches the ORM."""

    def __init__(self, dbname: str) -> None:
        self.cr = _Cursor(dbname)

    def __getitem__(self, model_name: str):
        raise AssertionError("guard accessed ORM model %s before rejecting" % model_name)


def _guard(
    dbname: str,
    *,
    scope: str | None = None,
    environment: str = "acceptance",
    allow_demo_data: str = "1",
    password: str = "secret",
) -> None:
    values = {
        "SC_ENVIRONMENT": environment,
        "SC_ALLOW_DEMO_DATA": allow_demo_data,
        "SC_ACCEPTANCE_FIXTURE_PASSWORD": password,
        FIXTURE_SCOPE_ENV: "" if scope is None else scope,
    }
    with patch.dict(os.environ, values, clear=False):
        _guard_acceptance_scope(_NoOrmEnvironment(dbname))


def _make_recipe(text: str, target: str) -> list[str]:
    """Return the recipe lines of one make target.

    Handles both a bare ``target:`` rule and target-specific variable
    declarations (``target: VAR := value``) that precede the recipe.
    """
    lines = text.splitlines()
    recipe: list[str] = []
    collecting = False
    for line in lines:
        if line.startswith(target + ":"):
            # A new declaration group for this target; its recipe follows.
            collecting = True
            recipe = []
            continue
        if collecting:
            if line.startswith("\t"):
                recipe.append(line)
                continue
            break
    return recipe


class FixtureScopeTests(unittest.TestCase):
    def test_declared_scopes_bind_the_two_authorized_databases(self) -> None:
        self.assertEqual(FIXTURE_SCOPES["acceptance"]["database"], FRONTEND_ACCEPTANCE_DB)
        self.assertEqual(FIXTURE_SCOPES["acceptance"]["environment"], "acceptance")
        self.assertEqual(FIXTURE_SCOPES["daily_dev"]["database"], DAILY_DEV_DB)
        self.assertEqual(FIXTURE_SCOPES["daily_dev"]["environment"], "dev")
        self.assertEqual(DAILY_DEV_DB, "sc_demo")

    def test_default_scope_keeps_accepting_the_isolated_acceptance_database(self) -> None:
        _guard(FRONTEND_ACCEPTANCE_DB)

    def test_default_scope_still_denies_the_daily_database(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "requires database"):
            _guard(DAILY_DEV_DB)

    def test_default_scope_still_denies_an_unrelated_database(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "requires database"):
            _guard("production")

    def test_daily_scope_accepts_the_declared_daily_database(self) -> None:
        _guard(DAILY_DEV_DB, scope="daily_dev", environment="dev")

    def test_daily_scope_denies_every_other_database(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "requires database"):
            _guard(FRONTEND_ACCEPTANCE_DB, scope="daily_dev", environment="dev")

    def test_daily_scope_requires_the_declared_environment(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "SC_ENVIRONMENT=dev"):
            _guard(DAILY_DEV_DB, scope="daily_dev", environment="acceptance")

    def test_daily_scope_still_requires_the_demo_data_flag_and_secret(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "SC_ALLOW_DEMO_DATA"):
            _guard(DAILY_DEV_DB, scope="daily_dev", environment="dev", allow_demo_data="0")
        with self.assertRaisesRegex(RuntimeError, "SC_ACCEPTANCE_FIXTURE_PASSWORD"):
            _guard(DAILY_DEV_DB, scope="daily_dev", environment="dev", password="")

    def test_unknown_scope_is_denied(self) -> None:
        with self.assertRaisesRegex(RuntimeError, FIXTURE_SCOPE_ENV):
            _guard(DAILY_DEV_DB, scope="production", environment="dev")


class DailyDeclarationTests(unittest.TestCase):
    def _declarations(self) -> tuple[dict, dict]:
        return (
            json.loads(ACCEPTANCE_DECLARATION.read_text(encoding="utf-8")),
            json.loads(DAILY_DECLARATION.read_text(encoding="utf-8")),
        )

    def test_daily_declaration_is_shape_valid_and_bound_to_the_daily_database(self) -> None:
        acceptance, daily = self._declarations()
        self.assertEqual(validate_acceptance_declaration(daily), [])
        self.assertEqual(daily["database"], DAILY_DEV_DB)
        self.assertEqual(acceptance["database"], FRONTEND_ACCEPTANCE_DB)

    def test_daily_declaration_keeps_every_required_check(self) -> None:
        acceptance, daily = self._declarations()
        self.assertEqual(daily["required_checks"], acceptance["required_checks"])
        self.assertEqual(daily["resolution"], acceptance["resolution"])
        self.assertEqual(daily["request"], acceptance["request"])
        self.assertEqual(daily["account"], acceptance["account"])

    def test_daily_declaration_schema_asset_exists(self) -> None:
        _, daily = self._declarations()
        self.assertTrue((ROOT / daily["schema_asset"]).is_file())


class ContractCredentialTests(unittest.TestCase):
    def test_declared_contract_credential_wins(self) -> None:
        self.assertEqual(_contract_credential("fixture-secret", "login-secret"), "fixture-secret")

    def test_absent_contract_credential_reuses_the_login_password(self) -> None:
        self.assertEqual(_contract_credential("", "login-secret"), "login-secret")

    def test_contract_credential_is_declared_in_the_environment(self) -> None:
        self.assertEqual(CONTRACT_PASSWORD_ENV, "ACCEPTANCE_CONTRACT_PASSWORD")


class DailyLaneWiringTests(unittest.TestCase):
    def setUp(self) -> None:
        self.text = MAKE_DEV.read_text(encoding="utf-8")

    def test_probe_forwards_the_declared_daily_contract_inputs(self) -> None:
        recipe = "\n".join(_make_recipe(self.text, "verify.daily_dev.acceptance.readonly.probe"))
        self.assertTrue(recipe, "daily probe recipe not found")
        for token in (
            'ACCEPTANCE_CONTRACT_DECLARATION="$(DAILY_ACCEPTANCE_CONTRACT_DECLARATION)"',
            'ACCEPTANCE_RECORD_RESOLUTION="$(ACCEPTANCE_RECORD_RESOLUTION)"',
            'ACCEPTANCE_CONTRACT_PASSWORD="$(ACCEPTANCE_CONTRACT_PASSWORD)"',
            'ACCEPTANCE_REQUIRE_CONTRACT="$(DAILY_ACCEPTANCE_REQUIRE_CONTRACT)"',
        ):
            self.assertIn(token, recipe, token)

    def test_defaults_point_at_the_daily_declaration_and_require_the_contract(self) -> None:
        self.assertIn("DAILY_ACCEPTANCE_CONTRACT_DECLARATION ?= config/acceptance/backend_contract_instance_daily_v1.json", self.text)
        self.assertIn("DAILY_ACCEPTANCE_REQUIRE_CONTRACT ?= 1", self.text)
        self.assertIn("DAILY_DEV_ACCEPTANCE_DB ?= sc_demo", self.text)

    def test_fixture_ensure_binds_the_daily_database_and_requires_confirmation(self) -> None:
        recipe = "\n".join(_make_recipe(self.text, "daily.dev.acceptance_fixture.ensure"))
        self.assertTrue(recipe, "daily fixture ensure recipe not found")
        self.assertIn("CONFIRM_DAILY_DEV_ACCEPTANCE_FIXTURE", recipe)
        self.assertIn('$(DAILY_DEV_ACCEPTANCE_DB)', recipe)
        self.assertIn("mod.install MODULE=smart_construction_acceptance_fixture", recipe)
        self.assertIn("scripts/dev/daily_dev_acceptance_fixture.sh", recipe)

    def test_contract_resolution_binds_the_served_runtime_sha(self) -> None:
        recipe = "\n".join(_make_recipe(self.text, "daily.dev.acceptance_contract.resolve"))
        self.assertTrue(recipe, "daily contract resolve recipe not found")
        self.assertIn("ACCEPTANCE_TARGET_SHA", recipe)
        self.assertIn("/api/runtime-version", recipe)
        self.assertIn('SC_ACCEPTANCE_FIXTURE_SCOPE=daily_dev', recipe)
        self.assertIn("acceptance.record_identity_resolution.v1", recipe)


if __name__ == "__main__":
    unittest.main()
