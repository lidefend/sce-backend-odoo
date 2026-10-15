"""Hermetic decision tests for the governed platform database ops entries.

The two ops entries (``scripts/ops/platform_database_register.py`` and
``scripts/ops/platform_database_lifecycle_apply.py``) are the only production
callers of the platform registration model, and they are what turns a declared
lifecycle state into a real environment fact. Their decision helpers stay
importable without odoo, so the fail-closed refusals are proven here; the real
PostgreSQL effect still requires an authorized governed runtime adapter and
its actual readback. No such runtime result is claimed by these tests.

These tests pin three boundaries the owner named:

* the ops tool never decides a tenant, a purpose or an initialization rule on
  its own -- it consumes the declaration by module identity;
* a request that would cut off the database serving the control plane, an
  unknown operation, a missing reason or a missing confirmation fails closed;
* a lifecycle operation is never reported as an environment change unless the
  catalog readback shows the declared fact.
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load(relative, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


governance = load(
    "addons/smart_core/security/database_governance.py", "governance_for_entry_test"
)
provisioning = load(
    "addons/smart_core/security/data_space_provisioning.py", "provisioning_for_entry_test"
)
register_entry = load(
    "scripts/ops/platform_database_register.py", "register_entry_under_test"
)
lifecycle_entry = load(
    "scripts/ops/platform_database_lifecycle_apply.py", "lifecycle_entry_under_test"
)

REGISTER_SOURCE = "scripts/ops/platform_database_register.py"
LIFECYCLE_SOURCE = "scripts/ops/platform_database_lifecycle_apply.py"


def lifecycle_environ(**overrides):
    environ = {
        "PLATFORM_DATABASE_EXECUTION_ID": "a" * 32,
        lifecycle_entry.CONFIRM_ENV: lifecycle_entry.CONFIRM_VALUE,
        lifecycle_entry.TARGET_ENV: "sc_test",
        lifecycle_entry.OPERATION_ENV: "suspend",
        lifecycle_entry.REASON_ENV: "governed lifecycle unit test",
    }
    environ.update(overrides)
    return environ


def register_environ(**overrides):
    environ = {
        "PLATFORM_DATABASE_EXECUTION_ID": "a" * 32,
        register_entry.CONFIRM_ENV: register_entry.CONFIRM_VALUE,
        register_entry.TARGET_ENV: "sc_test",
        register_entry.ROLE_ENV: "industry_acceptance",
        register_entry.PURPOSE_ENV: "test",
        register_entry.REASON_ENV: "governed registration unit test",
    }
    environ.update(overrides)
    return environ


class TestOpsEntriesConsumeTheDeclaration(unittest.TestCase):
    def test_ops_entries_address_the_declaration_by_module_identity(self):
        self.assertEqual(
            lifecycle_entry.VOCABULARY_MODULE,
            "odoo.addons.smart_core.security.database_governance",
        )
        self.assertEqual(
            register_entry.VOCABULARY_MODULE,
            "odoo.addons.smart_core.security.data_space_provisioning",
        )

    def test_ops_entries_keep_no_filesystem_candidate_copy(self):
        for module in (register_entry, lifecycle_entry):
            self.assertFalse(hasattr(module, "VOCABULARY_CANDIDATES"))

    def test_ops_entries_never_reach_a_declaration_by_filesystem_path(self):
        for relative in (REGISTER_SOURCE, LIFECYCLE_SOURCE):
            self.assertNotIn(
                "addons/smart_core/security/", (ROOT / relative).read_text(encoding="utf-8")
            )

    def test_register_entry_does_not_restate_the_onboarding_role_table(self):
        source = (ROOT / REGISTER_SOURCE).read_text(encoding="utf-8")
        body = source.split('"""', 2)[2]
        for role in set(provisioning.PURPOSE_ENVIRONMENT_ROLE.values()):
            # The entry resolves the role from the declaration; naming a role in
            # its own body would make it a second source.
            self.assertNotIn(role, body, role)


