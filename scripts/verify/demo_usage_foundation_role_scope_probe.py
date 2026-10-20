#!/usr/bin/env python3
"""Read-only demo role/scope startup acceptance (P4 delivery tooling, runtime).

Consumes the public login/system.init/my.work.summary contract for the F2
account set declared in the role-scope manifest. It only reads runtime state:
it never writes a database, never seeds a fact, and never fabricates a
first-screen. Role codes and company scope are asserted against the
authoritative manifest; my.work.summary counts are recorded, not invented.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from urllib import request as urlrequest
from urllib.error import HTTPError

SCHEMA_VERSION = 1
VALID_OWNER_LAYERS = ("P0", "P1", "P2", "P3", "P4")
VALID_EXPECTATIONS = ("role_code", "valid_surface")
VALID_NEGATIVE_EXPECTATIONS = ("login_denied",)
VALID_FIRST_SCREEN_EXPECTATIONS = ("non_empty", "record")

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = REPO_ROOT / "scripts/verify/demo_usage_foundation_role_scope_manifest.json"
READBACK_DIR = REPO_ROOT / ".runtime" / "agent-runs" / "DEMO-USAGE-FOUNDATION-20261020"


class ManifestError(ValueError):
    pass


def _read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ManifestError(f"unreadable JSON {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ManifestError(f"expected a JSON object: {path}")
    return data


def _require_str(value, field: str, ctx: str) -> str:
    if not isinstance(value, str) or not value:
        raise ManifestError(f"{ctx}: {field} must be a non-empty string")
    return value


def validate_manifest(data: dict) -> None:
    if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION:
        raise ManifestError(f"manifest must be an object with schema_version={SCHEMA_VERSION}")
    _require_str(data.get("id"), "id", "manifest")
    if data.get("owner_layer") not in VALID_OWNER_LAYERS:
        raise ManifestError(f"manifest owner_layer must be one of {VALID_OWNER_LAYERS}")
    _require_str(data.get("authority"), "authority", "manifest")

    runtime = data.get("runtime")
    if not isinstance(runtime, dict):
        raise ManifestError("manifest runtime must be an object")
    for field in ("base_url_env", "base_url_default", "entry_namespace", "database_env", "database_default"):
        _require_str(runtime.get(field), field, "runtime")

    scope = data.get("company_scope")
    if not isinstance(scope, dict):
        raise ManifestError("manifest company_scope must be an object")
    if not isinstance(scope.get("expected_company_id"), int):
        raise ManifestError("company_scope expected_company_id must be an integer")
    allowed = scope.get("expected_allowed_company_ids")
    if not isinstance(allowed, list) or not allowed or not all(isinstance(x, int) for x in allowed):
        raise ManifestError(
            "company_scope expected_allowed_company_ids must be a non-empty list of integers"
        )

    accounts = data.get("accounts")
    if not isinstance(accounts, list) or not accounts:
        raise ManifestError("manifest accounts must be a non-empty list")
    seen_keys: set[str] = set()
    seen_logins: set[str] = set()
    for account in accounts:
        if not isinstance(account, dict):
            raise ManifestError("each account must be an object")
        key = _require_str(account.get("key"), "key", "account")
        if key in seen_keys:
            raise ManifestError(f"duplicate account key {key!r}")
        seen_keys.add(key)
        login = _require_str(account.get("login"), "login", f"account {key}")
        if login in seen_logins:
            raise ManifestError(f"duplicate account login {login!r}")
        seen_logins.add(login)
        _require_str(account.get("label"), "label", f"account {key}")
        if account.get("expectation") not in VALID_EXPECTATIONS:
            raise ManifestError(
                f"account {key} expectation must be one of {VALID_EXPECTATIONS}"
            )
        if account.get("expectation") == "role_code":
            _require_str(account.get("expected_role_code"), "expected_role_code", f"account {key}")
        if "first_screen_expectation" in account and account.get(
            "first_screen_expectation"
        ) not in VALID_FIRST_SCREEN_EXPECTATIONS:
            raise ManifestError(
                f"account {key} first_screen_expectation must be one of "
                f"{VALID_FIRST_SCREEN_EXPECTATIONS}"
            )

    negatives = data.get("negatives")
    if not isinstance(negatives, list):
        raise ManifestError("manifest negatives must be a list")
    for neg in negatives:
        if not isinstance(neg, dict):
            raise ManifestError("each negative must be an object")
        key = _require_str(neg.get("key"), "key", "negative")
        _require_str(neg.get("login"), "login", f"negative {key}")
        _require_str(neg.get("password"), "password", f"negative {key}")
        if neg.get("expectation") not in VALID_NEGATIVE_EXPECTATIONS:
            raise ManifestError(
                f"negative {key} expectation must be one of {VALID_NEGATIVE_EXPECTATIONS}"
            )


def load_manifest(path: Path) -> dict:
    data = _read_json(path)
    validate_manifest(data)
    return data


def _post(url: str, payload: dict, token: str | None = None) -> tuple[int, dict]:
    body = json.dumps(payload).encode("utf-8")
    req = urlrequest.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("X-Anonymous-Intent", "1")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urlrequest.urlopen(req, timeout=30) as resp:
            text = resp.read().decode("utf-8") or "{}"
            return resp.status, json.loads(text)
    except HTTPError as exc:
        text = exc.read().decode("utf-8") if hasattr(exc, "read") else ""
        try:
            return exc.code, json.loads(text or "{}")
        except ValueError:
            return exc.code, {"raw": text}


def _login(base_url: str, namespace: str, login: str, password: str) -> tuple[int, dict, str]:
    status, body = _post(
        f"{base_url}/t/{namespace}/api/v1/intent",
        {"intent": "login", "params": {"login": login, "password": password}},
    )
    data = body.get("data") if isinstance(body, dict) and isinstance(body.get("data"), dict) else {}
    session = data.get("session") if isinstance(data.get("session"), dict) else {}
    token = str(session.get("token") or data.get("token") or "").strip()
    return status, body, token


def _probe_account(
    manifest: dict, account: dict, base_url: str, namespace: str, password: str
) -> dict:
    key = account["key"]
    login = account["login"]
    status, body, token = _login(base_url, namespace, login, password)
    result = {
        "key": key,
        "login": login,
        "label": account["label"],
        "login_ok": bool(token),
        "role_code": None,
        "role_ok": False,
        "company_ok": False,
        "route_ok": False,
        "my_work_ok": False,
        "first_screen_counts": {},
        "first_screen_total": 0,
        "first_screen_ok": True,
        "pass": False,
    }
    if not token:
        result["error"] = f"login denied status={status} ok={body.get('ok') if isinstance(body, dict) else None}"
        return result

    intent_url = f"{base_url}/t/{namespace}/api/v1/intent"
    init_status, init_body = _post(
        intent_url,
        {
            "intent": "system.init",
            "params": {
                "scene": "web",
                "with_preload": False,
                "scene_ready_mode": "registry",
                "with": ["workspace_home"],
            },
        },
        token,
    )
    data = init_body.get("data") if isinstance(init_body, dict) else {}
    role_surface = data.get("role_surface") if isinstance(data.get("role_surface"), dict) else {}
    user = data.get("user") if isinstance(data.get("user"), dict) else {}
    route = data.get("default_route") if isinstance(data.get("default_route"), dict) else {}
    role_code = role_surface.get("role_code")
    result["role_code"] = role_code

    expectation = account["expectation"]
    if expectation == "role_code":
        result["role_ok"] = role_code == account["expected_role_code"]
    else:
        result["role_ok"] = bool(role_code)

    scope = manifest["company_scope"]
    result["company_ok"] = (
        user.get("company_id") == scope["expected_company_id"]
        and user.get("allowed_company_ids") == scope["expected_allowed_company_ids"]
    )
    result["route_ok"] = bool(route.get("route")) and bool(route.get("scene_key"))

    work_status, work_body = _post(intent_url, {"intent": "my.work.summary", "params": {}}, token)
    work_data = work_body.get("data") if isinstance(work_body, dict) else {}
    summary = work_data.get("summary") if isinstance(work_data, dict) else []
    if isinstance(summary, list):
        result["first_screen_counts"] = {
            str(item.get("key")): item.get("count")
            for item in summary
            if isinstance(item, dict) and item.get("key") is not None
        }
    result["first_screen_total"] = sum(
        int(v or 0) for v in result["first_screen_counts"].values() if isinstance(v, (int, float))
    )
    first_screen_expectation = account.get("first_screen_expectation", "record")
    result["first_screen_ok"] = (
        result["first_screen_total"] > 0
        if first_screen_expectation == "non_empty"
        else True
    )
    result["my_work_ok"] = work_status == 200 and bool(
        work_body.get("ok") if isinstance(work_body, dict) else False
    )

    result["pass"] = all(
        [
            result["login_ok"],
            result["role_ok"],
            result["company_ok"],
            result["route_ok"],
            result["my_work_ok"],
            result["first_screen_ok"],
        ]
    )
    return result


def _probe_negative(
    neg: dict, base_url: str, namespace: str
) -> dict:
    status, body, token = _login(base_url, namespace, neg["login"], neg["password"])
    denied = not token
    result = {
        "key": neg["key"],
        "login": neg["login"],
        "denied": denied,
        "pass": denied,
    }
    if not denied:
        result["error"] = f"unexpected login accepted status={status}"
    return result


def probe(manifest: dict, base_url: str, namespace: str, password: str) -> dict:
    accounts = [
        _probe_account(manifest, account, base_url, namespace, password)
        for account in manifest["accounts"]
    ]
    negatives = [_probe_negative(neg, base_url, namespace) for neg in manifest["negatives"]]
    account_failed = [a for a in accounts if not a["pass"]]
    negative_failed = [n for n in negatives if not n["pass"]]
    return {
        "schema_version": SCHEMA_VERSION,
        "id": manifest["id"],
        "owner_layer": manifest["owner_layer"],
        "audit_kind": "runtime_readonly_startup_acceptance",
        "data_readback": "runtime_readonly",
        "runtime": {
            "base_url": base_url,
            "namespace": namespace,
        },
        "company_scope": manifest["company_scope"],
        "accounts": accounts,
        "negatives": negatives,
        "summary": {
            "account_count": len(accounts),
            "account_passed": len(accounts) - len(account_failed),
            "account_failed": len(account_failed),
            "negative_count": len(negatives),
            "negative_passed": len(negatives) - len(negative_failed),
            "negative_failed": len(negative_failed),
            "overall_pass": not account_failed and not negative_failed,
        },
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args(argv)
    try:
        manifest = load_manifest(args.manifest)
    except ManifestError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    runtime = manifest["runtime"]
    base_url = str(
        os.getenv(runtime["base_url_env"]) or runtime["base_url_default"]
    ).rstrip("/")
    namespace = str(runtime["entry_namespace"]).strip() or "demo"
    password = str(os.getenv("E2E_PASSWORD") or "123456").strip()
    report = probe(manifest, base_url, namespace, password)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    try:
        READBACK_DIR.mkdir(parents=True, exist_ok=True)
        (READBACK_DIR / "role_scope_readback.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    except OSError:
        pass
    return 0 if report["summary"]["overall_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
