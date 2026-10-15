#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Governed ops entry for the platform database lifecycle.

Owner ruling (2026-10-14): the platform side owns database registration, the
lifecycle state, the managed operation entry and the result readback; the *ops
tool* performs the actual execution and never decides a tenant, a purpose or an
initialization rule on its own. This module is that ops tool. It is the only
production caller of ``sc.platform.database.registration._apply_operation`` and
it is what turns a lifecycle state into a real environment fact:

* the registration state (declared/provisioned/active/suspended/retired) is
  written by the governed model entry, which refuses an operation the
  declaration does not authorize and appends one audit row per operation;
* ``suspend``/``retire`` additionally make the governed database unreachable by
  PostgreSQL (``datallowconn = false`` plus terminated sessions), ``resume``
  restores it, ``activate`` only accepts an already reachable database and
  ``provision`` only requires the database to exist. A state change is never
  reported as an environment change unless the catalog readback shows it.

This internal adapter requires a governed profile wrapper with an exact control
plane/target/cluster identity. That runtime binding is pending; importing or
unit-testing this module does not authorize an operator to assemble a shell
command or execute a real database lifecycle change.

The module body only needs the standard library, so the pure decision helpers
below stay importable by a hermetic unit test; Odoo and psycopg2 are imported
lazily inside the shell-only path.
"""

from __future__ import annotations

import os

from scripts.ops.platform_database_receipt import operation_receipt

ENTRY = "platform.database.lifecycle.apply"
CONFIRM_ENV = "SC_CONFIRM_PLATFORM_DATABASE_LIFECYCLE"
CONFIRM_VALUE = "APPLY_GOVERNED_PLATFORM_DATABASE_LIFECYCLE_OPERATION"
TARGET_ENV = "PLATFORM_DATABASE_LIFECYCLE_DB"
OPERATION_ENV = "PLATFORM_DATABASE_LIFECYCLE_OPERATION"
REASON_ENV = "PLATFORM_DATABASE_LIFECYCLE_REASON"
OUTPUT_ENV = "PLATFORM_DATABASE_LIFECYCLE_OUTPUT"
DEFAULT_OUTPUT = "/tmp/platform_database_lifecycle_apply.json"

#: Operation -> the connection-level fact the database must show. ``none`` is an
#: honest answer only for a database that was never created in the cluster.
CONNECTION_EFFECT = {
    "provision": "require_present",
    "activate": "require_connectable",
    "suspend": "deny_connections",
    "resume": "allow_connections",
    "retire": "deny_connections",
    "abandon": "none",
}

#: Operations that cut the governed database off, so applying one to the
#: database that is serving the platform control plane would destroy the very
#: governance surface that authorizes it.
CUTOFF_EFFECTS = ("deny_connections",)

#: The declaration vocabulary this entry consumes. It is addressed by its Odoo
#: module identity -- the same dotted path the platform model layer imports -- so
#: the entry can never drift onto a second, filesystem copy of the declaration.
VOCABULARY_MODULE = "odoo.addons.smart_core.security.database_governance"


class LifecycleApplyError(RuntimeError):
    """Any fail-closed refusal or unverifiable outcome of this entry."""


def load_vocabulary():
    """Import the declaration vocabulary without restating it here."""
    import importlib

    try:
        return importlib.import_module(VOCABULARY_MODULE)
    except ImportError as error:
        raise LifecycleApplyError(
            "DATABASE_GOVERNANCE_VOCABULARY_UNRESOLVED:%s" % (VOCABULARY_MODULE,)
        ) from error


def resolve_request(environ, vocabulary):
    """Validate the operator request against the declaration, fail closed."""
    if str(environ.get(CONFIRM_ENV) or "").strip() != CONFIRM_VALUE:
        raise LifecycleApplyError(
            "PLATFORM_DATABASE_LIFECYCLE_CONFIRMATION_REQUIRED:%s" % (CONFIRM_ENV,)
        )
    target = str(environ.get(TARGET_ENV) or "").strip()
    if not target:
        raise LifecycleApplyError("PLATFORM_DATABASE_LIFECYCLE_DB_REQUIRED")
    operation = str(environ.get(OPERATION_ENV) or "").strip()
    if operation not in vocabulary.DATABASE_OPERATIONS:
        raise LifecycleApplyError("PLATFORM_DATABASE_LIFECYCLE_OPERATION_UNKNOWN:%s" % (operation,))
    reason = str(environ.get(REASON_ENV) or "").strip()
    if not reason:
        raise LifecycleApplyError("PLATFORM_DATABASE_LIFECYCLE_REASON_REQUIRED")
    effect = CONNECTION_EFFECT.get(operation)
    if effect is None:
        raise LifecycleApplyError("PLATFORM_DATABASE_LIFECYCLE_EFFECT_UNDECLARED:%s" % (operation,))
    return {
        "db_name": target,
        "operation": operation,
        "reason": reason,
        "connection_effect": effect,
        "output": str(environ.get(OUTPUT_ENV) or DEFAULT_OUTPUT).strip() or DEFAULT_OUTPUT,
    }


def assert_control_plane_is_not_cut_off(request, control_plane_db):
    """Refuse to suspend the database the governance entry itself runs on."""
    if request["connection_effect"] in CUTOFF_EFFECTS and (
        request["db_name"] == str(control_plane_db or "").strip()
    ):
        raise LifecycleApplyError(
            "PLATFORM_DATABASE_LIFECYCLE_CONTROL_PLANE_CUTOFF_REFUSED:%s" % (request["db_name"],)
        )
    return request


def assert_effect_reached(effect, facts):
    """The database must show the declared connection fact, or there is no proof."""
    if facts is None:
        if effect == "none":
            return "absent"
        raise LifecycleApplyError("PLATFORM_DATABASE_LIFECYCLE_DATABASE_NOT_PRESENT")
    if effect == "none":
        raise LifecycleApplyError("PLATFORM_DATABASE_LIFECYCLE_DATABASE_UNEXPECTEDLY_PRESENT")
    if effect == "require_present":
        return "present"
    if effect == "require_connectable" and not facts["allow_connections"]:
        raise LifecycleApplyError("PLATFORM_DATABASE_LIFECYCLE_DATABASE_NOT_CONNECTABLE")
    if effect == "deny_connections" and facts["allow_connections"]:
        raise LifecycleApplyError("PLATFORM_DATABASE_LIFECYCLE_CONNECTIONS_STILL_ALLOWED")
    if effect == "allow_connections" and not facts["allow_connections"]:
        raise LifecycleApplyError("PLATFORM_DATABASE_LIFECYCLE_CONNECTIONS_STILL_DENIED")
    if effect == "deny_connections" and facts.get("sessions", 0):
        raise LifecycleApplyError("PLATFORM_DATABASE_LIFECYCLE_SESSIONS_REMAIN")
    return "connectable" if facts["allow_connections"] else "cut_off"


def maintenance_connection(database="postgres"):
    """Open an autocommit connection for statements PostgreSQL forbids in a tx."""
    import psycopg2
    import json
    from pathlib import Path

    config_path = os.environ.get("PLATFORM_DATABASE_MAINTENANCE_CONFIG")
    if not config_path:
        raise LifecycleApplyError("PLATFORM_DATABASE_MAINTENANCE_IDENTITY_REQUIRED")
    config = json.loads(Path(config_path).read_text())
    if set(config) != {"host", "port", "user", "password", "cluster_system_identifier"} or not all(config.values()):
        raise LifecycleApplyError("PLATFORM_DATABASE_MAINTENANCE_IDENTITY_INVALID")
    expected_cluster = str(config.pop("cluster_system_identifier"))
    connection = psycopg2.connect(dbname=database, connect_timeout=5, **config)
    connection.autocommit = True
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT system_identifier FROM pg_control_system()")
            if str(cursor.fetchone()[0]) != expected_cluster:
                raise LifecycleApplyError("PLATFORM_DATABASE_MAINTENANCE_CLUSTER_MISMATCH")
    except BaseException:
        connection.close()
        raise
    return connection


def database_facts(connection, db_name):
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT datallowconn, (SELECT count(*) FROM pg_stat_activity WHERE datname = %s) "
            "FROM pg_database WHERE datname = %s", (db_name, db_name)
        )
        row = cursor.fetchone()
    if not row:
        return None
    return {"present": True, "allow_connections": bool(row[0]), "sessions": row[1]}


def apply_connection_effect(connection, db_name, effect):
    """Return the number of sessions terminated while reaching the fact."""
    if effect == "none":
        return 0
    quoted = '"%s"' % db_name.replace('"', '""')
    with connection.cursor() as cursor:
        # Stop admission before terminating existing sessions; the reverse
        # order permits clients to reconnect between the two statements.
        if effect in CUTOFF_EFFECTS or effect == "allow_connections":
            cursor.execute(
                "ALTER DATABASE %s ALLOW_CONNECTIONS %s"
                % (quoted, "false" if effect in CUTOFF_EFFECTS else "true")
            )
        if effect in CUTOFF_EFFECTS:
            # P4 transport mechanism: wait at most 5s per backend for actual
            # exit, not merely signal delivery (PostgreSQL 15 bound runtime).
            cursor.execute(
                "SELECT pg_terminate_backend(pid, 5000) FROM pg_stat_activity "
                "WHERE datname = %s AND pid <> pg_backend_pid()", (db_name,),
            )
            outcomes = cursor.fetchall()
            if any(not row[0] for row in outcomes):
                raise LifecycleApplyError("PLATFORM_DATABASE_LIFECYCLE_TERMINATION_FAILED")
            return len(outcomes)
    return 0


def persisted_operation_state(control_db, operation_id):
    """Resolve an uncertain commit using the exact audit row, not a retry."""
    connection = maintenance_connection(control_db)
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT r.lifecycle_state, o.to_state "
                "FROM sc_platform_database_operation o "
                "JOIN sc_platform_database_registration r ON r.id = o.registration_id "
                "WHERE o.id = %s", (operation_id,),
            )
            return cursor.fetchone()
    finally:
        connection.close()


def committed_operation_readback(control_db, operation_id):
    connection = maintenance_connection(control_db)
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT o.result, o.from_state, o.to_state, r.lifecycle_state "
                "FROM sc_platform_database_operation o "
                "JOIN sc_platform_database_registration r ON r.id = o.registration_id "
                "WHERE o.id = %s", (operation_id,),
            )
            row = cursor.fetchone()
            if not row or row[2] != row[3]:
                raise LifecycleApplyError("COMMITTED_OPERATION_READBACK_MISMATCH")
            return {"registration": row[0], "audit": {
                "id": operation_id, "from_state": row[1], "to_state": row[2],
            }}
    finally:
        connection.close()


def _run_operation(env, environ, receipt):
    """Apply one governed lifecycle operation and prove the environment fact."""
    vocabulary = load_vocabulary()
    request = resolve_request(environ, vocabulary)
    assert_control_plane_is_not_cut_off(request, env.cr.dbname)

    Registry = env["sc.platform.database.registration"]
    # Validate authority before opening a maintenance connection, let alone
    # changing admission or killing another user's transaction.
    Registry._assert_governance_principal()
    record = Registry._resolve_entry(request["db_name"])
    connection = maintenance_connection()
    before = None
    external_started = False
    committed = False
    commit_unknown = False
    try:
        # Session advisory lock survives the ORM commit and covers compensation.
        # All operations on this exact cluster/database serialize here.
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT pg_try_advisory_lock(hashtextextended(%s, 0))",
                ("sc.platform.database:" + request["db_name"],),
            )
            if not cursor.fetchone()[0]:
                raise LifecycleApplyError("PLATFORM_DATABASE_LIFECYCLE_BUSY")
        env.cr.execute(
            "SELECT id FROM sc_platform_database_registration WHERE id = %s FOR UPDATE NOWAIT",
            (record.id,),
        )
        record.invalidate_recordset()
        from_state = record.lifecycle_state
        # The model owns the state machine. Prepare its transaction before
        # touching PostgreSQL; a refusal has zero external effects.
        readback = Registry._apply_operation(
            request["db_name"], request["operation"],
            reason=request["reason"], execution_id=receipt.identity["execution_id"],
        )
        operation_id = record.operation_ids.sorted("id")[-1].id
        receipt.effects["operation_id"] = operation_id
        before = database_facts(connection, request["db_name"])
        receipt.effects["before"] = before
        if before is None and request["connection_effect"] != "none":
            raise LifecycleApplyError("PLATFORM_DATABASE_LIFECYCLE_DATABASE_NOT_PRESENT")
        external_started = request["connection_effect"] in ("deny_connections", "allow_connections")
        receipt.effects.update(external_started=external_started, sessions_terminated=None,
                               compensation_scope="connection_admission_only", terminated_transactions_restorable=False)
        terminated = apply_connection_effect(connection, request["db_name"], request["connection_effect"])
        receipt.effects["sessions_terminated"] = terminated
        after = database_facts(connection, request["db_name"])
        effect_state = assert_effect_reached(request["connection_effect"], after)
        try:
            receipt.effects["commit_state"] = "unknown"
            env.cr.commit()
            committed = True
            receipt.effects["commit_state"] = "committed"
        except Exception as commit_error:
            rollback_confirmed = False
            try:
                env.cr.rollback()
                rollback_confirmed = True
            except Exception:
                pass
            try:
                persisted = persisted_operation_state(env.cr.dbname, operation_id)
            except Exception as read_error:
                commit_unknown = True
                raise LifecycleApplyError(
                    "PLATFORM_DATABASE_LIFECYCLE_COMMIT_UNKNOWN:operation_id=%s; "
                    "readback failed=%s; do not replay or compensate blindly"
                    % (operation_id, type(read_error).__name__)
                ) from commit_error
            if persisted is None:
                if not rollback_confirmed:
                    commit_unknown = True
                    raise LifecycleApplyError(
                        "PLATFORM_DATABASE_LIFECYCLE_COMMIT_UNKNOWN:operation_id=%s" % operation_id
                    ) from commit_error
                receipt.effects["commit_state"] = "not_committed"
                raise
            if tuple(persisted) != (readback["lifecycle_state"], readback["lifecycle_state"]):
                commit_unknown = True
                raise LifecycleApplyError(
                    "PLATFORM_DATABASE_LIFECYCLE_COMMIT_CONFLICT:operation_id=%s" % operation_id
                ) from commit_error
            committed = True
            receipt.effects["commit_state"] = "committed"
        # Keep the cluster/database lock through committed authoritative reads.
        # The audit snapshot belongs to this operation, never a later last_readback.
        try:
            committed_readback = committed_operation_readback(env.cr.dbname, operation_id)
            after = database_facts(connection, request["db_name"])
            effect_state = assert_effect_reached(request["connection_effect"], after)
        except Exception as error:
            raise LifecycleApplyError(
                "PLATFORM_DATABASE_LIFECYCLE_COMMITTED_RECEIPT_FAILED:operation_id=%s; do not replay"
                % operation_id
            ) from error
    except Exception as original_error:
        try:
            env.cr.rollback()
        except Exception:
            pass  # Preserve the original outcome and still reconcile admission.
        if external_started and not committed and not commit_unknown and before is not None:
            try:
                apply_connection_effect(
                    connection, request["db_name"],
                    "allow_connections" if before["allow_connections"] else "deny_connections",
                )
                restored = database_facts(connection, request["db_name"])
                receipt.effects["compensation_readback"] = restored
                assert_effect_reached(
                    "allow_connections" if before["allow_connections"] else "deny_connections", restored
                )
            except Exception as recovery_error:
                raise LifecycleApplyError(
                    "PLATFORM_DATABASE_LIFECYCLE_RECOVERY_FAILED:original=%s; recovery=%s"
                    % (original_error, recovery_error)
                ) from original_error
        raise
    finally:
        connection.close()  # Releases the session advisory lock, including on failure.

    readback = committed_readback["registration"]
    if readback.get("operation_request") != {
        "reason": request["reason"], "execution_id": receipt.identity["execution_id"],
    }:
        raise LifecycleApplyError("COMMITTED_OPERATION_REQUEST_MISMATCH:operation_id=%s; do not replay" % operation_id)
    result = {
        "ok": True,
        "entry": ENTRY,
        "db_name": request["db_name"],
        "operation": request["operation"],
        "operation_id": operation_id,
        "reason": request["reason"],
        "from_state": from_state,
        "to_state": readback["lifecycle_state"],
        "connection_effect": request["connection_effect"],
        "environment_effect": effect_state,
        "sessions_terminated": terminated,
        "control_plane_db": env.cr.dbname,
        "audit_operations": readback["operation_count"],
        "registration_readback": readback,
        "operation_readback": committed_readback["audit"],
        "database_readback": after,
    }
    receipt.effects["commit_state"] = "committed"
    try:
        return receipt.succeed(result)
    except Exception as error:
        raise LifecycleApplyError(
            "PLATFORM_DATABASE_LIFECYCLE_COMMITTED_RECEIPT_FAILED:operation_id=%s; do not replay"
            % operation_id
        ) from error



def run(env, environ):
    request_identity = {key: str(environ.get(key) or "") for key in (
        "PLATFORM_DATABASE_LIFECYCLE_DB",
        "PLATFORM_DATABASE_LIFECYCLE_OPERATION",
        "PLATFORM_DATABASE_LIFECYCLE_REASON",
    )}
    output = str(environ.get(OUTPUT_ENV) or DEFAULT_OUTPUT).strip() or DEFAULT_OUTPUT
    with operation_receipt(output, ENTRY, environ.get("PLATFORM_DATABASE_EXECUTION_ID"),
                           request_identity) as receipt:
        return _run_operation(env, environ, receipt)


def _odoo_shell_env():
    """Return the odoo shell env, or None when imported outside odoo shell."""
    return globals().get("env")


def _entrypoint():
    shell_env = _odoo_shell_env()
    if shell_env is None:
        raise SystemExit(
            "platform database lifecycle entry must run through odoo shell "
            "(scripts/ops/odoo_shell_exec.sh)"
        )
    try:
        result = run(shell_env, os.environ)
    except Exception as error:  # fail closed, and leave the reason on stdout
        print("[%s] FAILED: %s" % (ENTRY, error))
        raise
    print(
        "[%s] %s %s: %s -> %s (effect=%s, terminated=%s)"
        % (
            ENTRY,
            result["db_name"],
            result["operation"],
            result["from_state"],
            result["to_state"],
            result["environment_effect"],
            result["sessions_terminated"],
        )
    )


try:
    env  # noqa: B018 - provided by odoo shell
except NameError:
    pass
else:
    _entrypoint()