class TestLifecycleRequestValidation(unittest.TestCase):
    def test_declared_request_resolves(self):
        request = lifecycle_entry.resolve_request(lifecycle_environ(), governance)
        self.assertEqual(request["db_name"], "sc_test")
        self.assertEqual(request["operation"], "suspend")
        self.assertEqual(request["connection_effect"], "deny_connections")
        self.assertTrue(request["output"])

    def test_confirmation_token_is_required(self):
        for bad in ("", "APPLY", "yes"):
            with self.assertRaises(lifecycle_entry.LifecycleApplyError):
                lifecycle_entry.resolve_request(
                    lifecycle_environ(**{lifecycle_entry.CONFIRM_ENV: bad}), governance
                )

    def test_target_database_is_required(self):
        with self.assertRaises(lifecycle_entry.LifecycleApplyError):
            lifecycle_entry.resolve_request(
                lifecycle_environ(**{lifecycle_entry.TARGET_ENV: "  "}), governance
            )

    def test_reason_is_required(self):
        with self.assertRaises(lifecycle_entry.LifecycleApplyError):
            lifecycle_entry.resolve_request(
                lifecycle_environ(**{lifecycle_entry.REASON_ENV: " "}), governance
            )

    def test_unknown_operation_is_refused(self):
        with self.assertRaises(lifecycle_entry.LifecycleApplyError):
            lifecycle_entry.resolve_request(
                lifecycle_environ(**{lifecycle_entry.OPERATION_ENV: "explode"}), governance
            )

    def test_every_declared_operation_has_a_declared_connection_effect(self):
        self.assertEqual(
            set(lifecycle_entry.CONNECTION_EFFECT),
            set(governance.DATABASE_OPERATION_TARGET_STATE),
        )
        for operation in governance.DATABASE_OPERATIONS:
            request = lifecycle_entry.resolve_request(
                lifecycle_environ(**{lifecycle_entry.OPERATION_ENV: operation}), governance
            )
            self.assertEqual(request["operation"], operation)

    def test_only_suspension_and_retirement_deny_connections(self):
        self.assertEqual(lifecycle_entry.CUTOFF_EFFECTS, ("deny_connections",))
        denying = sorted(
            operation
            for operation, effect in lifecycle_entry.CONNECTION_EFFECT.items()
            if effect in lifecycle_entry.CUTOFF_EFFECTS
        )
        self.assertEqual(denying, ["retire", "suspend"])


class TestControlPlaneGuard(unittest.TestCase):
    def test_cutting_off_the_control_plane_database_is_refused(self):
        request = lifecycle_entry.resolve_request(
            lifecycle_environ(**{lifecycle_entry.TARGET_ENV: "sc_dev_demo"}), governance
        )
        with self.assertRaises(lifecycle_entry.LifecycleApplyError):
            lifecycle_entry.assert_control_plane_is_not_cut_off(request, "sc_dev_demo")

    def test_a_governed_database_may_be_cut_off(self):
        request = lifecycle_entry.resolve_request(lifecycle_environ(), governance)
        self.assertIs(
            lifecycle_entry.assert_control_plane_is_not_cut_off(request, "sc_dev_demo"), request
        )

    def test_a_non_cutoff_operation_on_the_control_plane_is_allowed(self):
        request = lifecycle_entry.resolve_request(
            lifecycle_environ(
                **{
                    lifecycle_entry.TARGET_ENV: "sc_dev_demo",
                    lifecycle_entry.OPERATION_ENV: "resume",
                }
            ),
            governance,
        )
        self.assertIs(
            lifecycle_entry.assert_control_plane_is_not_cut_off(request, "sc_dev_demo"), request
        )


