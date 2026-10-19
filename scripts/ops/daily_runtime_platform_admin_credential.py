#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Governed runtime binding for the declared platform administrator credential.

Owner ruling (2026-10-20): the platform administrator signs in at
``/platform-admin`` with a simple, owner-maintained default credential.  That
makes the credential a *property of the platform control duty*, not a one-off
shell remark: it is declared beside the duty, its value lives only in the duty's
own 0600 credential file on the governed host, and it is reconciled by this entry
so a rebuilt platform duty comes back with the same administrator instead of
whatever the last hand run left behind.

Three properties are deliberate:

* **Declared, not improvised.**  The login and the credential key come from the
  duty declaration.  A duty that declares nothing is not touched, and a declared
  credential whose value is absent fails closed instead of minting a random
  secret nobody can use.
* **Verify before write.**  Every run first proves whether the declared
  credential already authenticates.  Only a mismatch writes, so a routine refresh
  does not re-hash the password and silently drop live sessions.
* **No credential in evidence.**  The value travels to the container through the
  process environment only; it is never an argv element, never printed and never
  written to a report.  Every receipt this entry prints is a boolean fact.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import daily_runtime_duty_identity as duty_identity  # noqa: E402
import daily_runtime_duty_payload as duty_runtime  # noqa: E402


PLATFORM_CONTROL_DUTY = "platform_control"
PLATFORM_CONTROL_PURPOSE = "platform_control"
DECLARATION_KEY = "admin_credential"
REQUIRED_FIELDS = ("login", "password_env", "purpose")
LOGIN_PATTERN = re.compile(r"^[A-Za-z0-9_.@+-]{1,128}$")
ENV_KEY_PATTERN = re.compile(r"^SC_[A-Z0-9_]{1,64}$")
MARKER = "PLATFORM_ADMIN_CREDENTIAL="
ACTIONS = ("verify", "ensure", "seed")
CONFIRM_ENV = "SC_CONFIRM_PLATFORM_ADMIN_CREDENTIAL"
CONFIRM_VALUE = "ENSURE_DECLARED_PLATFORM_ADMIN_CREDENTIAL"
SEED_CONFIRM_ENV = "SC_CONFIRM_PLATFORM_ADMIN_CREDENTIAL_SEED"
SEED_CONFIRM_VALUE = "REPLACE_DECLARED_PLATFORM_ADMIN_CREDENTIAL"
MODE_ENV = "SC_PLATFORM_ADMIN_CREDENTIAL_MODE"
LOGIN_ENV = "SC_PLATFORM_ADMIN_CREDENTIAL_LOGIN"

#: Runs inside the duty's own Odoo, on stdin, and prints one marked receipt.
#: It is a module constant so the text a test asserts is the text that runs.
PROGRAM = r'''
import json
import os

from odoo.api import Environment
from odoo.exceptions import AccessDenied

from odoo import SUPERUSER_ID

mode = os.environ["SC_PLATFORM_ADMIN_CREDENTIAL_MODE"]
login = os.environ["SC_PLATFORM_ADMIN_CREDENTIAL_LOGIN"]
password = os.environ[os.environ["SC_PLATFORM_ADMIN_CREDENTIAL_PASSWORD_KEY"]]
report = {"mode": mode, "login": login, "matched": 0, "active": False,
          "authenticated": False, "result": "refused", "writes": 0}
users = env["res.users"].with_context(active_test=False).sudo().search([("login", "=", login)])
report["matched"] = len(users)
user = users[:1]
if not user:
    report["result"] = "login_missing"
elif not user.active:
    report["result"] = "login_inactive"
else:
    report["active"] = True

    def authenticates(record):
        target = Environment(env.cr, record.id, {})
        try:
            target["res.users"].browse(record.id)._check_credentials(
                password, {"interactive": False})
            return True
        except AccessDenied:
            return False

    report["authenticated"] = authenticates(user)
    if report["authenticated"]:
        report["result"] = "unchanged"
    elif mode != "ensure":
        report["result"] = "mismatch"
    else:
        user.write({"password": password})
        env.cr.commit()
        report["writes"] = 1
        report["authenticated"] = authenticates(user)
        report["result"] = "applied" if report["authenticated"] else "failed"
print("PLATFORM_ADMIN_CREDENTIAL=" + json.dumps(report, sort_keys=True))
'''


class CredentialEntryError(RuntimeError):
    pass


def _fail(message: str) -> None:
    raise CredentialEntryError(message)


def _text(value) -> str:
    return value.strip() if isinstance(value, str) else ""


