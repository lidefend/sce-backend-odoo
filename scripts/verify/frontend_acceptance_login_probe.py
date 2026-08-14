#!/usr/bin/env python3
"""Fail-fast, secret-safe HTTP login probe for the governed acceptance route."""

from __future__ import annotations

import json
import os
from urllib import error as urlerror
from urllib import request as urlrequest


DATABASE = "sc_frontend_acceptance"
LOGIN = "fixture_role_finance"
INTENT_URL = f"http://127.0.0.1:18082/api/v1/intent?db={DATABASE}"


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

    body = json.dumps(
        {
            "intent": "login",
            "params": {
                "login": LOGIN,
                "password": password,
                "db": DATABASE,
                "contract_mode": "default",
            },
        }
    ).encode("utf-8")
    request = urlrequest.Request(
        INTENT_URL,
        data=body,
        headers={"Content-Type": "application/json", "X-Anonymous-Intent": "true"},
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
    data = envelope.get("data") if isinstance(envelope.get("data"), dict) else {}
    session = data.get("session") if isinstance(data.get("session"), dict) else {}
    token_present = bool(session.get("token") or data.get("token"))
    if status >= 400 or envelope.get("ok") is not True or not token_present:
        diagnostic = _safe_diagnostic(status, content_type, payload)
        print(f"[acceptance.login.probe] FAIL {diagnostic}")
        return 2

    print(f"[acceptance.login.probe] PASS http={status} db={DATABASE} login={LOGIN}")
    return 0


if __name__ == "__main__":
    raise SystemExit(probe())
