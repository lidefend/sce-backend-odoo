# -*- coding: utf-8 -*-
import os
from unittest.mock import patch, Mock

from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import UserError

from ..hooks import guard_demo_scope


class _GuardCursor:
    def __init__(self, dbname):
        self.dbname = dbname


class _NoOrmEnvironment:
    def __init__(self, dbname):
        self.cr = _GuardCursor(dbname)

    def __getitem__(self, model_name):
        raise AssertionError("demo guard accessed ORM before rejecting: %s" % model_name)


@tagged("post_install", "-at_install", "sc_gate", "demo_gate")
class TestDemoShowcaseGate(TransactionCase):
    """Prevent demo filters from leaking into core business entries."""

    def test_demo_project_seed_closes_showroom_boq_coverage(self):
        demo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
        seed_path = os.path.join(demo_root, "seed", "steps", "step_20_projects_demo.py")
        with open(seed_path, "r", encoding="utf-8") as handle:
            source = handle.read()

        showroom_tail = source.split("showroom_projects = _get_showroom_projects(env)", 1)[1]
        self.assertIn('Boq.search_count([("project_id", "=", project.id)]) == 0', showroom_tail)
        self.assertIn("_ensure_boq(env, project, code_prefix, uom_unit)", showroom_tail)

    def test_contract_seed_uses_controlled_fact_lifecycles(self):
        demo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
        seed_path = os.path.join(
            demo_root, "seed", "steps", "step_40_contracts_demo.py"
        )
        with open(seed_path, "r", encoding="utf-8") as handle:
            source = handle.read()

        self.assertNotIn("UPDATE sc_settlement_order SET state", source)
        self.assertNotIn("UPDATE payment_request SET state", source)
        self.assertNotIn('"state": "active"', source)
        self.assertIn("baseline.action_create_revision", source)
        self.assertIn("baseline.action_activate()", source)
        from ..seed.steps import step_40_contracts_demo
        from ..tools import scenario_loader
        settlement = Mock(state="draft")
        actor_record = Mock()
        def submit():
            settlement.state = "approve"
        actor_record.action_submit.side_effect = submit
        with patch.object(scenario_loader, "_demo_action_record", return_value=actor_record) as resolve_actor:
            self.assertIs(step_40_contracts_demo._approve_settlement(self.env, settlement), settlement)
        resolve_actor.assert_called_once_with(
            settlement.env, settlement, "action_submit", step_40_contracts_demo._DEMO_DOCUMENT_SUBMITTER)
        actor_record.action_submit.assert_called_once_with()
        settlement.write.assert_not_called()
        payment = Mock(state="draft")
        def approve(env, record):
            self.assertIs(env, self.env)
            self.assertIs(record, payment)
            record.state = "approved"
        with patch.object(step_40_contracts_demo, "_demo_drive_approval", side_effect=approve) as drive:
            self.assertIs(step_40_contracts_demo._approve_payment(self.env, payment), payment)
        drive.assert_called_once_with(self.env, payment)
        payment.write.assert_not_called()
        payment.state = "draft"
        with patch.object(step_40_contracts_demo, "_demo_drive_approval"):
            with self.assertRaises(UserError):
                step_40_contracts_demo._approve_payment(self.env, payment)
        self.assertIn('record=%s,%s(%s); state=%s;', source)
        self.assertIn('calculation=round(%s=%s * ratio=%s, 2), currency_rounding=%s;', source)
        self.assertIn('invoice_ref[expected=non-empty,actual=%s,match=%s]', source)
        self.assertIn('invoice_date[expected=present,actual=%s,match=%s]', source)
        self.assertIn('invoice_amount[expected=%s,actual=%s,match=%s]', source)

    def test_project_seed_does_not_forge_fact_sources_or_lifecycle(self):
        demo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
        seed_path = os.path.join(
            demo_root, "seed", "steps", "step_20_projects_demo.py"
        )
        with open(seed_path, "r", encoding="utf-8") as handle:
            source = handle.read()

        self.assertNotIn("UPDATE project_project SET lifecycle_state", source)
        self.assertNotIn('"source_model": "purchase.order"', source)
        self.assertNotIn('"source_model": "account.move"', source)
        self.assertIn('vals["lifecycle_state"] = "draft"', source)
        self.assertIn("project.action_set_lifecycle_state(state)", source)

    def test_no_demo_showcase_filters_in_core(self):
        demo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
        addons_root = os.path.abspath(os.path.join(demo_root, os.pardir))
        module_root = os.path.join(addons_root, "smart_construction_core")
        allow_paths = {
            os.path.join("models", "core", "project_core.py"),
            os.path.join("migrations", "17.0.0.60", "post-migration.py"),
        }
        legacy_tokens = ("sc_demo_showcase", "sc_demo_showcase_ready")

        hits = []
        for root, _, files in os.walk(module_root):
            if "__pycache__" in root:
                continue
            for name in files:
                if not (name.endswith(".py") or name.endswith(".xml")):
                    continue
                path = os.path.join(root, name)
                with open(path, "r", encoding="utf-8") as handle:
                    content = handle.read()
                if not any(token in content for token in legacy_tokens):
                    continue
                rel_path = os.path.relpath(path, module_root)
                if rel_path.startswith("tests" + os.sep):
                    continue
                for idx, line in enumerate(content.splitlines(), start=1):
                    if not any(token in line for token in legacy_tokens):
                        continue
                    if rel_path in allow_paths:
                        continue
                    hits.append(f"{rel_path}:{idx}")

        self.assertFalse(
            hits,
            "禁止 core 模块硬编码 demo 过滤（sc_demo_showcase*），命中：%s"
            % ", ".join(hits),
        )

    def _assert_scope_denied(self, dbname, environment, allow, password, message):
        with patch.dict(
            os.environ,
            {
                "SC_ENVIRONMENT": environment,
                "SC_ALLOW_DEMO_DATA": allow,
                "SC_DEMO_USER_PASSWORD": password,
            },
            clear=False,
        ):
            with self.assertRaisesRegex(RuntimeError, message):
                guard_demo_scope(_NoOrmEnvironment(dbname))

    def test_demo_scope_rejects_production_database_before_orm(self):
        self._assert_scope_denied("production", "demo", "1", "secret", "authorized demo database")

    def test_demo_scope_rejects_history_database_before_orm(self):
        self._assert_scope_denied(
            "history_rehearsal", "demo", "1", "secret", "authorized demo database"
        )

    def test_demo_scope_rejects_empty_database_before_orm(self):
        self._assert_scope_denied("", "demo", "1", "secret", "authorized demo database")

    def test_local_feature_demo_database_is_authorized(self):
        with patch.dict(
            os.environ,
            {
                "SC_ENVIRONMENT": "demo",
                "SC_ALLOW_DEMO_DATA": "1",
                "SC_DEMO_USER_PASSWORD": "secret",
            },
            clear=False,
        ):
            guard_demo_scope(_NoOrmEnvironment("sc_dev_demo"))

    def test_technical_sample_database_is_not_demo_authority(self):
        self._assert_scope_denied(
            "sc_dev_sample", "demo", "1", "secret", "authorized demo database"
        )

    def test_demo_scope_rejects_unauthorized_environment_before_orm(self):
        self._assert_scope_denied("sc_demo", "production", "1", "secret", "SC_ENVIRONMENT")

    def test_demo_scope_rejects_missing_secret_before_orm(self):
        self._assert_scope_denied("sc_demo", "demo", "1", "", "SC_DEMO_USER_PASSWORD")