class TestEffectVerification(unittest.TestCase):
    def test_absent_database_is_only_accepted_for_an_effectless_operation(self):
        self.assertEqual(lifecycle_entry.assert_effect_reached("none", None), "absent")
        for effect in ("require_present", "require_connectable", "deny_connections"):
            with self.assertRaises(lifecycle_entry.LifecycleApplyError):
                lifecycle_entry.assert_effect_reached(effect, None)

    def test_unexpectedly_present_database_is_refused(self):
        with self.assertRaises(lifecycle_entry.LifecycleApplyError):
            lifecycle_entry.assert_effect_reached(
                "none", {"present": True, "allow_connections": True}
            )

    def test_require_present_accepts_a_present_database(self):
        for allow in (True, False):
            self.assertEqual(
                lifecycle_entry.assert_effect_reached(
                    "require_present", {"present": True, "allow_connections": allow}
                ),
                "present",
            )

    def test_require_connectable_needs_an_actually_reachable_database(self):
        self.assertEqual(
            lifecycle_entry.assert_effect_reached(
                "require_connectable", {"present": True, "allow_connections": True}
            ),
            "connectable",
        )
        with self.assertRaises(lifecycle_entry.LifecycleApplyError):
            lifecycle_entry.assert_effect_reached(
                "require_connectable", {"present": True, "allow_connections": False}
            )

    def test_deny_connections_must_be_visible_in_the_catalog(self):
        self.assertEqual(
            lifecycle_entry.assert_effect_reached(
                "deny_connections", {"present": True, "allow_connections": False}
            ),
            "cut_off",
        )
        with self.assertRaises(lifecycle_entry.LifecycleApplyError):
            lifecycle_entry.assert_effect_reached(
                "deny_connections", {"present": True, "allow_connections": True}
            )

    def test_allow_connections_must_be_visible_in_the_catalog(self):
        self.assertEqual(
            lifecycle_entry.assert_effect_reached(
                "allow_connections", {"present": True, "allow_connections": True}
            ),
            "connectable",
        )
        with self.assertRaises(lifecycle_entry.LifecycleApplyError):
            lifecycle_entry.assert_effect_reached(
                "allow_connections", {"present": True, "allow_connections": False}
            )

    def test_effectless_operation_touches_no_connection(self):
        self.assertEqual(lifecycle_entry.apply_connection_effect(None, "sc_test", "none"), 0)


class TestRegisterRequestValidation(unittest.TestCase):
    def test_declared_request_resolves(self):
        request = register_entry.resolve_request(register_environ(), provisioning)
        self.assertEqual(request["db_name"], "sc_test")
        self.assertEqual(request["environment_role"], "industry_acceptance")
        self.assertEqual(request["data_purpose"], "test")
        self.assertTrue(request["output"])

    def test_confirmation_token_is_required(self):
        with self.assertRaises(register_entry.RegisterError):
            register_entry.resolve_request(
                register_environ(**{register_entry.CONFIRM_ENV: ""}), provisioning
            )

    def test_target_database_is_required(self):
        with self.assertRaises(register_entry.RegisterError):
            register_entry.resolve_request(
                register_environ(**{register_entry.TARGET_ENV: " "}), provisioning
            )

    def test_undeclared_purpose_is_refused(self):
        with self.assertRaises(register_entry.RegisterError):
            register_entry.resolve_request(
                register_environ(**{register_entry.PURPOSE_ENV: "sandbox"}), provisioning
            )

    def test_role_must_match_the_declared_purpose(self):
        with self.assertRaises(register_entry.RegisterError):
            register_entry.resolve_request(
                register_environ(**{register_entry.ROLE_ENV: "customer_production"}),
                provisioning,
            )

    def test_reason_is_required(self):
        with self.assertRaises(register_entry.RegisterError):
            register_entry.resolve_request(
                register_environ(**{register_entry.REASON_ENV: " "}), provisioning
            )

    def test_every_declared_purpose_resolves_to_its_declared_role(self):
        for purpose, role in provisioning.PURPOSE_ENVIRONMENT_ROLE.items():
            request = register_entry.resolve_request(
                register_environ(
                    **{
                        register_entry.PURPOSE_ENV: purpose,
                        register_entry.ROLE_ENV: role,
                    }
                ),
                provisioning,
            )
            self.assertEqual(request["data_purpose"], purpose)
            self.assertEqual(request["environment_role"], provisioning.PURPOSE_ENVIRONMENT_ROLE[purpose])