def declaration_error(duty: dict) -> str:
    """Why a duty's declared platform administrator credential is unusable.

    The declaration is the authority, so a duty that names a credential without
    saying which login, which credential key or why is refused here rather than
    discovered halfway through a write.
    """
    declaration = duty.get(DECLARATION_KEY)
    if declaration is None:
        return "duty %s declares no %s" % (duty.get("duty") or "<unset>", DECLARATION_KEY)
    if not isinstance(declaration, dict) or not declaration:
        return "duty %s: %s must be a non-empty object" % (duty.get("duty"), DECLARATION_KEY)
    missing = [field for field in REQUIRED_FIELDS if not _text(declaration.get(field))]
    if missing:
        return "duty %s: %s.%s is required" % (
            duty.get("duty"), DECLARATION_KEY, ",".join(missing))
    if not LOGIN_PATTERN.fullmatch(_text(declaration["login"])):
        return "the declared administrator login is not a plain login"
    if not ENV_KEY_PATTERN.fullmatch(_text(declaration["password_env"])):
        return "the declared credential key is not a governed environment key"
    if duty.get("data_purpose") != PLATFORM_CONTROL_PURPOSE:
        return ("the declared administrator credential belongs to the %s duty, not to a %s duty"
                % (PLATFORM_CONTROL_PURPOSE, duty.get("data_purpose")))
    return ""


def validate_declaration(duty: dict) -> dict:
    error = declaration_error(duty)
    if error:
        _fail(error)
    return duty[DECLARATION_KEY]


def resolve_control_duty(declaration: Path | None = None) -> dict:
    """Resolve the control duty, keeping the credential declaration beside it.

    ``duty_identity.resolve`` returns the *runtime* identity of a duty -- the
    names, ports and volumes an entry needs -- and deliberately drops the rest of
    the declaration.  The credential declaration lives in that rest, so it is
    carried over from the reviewed document instead of being re-declared here.
    """
    try:
        duty = duty_identity.resolve(PLATFORM_CONTROL_DUTY, declaration)
        document = duty_identity.load_declaration(declaration)
    except duty_identity.DutyIdentityError as exc:
        _fail(str(exc))
    if duty.get("duty") != PLATFORM_CONTROL_DUTY:
        _fail("the resolved duty is not the platform control duty")
    declared = [item for item in document.get("duties") or []
                if isinstance(item, dict) and item.get("duty") == PLATFORM_CONTROL_DUTY]
    duty = dict(duty, **{DECLARATION_KEY: (declared[0] or {}).get(DECLARATION_KEY) if declared else None})
    validate_declaration(duty)
    return duty


def ops_root_of(declaration: Path | None) -> Path:
    document = duty_identity.load_declaration(declaration)
    ops_root = Path(_text(document.get("ops_root")))
    if not ops_root.is_absolute():
        _fail("the declaration must name an absolute ops root")
    return ops_root


def declared_password(duty: dict, ops_root: Path) -> tuple[str, Path]:
    """The one credential the declaration names, read from the duty's own file."""
    declaration = validate_declaration(duty)
    path = duty_identity.duty_env_path(duty, ops_root, reading=True)
    try:
        values = duty_runtime.read_duty_env(path, duty)
    except duty_runtime.PayloadEntryError as exc:
        _fail(str(exc))
    value = _text(values.get(declaration["password_env"]))
    if not value:
        _fail("the declared credential %s is absent from the duty environment; set it on the "
              "governed host instead of letting this entry invent one" % declaration["password_env"])
    if "\n" in value or "\x00" in value:
        _fail("the declared credential contains a line break or NUL and cannot be rendered")
    return value, path


def seed_target(duty: dict, ops_root: Path) -> Path:
    """The file that must carry the declared credential, created if absent."""
    path = Path(duty_identity.duty_env_path(duty, ops_root))
    if path.is_symlink():
        _fail("the duty environment is a symlink; refusing to write a credential through it")
    return path


def seed_declaration(duty: dict, ops_root: Path, value: str, replace: bool) -> dict:
    """Record the operator-supplied credential in the duty's own 0600 file.

    This is the only write path that *introduces* the declared value.  It never
    mints a secret: the value arrives on stdin, is written once, and every later
    step reads it back.  A different existing value is only replaced with an
    explicit confirmation, so a routine seed cannot silently rotate the
    administrator's password.
    """
    declaration = validate_declaration(duty)
    key = declaration["password_env"]
    if not value:
        _fail("the supplied administrator credential is empty")
    if "\n" in value or "\r" in value or "\x00" in value:
        _fail("the supplied administrator credential contains a line break or NUL")
    path = seed_target(duty, ops_root)
    if path.exists() and path.is_dir():
        _fail("the duty environment path is a directory")
    existing = ""
    lines = []
    if path.exists():
        mode = path.stat().st_mode & 0o777
        if mode != 0o600:
            _fail("the duty environment is mode %s; refusing to write a credential into it"
                  % (oct(mode),))
        for row in path.read_text(encoding="utf-8").splitlines():
            if row.startswith(key + "="):
                existing = row[len(key) + 1:]
                continue
            lines.append(row)
    if existing and existing != value and not replace:
        _fail("%s already carries another value; reuse --replace with %s=%s to rotate it"
              % (key, SEED_CONFIRM_ENV, SEED_CONFIRM_VALUE))
    if existing == value:
        return {"seeded": False, "replaced": False, "value_env": key, "path": str(path)}
    if not path.parent.exists():
        _fail("the governed ops root does not exist: %s" % (path.parent,))
    lines.append("%s=%s" % (key, value))
    temporary = path.with_name(path.name + ".seed")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        stream.write("\n".join(lines) + "\n")
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)
    if (path.stat().st_mode & 0o777) != 0o600:
        _fail("the seeded duty environment is not mode 0600")
    observed = ""
    for row in path.read_text(encoding="utf-8").splitlines():
        if row.startswith(key + "="):
            observed = row[len(key) + 1:]
    if observed != value:
        _fail("the seeded credential did not read back from the duty environment")
    return {"seeded": True, "replaced": bool(existing), "value_env": key, "path": str(path)}


