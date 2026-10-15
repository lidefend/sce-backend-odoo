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
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from addons.smart_construction_acceptance_fixture.tools.frontend_productization_fixture import (
    DAILY_DEV_DB,
    DATA_SPACE_TENANT_KEY,
    FIXTURE_SCOPES,
    FIXTURE_SCOPE_ENV,
    FRONTEND_ACCEPTANCE_DB,
    _activity_move,
    _company,
    _guard_acceptance_scope,
    _reconcile_activity_move,
    _resolve_existing_fixture_company,
)

FIXTURE_MODULE = "addons.smart_construction_acceptance_fixture.tools.frontend_productization_fixture"
from scripts.ops.dev_acceptance_release_probe import (
    CONTRACT_PASSWORD_ENV,
    _contract_credential,
    published_face_checks,
    validate_acceptance_declaration,
)

ROOT = Path(__file__).resolve().parents[2]
MAKE_DEV = ROOT / "make" / "dev.mk"
ACCEPTANCE_DECLARATION = ROOT / "config" / "acceptance" / "backend_contract_instance_v1.json"
DAILY_DECLARATION = ROOT / "config" / "acceptance" / "backend_contract_instance_daily_v1.json"
DAILY_FIXTURE_SCRIPT = ROOT / "scripts" / "dev" / "daily_dev_acceptance_fixture.sh"
CANONICAL_FIXTURE_SCRIPT = ROOT / "scripts" / "test" / "frontend_productization_fixture.sh"


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
        self.assertEqual(daily["account"], acceptance["account"])
        # The daily instance mirrors the acceptance request binding exactly, plus
        # the one declared daily-only derived key the probe consumes verbatim.
        # The released record page replays the runtime-declared record context
        # into params.context and the sealed contract echoes it, so the daily
        # instance must bind that source; the shared instance stays without it.
        daily_only = set(daily["request"]) - set(acceptance["request"])
        self.assertEqual(daily_only, {"params_context_from"})
        self.assertTrue(str(daily["request"]["params_context_from"]).strip())
        self.assertEqual(
            {key: value for key, value in daily["request"].items() if key not in daily_only},
            acceptance["request"],
        )

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


class DailyFixtureVerifyOrderTests(unittest.TestCase):
    """The credential self-check authenticates through its own transaction.

    ``res.users.authenticate`` opens a fresh cursor, so fixture rows that are
    still uncommitted are invisible and the login check can only pass after the
    deterministic fixture has been committed. Locking the ordering keeps the
    daily entry aligned with the canonical fixture entry instead of asserting a
    literal string that merely appears in the tree.
    """

    def _verify_commit_precedes_authenticate(self, text: str) -> None:
        commit = text.index("env.cr.commit()")
        authenticate = text.index('env["res.users"].sudo().authenticate(')
        self.assertLess(
            commit,
            authenticate,
            "fixture rows must be committed before the cross-transaction login self-check",
        )

    def test_daily_entry_commits_before_the_credential_self_check(self) -> None:
        self._verify_commit_precedes_authenticate(DAILY_FIXTURE_SCRIPT.read_text(encoding="utf-8"))

    def test_daily_entry_keeps_the_canonical_fixture_entry_ordering(self) -> None:
        self._verify_commit_precedes_authenticate(
            CANONICAL_FIXTURE_SCRIPT.read_text(encoding="utf-8")
        )


class _Row(types.SimpleNamespace):
    """Record double with both attribute and field-name item access."""

    def __getitem__(self, key):
        return getattr(self, key)


class _Recordset(list):
    """Minimal recordset double: sized, truthy and attribute-proxying."""

    def __getitem__(self, key):
        if isinstance(key, str):
            if not self:
                raise KeyError(key)
            return self[0][key]
        return list.__getitem__(self, key)

    def __getattr__(self, name):
        if not self:
            raise AttributeError(name)
        return getattr(self[0], name)

    def exists(self):
        return self


