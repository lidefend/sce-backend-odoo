#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from python_http_smoke_utils import (
    build_intent_url,
    extract_login_token,
    get_base_url,
    http_post_json,
)


ROOT = Path(__file__).resolve().parents[2]
BASELINE_PATH = ROOT / "scripts" / "verify" / "baselines" / "scene_company_snapshot_collect.json"
SNAPSHOT_GUARD_PATH = ROOT / "scripts" / "verify" / "scene_registry_asset_snapshot_guard.py"
PROFILES_JSON_ENV = "SC_SCENE_COMPANY_SNAPSHOT_PROFILES_JSON"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _as_dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list:
    return value if isinstance(value, list) else []


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _safe_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    text = _text(value).lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default


def _profile_value(profile: dict, key: str) -> str:
    direct = _text(profile.get(key))
    if direct:
        return direct
    env_keys = [
        _text(item)
        for item in _as_list(profile.get(f"{key}_envs"))
        if _text(item)
    ]
    single_env_key = _text(profile.get(f"{key}_env"))
    if single_env_key:
        env_keys.insert(0, single_env_key)
    for env_key in env_keys:
        value = _text(os.getenv(env_key))
        if value:
            return value
    return _text(profile.get(f"{key}_default"))


def _select_non_primary_company_id(profile: dict, state: dict) -> int:
    excluded = {
        _safe_int(item, 0)
        for item in _as_list(profile.get("exclude_company_ids"))
        if _safe_int(item, 0) > 0
    }
    candidates = sorted(
        {
            _safe_int(item, 0)
            for item in _as_list(state.get("allowed_company_ids"))
            if _safe_int(item, 0) > 0 and _safe_int(item, 0) not in excluded
        }
    )
    return candidates[0] if candidates else 0


def _discover_allowed_company_ids(login: str, password: str) -> list[int]:
    db_name = _text(os.getenv("E2E_DB") or os.getenv("DB_NAME"))
    intent_url = build_intent_url(get_base_url(), db_name)
    status, payload = http_post_json(
        intent_url,
        {
            "intent": "login",
            "params": {"db": db_name, "login": login, "password": password},
        },
        headers={"X-Anonymous-Intent": "1", "X-Odoo-DB": db_name},
    )
    if status >= 400 or payload.get("ok") is not True or not extract_login_token(payload):
        return []
    data = _as_dict(payload.get("data"))
    user = _as_dict(data.get("user"))
    return sorted(
        {
            _safe_int(item, 0)
            for item in _as_list(user.get("allowed_company_ids"))
            if _safe_int(item, 0) > 0
        }
    )


def _load_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _resolve_profiles(baseline: dict) -> list:
    raw_override = os.environ.get(PROFILES_JSON_ENV)
    if raw_override is None:
        profiles = _as_list(baseline.get("profiles"))
    else:
        try:
            profiles = json.loads(raw_override)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError(f"{PROFILES_JSON_ENV} must be a valid JSON array") from exc
        if not isinstance(profiles, list):
            raise ValueError(f"{PROFILES_JSON_ENV} must be a JSON array")

    if not profiles:
        source = PROFILES_JSON_ENV if raw_override is not None else "profiles"
        raise ValueError(f"{source} is empty")
    return profiles


def _redact_passwords(value: Any, passwords: list[str]) -> str:
    text = _text(value)
    for password in sorted(set(filter(None, passwords)), key=len, reverse=True):
        text = text.replace(password, "[REDACTED]")
    return text


def _redact_password(value: Any, password: str) -> str:
    return _redact_passwords(value, [password])


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _run_snapshot(
    profile_key: str,
    company_id: int,
    state_file: str,
    require_live: bool,
    login: str,
    password: str,
) -> tuple[int, str]:
    env = os.environ.copy()
    env.pop(PROFILES_JSON_ENV, None)
    env["SC_SCENE_REGISTRY_ASSET_SNAPSHOT_STATE_FILE"] = state_file
    env["SC_SCENE_REGISTRY_ASSET_SNAPSHOT_REQUIRE_LIVE"] = "1" if require_live else "0"
    env["SC_SCENE_REGISTRY_ASSET_SNAPSHOT_ALLOW_STATE_FALLBACK_ON_LIVE_FAIL"] = "0"
    if company_id > 0:
        env["E2E_COMPANY_ID"] = str(company_id)
    else:
        env.pop("E2E_COMPANY_ID", None)
    if login:
        env["E2E_LOGIN"] = login
    if password:
        env["E2E_PASSWORD"] = password

    process = subprocess.run(
        [sys.executable, SNAPSHOT_GUARD_PATH.as_posix()],
        cwd=ROOT.as_posix(),
        env=env,
        capture_output=True,
        text=True,
    )
    merged = "\n".join([_text(process.stdout), _text(process.stderr)]).strip()
    header = f"[{profile_key}] company_id={company_id if company_id > 0 else 'auto'} state_file={state_file}"
    output = f"{header}\n{merged}".strip()
    return process.returncode, output