def command_for(duty: dict, ops_root: Path, env_path: Path, stack: Path, declaration: dict) -> list[str]:
    return duty_runtime.compose_base(duty, ops_root, env_path, stack) + [
        "run", "--rm", "--no-deps", "-T",
        "--label", "sc.daily-duty-platform-admin-credential=true",
        "--label", "sc.daily-duty=%s" % duty["duty"],
        "-e", MODE_ENV,
        "-e", LOGIN_ENV,
        "-e", declaration["password_env"],
        "--entrypoint", duty_runtime.APPLICATION_ENTRY,
        "odoo", "shell", "-c", duty_runtime.ODOO_CONF,
        "-d", duty["database"],
        "--no-http", "--log-level=error",
    ]


def marked_report(output: str) -> dict:
    for line in reversed((output or "").splitlines()):
        row = line.strip()
        if row.startswith(MARKER):
            try:
                report = json.loads(row[len(MARKER):])
            except json.JSONDecodeError as exc:
                _fail("the administrator credential report is not JSON: %s" % (exc,))
            if not isinstance(report, dict):
                _fail("the administrator credential report is not an object")
            return report
    _fail("the administrator credential step emitted no report")


def verdict(action: str, report: dict, declaration: dict) -> dict:
    """Assert the received facts; a claim of success alone is not evidence."""
    if _text(report.get("login")) != declaration["login"]:
        _fail("the report names another login than the declared administrator")
    if int(report.get("matched") or 0) != 1:
        _fail("the declared administrator login does not identify exactly one account")
    if report.get("active") is not True:
        _fail("the declared administrator account is not active")
    if report.get("authenticated") is not True:
        _fail("the declared credential does not authenticate the declared administrator")
    writes = int(report.get("writes") or 0)
    result = _text(report.get("result"))
    if action == "verify" and writes != 0:
        _fail("a verification run wrote to the duty")
    if action == "ensure" and result not in ("unchanged", "applied"):
        _fail("the credential reconcile did not report an applied or unchanged state")
    return {
        "login": declaration["login"],
        "password_env": declaration["password_env"],
        "result": result,
        "writes": writes,
        "authenticated": True,
    }


def execute(action: str, declaration_path: Path | None = None) -> dict:
    if action not in ACTIONS:
        _fail("unsupported platform administrator credential action: %s" % action)
    if action == "seed":
        duty = resolve_control_duty(declaration_path)
        validate_declaration(duty)
        ops_root = ops_root_of(declaration_path)
        value = sys.stdin.readline().rstrip("\r\n")
        replace = os.environ.get(SEED_CONFIRM_ENV) == SEED_CONFIRM_VALUE
        return seed_declaration(duty, ops_root, value, replace=replace)
    if action == "ensure" and os.environ.get(CONFIRM_ENV) != CONFIRM_VALUE:
        _fail("%s=%s is required" % (CONFIRM_ENV, CONFIRM_VALUE))
    duty = resolve_control_duty(declaration_path)
    declaration = validate_declaration(duty)
    ops_root = ops_root_of(declaration_path)
    password, env_path = declared_password(duty, ops_root)
    stack = duty_runtime.stack_compose_path(ops_root)
    duty_runtime.inspect_odoo_container(duty, duty_runtime.read_duty_env(env_path, duty))
    command = command_for(duty, ops_root, env_path, stack, declaration)

    environ = {
        MODE_ENV: action,
        LOGIN_ENV: declaration["login"],
        declaration["password_env"]: password,
    }
    saved = {key: os.environ.get(key) for key in environ}
    os.environ.update(environ)
    try:
        output = duty_runtime.run(command, input=PROGRAM, cwd=str(ops_root))
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    return verdict(action, marked_report(output), declaration)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=ACTIONS)
    parser.add_argument("--declaration", default=None)
    args = parser.parse_args(argv)
    try:
        result = execute(args.action, Path(args.declaration) if args.declaration else None)
    except (CredentialEntryError, duty_runtime.PayloadEntryError) as exc:
        print("[platform.admin.credential] FAILED: %s" % (exc,))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
