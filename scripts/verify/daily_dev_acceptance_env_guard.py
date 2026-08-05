#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fail-closed environment guard for the governed daily acceptance probe."""
from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config/frontend/acceptance_environments_v1.json"


def _norm_env_file(value: str) -> str:
    path = Path(value)
    if not value or not path.is_absolute():
        return path.as_posix()
    try:
        return path.resolve().name if path.resolve().parent == ROOT else path.as_posix()
    except OSError:
        return path.as_posix()


def main() -> int:
    profile_name = os.getenv("SC_ACCEPTANCE_PROFILE", "daily").strip()
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    profile = config.get("profiles", {}).get(profile_name)
    errors: list[str] = []
    if profile_name != "daily" or not profile:
        errors.append("SC_ACCEPTANCE_PROFILE must resolve to the governed daily profile")
        profile = {}

    location = os.getenv("SC_ACCEPTANCE_LOCATION", "host").strip()
    governed_url = profile.get("host_base_url") if location == "host" else profile.get("base_url")
    if location not in {"remote", "host"}:
        errors.append("SC_ACCEPTANCE_LOCATION must be remote or host")
    observed_url = os.getenv("ACCEPTANCE_BASE_URL", governed_url or "").strip().rstrip("/")
    if observed_url != str(governed_url or "").rstrip("/"):
        errors.append(f"ACCEPTANCE_BASE_URL conflicts with the {location} daily endpoint")
    if urlparse(observed_url).scheme not in {"http", "https"}:
        errors.append("ACCEPTANCE_BASE_URL must be an HTTP(S) URL")

    navigation_policy = profile.get("navigation_policy", {})
    expected = {
        "ENV": profile.get("environment", ""),
        "ENV_FILE": ".env.dev",
        "DB_NAME": profile.get("database", ""),
        "ACCEPTANCE_NAV_MIN_ACTIONS": str(navigation_policy.get("min_actions", "")),
        "ACCEPTANCE_NAV_MAX_ACTIONS": str(navigation_policy.get("max_actions", "")),
        "ACCEPTANCE_NAV_FORBIDDEN_LABELS": ",".join(navigation_policy.get("forbidden_labels", [])),
        "ACCEPTANCE_NAV_REQUIRED_PATHS": ",".join(navigation_policy.get("required_paths", [])),
        "ACCEPTANCE_PROBE_OUTPUT": "artifacts/backend/dev_acceptance_release_probe.json",
        "FRONTEND_DIST_DIR": "./frontend/apps/web/dist-dev",
        "VITE_PLATFORM_ADMIN_DB": "sc_platform_core",
    }
    for key, wanted in expected.items():
        actual = _norm_env_file(os.getenv(key, "").strip()) if key == "ENV_FILE" else os.getenv(key, "").strip()
        if actual != wanted:
            errors.append(f"{key} must be {wanted!r}, got {actual!r}")

    if not os.getenv("ACCEPTANCE_LOGIN", "").strip() or not os.getenv("ACCEPTANCE_PASSWORD", "").strip():
        errors.append("daily acceptance credentials must be supplied through the governed environment")
    if os.getenv("ACCEPTANCE_NAV_REQUIRED_ACTIONS", "").strip():
        errors.append("numeric action-id pinning is forbidden; discover actions from authenticated navigation")

    forbidden = (
        "VITE_API_BASE_URL", "VITE_API_PROXY_TARGET", "VITE_ODOO_DB", "VITE_ODOO_DB_LOCKED",
        "VITE_APP_ENV", "VITE_BUILD_MODE", "VITE_BUILD_OUT_DIR", "VITE_DELIVERY_MODE",
        "VITE_FEATURE_FLAGS", "VITE_LITE_CONTRACT_PILOT", "VITE_LITE_CONTRACT_ROLLOUT", "VITE_TENANT",
    )
    for key in forbidden:
        if os.getenv(key, "").strip():
            errors.append(f"{key} must not override the governed daily profile")

    if errors:
        print("[daily_dev_acceptance_env_guard] FAIL")
        for error in errors:
            print(f"- {error}")
        return 2
    print(
        "[daily_dev_acceptance_env_guard] PASS "
        f"profile=daily location={location} base_url={observed_url} db={profile.get('database')} "
        "navigation=authenticated-discovery"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