@tagged("post_install", "-at_install", "sc_gate", "demo_gate")
class TestDemoSeedReproducibilityContract(TransactionCase):
    """Rebuild/reseed must restore the published demo identity from the module."""

    def test_published_identity_and_password_are_authored_in_the_module(self):
        from ..hooks import DEMO_COMPANY_NAME, DEMO_PRINCIPAL_LOGINS, DEMO_USER_PASSWORD
        self.assertEqual(DEMO_COMPANY_NAME, "四川智汇某某建设集团有限公司")
        self.assertEqual(DEMO_USER_PASSWORD, "123456")
        self.assertIn("wutao", DEMO_PRINCIPAL_LOGINS)
        self.assertIn("demo_full", DEMO_PRINCIPAL_LOGINS)

    def test_post_init_restores_identity_before_applying_passwords(self):
        demo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
        with open(os.path.join(demo_root, "hooks.py"), "r", encoding="utf-8") as handle:
            source = handle.read()
        body = source.split("def post_init_hook(env):", 1)[1]
        self.assertLess(body.index("apply_demo_company_identity(env)"),
                        body.index("apply_demo_user_passwords(env)"))

    def test_reseed_entries_restore_company_identity(self):
        import ast
        demo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
        path = os.path.join(demo_root, "tools", "scenario_loader.py")
        with open(path, "r", encoding="utf-8") as handle:
            source = handle.read()
        tree = ast.parse(source)
        for name in ("load_base_seed", "load_scenario"):
            node = next(n for n in tree.body
                        if isinstance(n, ast.FunctionDef) and n.name == name)
            body = ast.get_source_segment(source, node)
            self.assertIn("apply_demo_company_identity(env)", body, name)

    def test_seed_profile_starts_with_identity_and_ends_with_verify(self):
        import ast
        demo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
        with open(os.path.join(demo_root, "seed", "registry.py"), "r", encoding="utf-8") as handle:
            tree = ast.parse(handle.read())
        profiles = next(ast.literal_eval(n.value) for n in tree.body
                        if isinstance(n, ast.AnnAssign) and n.target.id == "_PROFILES")
        steps = profiles["demo_full"]
        self.assertEqual(steps[0], "demo_company_identity")
        self.assertEqual(steps[-1], "demo_90_verify")