class TestRegistrationCommitReceipt(unittest.TestCase):
    def setUp(self):
        from types import SimpleNamespace
        from unittest.mock import MagicMock, patch
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.env = MagicMock()
        record = self.env.__getitem__.return_value._resolve_entry.return_value
        record.operation_ids.sorted.return_value = [SimpleNamespace(id=61)]
        self.request = register_environ(**{register_entry.OUTPUT_ENV: str(Path(self.tmp.name) / "receipt.json")})
        for name, value in (
            ("load_provisioning", provisioning),
            ("committed_registration_readback", {"lifecycle_state": "declared", "strategy": "demo_from_seed", "operation_request": {"reason": self.request[register_entry.REASON_ENV], "execution_id": "a" * 32}}),
        ):
            patcher = patch.object(register_entry, name, return_value=value)
            setattr(self, name, patcher.start())
            self.addCleanup(patcher.stop)

    def test_success_uses_committed_audit_not_precommit_payload(self):
        result = register_entry.run(self.env, self.request)
        self.assertEqual(result["operation_id"], 61)
        self.assertEqual(result["initial_state"], "declared")
        self.committed_registration_readback.assert_called_once_with(self.env, 61)

    def test_lost_commit_ack_is_resolved_by_exact_audit(self):
        self.env.cr.commit.side_effect = ConnectionError("lost ack")
        result = register_entry.run(self.env, self.request)
        self.assertTrue(result["ok"])
        self.env.cr.rollback.assert_called_once()

    def test_unknown_commit_never_issues_success_receipt(self):
        self.env.cr.commit.side_effect = ConnectionError("lost ack")
        self.committed_registration_readback.side_effect = ConnectionError("unreachable")
        with self.assertRaisesRegex(register_entry.RegisterError, "COMMIT_UNCONFIRMED"):
            register_entry.run(self.env, self.request)
        self.assertFalse(json.loads(Path(self.request[register_entry.OUTPUT_ENV]).read_text())["ok"])

    def test_committed_read_failure_does_not_invite_replay(self):
        self.committed_registration_readback.side_effect = ConnectionError("unreachable")
        with self.assertRaisesRegex(register_entry.RegisterError, "COMMITTED_RECEIPT_FAILED.*do not replay"):
            register_entry.run(self.env, self.request)


