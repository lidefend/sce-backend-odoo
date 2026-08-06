#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fail closed through the canonical frontend acceptance environment resolver."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/frontend/acceptance_environments_v1.json"
CLI = ROOT / "scripts/verify/frontend_acceptance_environment_cli.mjs"


def main() -> int:
    policy = json.loads(POLICY.read_text(encoding="utf-8"))["profiles"]["daily"]
    child_env = os.environ.copy()
    child_env["SC_ACCEPTANCE_PROFILE"] = "daily"
    child_env["SC_ACCEPTANCE_FRONTEND_URL"] = os.getenv("ACCEPTANCE_BASE_URL", "").strip()
    child_env["SC_ACCEPTANCE_DATABASE"] = os.getenv("DB_NAME", "").strip()
    if not child_env.get("SC_ACCEPTANCE_EXPECTED_SHA"):
        child_env["SC_ACCEPTANCE_EXPECTED_SHA"] = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
    result = subprocess.run(
        ["node", str(CLI), "--tool", "daily-release-probe", "--operation", "readonly"],
        cwd=ROOT, env=child_env, text=True, capture_output=True, check=False,
    )
    errors: list[str] = []
    if result.returncode:
        errors.append(result.stderr.strip() or result.stdout.strip())
    expected = {
        "ENV": policy["environment"],
        "ENV_FILE": ".env.dev",
        "DB_NAME": policy["database"],
        "ACCEPTANCE_NAV_MIN_ACTIONS": str(policy["navigation_policy"]["min_actions"]),
        "ACCEPTANCE_NAV_MAX_ACTIONS": str(policy["navigation_policy"]["max_actions"]),
        "ACCEPTANCE_NAV_FORBIDDEN_LABELS": ",".join(policy["navigation_policy"]["forbidden_labels"]),
        "ACCEPTANCE_NAV_REQUIRED_PATHS": ",".join(policy["navigation_policy"]["required_paths"]),
        "ACCEPTANCE_PROBE_OUTPUT": "artifacts/backend/dev_acceptance_release_probe.json",
        "FRONTEND_DIST_DIR": "./frontend/apps/web/dist-dev",
        "VITE_PLATFORM_ADMIN_DB": "sc_platform_core",
    }
    for key, wanted in expected.items():
        actual = os.getenv(key, "").strip()
        if key == "ENV_FILE" and actual:
            actual = Path(actual).name
        if actual != wanted:
            errors.append(f"{key} must be {wanted!r}, got {actual!r}")
    if not os.getenv("ACCEPTANCE_LOGIN", "").strip() or not os.getenv("ACCEPTANCE_PASSWORD", "").strip():
        errors.append("daily acceptance credentials must be supplied through the governed environment")
    if os.getenv("ACCEPTANCE_NAV_REQUIRED_ACTIONS", "").strip():
        errors.append("numeric action-id pinning is forbidden; use authenticated navigation discovery")
    if errors:
        print("[daily_dev_acceptance_env_guard] FAIL")
        for error in errors:
            print(f"- {error}")
        return 2
    resolved = json.loads(result.stdout)
    print(
        "[daily_dev_acceptance_env_guard] PASS "
        f"profile={resolved['profile']} target={resolved['target']['baseUrl']} "
        f"db={resolved['data']['database']} sha={resolved['provenance']['expectedSha']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