def main() -> int:
    baseline = _load_json(BASELINE_PATH)
    if not baseline:
        print("[scene_company_snapshot_collect] FAIL")
        print(f" - missing or invalid baseline: {BASELINE_PATH.relative_to(ROOT).as_posix()}")
        return 1

    try:
        profiles = _resolve_profiles(baseline)
    except ValueError as exc:
        print("[scene_company_snapshot_collect] FAIL")
        print(f" - {exc}")
        return 1

    profile_passwords = [
        password
        for password in (_profile_value(_as_dict(row), "password") for row in profiles)
        if password
    ]

    min_profiles_success = _safe_int(baseline.get("min_profiles_success"), 1)
    require_distinct_company_ids = _safe_bool(baseline.get("require_distinct_company_ids"), False)
    min_distinct_company_ids = _safe_int(baseline.get("min_distinct_company_ids"), 1)
    require_live = _safe_bool(baseline.get("require_live"), True)
    allow_state_fallback_on_guard_failure = _safe_bool(
        baseline.get("allow_state_fallback_on_guard_failure"), True
    )

    report_json_path = ROOT / _text(
        baseline.get("report_json") or "artifacts/backend/scene_company_snapshot_collect_report.json"
    )
    report_md_path = ROOT / _text(
        baseline.get("report_md") or "artifacts/backend/scene_company_snapshot_collect_report.md"
    )

    errors: list[str] = []
    warnings: list[str] = []
    profile_reports: list[dict[str, Any]] = []
    observed_company_ids: set[int] = set()

    for row in profiles:
        profile = _as_dict(row)
        profile_key = _text(profile.get("key"))
        if not profile_key:
            errors.append("profile key is required")
            continue
        company_id = _safe_int(profile.get("company_id"), 0)
        state_file = _text(profile.get("state_file"))
        login = _profile_value(profile, "login")
        password = _profile_value(profile, "password")
        if not state_file:
            errors.append(f"{profile_key}: state_file is required")
            continue

        if _safe_bool(profile.get("select_non_primary_company"), False):
            allowed_company_ids = _discover_allowed_company_ids(login, password)
            selected_company_id = _select_non_primary_company_id(
                profile,
                {"allowed_company_ids": allowed_company_ids},
            )
            if selected_company_id <= 0:
                code = 1
                output = f"[{profile_key}] no eligible non-primary company in allowed_company_ids"
                state_payload = {}
            else:
                company_id = selected_company_id
                code, output = _run_snapshot(
                    profile_key,
                    company_id,
                    state_file,
                    require_live,
                    login,
                    password,
                )
                state_payload = _load_json(ROOT / state_file)
        else:
            code, output = _run_snapshot(
                profile_key,
                company_id,
                state_file,
                require_live,
                login,
                password,
            )
            state_payload = _load_json(ROOT / state_file)
        output = _redact_passwords(output, profile_passwords)
        effective_company_id = _safe_int(state_payload.get("company_id"), 0)
        if effective_company_id > 0:
            observed_company_ids.add(effective_company_id)

        ok = code == 0
        if code != 0:
            state_scene_count = _safe_int(state_payload.get("scene_count"), 0)
            if allow_state_fallback_on_guard_failure and state_scene_count > 0:
                ok = True
                warnings.append(
                    f"{profile_key}: snapshot guard failed but fallback state accepted (scene_count={state_scene_count})"
                )
            else:
                errors.append(f"{profile_key}: snapshot guard failed")

        profile_reports.append(
            {
                "key": profile_key,
                "requested_company_id": company_id,
                "effective_company_id": effective_company_id,
                "login": login,
                "state_file": state_file,
                "ok": ok,
                "guard_exit_code": code,
                "output": output,
            }
        )

    success_count = sum(1 for item in profile_reports if bool(item.get("ok")))
    if success_count < min_profiles_success:
        errors.append(f"success profile count {success_count} < {min_profiles_success}")

    distinct_count = len(observed_company_ids)
    if distinct_count < min_distinct_company_ids:
        warnings.append(
            f"observed distinct company ids {distinct_count} < target {min_distinct_company_ids}; observed={sorted(observed_company_ids)}"
        )
        if require_distinct_company_ids:
            errors.append(
                f"distinct company ids requirement not met: {distinct_count} < {min_distinct_company_ids}"
            )

    report = {
        "ok": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "profile_count": len(profile_reports),
            "success_count": success_count,
            "observed_company_ids": sorted(observed_company_ids),
            "distinct_company_id_count": distinct_count,
            "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        },
        "profiles": profile_reports,
        "thresholds": {
            "min_profiles_success": min_profiles_success,
            "min_distinct_company_ids": min_distinct_company_ids,
            "require_distinct_company_ids": require_distinct_company_ids,
            "require_live": require_live,
        },
        "sources": {
            "baseline": BASELINE_PATH.relative_to(ROOT).as_posix(),
            "snapshot_guard": SNAPSHOT_GUARD_PATH.relative_to(ROOT).as_posix(),
        },
    }

    lines = [
        "# Scene Company Snapshot Collect Report",
        "",
        f"- profile_count: `{len(profile_reports)}`",
        f"- success_count: `{success_count}`",
        f"- observed_company_ids: `{sorted(observed_company_ids)}`",
    ]
    if warnings:
        lines.extend(["", "## Warnings"] + [f"- {item}" for item in warnings])
    if errors:
        lines.extend(["", "## Errors"] + [f"- {item}" for item in errors])

    _write(
        report_json_path,
        _redact_passwords(json.dumps(report, ensure_ascii=False, indent=2), profile_passwords),
    )
    _write(report_md_path, _redact_passwords("\n".join(lines) + "\n", profile_passwords))

    if errors:
        print("[scene_company_snapshot_collect] FAIL")
        for item in errors:
            print(f" - {_redact_passwords(item, profile_passwords)}")
        print(_redact_passwords(report_json_path, profile_passwords))
        print(_redact_passwords(report_md_path, profile_passwords))
        return 1

    print(_redact_passwords(report_json_path, profile_passwords))
    print(_redact_passwords(report_md_path, profile_passwords))
    if warnings:
        print("[scene_company_snapshot_collect] PASS_WITH_WARNINGS")
        for item in warnings:
            print(f" - {_redact_passwords(item, profile_passwords)}")
    else:
        print("[scene_company_snapshot_collect] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
