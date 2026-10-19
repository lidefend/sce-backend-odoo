#!/usr/bin/env python3
"""Fail-fast, secret-safe HTTP login probe for the governed acceptance route."""

from __future__ import annotations

import json
import os
from pathlib import Path
from urllib import error as urlerror
from urllib import request as urlrequest
from python_http_smoke_utils import extract_login_token


DATABASE = "sc_frontend_acceptance"
LOGIN = "fixture_role_finance"
INTENT_URL = str(
    os.environ.get("SC_ACCEPTANCE_INTENT_URL") or "http://127.0.0.1:18082/api/v1/intent"
).strip()
ENTRY_IDENTITY_FILE = (
    Path(__file__).resolve().parents[2]
    / "config"
    / "acceptance"
    / "isolated_entry_identity.v1.env"
)


def _entry_identity() -> dict[str, str]:
    """Load the isolated acceptance entry stamp, with the environment winning."""

    values: dict[str, str] = {}
    try:
        for raw_line in ENTRY_IDENTITY_FILE.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    except OSError:
        pass
    for key in (
        "SC_ENTRY_NAMESPACE",
        "SC_ENTRY_AUDIENCE",
        "SC_ENTRY_SHARED_SECRET",
        "SC_ENTRY_ROUTE_VERSION",
    ):
        override = str(os.environ.get(key) or "").strip()
        if override:
            values[key] = override
    return values


def _envelope(payload: object) -> dict:
    envelope = payload if isinstance(payload, dict) else {}
    for key in ("result", "data"):
        candidate = envelope.get(key)
        if isinstance(candidate, dict) and ("ok" in candidate or "error" in candidate or "code" in candidate):
            envelope = candidate
    return envelope


def _safe_diagnostic(status: int, content_type: str, payload: object) -> str:
    envelope = _envelope(payload)
    error = envelope.get("error") if isinstance(envelope.get("error"), dict) else {}
    code = envelope.get("code") or error.get("code") or "unknown"
    error_code = error.get("error_code") or envelope.get("error_code") or "unknown"
    media_type = str(content_type or "unknown").split(";", 1)[0]
    return f"http={status} content_type={media_type} code={code} error_code={error_code}"


def _decode_payload(body: bytes) -> object:
    try:
        return json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {}


def probe() -> int:
    database = str(os.environ.get("DB_NAME") or "").strip()
    password = str(os.environ.get("SC_ACCEPTANCE_FIXTURE_PASSWORD") or "")
    if database != DATABASE:
        print("[acceptance.login.probe] DENY database identity mismatch")
        return 2
    if not password:
        print("[acceptance.login.probe] DENY fixture credential is required")
        return 2

    entry = _entry_identity()
    required_entry = (
        "SC_ENTRY_NAMESPACE",
        "SC_ENTRY_AUDIENCE",
        "SC_ENTRY_SHARED_SECRET",
        "SC_ENTRY_ROUTE_VERSION",
    )
    if any(not entry.get(key) for key in required_entry):
        print("[acceptance.login.probe] DENY entry identity is incomplete")
        return 2

    body = json.dumps(
        {
            "intent": "login",
            "params": {
                "login": LOGIN,
                "password": password,
                "contract_mode": "default",
            },
        }
    ).encode("utf-8")
    request = urlrequest.Request(
        INTENT_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Anonymous-Intent": "true",
            "X-SC-Namespace": entry["SC_ENTRY_NAMESPACE"],
            "X-SC-Audience": entry["SC_ENTRY_AUDIENCE"],
            "X-SC-Entry-Secret": entry["SC_ENTRY_SHARED_SECRET"],
            "X-SC-Route-Version": entry["SC_ENTRY_ROUTE_VERSION"],
        },
        method="POST",
    )
    try:
        with urlrequest.urlopen(request, timeout=15) as response:
            status = int(response.status)
            content_type = response.headers.get("Content-Type", "")
            payload = _decode_payload(response.read())
    except urlerror.HTTPError as exc:
        payload = _decode_payload(exc.read())
        diagnostic = _safe_diagnostic(exc.code, exc.headers.get("Content-Type", ""), payload)
        print(f"[acceptance.login.probe] FAIL {diagnostic}")
        return 2
    except urlerror.URLError as exc:
        print(f"[acceptance.login.probe] FAIL transport={type(exc.reason).__name__}")
        return 2

    envelope = _envelope(payload)
    token_present = bool(extract_login_token(envelope))
    if status >= 400 or envelope.get("ok") is not True or not token_present:
        diagnostic = _safe_diagnostic(status, content_type, payload)
        print(f"[acceptance.login.probe] FAIL {diagnostic}")
        return 2

    print(f"[acceptance.login.probe] PASS http={status} db={DATABASE} login={LOGIN}")
    return 0


if __name__ == "__main__":
    raise SystemExit(probe())
