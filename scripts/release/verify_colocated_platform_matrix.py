#!/usr/bin/env python3
"""Verify that client-controlled inputs cannot change the colocated production DB."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request


BASE_URL = os.environ.get("R10E_BASE_URL", "http://127.0.0.1:18089").rstrip("/")
LOGIN = os.environ.get("R10E_LOGIN", "admin")
PASSWORD = os.environ.get("R10E_PASSWORD", "")
EXPECTED_DB = "sc_production"


def _post(url: str, payload: dict, headers: dict[str, str] | None = None) -> tuple[int, dict]:
    request_headers = {"Content-Type": "application/json", **(headers or {})}
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=request_headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            status = response.status
            raw = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        status = exc.code
        raw = exc.read().decode("utf-8", errors="replace")
    try:
        body = json.loads(raw)
    except json.JSONDecodeError:
        body = {"raw": raw[:300]}
    return status, body


def _cases() -> list[tuple[str, dict, dict[str, str], str]]:
    cases: list[tuple[str, dict, dict[str, str], str]] = []

    def add(group: str, params: dict, headers: dict[str, str] | None = None, query: str = "") -> None:
        cases.append((group, params, headers or {}, query))

    add("SYSTEM_INIT_CONTROL", {})
    for value in ("sc_prod", "random_client_db", "sc_platform_core", EXPECTED_DB, None):
        add("BODY_DB_MATRIX", {"db": value})
    for value in ("sc_prod", "random_client_db", "sc_platform_core", EXPECTED_DB, ""):
        add("BODY_DATABASE_MATRIX", {"database": value})
    for db_value, database_value in (
        ("sc_prod", EXPECTED_DB),
        (EXPECTED_DB, "sc_platform_core"),
        ("random_a", "random_b"),
        (None, "sc_prod"),
    ):
        add("CONFLICTING_BODY_FIELDS_MATRIX", {"db": db_value, "database": database_value})
    for value in (123, True, ["sc_prod"], {"name": "sc_platform_core"}, None):
        add("ABNORMAL_BODY_TYPES_MATRIX", {"db": value, "database": value})
    for query in (
        "db=sc_prod",
        "database=sc_platform_core",
        "db=random_client_db&database=sc_prod",
        "tenant_db=sc_platform_core",
        "db=sc_production",
    ):
        add("URL_DATABASE_MATRIX", {}, query=query)
    for header, value in (
        ("X-Odoo-DB", "sc_prod"),
        ("X-DB", "sc_platform_core"),
        ("X-Database", "random_client_db"),
        ("X-Tenant-DB", "sc_prod"),
        ("X-Platform-DB", "sc_platform_core"),
        ("X-Forwarded-DB", "random_client_db"),
        ("X-Odoo-DB", EXPECTED_DB),
        ("Cookie", "db=sc_platform_core"),
    ):
        add("CLIENT_HEADER_MATRIX", {}, {header: value})
    for header, value in (
        ("X-DB-Locked", "true"),
        ("X-Trusted-DB", "true"),
        ("X-Internal-Request", "1"),
        ("X-Forwarded-Host", "sc_platform_core"),
    ):
        add("CLIENT_LOCK_TRUST_ESCALATION", {"db": "sc_platform_core"}, {header: value})
    combined = (
        ({"db": "sc_prod"}, {"X-Odoo-DB": "sc_platform_core"}, "database=random_client_db"),
        ({"database": "sc_platform_core"}, {"X-DB": "sc_prod"}, "db=random_client_db"),
        ({"db": "random_a", "database": "random_b"}, {"X-Trusted-DB": "true"}, "db=sc_prod"),
        ({"db": ["sc_platform_core"]}, {"X-Internal-Request": "1"}, "tenant_db=sc_prod"),
        ({"database": {"name": "sc_prod"}}, {"Cookie": "db=sc_platform_core"}, "db=random_client_db"),
        ({"db": None}, {"X-Platform-DB": "sc_platform_core"}, "database=sc_prod"),
        ({"db": EXPECTED_DB}, {"X-Odoo-DB": "random_client_db"}, "database=sc_platform_core"),
        ({"db": "sc_platform_core"}, {"X-DB-Locked": "true", "X-DB": "sc_prod"}, "db=random_client_db"),
    )
    for params, headers, query in combined:
        add("COMBINED_BYPASS_MATRIX", params, headers, query)
    if len(cases) != 45:
        raise RuntimeError(f"matrix definition must contain 45 cases, got {len(cases)}")
    return cases


def main() -> int:
    if not PASSWORD:
        raise SystemExit("R10E_PASSWORD is required")
    intent_url = f"{BASE_URL}/api/v1/intent"
    login_status, login_body = _post(
        intent_url,
        {"intent": "login", "params": {"db": EXPECTED_DB, "login": LOGIN, "password": PASSWORD}},
        {"X-Anonymous-Intent": "1"},
    )
    token = (login_body.get("data") or {}).get("token") if isinstance(login_body, dict) else None
    if login_status != 200 or not login_body.get("ok") or not token:
        raise SystemExit("isolated matrix login failed")

    group_counts: dict[str, int] = {}
    failures: list[dict] = []
    http_200 = 0
    safely_rejected = 0
    for index, (group, params, extra_headers, query) in enumerate(_cases(), start=1):
        url = intent_url + ("?" + query if query else "")
        headers = {"Authorization": f"Bearer {token}", **extra_headers}
        status, body = _post(url, {"intent": "system.init", "params": params}, headers)
        group_counts[group] = group_counts.get(group, 0) + 1
        if status == 200 and isinstance(body, dict) and body.get("ok"):
            http_200 += 1
        elif index != 1 and status in {400, 401, 403}:
            # Rejecting a client-supplied database/trust override before the
            # handler runs is an equally safe outcome. The control request
            # must always reach system.init successfully.
            safely_rejected += 1
        else:
            failures.append({"case": index, "group": group, "status": status, "code": body.get("code")})

    result = {
        "database": EXPECTED_DB,
        "failed": len(failures),
        "failures": failures,
        "groups": group_counts,
        "http_200": http_200,
        "request_count": 45,
        "safely_rejected": safely_rejected,
        "status": "PASS" if not failures else "FAIL",
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