class _FakeModel:
    def __init__(self, rows=None):
        self._rows = list(rows or [])
        self.created = []

    def sudo(self, *args, **kwargs):
        return self

    def with_context(self, *args, **kwargs):
        return self

    def search(self, domain, limit=None):
        return _Recordset(self._rows)

    def browse(self, ids=None):
        if ids is None:
            selected = []
        elif isinstance(ids, int):
            selected = [ids]
        else:
            selected = list(ids)
        return _Recordset([row for row in self._rows if row.id in selected])

    def create(self, values):
        record = types.SimpleNamespace(id=99, **values)
        self.created.append(values)
        self._rows.append(record)
        return record


class _FakeEnv:
    def __init__(self, models, refs):
        self._models = models
        self._refs = refs

    def __getitem__(self, name):
        return self._models[name]

    def ref(self, xmlid, raise_if_not_found=False):
        record = self._refs.get(xmlid)
        if record is None and raise_if_not_found:
            raise RuntimeError("missing xmlid %s" % xmlid)
        return record


def _load_provisioning_module():
    """Load the provisioning module under its real import path.

    The fixture builder imports it lazily by dotted path, so the double has to
    live in ``sys.modules`` exactly where the fixture will look for it.
    """
    for name in ("odoo", "odoo.addons", "odoo.addons.smart_core", "odoo.addons.smart_core.security"):
        if name not in sys.modules:
            package = types.ModuleType(name)
            package.__path__ = []
            sys.modules[name] = package
    spec = importlib.util.spec_from_file_location(
        "odoo.addons.smart_core.security.data_space_provisioning",
        ROOT / "addons" / "smart_core" / "security" / "data_space_provisioning.py",
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    setattr(sys.modules["odoo.addons.smart_core.security"], "data_space_provisioning", module)
    return module


provisioning = _load_provisioning_module()


class TestLegacyFixtureCarrierAdoption(unittest.TestCase):
    """A carrier a previous fixture version left unregistered is onboarded, not orphaned."""

    def _company(self, *, bootstrap=False):
        return _Row(
            id=21, _name="res.company", name="FE Company A",
            is_platform_bootstrap_company=bootstrap,
        )

    def test_owned_legacy_carrier_is_adopted_through_the_declared_entry(self):
        registration_model = _FakeModel()
        env = _FakeEnv(
            {
                "sc.tenant.company.registration": registration_model,
                "ir.model.data": _FakeModel(rows=[types.SimpleNamespace(id=1)]),
            },
            {},
        )
        adopted = _Recordset([
            types.SimpleNamespace(
                active=True, data_purpose="test", tenant_key=DATA_SPACE_TENANT_KEY,
            )
        ])
        with patch.object(provisioning, "adopt_business_company", return_value=adopted) as adopt:
            result = _resolve_existing_fixture_company(env, self._company())
        adopt.assert_called_once_with(
            env, tenant_key=DATA_SPACE_TENANT_KEY, purpose="test", company_id=21,
        )
        self.assertIs(result, adopted)
        self.assertEqual(len(result), 1)

    def test_carrier_the_fixture_does_not_own_is_never_adopted(self):
        env = _FakeEnv(
            {
                "sc.tenant.company.registration": _FakeModel(),
                "ir.model.data": _FakeModel(rows=[]),
            },
            {},
        )
        with patch.object(provisioning, "adopt_business_company") as adopt:
            result = _resolve_existing_fixture_company(env, self._company())
        adopt.assert_not_called()
        self.assertEqual(len(result), 0)

    def test_bootstrap_carrier_is_never_adopted(self):
        env = _FakeEnv(
            {
                "sc.tenant.company.registration": _FakeModel(),
                "ir.model.data": _FakeModel(rows=[types.SimpleNamespace(id=1)]),
            },
            {},
        )
        with patch.object(provisioning, "adopt_business_company") as adopt:
            result = _resolve_existing_fixture_company(env, self._company(bootstrap=True))
        adopt.assert_not_called()
        self.assertEqual(len(result), 0)

    def test_existing_registration_is_used_without_re_onboarding(self):
        existing = _Recordset([
            types.SimpleNamespace(
                active=True, data_purpose="test", tenant_key=DATA_SPACE_TENANT_KEY,
            )
        ])
        env = _FakeEnv(
            {
                "sc.tenant.company.registration": _FakeModel(rows=list(existing)),
                "ir.model.data": _FakeModel(rows=[types.SimpleNamespace(id=1)]),
            },
            {},
        )
        with patch.object(provisioning, "adopt_business_company") as adopt:
            result = _resolve_existing_fixture_company(env, self._company())
        adopt.assert_not_called()
        self.assertEqual(len(result), 1)

    def test_company_entry_completes_after_legacy_carrier_adoption(self):
        company = self._company()
        company._fields = {
            "name": types.SimpleNamespace(type="char"),
            "currency_id": types.SimpleNamespace(type="many2one"),
            "country_id": types.SimpleNamespace(type="many2one"),
        }
        company.currency_id = types.SimpleNamespace(id=1)
        company.country_id = types.SimpleNamespace(id=2)
        xmlid_row = types.SimpleNamespace(id=7, writes=[])
        xmlid_row.write = lambda values: xmlid_row.writes.append(values)
        env = _FakeEnv(
            {
                "sc.tenant.company.registration": _FakeModel(),
                "ir.model.data": _FakeModel(rows=[xmlid_row]),
                "res.company": _FakeModel(rows=[company]),
            },
            {
                "smart_construction_acceptance_fixture.fe_company_a": company,
                "base.CNY": types.SimpleNamespace(id=1),
                "base.cn": types.SimpleNamespace(id=2),
            },
        )
        adopted = _Recordset([
            types.SimpleNamespace(
                active=True, data_purpose="test", tenant_key=DATA_SPACE_TENANT_KEY,
            )
        ])
        with patch.object(provisioning, "adopt_business_company", return_value=adopted):
            resolved = _company(env, "A")
        self.assertIs(resolved[0], company)

    def test_company_entry_fails_closed_for_an_unowned_legacy_carrier(self):
        company = self._company()
        env = _FakeEnv(
            {
                "sc.tenant.company.registration": _FakeModel(),
                "ir.model.data": _FakeModel(rows=[]),
                "res.company": _FakeModel(rows=[company]),
            },
            {"smart_construction_acceptance_fixture.fe_company_a": company},
        )
        with self.assertRaises(RuntimeError) as caught:
            _company(env, "A")
        self.assertIn("governed baseline reset", str(caught.exception))


class _FakeMove(types.SimpleNamespace):
    """account.move double that records its writes and mirrors them back."""

    def __init__(self, **kwargs):
        super().__init__(writes=[], **kwargs)

    def sudo(self, *args, **kwargs):
        return self

    def write(self, values):
        self.writes.append(values)
        for key, value in values.items():
            setattr(self, key, value)
        return True


class TestReusedDatabaseActivityCarrierReconciliation(unittest.TestCase):
    """A reused acceptance database converges the fixture's own drifted entry.

    The fixture's own account.move carrier was once materialised inside the
    platform company with that company's miscellaneous journal. Re-running on
    the reused database must repair its own row instead of demanding a database
    rebuild - and must still refuse to touch an entry that carries any booking.
    """

    def _company(self):
        return types.SimpleNamespace(id=21, currency_id=types.SimpleNamespace(id=1))

    def _journal(self, company):
        return types.SimpleNamespace(id=77, company_id=company, type="general")

    def _drifted_move(self, **overrides):
        values = {
            "_name": "account.move",
            "state": "draft",
            "posted_before": False,
            "line_ids": [],
            "company_id": types.SimpleNamespace(id=1),
            "journal_id": types.SimpleNamespace(id=3),
        }
        values.update(overrides)
        return _FakeMove(**values)

    def test_empty_draft_entry_is_re_homed_onto_the_declared_company(self):
        company = self._company()
        move = self._drifted_move()
        result = _reconcile_activity_move(None, move, company, self._journal(company))
        self.assertIs(result, move)
        self.assertEqual(
            move.writes,
            [{"company_id": 21, "journal_id": 77, "currency_id": 1, "name": "/"}],
        )

    def test_booked_entry_drift_still_fails_closed(self):
        company = self._company()
        journal = self._journal(company)
        for overrides in (
            {"state": "posted"},
            {"posted_before": True},
            {"line_ids": [types.SimpleNamespace(id=1)]},
        ):
            with self.subTest(overrides=sorted(overrides)):
                move = self._drifted_move(**overrides)
                with self.assertRaises(RuntimeError) as caught:
                    _reconcile_activity_move(None, move, company, journal)
                self.assertIn("governed baseline reset", str(caught.exception))
                self.assertEqual(move.writes, [])

    def test_already_declared_entry_is_left_untouched(self):
        company = self._company()
        journal = self._journal(company)
        move = self._drifted_move(company_id=company, journal_id=journal)
        self.assertIs(_reconcile_activity_move(None, move, company, journal), move)
        self.assertEqual(move.writes, [])

    def test_entry_consumes_the_reconciled_record_instead_of_failing_early(self):
        company = self._company()
        journal = self._journal(company)
        move = self._drifted_move()
        env = _FakeEnv(
            {
                "sc.tenant.company.registration": _FakeModel(rows=[types.SimpleNamespace(id=1)]),
                "ir.model.data": _FakeModel(),
            },
            {"smart_construction_acceptance_fixture.fe_activity_journal_entry": move},
        )
        sentinel = object()
        with patch("%s._upsert" % FIXTURE_MODULE, return_value=sentinel) as upsert:
            self.assertIs(_activity_move(env, company, types.SimpleNamespace(id=8990), journal), sentinel)
        upsert.assert_called_once()
        self.assertEqual(move.writes[0]["company_id"], 21)



class PublishedFaceIdentityTests(unittest.TestCase):
    """The served published leaves must equal the declared acceptance surface.

    A released leaf that nobody registered, or a delivery carrier that was
    silently swapped for another leaf, keeps the total count; identity must
    therefore be compared, and the released population must equal the
    acceptance rows plus the declared carriers.
    """

    SCENE = "smart_construction_core.menu_sc_workspace_home"

    @staticmethod
    def _leaf(xmlid, action_id=0):
        return {"menu_xmlid": xmlid, "child_count": 0, "action_id": action_id}

    def test_declared_carrier_matches_the_served_surface(self) -> None:
        rows = [self._leaf("t.menu_a", 780), self._leaf(self.SCENE, 0)]
        errors, checks = published_face_checks(rows, 2, {self.SCENE}, 1)
        self.assertEqual(errors, [])
        self.assertEqual(checks["nav_non_action_entries"], [self.SCENE])
        self.assertEqual(checks["nav_published_universe_expected"], 2)

    def test_swapped_carrier_fails_even_though_the_leaf_count_matches(self) -> None:
        rows = [self._leaf("t.menu_a", 780), self._leaf("t.menu_other_scene", 0)]
        errors, _checks = published_face_checks(rows, 2, {self.SCENE}, 1)
        self.assertIn("nav_non_action_entry_drift", errors)
        self.assertNotIn("nav_published_universe_drift", errors)

    def test_undeclared_published_leaf_fails_closed(self) -> None:
        rows = [self._leaf("t.menu_a", 780), self._leaf(self.SCENE, 0)]
        errors, _checks = published_face_checks(rows, 2, set(), 1)
        self.assertIn("nav_non_action_entry_drift", errors)

    def test_published_growth_beyond_the_acceptance_rows_fails_closed(self) -> None:
        rows = [self._leaf("t.menu_a", 780), self._leaf(self.SCENE, 0), self._leaf("t.menu_new", 781)]
        errors, _checks = published_face_checks(rows, 3, {self.SCENE}, 1)
        self.assertIn("nav_published_universe_drift", errors)



if __name__ == "__main__":
    unittest.main()
