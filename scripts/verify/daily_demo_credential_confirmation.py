#!/usr/bin/env python3
"""Derive the daily read-only credential confirmation for the fixed demo account.

The acceptance environment refuses known default passwords on the daily profile
unless the caller presents a short-lived, identity-bound confirmation. The owner
fixed the internal demo password in
``config/acceptance/daily_demo_credential.v1.json``, so the governed lane derives
that confirmation itself instead of asking a human to hand-write JSON on every
run.

This helper does not bypass the guard: it only confirms the declared daily demo
login, the declared tool and the read-only operation, and only when the supplied
password is exactly the declared fixed demo password. Every other weak or
default credential remains refused by
``scripts/verify/lib/frontend_acceptance_environment.mjs``.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DECLARATION = ROOT / "config" / "acceptance" / "daily_demo_credential.v1.json"
SCHEMA = "daily-readonly-credential-confirmation.v1"
DECLARATION_SCHEMA = "daily_demo_credential.v1"


class ConfirmationError(RuntimeError):
    """The declared fixed demo identity does not match the requested run."""


def load_declaration(path: Path) -> dict:
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("schema") != DECLARATION_SCHEMA:
        raise ConfirmationError(f"declaration schema must be {DECLARATION_SCHEMA}")
    if document.get("profile") != "daily":
        raise ConfirmationError("declaration profile must be daily")
    if document.get("operation") != "readonly":
        raise ConfirmationError("declaration operation must be readonly")
    password = str(document.get("password") or "")
    if not password:
        raise ConfirmationError("declaration must name the fixed demo password")
    ttl = int(document.get("confirmation_ttl_seconds") or 0)
    if not 60 <= ttl <= 600:
        raise ConfirmationError("confirmation_ttl_seconds must be between 60 and 600")
    return document


def build_confirmation(
    declaration: dict,
    *,
    base_url: str,
    login: str,
    expected_sha: str,
    tool: str,
    run_id: str,
    password: str,
    now: datetime.datetime | None = None,
) -> dict:
    if not base_url or not login or not expected_sha or not tool or not run_id:
        raise ConfirmationError("base-url, login, expected-sha, tool and run-id are required")
    if tool not in (declaration.get("tools") or []):
        raise ConfirmationError(f"tool {tool!r} is not declared for the fixed demo credential")
    if login != declaration.get("login"):
        raise ConfirmationError(
            f"login {login!r} is not the declared fixed demo login {declaration.get('login')!r}"
        )
    if password != declaration.get("password"):
        raise ConfirmationError("supplied password is not the declared fixed demo password")
    moment = now or datetime.datetime.now(datetime.timezone.utc)
    expires = moment + datetime.timedelta(seconds=int(declaration["confirmation_ttl_seconds"]))
    return {
        "schema": SCHEMA,
        "profile": "daily",
        "operation": "readonly",
        "tool": tool,
        "baseUrl": base_url,
        "apiUrl": base_url,
        "database": "sc_demo",
        "login": login,
        "expectedSha": expected_sha,
        "runId": run_id,
        "expiresAt": expires.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--declaration", default=str(DEFAULT_DECLARATION))
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--login", required=True)
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--tool", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--password-env", default="ACCEPTANCE_PASSWORD")
    args = parser.parse_args(argv)
    try:
        declaration = load_declaration(Path(args.declaration))
        password = os.environ.get(args.password_env, "")
        confirmation = build_confirmation(
            declaration,
            base_url=args.base_url,
            login=args.login,
            expected_sha=args.expected_sha,
            tool=args.tool,
            run_id=args.run_id,
            password=password,
        )
    except (ConfirmationError, OSError, ValueError) as exc:
        print(f"[daily_demo_credential_confirmation] FAIL {exc}", file=sys.stderr)
        return 1
    print(json.dumps(confirmation, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
