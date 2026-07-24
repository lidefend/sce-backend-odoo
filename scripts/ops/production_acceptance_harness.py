#!/usr/bin/env python3
"""Immutable, read-only production acceptance harness over real HTTP.

The harness intentionally has no Odoo import and never calls application
authentication helpers directly.  Every run starts with an anonymous HTTP
login and uses the returned bearer token for all authenticated checks.  It
does not call ``auth.logout`` because that endpoint increments the persistent
token version; the permission boundary is checked with missing and invalid
credentials instead.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = Path(__file__).with_name("production_acceptance_contract_v1.json")
PACKAGE_FILES = (
    Path(__file__).resolve(),
    CONTRACT_PATH.resolve(),
)
DEFAULT_OUTPUT = ROOT / "artifacts" / "backend" / "production_acceptance_harness.json"


class AcceptanceError(RuntimeError):
    pass


def package_digest() -> str:
    digest = hashlib.sha256()
    for path in sorted(PACKAGE_FILES, key=lambda item: item.name):
        content_digest = hashlib.sha256(path.read_bytes()).hexdigest()
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(content_digest.encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def load_contract() -> dict[str, Any]:
    payload = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "production_acceptance_contract.v1":
        raise AcceptanceError("unsupported acceptance contract")
    return payload


def http_json(
    url: str,
    payload: dict[str, Any],
    *,
    headers: dict[str, str] | None = None,
    timeout: int = 30,
) -> tuple[int, dict[str, Any]]:
    request_headers = {"Content-Type": "application/json", **(headers or {})}
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=request_headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = response.status
            body = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        status = exc.code
        body = exc.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError) as exc:
        raise AcceptanceError(f"HTTP request failed: {type(exc).__name__}") from exc
    try:
        parsed = json.loads(body or "{}")
    except json.JSONDecodeError:
        parsed = {}
    return status, parsed if isinstance(parsed, dict) else {}


def http_get(url: str, *, timeout: int = 30) -> tuple[int, str, dict[str, str]]:
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return (
                response.status,
                response.read().decode("utf-8", errors="replace"),
                dict(response.headers),
            )
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace"), dict(exc.headers)
    except (urllib.error.URLError, TimeoutError) as exc:
        raise AcceptanceError(f"HTTP request failed: {type(exc).__name__}") from exc


def error_code(payload: dict[str, Any]) -> str:
    error = payload.get("error") if isinstance(payload.get("error"), dict) else {}
    return str(error.get("code") or payload.get("code") or "")


def unwrap_data(payload: dict[str, Any]) -> dict[str, Any]:
    data: Any = payload.get("data")
    while isinstance(data, dict) and isinstance(data.get("data"), dict):
        data = data["data"]
    return data if isinstance(data, dict) else {}


def node_label(node: dict[str, Any]) -> str:
    return str(
        node.get("label")
        or node.get("title")
        or node.get("name")
        or node.get("display_name")
        or ""
    ).strip()


def walk_navigation(value: Any, path: tuple[str, ...] = ()) -> list[str]:
    rows: list[str] = []
    if not isinstance(value, list):
        return rows
    for node in value:
        if not isinstance(node, dict):
            continue
        label = node_label(node)
        current = path + ((label,) if label else ())
        if current:
            rows.append(" / ".join(current))
        rows.extend(walk_navigation(node.get("children"), current))
    return rows


def navigation_from_init(data: dict[str, Any]) -> list[str]:
    for key in ("nav", "menus", "navigation"):
        paths = walk_navigation(data.get(key))
        if paths:
            return paths
    workspace = data.get("workspace_home")
    if isinstance(workspace, dict):
        for key in ("nav", "menus", "navigation"):
            paths = walk_navigation(workspace.get(key))
            if paths:
                return paths
    return []


def role_code_from_init(data: dict[str, Any]) -> str:
    role_surface = data.get("role_surface")
    if isinstance(role_surface, dict):
        value = str(role_surface.get("role_code") or "").strip()
        if value:
            return value
    return str(data.get("role_code") or "").strip()


def check_frontend(base_url: str) -> dict[str, Any]:
    status, body, _headers = http_get(base_url.rstrip("/") + "/")
    asset_match = re.search(r'<script[^>]+src="([^"]+\.js)"', body)
    asset_status = 0
    if asset_match:
        asset_url = urllib.parse.urljoin(base_url.rstrip("/") + "/", asset_match.group(1))
        asset_status, _asset_body, _asset_headers = http_get(asset_url)
    return {
        "root_http_status": status,
        "script_asset_found": bool(asset_match),
        "script_asset_http_status": asset_status,
        "pass": status == 200 and bool(asset_match) and asset_status == 200,
    }


def run_once(
    *,
    base_url: str,
    db_name: str,
    login: str,
    password: str,
    contract: dict[str, Any],
    timeout: int,
) -> tuple[dict[str, Any], str]:
    endpoint = str((contract.get("authentication") or {}).get("endpoint") or "/api/v1/intent")
    intent_url = base_url.rstrip("/") + endpoint + "?" + urllib.parse.urlencode({"db": db_name})
    db_headers = {"X-Odoo-DB": db_name, "X-DB": db_name}

    noauth_status, noauth_payload = http_json(
        intent_url,
        {"intent": "system.init", "params": {"db": db_name}},
        headers=db_headers,
        timeout=timeout,
    )
    noauth_pass = noauth_status in {401, 403} and error_code(noauth_payload) == "AUTH_REQUIRED"

    anonymous_header = str(
        (contract.get("authentication") or {}).get("anonymous_header") or "X-Anonymous-Intent"
    )
    login_status, login_payload = http_json(
        intent_url,
        {"intent": "login", "params": {"db": db_name, "login": login, "password": password}},
        headers={**db_headers, anonymous_header: "1"},
        timeout=timeout,
    )
    login_data = unwrap_data(login_payload)
    token = str(login_data.get("token") or "").strip()
    login_pass = login_status == 200 and login_payload.get("ok") is True and bool(token)
    if not login_pass:
        raise AcceptanceError(
            f"real HTTP login failed status={login_status} code={error_code(login_payload) or 'UNKNOWN'}"
        )

    auth_headers = {**db_headers, "Authorization": f"Bearer {token}"}
    init_status, init_payload = http_json(
        intent_url,
        {
            "intent": "system.init",
            "params": {"db": db_name, "with": ["workspace_home"]},
        },
        headers=auth_headers,
        timeout=timeout,
    )
    init_data = unwrap_data(init_payload)
    role_code = role_code_from_init(init_data)
    navigation = navigation_from_init(init_data)
    expected_roles = {
        str(item).strip() for item in contract.get("expected_role_codes", []) if str(item).strip()
    }
    role_pass = bool(role_code) and (not expected_roles or role_code in expected_roles)
    required_fragments = [
        str(item).strip()
        for item in contract.get("required_navigation_fragments", [])
        if str(item).strip()
    ]
    forbidden_fragments = [
        str(item).strip()
        for item in contract.get("forbidden_navigation_fragments", [])
        if str(item).strip()
    ]
    required_misses = [
        fragment for fragment in required_fragments if not any(fragment in path for path in navigation)
    ]
    forbidden_hits = [
        fragment for fragment in forbidden_fragments if any(fragment in path for path in navigation)
    ]
    init_pass = init_status == 200 and init_payload.get("ok") is True
    navigation_pass = bool(navigation) and not required_misses and not forbidden_hits
    workspace_home = init_data.get("workspace_home")
    workspace_serialized = (
        json.dumps(workspace_home, ensure_ascii=False, sort_keys=True)
        if isinstance(workspace_home, dict)
        else ""
    )
    required_workspace_fragments = [
        str(item).strip()
        for item in contract.get("required_workspace_fragments", [])
        if str(item).strip()
    ]
    workspace_fragment_misses = [
        fragment for fragment in required_workspace_fragments if fragment not in workspace_serialized
    ]
    my_work_pass = bool(workspace_serialized) and not workspace_fragment_misses

    contract_status, contract_payload = http_json(
        intent_url,
        {"intent": "ui.contract", "params": {"db": db_name, "op": "nav"}},
        headers=auth_headers,
        timeout=timeout,
    )
    ui_contract_pass = contract_status == 200 and contract_payload.get("ok") is True

    read_probes: list[dict[str, Any]] = []
    for probe in contract.get("core_read_probes", []):
        model = str(probe.get("model") or "").strip()
        fields = [str(field) for field in probe.get("fields", []) if str(field)]
        status, payload = http_json(
            intent_url,
            {
                "intent": "api.data",
                "params": {
                    "db": db_name,
                    "op": "list",
                    "model": model,
                    "fields": fields,
                    "limit": 1,
                },
            },
            headers=auth_headers,
            timeout=timeout,
        )
        data = unwrap_data(payload)
        records = data.get("records") if isinstance(data.get("records"), list) else []
        read_probes.append(
            {
                "model": model,
                "http_status": status,
                "response_ok": payload.get("ok") is True,
                "record_count": len(records),
                "pass": status == 200 and payload.get("ok") is True,
            }
        )
    core_reads_pass = bool(read_probes) and all(item["pass"] for item in read_probes)

    invalid_status, invalid_payload = http_json(
        intent_url,
        {"intent": "system.init", "params": {"db": db_name}},
        headers={**db_headers, "Authorization": "Bearer acceptance-invalid-token"},
        timeout=timeout,
    )
    invalid_token_pass = (
        invalid_status in {401, 403} and error_code(invalid_payload) == "AUTH_REQUIRED"
    )
    permission_boundary_pass = noauth_pass and invalid_token_pass

    result = {
        "authentication_method": "REAL_HTTP_BEARER_TOKEN",
        "login_pass": login_pass,
        "system_init_pass": init_pass,
        "navigation_pass": navigation_pass and ui_contract_pass,
        "navigation_node_count": len(navigation),
        "navigation_required_fragment_misses": required_misses,
        "navigation_forbidden_fragment_hits": forbidden_hits,
        "my_work_acceptance_pass": my_work_pass,
        "workspace_required_fragment_misses": workspace_fragment_misses,
        "core_role_acceptance_pass": role_pass,
        "observed_role_code": role_code,
        "permission_boundary_pass": permission_boundary_pass,
        "unauthenticated_system_init_rejected": noauth_pass,
        "invalid_token_rejected": invalid_token_pass,
        "core_read_acceptance_pass": core_reads_pass,
        "core_read_probes": read_probes,
    }
    result["pass"] = all(
        (
            result["login_pass"],
            result["system_init_pass"],
            result["navigation_pass"],
            result["my_work_acceptance_pass"],
            result["core_role_acceptance_pass"],
            result["permission_boundary_pass"],
            result["core_read_acceptance_pass"],
        )
    )
    return result, token


def run_acceptance(
    *,
    base_url: str,
    db_name: str,
    login: str,
    password: str,
    run_count: int,
    timeout: int = 30,
) -> dict[str, Any]:
    if not base_url.startswith(("http://", "https://")):
        raise AcceptanceError("base URL must use http or https")
    if not db_name or not login or not password:
        raise AcceptanceError("database, login, and password are required")
    if run_count < 1:
        raise AcceptanceError("run count must be positive")
    contract = load_contract()
    frontend = check_frontend(base_url)
    runs: list[dict[str, Any]] = []
    token_fingerprints: list[str] = []
    for _index in range(run_count):
        result, token = run_once(
            base_url=base_url,
            db_name=db_name,
            login=login,
            password=password,
            contract=contract,
            timeout=timeout,
        )
        runs.append(result)
        token_fingerprints.append(hashlib.sha256(token.encode("utf-8")).hexdigest())
    clean_sessions_pass = len(set(token_fingerprints)) == run_count
    report = {
        "schema_version": "production_acceptance_harness_evidence.v1",
        "package_digest": package_digest(),
        "authentication_method": "REAL_HTTP_BEARER_TOKEN",
        "preexisting_session_input": False,
        "database": db_name,
        "base_url": base_url.rstrip("/"),
        "run_count": run_count,
        "repeated_clean_session_pass": clean_sessions_pass,
        "frontend": frontend,
        "runs": runs,
    }
    report["status"] = (
        "PASS"
        if frontend["pass"] and clean_sessions_pass and all(item["pass"] for item in runs)
        else "FAIL"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=os.getenv("ACCEPTANCE_BASE_URL", ""))
    parser.add_argument("--db-name", default=os.getenv("DB_NAME", ""))
    parser.add_argument("--login", default=os.getenv("ACCEPTANCE_LOGIN", ""))
    parser.add_argument("--password", default=os.getenv("ACCEPTANCE_PASSWORD", ""))
    parser.add_argument("--run-count", type=int, default=int(os.getenv("ACCEPTANCE_RUN_COUNT", "1")))
    parser.add_argument("--timeout", type=int, default=int(os.getenv("ACCEPTANCE_HTTP_TIMEOUT", "30")))
    parser.add_argument("--output", default=os.getenv("ACCEPTANCE_HARNESS_OUTPUT", str(DEFAULT_OUTPUT)))
    parser.add_argument(
        "--expected-package-digest",
        default=os.getenv("ACCEPTANCE_PACKAGE_DIGEST", ""),
    )
    parser.add_argument("--print-package-digest", action="store_true")
    args = parser.parse_args()

    observed_digest = package_digest()
    if args.print_package_digest:
        print(observed_digest)
        return 0
    if not args.expected_package_digest:
        print("[production_acceptance_harness] FAIL expected package digest is required", file=sys.stderr)
        return 2
    if args.expected_package_digest != observed_digest:
        print(
            "[production_acceptance_harness] FAIL immutable package digest mismatch "
            f"expected={args.expected_package_digest} observed={observed_digest}",
            file=sys.stderr,
        )
        return 2
    started = time.time()
    try:
        report = run_acceptance(
            base_url=args.base_url,
            db_name=args.db_name,
            login=args.login,
            password=args.password,
            run_count=args.run_count,
            timeout=args.timeout,
        )
    except AcceptanceError as exc:
        print(f"[production_acceptance_harness] FAIL {exc}", file=sys.stderr)
        return 1
    report["duration_seconds"] = round(time.time() - started, 3)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        "[production_acceptance_harness] "
        f"{report['status']} package_digest={report['package_digest']} "
        f"runs={report['run_count']} output={output}"
    )
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
