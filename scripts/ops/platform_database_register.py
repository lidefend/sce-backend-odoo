#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Governed ops entry for platform database registration.

Owner ruling (2026-10-14): a database is a governed object, not an ambient
convention. The platform model owns the registration fact; this ops entry is
its only production writer. It resolves the environment role, the data purpose
and the strategy from the declaration -- it never decides a tenant, a purpose or
an initialization rule by itself -- and it fails closed unless the operator
presents the explicit confirmation.

This internal adapter requires a governed profile wrapper with an exact control
plane/target/cluster identity. That runtime binding is pending; importing or
unit-testing this module does not authorize an operator to assemble a shell
command or execute a real database lifecycle change.

The module body only needs the standard library, so the pure decision helpers
stay importable by a hermetic unit test.
"""

from __future__ import annotations

import os

from scripts.ops.platform_database_receipt import operation_receipt

ENTRY = "platform.database.register"
CONFIRM_ENV = "SC_CONFIRM_PLATFORM_DATABASE_REGISTRY"
CONFIRM_VALUE = "REGISTER_GOVERNED_PLATFORM_DATABASE"
TARGET_ENV = "PLATFORM_DATABASE_REGISTER_DB"
ROLE_ENV = "PLATFORM_DATABASE_REGISTER_ENVIRONMENT_ROLE"
PURPOSE_ENV = "PLATFORM_DATABASE_REGISTER_DATA_PURPOSE"
TENANT_ENV = "PLATFORM_DATABASE_REGISTER_TENANT_KEY"
DBFILTER_ENV = "PLATFORM_DATABASE_REGISTER_DBFILTER"
REASON_ENV = "PLATFORM_DATABASE_REGISTER_REASON"
OUTPUT_ENV = "PLATFORM_DATABASE_REGISTER_OUTPUT"
DEFAULT_OUTPUT = "/tmp/platform_database_register.json"

#: The onboarding declaration vocabulary this entry consumes. It is addressed by
#: its Odoo module identity -- the same dotted path the platform model layer
#: imports -- so the entry can never drift onto a second, filesystem copy of the
#: declaration.
VOCABULARY_MODULE = "odoo.addons.smart_core.security.data_space_provisioning"


class RegisterError(RuntimeError):
    """Any fail-closed refusal of this entry."""


def load_provisioning():
    import importlib

    try:
        return importlib.import_module(VOCABULARY_MODULE)
    except ImportError as error:
        raise RegisterError(
            "PLATFORM_DATABASE_REGISTER_VOCABULARY_UNRESOLVED:%s" % (VOCABULARY_MODULE,)
        ) from error


def resolve_request(environ, provisioning):
    """Validate the request against the onboarding declaration, fail closed."""
    if str(environ.get(CONFIRM_ENV) or "").strip() != CONFIRM_VALUE:
        raise RegisterError("PLATFORM_DATABASE_REGISTER_CONFIRMATION_REQUIRED:%s" % (CONFIRM_ENV,))
    target = str(environ.get(TARGET_ENV) or "").strip()
    if not target:
        raise RegisterError("PLATFORM_DATABASE_REGISTER_DB_REQUIRED")
    role = str(environ.get(ROLE_ENV) or "").strip()
    purpose = str(environ.get(PURPOSE_ENV) or "").strip()
    if purpose not in provisioning.PURPOSE_STRATEGY:
        raise RegisterError("PLATFORM_DATABASE_REGISTER_PURPOSE_UNDECLARED:%s" % (purpose,))
    declared_role = provisioning.PURPOSE_ENVIRONMENT_ROLE.get(purpose)
    if role != declared_role:
        raise RegisterError(
            "PLATFORM_DATABASE_REGISTER_ROLE_PURPOSE_MISMATCH:%s:%s" % (role, purpose)
        )
    reason = str(environ.get(REASON_ENV) or "").strip()
    if not reason:
        raise RegisterError("PLATFORM_DATABASE_REGISTER_REASON_REQUIRED")
    return {
        "db_name": target,
        "environment_role": role,
        "data_purpose": purpose,
        "tenant_key": str(environ.get(TENANT_ENV) or "").strip(),
        "dbfilter": str(environ.get(DBFILTER_ENV) or "").strip(),
        "reason": reason,
        "output": str(environ.get(OUTPUT_ENV) or DEFAULT_OUTPUT).strip() or DEFAULT_OUTPUT,
    }


def committed_registration_readback(env, operation_id):
    """Read the immutable audit after commit using an independent transaction."""
    from odoo.api import Environment

    with env.registry.cursor() as cursor:
        independent = Environment(cursor, env.uid, {})
        operation = independent["sc.platform.database.operation"].browse(operation_id).exists()
        if not operation or operation.operation != "register":
            raise RegisterError("PLATFORM_DATABASE_REGISTER_COMMIT_UNCONFIRMED")
        return dict(operation.result)


def _run_operation(env, environ, receipt):
    provisioning = load_provisioning()
    request = resolve_request(environ, provisioning)
    Registry = env["sc.platform.database.registration"]
    readback = Registry._register_database(
        db_name=request["db_name"],
        environment_role=request["environment_role"],
        data_purpose=request["data_purpose"],
        tenant_key=request["tenant_key"],
        dbfilter=request["dbfilter"],
        reason=request["reason"], execution_id=receipt.identity["execution_id"],
    )
    record = Registry._resolve_entry(request["db_name"])
    operation_id = record.operation_ids.sorted("id")[-1].id
    receipt.effects["operation_id"] = operation_id
    try:
        receipt.effects["commit_state"] = "unknown"
        env.cr.commit()
    except Exception as error:
        try:
            env.cr.rollback()
        except Exception:
            pass
        try:
            readback = committed_registration_readback(env, operation_id)
        except Exception as read_error:
            raise RegisterError(
                "PLATFORM_DATABASE_REGISTER_COMMIT_UNCONFIRMED:operation_id=%s; do not replay"
                % operation_id
            ) from read_error
    else:
        try:
            readback = committed_registration_readback(env, operation_id)
        except Exception as error:
            raise RegisterError(
                "PLATFORM_DATABASE_REGISTER_COMMITTED_RECEIPT_FAILED:operation_id=%s; do not replay"
                % operation_id
            ) from error
    receipt.effects["commit_state"] = "committed"
    if readback.get("operation_request") != {
        "reason": request["reason"], "execution_id": receipt.identity["execution_id"],
    }:
        raise RegisterError("COMMITTED_OPERATION_REQUEST_MISMATCH:operation_id=%s; do not replay" % operation_id)
    result = {
        "ok": True,
        "entry": ENTRY,
        "operation_id": operation_id,
        "db_name": request["db_name"],
        "environment_role": request["environment_role"],
        "data_purpose": request["data_purpose"],
        "reason": request["reason"],
        "initial_state": readback["lifecycle_state"],
        "strategy": readback["strategy"],
        "registration_readback": readback,
    }
    receipt.effects["commit_state"] = "committed"
    try:
        return receipt.succeed(result)
    except Exception as error:
        raise RegisterError(
            "PLATFORM_DATABASE_REGISTER_COMMITTED_RECEIPT_FAILED:operation_id=%s; do not replay"
            % operation_id
        ) from error



def run(env, environ):
    request_identity = {key: str(environ.get(key) or "") for key in (
        "PLATFORM_DATABASE_REGISTER_DB",
        "PLATFORM_DATABASE_REGISTER_ENVIRONMENT_ROLE",
        "PLATFORM_DATABASE_REGISTER_DATA_PURPOSE",
        "PLATFORM_DATABASE_REGISTER_TENANT_KEY",
        "PLATFORM_DATABASE_REGISTER_DBFILTER",
        "PLATFORM_DATABASE_REGISTER_REASON",
    )}
    output = str(environ.get(OUTPUT_ENV) or DEFAULT_OUTPUT).strip() or DEFAULT_OUTPUT
    with operation_receipt(output, ENTRY, environ.get("PLATFORM_DATABASE_EXECUTION_ID"),
                           request_identity) as receipt:
        return _run_operation(env, environ, receipt)


def _entrypoint():
    shell_env = globals().get("env")
    if shell_env is None:
        raise SystemExit(
            "platform database registration must run through odoo shell "
            "(scripts/ops/odoo_shell_exec.sh)"
        )
    try:
        result = run(shell_env, os.environ)
    except Exception as error:
        print("[%s] FAILED: %s" % (ENTRY, error))
        raise
    print(
        "[%s] %s registered as %s/%s (state=%s)"
        % (
            ENTRY,
            result["db_name"],
            result["environment_role"],
            result["data_purpose"],
            result["initial_state"],
        )
    )


try:
    env  # noqa: B018 - provided by odoo shell
except NameError:
    pass
else:
    _entrypoint()
