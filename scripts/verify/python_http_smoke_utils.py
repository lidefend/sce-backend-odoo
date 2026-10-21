#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import os
import time
from http.client import RemoteDisconnected
from typing import Any
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def request_timeout_seconds() -> int:
    raw = str(os.getenv("HTTP_SMOKE_TIMEOUT_SECONDS") or "").strip()
    if raw:
        try:
            return max(1, int(raw))
        except ValueError:
            pass
    return 30


def load_env_value_from_file(env_path: str, key: str) -> str | None:
    if not env_path or not os.path.isfile(env_path):
        return None
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                if k.strip() == key:
                    return v.strip().strip('"').strip("'")
    except Exception:
        return None
    return None


def get_base_url() -> str:
    base = os.getenv("E2E_BASE_URL", "").strip()
    if not base:
        raise ValueError("E2E_BASE_URL must identify the governed entry; implicit ports are unsupported")
    return base.rstrip("/")


def assert_entry_request(url: str, payload: dict | None = None, headers: dict | None = None) -> None:
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or not parts.netloc or parts.username or parts.password:
        raise ValueError("explicit HTTP entry URL without embedded credentials is required")
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    forbidden_headers = {"x-odoo-db", "x-odoo-database", "x-db", "x-odoo-db-locked"}
    containers = [payload or {}, (payload or {}).get("params") or {}, (payload or {}).get("context") or {}]
    if "db" in query or "database" in query or forbidden_headers.intersection(str(k).lower() for k in (headers or {})) or any(
        isinstance(value, dict) and ("db" in value or "database" in value) for value in containers
    ):
        raise ValueError("PROBE_TOOL_UNSUPPORTED: client database routing is forbidden; use the entry namespace")


def build_intent_url(base_url: str | None = None) -> str:
    base = str(base_url or get_base_url()).rstrip("/")
    assert_entry_request(base)
    if urlsplit(base).query or urlsplit(base).fragment:
        raise ValueError("entry base URL cannot contain a query or fragment")
    return f"{base}/api/v1/intent"


def env_value(key: str, env_file: str | None = None) -> str:
    value = str(os.getenv(key) or "").strip()
    if value:
        return value
    path = str(env_file or os.getenv("ENV_FILE") or "").strip()
    return str(load_env_value_from_file(path, key) or "").strip()


def extract_login_token(payload: dict[str, Any]) -> str:
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    session = data.get("session") if isinstance(data.get("session"), dict) else {}
    return str(session.get("token") or data.get("token") or "").strip()


def obtain_runtime_probe_token(intent_url: str) -> tuple[bool, str, str]:
    assert_entry_request(intent_url)
    login = env_value("E2E_LOGIN")
    password = env_value("E2E_PASSWORD")
    if not login or not password:
        return False, "", "unconfigured"
    params: dict[str, Any] = {"login": login, "password": password}
    raw_company_id = env_value("E2E_COMPANY_ID")
    if raw_company_id:
        company_id = int(raw_company_id)
        if company_id <= 0:
            raise ValueError("E2E_COMPANY_ID must be positive")
        params["company_id"] = company_id
    status, payload = http_post_json(intent_url, {"intent": "login", "params": params},
                                     headers={"X-Anonymous-Intent": "1"})
    data = payload.get("data") or {}
    user = data.get("user") or {}
    token = extract_login_token(payload) if status == 200 and payload.get("ok") is True else ""
    if token and (user.get("login") != login or not isinstance(user.get("id"), int) or user["id"] <= 0):
        raise ValueError("login: authenticated principal mismatch")
    return bool(token), token, "e2e_login"


def live_login_failure_hint(
    *,
    status: int,
    payload: dict[str, Any],
    base_url: str,
    db_name: str,
    login: str,
) -> str:
    message = ""
    if isinstance(payload.get("error"), dict):
        message = str(payload["error"].get("message") or payload["error"].get("data") or "").strip()
    elif payload.get("message"):
        message = str(payload.get("message") or "").strip()
    detail = f"ENV_UNAVAILABLE: login failed status={status} base_url={base_url} db={db_name or '<empty>'} login={login or '<empty>'}"
    if message:
        detail = f"{detail} message={message}"
    return (
        f"{detail}; set E2E_BASE_URL/E2E_DB/E2E_LOGIN/E2E_PASSWORD "
        "or run against a seeded database with valid smoke credentials"
    )


def _request_json(
    req: urlrequest.Request,
    *,
    retries: int = 3,
    backoff_sec: float = 0.5,
) -> tuple[int, dict, dict]:
    attempt = 0
    while True:
        attempt += 1
        try:
            with urlrequest.urlopen(req, timeout=request_timeout_seconds()) as resp:
                body = resp.read().decode("utf-8") or "{}"
                return resp.status, json.loads(body), dict(resp.headers or {})
        except HTTPError as e:
            body = e.read().decode("utf-8") if hasattr(e, "read") else ""
            try:
                payload = json.loads(body or "{}")
            except Exception:
                payload = {"raw": body}
            return e.code, payload, dict(getattr(e, "headers", {}) or {})
        except (RemoteDisconnected, ConnectionResetError, URLError) as e:
            if attempt >= retries:
                raise RuntimeError(f"HTTP request failed after retries: {e}") from e
            time.sleep(backoff_sec * attempt)


def http_post_json(url: str, payload: dict, headers: dict | None = None) -> tuple[int, dict]:
    assert_entry_request(url, payload, headers)
    data = json.dumps(payload).encode("utf-8")
    req = urlrequest.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    status, body, _ = _request_json(req)
    return status, body


def http_get_json(url: str, headers: dict | None = None) -> tuple[int, dict]:
    status, payload, _ = http_get_json_with_headers(url, headers=headers)
    return status, payload


def http_get_json_with_headers(url: str, headers: dict | None = None) -> tuple[int, dict, dict]:
    assert_entry_request(url, headers=headers)
    req = urlrequest.Request(url, method="GET")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    return _request_json(req)