class TestLifecycleOrchestration(unittest.TestCase):
    """Exercise ordering, compensation and commit ambiguity, not just tokens."""

    def setUp(self):
        from types import SimpleNamespace
        from unittest.mock import MagicMock, patch
        self.patch = patch
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.environment = lifecycle_environ(**{
            lifecycle_entry.OUTPUT_ENV: str(Path(self.tmp.name) / "receipt.json"),
        })
        self.env = MagicMock()
        self.env.cr.dbname = "sc_control"
        self.registry = self.env.__getitem__.return_value
        self.record = self.registry._resolve_entry.return_value
        self.record.id = 7
        self.record.lifecycle_state = "active"
        self.record.operation_ids.sorted.return_value = [SimpleNamespace(id=55)]
        self.registry._apply_operation.return_value = {
            "lifecycle_state": "suspended", "operation_count": 1,
        }
        self.connection = MagicMock()
        self.connection.cursor.return_value.__enter__.return_value.fetchone.return_value = (True,)
        self.events = []
        self.facts = {"present": True, "allow_connections": True, "sessions": 0}
        self.registry._apply_operation.side_effect = self.prepare
        for name, options in (
            ("load_vocabulary", {"return_value": governance}),
            ("committed_operation_readback", {"return_value": {
                "registration": {"lifecycle_state": "suspended", "operation_count": 1, "last_operation": "suspend", "operation_request": {"reason": self.environment[lifecycle_entry.REASON_ENV], "execution_id": "a" * 32}},
                "audit": {"id": 55, "from_state": "active", "to_state": "suspended"},
            }}),
            ("maintenance_connection", {"return_value": self.connection}),
            ("database_facts", {"side_effect": lambda *_: dict(self.facts)}),
            ("apply_connection_effect", {"side_effect": self.effect}),
        ):
            patcher = patch.object(lifecycle_entry, name, **options)
            setattr(self, name, patcher.start())
            self.addCleanup(patcher.stop)

    def prepare(self, *_, **kwargs):
        self.events.append("model_prepared")
        return {"lifecycle_state": "suspended", "operation_count": 1}

    def effect(self, _connection, _db, effect):
        self.events.append(effect)
        if effect == "deny_connections":
            self.facts["allow_connections"] = False
        elif effect == "allow_connections":
            self.facts["allow_connections"] = True
        return 0

    def test_authority_refusal_opens_no_connection(self):
        self.registry._assert_governance_principal.side_effect = PermissionError("denied")
        with self.assertRaises(PermissionError):
            lifecycle_entry.run(self.env, self.environment)
        self.maintenance_connection.assert_not_called()
        self.apply_connection_effect.assert_not_called()

    def test_committed_audit_must_bind_this_request(self):
        self.committed_operation_readback.return_value["registration"]["operation_request"]["execution_id"] = "b" * 32
        with self.assertRaisesRegex(lifecycle_entry.LifecycleApplyError, "COMMITTED_OPERATION_REQUEST_MISMATCH"):
            lifecycle_entry.run(self.env, self.environment)
        receipt = json.loads(Path(self.environment[lifecycle_entry.OUTPUT_ENV]).read_text())
        self.assertFalse(receipt["ok"])
        self.assertEqual(receipt["effects"]["commit_state"], "committed")
        self.assertNotIn("allow_connections", self.events)

    def test_invalid_transition_has_zero_external_effects(self):
        self.registry._apply_operation.side_effect = ValueError("illegal transition")
        with self.assertRaises(ValueError):
            lifecycle_entry.run(self.env, self.environment)
        self.apply_connection_effect.assert_not_called()
        self.env.cr.commit.assert_not_called()

    def test_busy_object_does_not_prepare_or_mutate(self):
        self.connection.cursor.return_value.__enter__.return_value.fetchone.return_value = (False,)
        with self.assertRaisesRegex(lifecycle_entry.LifecycleApplyError, "BUSY"):
            lifecycle_entry.run(self.env, self.environment)
        self.registry._apply_operation.assert_not_called()
        self.apply_connection_effect.assert_not_called()

    def test_native_model_prepares_before_external_effect(self):
        result = lifecycle_entry.run(self.env, self.environment)
        self.assertEqual(self.events, ["model_prepared", "deny_connections"])
        self.assertEqual(result["operation_id"], 55)
        self.assertEqual(result["database_readback"]["allow_connections"], False)
        self.env.cr.commit.assert_called_once()
        self.connection.close.assert_called_once()

    def test_lock_is_held_through_committed_readback(self):
        def readback(*_):
            self.env.cr.commit.assert_called_once()
            self.connection.close.assert_not_called()
            return {
                "registration": {"lifecycle_state": "suspended", "operation_count": 1, "operation_request": {"reason": self.environment[lifecycle_entry.REASON_ENV], "execution_id": "a" * 32}},
                "audit": {"id": 55, "from_state": "active", "to_state": "suspended"},
            }
        self.committed_operation_readback.side_effect = readback
        lifecycle_entry.run(self.env, self.environment)
        self.connection.close.assert_called_once()

    def test_effect_failure_restores_admission_and_rolls_back(self):
        def fail_after_change(connection, db, effect):
            self.effect(connection, db, effect)
            if effect == "deny_connections":
                raise RuntimeError("terminate failed")
            return 0
        self.apply_connection_effect.side_effect = fail_after_change
        with self.assertRaisesRegex(RuntimeError, "terminate failed"):
            lifecycle_entry.run(self.env, self.environment)
        self.assertTrue(self.facts["allow_connections"])
        receipt = json.loads(Path(self.environment[lifecycle_entry.OUTPUT_ENV]).read_text())
        self.assertTrue(receipt["effects"]["external_started"])
        self.assertIsNone(receipt["effects"]["sessions_terminated"])
        self.assertFalse(receipt["effects"]["terminated_transactions_restorable"])
        self.env.cr.rollback.assert_called()
        self.env.cr.commit.assert_not_called()

    def test_uncommitted_failure_restores_after_authoritative_absence(self):
        self.env.cr.commit.side_effect = RuntimeError("commit failed")
        with self.patch.object(lifecycle_entry, "persisted_operation_state", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "commit failed"):
                lifecycle_entry.run(self.env, self.environment)
        self.assertTrue(self.facts["allow_connections"])

    def test_committed_but_lost_ack_is_not_reverted(self):
        self.env.cr.commit.side_effect = RuntimeError("connection lost")
        with self.patch.object(lifecycle_entry, "persisted_operation_state", return_value=("suspended", "suspended")):
            result = lifecycle_entry.run(self.env, self.environment)
        self.assertTrue(result["ok"])
        self.assertFalse(self.facts["allow_connections"])
        self.assertNotIn("allow_connections", self.events)

    def test_unknown_commit_never_blindly_restores(self):
        self.env.cr.commit.side_effect = RuntimeError("connection lost")
        with self.patch.object(lifecycle_entry, "persisted_operation_state", side_effect=ConnectionError("unreachable")):
            with self.assertRaisesRegex(lifecycle_entry.LifecycleApplyError, "COMMIT_UNKNOWN"):
                lifecycle_entry.run(self.env, self.environment)
        self.assertNotIn("allow_connections", self.events)
        self.assertFalse(json.loads((Path(self.tmp.name) / "receipt.json").read_text())["ok"])

    def test_committed_readback_failure_is_not_reported_as_unexecuted(self):
        self.committed_operation_readback.side_effect = ConnectionError("readback down")
        with self.assertRaisesRegex(lifecycle_entry.LifecycleApplyError, "COMMITTED_RECEIPT_FAILED:operation_id=55"):
            lifecycle_entry.run(self.env, self.environment)
        self.assertNotIn("allow_connections", self.events)
        self.env.cr.commit.assert_called_once()

    def test_failed_recovery_preserves_original_reason(self):
        self.apply_connection_effect.side_effect = [RuntimeError("original effect failed"), RuntimeError("restore failed")]
        with self.assertRaisesRegex(lifecycle_entry.LifecycleApplyError, "RECOVERY_FAILED:original=original effect failed; recovery=restore failed"):
            lifecycle_entry.run(self.env, self.environment)


