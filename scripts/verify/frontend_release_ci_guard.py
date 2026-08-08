#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/frontend_release_gate.yml"
POLICY = ROOT / "config/ci/frontend_release_gate_v1.json"


def findings(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    workflow = root / ".github/workflows/frontend_release_gate.yml"
    policy_path = root / "config/ci/frontend_release_gate_v1.json"
    runtime_make = root / "make/runtime_ops.mk"
    compose_file = root / "docker-compose.yml"
    try:
        text = workflow.read_text(encoding="utf-8")
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
        runtime_text = runtime_make.read_text(encoding="utf-8")
        compose_text = compose_file.read_text(encoding="utf-8")
    except (OSError, json.JSONDecodeError) as exc:
        return [f"CI_GATE_INPUT_INVALID:{exc}"]
    required_text = (
        "name: frontend_release_gate",
        "  frontend_release_gate:",
        "    name: frontend_release_gate",
        "pull_request:",
        "push:",
        "workflow_dispatch:",
        "cd frontend/apps/web",
        "pnpm test:release",
        "if: always()",
        "steps.release.outcome",
        "frontend_release_gate.py",
        "github.run_id",
        "github.run_attempt",
        "env.CHECKOUT_SHA",
        "retention-days: 30",
        "if-no-files-found: error",
    )
    errors.extend(f"WORKFLOW_CONTRACT_MISSING:{item}" for item in required_text if item not in text)
    forbidden = (
        "continue-on-error:",
        "actions/download-artifact",
        "matrix:",
        "|| true",
        "DAILY",
        ".env.prod",
    )
    errors.extend(f"WORKFLOW_FORBIDDEN:{item}" for item in forbidden if item in text)
    workflow_occurrences = 0
    for candidate in (root / ".github/workflows").glob("*.yml"):
        candidate_text = candidate.read_text(encoding="utf-8")
        workflow_occurrences += candidate_text.count("    name: frontend_release_gate")
    if workflow_occurrences != 1:
        errors.append(f"CHECK_NAME_NOT_UNIQUE:{workflow_occurrences}")
    if policy.get("authoritative_command") != "cd frontend/apps/web && pnpm test:release":
        errors.append("AUTHORITATIVE_COMMAND_DRIFT")
    if (
        'frontend/apps/web/dist/.build-sha256' not in runtime_text
        or 'export FRONTEND_BUILD_SHA256="$$frontend_build_sha"' not in runtime_text
    ):
        errors.append("CURRENT_FRONTEND_BUILD_IDENTITY_NOT_PROPAGATED")
    static_audit_text = (root / "scripts/verify/frontend_static_release_audit.py").read_text(
        encoding="utf-8"
    )
    if "scripts/verify/frontend_build_fingerprint.sh" not in static_audit_text:
        errors.append("CURRENT_FRONTEND_BUILD_IDENTITY_NOT_GENERATED")
    if (
        "VITE_ODOO_DB=$(FRONTEND_ACCEPTANCE_DB)" not in runtime_text
        or "VITE_APP_ENV=acceptance" not in runtime_text
        or "VITE_ODOO_DB: ${VITE_ODOO_DB:-sc_prod}" not in compose_text
        or "VITE_APP_ENV: ${VITE_APP_ENV:-production}" not in compose_text
    ):
        errors.append("FRONTEND_BUILD_ENVIRONMENT_NOT_ALIGNED")
    if (
        "verify.frontend.delivery_hardening.release.browser: "
        "ACCEPTANCE_BASE_URL := $(FRONTEND_ACCEPTANCE_BASE_URL)"
        not in runtime_text
    ):
        errors.append("FRONTEND_ACCEPTANCE_URL_ALIASES_NOT_ALIGNED")
    if policy.get("check_name") != "frontend_release_gate":
        errors.append("CHECK_NAME_DRIFT")
    after = policy.get("required_checks_after") or []
    if after != [
        "public_guard",
        "professional_authorization",
        "professional_quality_gate",
        "frontend_release_gate",
    ]:
        errors.append("REQUIRED_CHECK_POLICY_DRIFT")
    final_authorities = [
        row for row in policy.get("release_entrypoint_inventory") or [] if row.get("final_release_authority")
    ]
    if len(final_authorities) != 1 or final_authorities[0].get("check_name") != "frontend_release_gate":
        errors.append("FINAL_RELEASE_AUTHORITY_NOT_UNIQUE")
    return errors


def main() -> int:
    errors = findings()
    if errors:
        print("[frontend_release_ci_guard] FAIL", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 2
    print("[frontend_release_ci_guard] PASS authoritative_command=pnpm_test_release check=frontend_release_gate")
    return 0


if __name__ == "__main__":
    sys.exit(main())
