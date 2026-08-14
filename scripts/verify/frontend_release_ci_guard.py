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
        makefile_text = (root / "Makefile").read_text(encoding="utf-8")
        dev_make_text = (root / "make/dev.mk").read_text(encoding="utf-8")
        identity_text = (root / "scripts/common/frontend_release_ci_identity.sh").read_text(encoding="utf-8")
        operation_text = (root / "scripts/dev/frontend_acceptance_operation_entry.sh").read_text(encoding="utf-8")
        cleanup_text = (root / "scripts/ci/self_hosted_runner_cleanup.sh").read_text(encoding="utf-8")
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
    if text.count("printf 'COMPOSE_PROJECT_NAME=%s\\n' \"${CI_PROJECT_NAME}\"") != 2:
        errors.append("ISOLATED_COMPOSE_PROJECT_NOT_EXPORTED")
    if text.count("printf 'ODOO_PORT=18082\\n'") != 2:
        errors.append("ISOLATED_BACKEND_PORT_NOT_EXPORTED")
    if text.count("printf 'SC_SOURCE_REVISION=%s\\n' \"${CHECKOUT_SHA}\"") != 2:
        errors.append("ISOLATED_SOURCE_REVISION_NOT_EXPORTED")
    identity_markers = (
        "CI_PROJECT_NAME: sc-fe-release-${{ github.run_id }}-${{ github.run_attempt }}",
        "sce-ci-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}-frontend-release.env",
        "SC_FRONTEND_RELEASE_IDENTITY_FILE=%s\\n",
        "frontend_release_ci_identity.sh freeze",
    )
    errors.extend(
        f"FROZEN_CI_IDENTITY_MISSING:{marker}"
        for marker in identity_markers
        if marker not in text
    )
    freeze_at = text.find("- name: Freeze isolated frontend release identity")
    install_at = text.find("- name: Install locked frontend toolchain")
    release_at = text.find("- name: Run the single authoritative frontend release command")
    if min(freeze_at, install_at, release_at) < 0 or not (freeze_at < install_at < release_at):
        errors.append("CI_IDENTITY_NOT_FROZEN_BEFORE_RESOURCE_SIDE_EFFECTS")
    if "sc-fe-release-$(GITHUB_RUN_ID)-$(GITHUB_RUN_ATTEMPT)" not in makefile_text:
        errors.append("CI_ENV_FILE_PREPARSE_BYPASS_NOT_ATTEMPT_SCOPED")
    route_markers = (
        "verify_frozen_frontend_release_ci_identity",
        "validate_frozen_frontend_release_ci_resources",
        "db-ensure)",
        "fixture)",
        "release-snapshot)",
        "backend-up)",
        "backend-down)",
        "frontend-up)",
        "frontend-down)",
    )
    errors.extend(f"CI_OPERATION_ROUTE_MISSING:{marker}" for marker in route_markers if marker not in operation_text)
    process_identity_markers = (
        "sce-ci-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}-frontend-release.pid",
        "validate_ci_frontend_pidfile",
        "validate_ci_frontend_live_process",
        "GITHUB_RUN_ID=$GITHUB_RUN_ID",
        "COMPOSE_PROJECT_NAME=$COMPOSE_PROJECT_NAME",
        "SC_SOURCE_REVISION=$SC_SOURCE_REVISION",
        "FRONTEND_ACCEPTANCE_ALLOW_REUSE=1",
        "isolated CI frontend port is owned without this run identity",
    )
    errors.extend(
        f"CI_FRONTEND_PROCESS_IDENTITY_MISSING:{marker}"
        for marker in process_identity_markers
        if marker not in operation_text
    )
    for target in ("frontend.acceptance.up", "frontend.acceptance.down", "backend.acceptance.up", "backend.acceptance.down"):
        if target not in dev_make_text or "frontend_acceptance_operation_entry.sh" not in dev_make_text:
            errors.append(f"CI_MAKE_ROUTE_MISSING:{target}")
    for target in ("db.frontend.acceptance.ensure", "acceptance.frontend.fixture", "acceptance.frontend.release_snapshot"):
        if target not in runtime_text or "frontend_acceptance_operation_entry.sh" not in runtime_text:
            errors.append(f"CI_MAKE_ROUTE_MISSING:{target}")
    make_sources = [makefile_text, dev_make_text, runtime_text]
    frontend_make = root / "make/frontend.mk"
    if frontend_make.exists():
        make_sources.append(frontend_make.read_text(encoding="utf-8"))
    if any("bash scripts/dev/frontend_acceptance_runtime.sh" in source for source in make_sources):
        errors.append("FRONTEND_ACCEPTANCE_RUNTIME_DIRECT_MAKE_BYPASS")
    identity_required = (
        "! -L \"$path\"",
        "stat -c '%u'",
        "stat -c '%a'",
        "GITHUB_RUN_ATTEMPT",
        "ENV_SHA256",
        "validate_frozen_frontend_release_ci_resources",
    )
    errors.extend(f"CI_IDENTITY_GUARD_MISSING:{marker}" for marker in identity_required if marker not in identity_text)
    cleanup_verify = cleanup_text.find("verify_frozen_frontend_release_ci_identity")
    cleanup_remove = cleanup_text.find('docker compose -p "${project}" down')
    if min(cleanup_verify, cleanup_remove) < 0 or cleanup_verify > cleanup_remove:
        errors.append("CI_CLEANUP_NOT_BOUND_TO_FROZEN_IDENTITY")
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