class TestConnectionEffectOrdering(unittest.TestCase):
    def test_cutoff_precedes_termination_and_false_is_not_success(self):
        from unittest.mock import MagicMock
        connection = MagicMock()
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.fetchall.return_value = [(True,), (False,)]
        with self.assertRaisesRegex(lifecycle_entry.LifecycleApplyError, "TERMINATION_FAILED"):
            lifecycle_entry.apply_connection_effect(connection, "fixture", "deny_connections")
        calls = cursor.execute.call_args_list
        self.assertIn("ALLOW_CONNECTIONS false", calls[0].args[0])
        self.assertIn("pg_terminate_backend(pid, 5000)", calls[1].args[0])

    def test_open_sessions_block_success(self):
        with self.assertRaisesRegex(lifecycle_entry.LifecycleApplyError, "SESSIONS_REMAIN"):
            lifecycle_entry.assert_effect_reached("deny_connections", {
                "present": True, "allow_connections": False, "sessions": 1,
            })


class TestRequestBoundReceipt(unittest.TestCase):
    def test_previous_success_is_invalidated_before_failed_attempt(self):
        from scripts.ops.platform_database_receipt import operation_receipt, validate_success
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "receipt.json"
            path.write_text('{"ok": true}')
            with self.assertRaisesRegex(RuntimeError, "refused"):
                with operation_receipt(path, "test", "a" * 32, {"db": "target"}):
                    pending = json.loads(path.read_text())
                    self.assertFalse(pending["ok"])
                    self.assertEqual(pending["effects"]["commit_state"], "unknown")
                    self.assertFalse(pending["effects"]["replay_allowed"])
                    raise RuntimeError("refused")
            result = json.loads(path.read_text())
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["execution_id"], "a" * 32)
            with self.assertRaises(ValueError):
                validate_success(result, "a" * 32, {"db": "target"})

    def test_consumer_rejects_other_attempt_and_other_request(self):
        from scripts.ops.platform_database_receipt import operation_receipt, validate_success
        with tempfile.TemporaryDirectory() as directory:
            with operation_receipt(Path(directory) / "receipt.json", "test", "a" * 32, {"db": "target"}) as receipt:
                result = receipt.succeed({"ok": True})
            validate_success(result, "a" * 32, {"db": "target"})
            for execution_id, request in [("b" * 32, {"db": "target"}), ("a" * 32, {"db": "other"})]:
                with self.assertRaises(ValueError):
                    validate_success(result, execution_id, request)

    def test_same_output_concurrent_writer_is_refused(self):
        from scripts.ops.platform_database_receipt import operation_receipt
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "receipt.json"
            with operation_receipt(path, "test", "a" * 32, {}):
                with self.assertRaises(BlockingIOError):
                    with operation_receipt(path, "test", "b" * 32, {}):
                        self.fail("concurrent writer entered")
                self.assertEqual(json.loads(path.read_text())["execution_id"], "a" * 32)


if __name__ == "__main__":
    unittest.main()
