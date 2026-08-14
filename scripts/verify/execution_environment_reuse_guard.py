#!/usr/bin/env python3
"""Inventory governed execution environments and reject duplicate setup paths."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]


def inventory() -> dict:
    policy = json.loads(
        (ROOT / "config/frontend/acceptance_environments_v1.json").read_text(encoding="utf-8")
    )
    local = policy["profiles"]["local"]
    runtime = local["managed_runtime"]
    services = runtime["services"]
    tools = json.loads(
        (ROOT / "config/frontend/acceptance_tool_matrix_v1.json").read_text(encoding="utf-8")
    )["tools"]
    return {
        "schema": "execution_environment_capability_inventory.v1",
        "decision": "REUSE_EXISTING_GOVERNED_ENVIRONMENT",
        "prohibition": "P0-P3 topics must not create or override environment topology",
        "capabilities": {
            "governed_worktree": ["make workspace.worktree.create", "make workspace.worktree.cleanup"],
            "isolated_backend_test": ["make test.safe", "make ci.gate", "make ci.smoke", "make ci.full"],
            "isolated_frontend_release_ci": {
                "entry": "make db.frontend.acceptance.ensure",
                "environment_authority": "GitHub Actions RUNNER_TEMP ENV_FILE",
                "compose_project_pattern": "sc-fe-release-${GITHUB_RUN_ID}",
                "database": "sc_frontend_acceptance",
                "database_filter": "^sc_frontend_acceptance$",
                "volume_patterns": {
                    "database": "sc-fe-release-${GITHUB_RUN_ID}-db-data",
                    "redis": "sc-fe-release-${GITHUB_RUN_ID}-redis-data",
                    "odoo": "sc-fe-release-${GITHUB_RUN_ID}-odoo-data",
                },
                "identity": ["repository", "workspace", "checkout SHA", "run ID", "0600 env file"],
            },
            "managed_acceptance": {
                "database": local["database"],
                "database_filter": runtime["database_filter"],
                "compose_project": runtime["compose_project"],
                "volumes": runtime["volumes"],
                "backend_port": services["backend_port"],
                "frontend_port": services["frontend_port"],
                "role_bindings": local["role_bindings"],
                "allowed_operations": local["allowed_operations"],
                "entries": [
                    "make acceptance.runtime.preflight",
                    "make backend.acceptance.up",
                    "make frontend.acceptance.up",
                    "make acceptance.module.upgrade",
                    "make acceptance.baseline.upgrade",
                    "make acceptance.frontend.fixture",
                    "make acceptance.frontend.release_snapshot",
                    "make verify.frontend.collection_view_semantics.browser",
                ],
            },
            "runtime_identity": ["source revision", "dirty/staged/untracked source fingerprint"],
            "browser_coordination": {
                "mechanisms": ["profile resolver", "shared-read lease", "exclusive-write lease"],
                "governed_tools": sorted(tools),
            },
            "install_upgrade_gates": [
                "make local.clean.install",
                "make test-install-gate",
                "make test-upgrade-gate",
            ],
        },
    }


def verify() -> list[str]:
    errors: list[str] = []
    expected = inventory()
    managed = expected["capabilities"]["managed_acceptance"]
    if managed["database"] != "sc_frontend_acceptance":
        errors.append("managed acceptance database drift")
    if managed["database_filter"] != "^sc_frontend_acceptance$":
        errors.append("managed acceptance database filter drift")
    if managed["backend_port"] != 18082 or managed["frontend_port"] != 5175:
        errors.append("managed acceptance port drift")
    if managed["compose_project"] != "sc-fe-r2-p1-01":
        errors.append("managed acceptance compose project drift")
    expected_volumes = {
        "database": "sc_fe_r2_p1_01_db",
        "redis": "sc_fe_r2_p1_01_redis",
        "odoo": "sc_fe_r2_p1_01_odoo",
    }
    if managed["volumes"] != expected_volumes:
        errors.append("managed acceptance volume identity drift")
    isolated_release = expected["capabilities"]["isolated_frontend_release_ci"]
    if isolated_release["compose_project_pattern"] != "sc-fe-release-${GITHUB_RUN_ID}":
        errors.append("isolated frontend release project identity drift")
    if isolated_release["database"] != "sc_frontend_acceptance" or isolated_release["database_filter"] != "^sc_frontend_acceptance$":
        errors.append("isolated frontend release database identity drift")

    sources = {
        "Makefile": (ROOT / "Makefile").read_text(encoding="utf-8"),
        "make/ci.mk": (ROOT / "make/ci.mk").read_text(encoding="utf-8"),
        "make/dev.mk": (ROOT / "make/dev.mk").read_text(encoding="utf-8"),
        "make/runtime_ops.mk": (ROOT / "make/runtime_ops.mk").read_text(encoding="utf-8"),
        "scripts/ci/run_ci.sh": (ROOT / "scripts/ci/run_ci.sh").read_text(encoding="utf-8"),
        "scripts/dev/frontend_acceptance_runtime.sh": (
            ROOT / "scripts/dev/frontend_acceptance_runtime.sh"
        ).read_text(encoding="utf-8"),
        "scripts/dev/frontend_acceptance_db_ensure_entry.sh": (ROOT / "scripts/dev/frontend_acceptance_db_ensure_entry.sh").read_text(encoding="utf-8"),
        "scripts/dev/frontend_acceptance_operation_entry.sh": (ROOT / "scripts/dev/frontend_acceptance_operation_entry.sh").read_text(encoding="utf-8"),
        "scripts/common/frontend_release_ci_identity.sh": (ROOT / "scripts/common/frontend_release_ci_identity.sh").read_text(encoding="utf-8"),
        "scripts/test/frontend_acceptance_db_ensure.sh": (ROOT / "scripts/test/frontend_acceptance_db_ensure.sh").read_text(encoding="utf-8"),
        "scripts/ci/self_hosted_runner_cleanup.sh": (ROOT / "scripts/ci/self_hosted_runner_cleanup.sh").read_text(encoding="utf-8"),
        "scripts/dev/backend_acceptance_up.sh": (ROOT / "scripts/dev/backend_acceptance_up.sh").read_text(encoding="utf-8"),
        "scripts/dev/backend_acceptance_down.sh": (ROOT / "scripts/dev/backend_acceptance_down.sh").read_text(encoding="utf-8"),
        "scripts/dev/frontend_acceptance_up.sh": (ROOT / "scripts/dev/frontend_acceptance_up.sh").read_text(encoding="utf-8"),
        "scripts/dev/frontend_acceptance_down.sh": (ROOT / "scripts/dev/frontend_acceptance_down.sh").read_text(encoding="utf-8"),
        "scripts/ci/upgrade_gate.sh": (ROOT / "scripts/ci/upgrade_gate.sh").read_text(encoding="utf-8"),
        "scripts/ci/install_gate.sh": (ROOT / "scripts/ci/install_gate.sh").read_text(encoding="utf-8"),
        "scripts/common/governed_make_entry.sh": (ROOT / "scripts/common/governed_make_entry.sh").read_text(encoding="utf-8"),
        "scripts/mod/install.sh": (ROOT / "scripts/mod/install.sh").read_text(encoding="utf-8"),
        "scripts/mod/upgrade.sh": (ROOT / "scripts/mod/upgrade.sh").read_text(encoding="utf-8"),
        "scripts/test/frontend_productization_fixture.sh": (ROOT / "scripts/test/frontend_productization_fixture.sh").read_text(encoding="utf-8"),
        "scripts/verify/collection_view_semantics_browser.mjs": (ROOT / "scripts/verify/collection_view_semantics_browser.mjs").read_text(encoding="utf-8"),
    }
    required = {
        "Makefile": ("sc-fe-release-$(GITHUB_RUN_ID)", "CI_PROJECT_NAME", "include $(ENV_FILE_RESOLVED)"),
        "make/ci.mk": ("environment.capability.inventory", "SC_GOVERNED_CI_ENTRY=1"),
        "make/dev.mk": ("environment.capability.inventory", "SC_GOVERNED_ACCEPTANCE_ENTRY=1"),
        "make/runtime_ops.mk": ("environment.capability.inventory", "SC_GOVERNED_ACCEPTANCE_ENTRY=1"),
        "scripts/ci/run_ci.sh": ("SC_GOVERNED_CI_ENTRY", "direct run_ci.sh execution is forbidden", "require_governed_make_ancestor"),
        "scripts/dev/frontend_acceptance_runtime.sh": (
            "SC_GOVERNED_ACCEPTANCE_ENTRY",
            "direct runtime script execution is forbidden",
            "SC_GOVERNED_ACCEPTANCE_LOWER_ENTRY=1",
            "require_governed_make_ancestor",
        ),
        "scripts/dev/frontend_acceptance_db_ensure_entry.sh": ("SC_GOVERNED_FRONTEND_DB_ENSURE_ENTRY", "require_governed_make_ancestor", "validate_frontend_release_ci_identity", "SC_GOVERNED_ACCEPTANCE_ENTRY=1"),
        "scripts/dev/frontend_acceptance_operation_entry.sh": ("SC_GOVERNED_FRONTEND_ACCEPTANCE_OPERATION_ENTRY", "require_governed_make_ancestor", "validate_frontend_release_ci_identity", "PortBindings", "com.docker.compose.project", "SC_SOURCE_REVISION", "source or data mount identity mismatch", "REUSED isolated_ci", "RETAINED isolated_ci", "SC_GOVERNED_ACCEPTANCE_LOWER_ENTRY=1"),
        "scripts/common/frontend_release_ci_identity.sh": ("GITHUB_ACTIONS", "CI_PROJECT_NAME", "RUNNER_TEMP", "CHECKOUT_SHA", "SC_SOURCE_REVISION", "COMPOSE_FILES", "allowed_keys", "unknown or duplicate keys", "compose command override", "route override", "sc_frontend_acceptance", "volume identity mismatch"),
        "scripts/test/frontend_acceptance_db_ensure.sh": ("SC_GOVERNED_FRONTEND_DB_ENSURE_LOWER_ENTRY", "require_governed_make_ancestor"),
        "scripts/ci/self_hosted_runner_cleanup.sh": ('"sc-prof-${run_id}"', '"sc-fe-release-${run_id}"', "GITHUB_REPOSITORY", 'readlink -f "$root_dir"', "invalid project scope", "invalid workspace scope", "invalid runner temp scope"),
        "scripts/dev/backend_acceptance_up.sh": ("SC_GOVERNED_ACCEPTANCE_LOWER_ENTRY", "require_governed_make_ancestor", "non-canonical port", "non-canonical database"),
        "scripts/dev/backend_acceptance_down.sh": ("SC_GOVERNED_ACCEPTANCE_LOWER_ENTRY", "require_governed_make_ancestor", "SC_SOURCE_REVISION", "SC_SOURCE_FINGERPRINT", "SC_PRODUCT_VERSION", "sc_fe_r2_p1_01_odoo"),
        "scripts/dev/frontend_acceptance_up.sh": ("SC_GOVERNED_ACCEPTANCE_LOWER_ENTRY", "require_governed_make_ancestor", "non-canonical pidfile", "non-canonical port", "unsupported mode", "non-canonical production dist"),
        "scripts/dev/frontend_acceptance_down.sh": ("SC_GOVERNED_ACCEPTANCE_LOWER_ENTRY", "require_governed_make_ancestor", "VITE_APP_ENV=acceptance", "process starttime changed", "process command identity changed"),
        "scripts/ci/upgrade_gate.sh": ("SC_GOVERNED_GATE_ENTRY", "SC_GOVERNED_CI_ENTRY=1", "require_governed_make_ancestor"),
        "scripts/ci/install_gate.sh": ("SC_GOVERNED_GATE_ENTRY", "require_governed_make_ancestor"),
        "scripts/common/governed_make_entry.sh": ("require_governed_make_ancestor", "allowed make targets required", "GNU long-option abbreviations", "-*) injected=1", "MAKEFILES", "MAKEFLAGS=*|GNUMAKEFLAGS=*", "mapfile -d '' -t argv", '"${#goals[@]}" == "1"', '"${goals[0]}" == "$target"'),
        "scripts/mod/install.sh": ("SC_GOVERNED_MODULE_LIFECYCLE_ENTRY", "direct module install is forbidden", "require_governed_make_ancestor"),
        "scripts/mod/upgrade.sh": ("SC_GOVERNED_MODULE_LIFECYCLE_ENTRY", "direct module upgrade is forbidden", "require_governed_make_ancestor"),
        "scripts/test/frontend_productization_fixture.sh": ("SC_GOVERNED_FRONTEND_FIXTURE_LOWER_ENTRY", "direct fixture execution is forbidden", "require_governed_make_ancestor"),
        "scripts/verify/collection_view_semantics_browser.mjs": ("SC_GOVERNED_BROWSER_ENTRY", "direct browser execution is forbidden", "require_governed_make_ancestor", "SC_ACCEPTANCE_FRONTEND_URL: 'http://127.0.0.1:5175'", "SC_ACCEPTANCE_API_URL: 'http://127.0.0.1:5175'", "SC_ACCEPTANCE_DATABASE: 'sc_frontend_acceptance'", "acquireAcceptanceLease"),
    }
    for path, markers in required.items():
        for marker in markers:
            if marker not in sources[path]:
                errors.append(f"{path}: missing reuse guard marker: {marker}")
    collection_source = sources["scripts/verify/collection_view_semantics_browser.mjs"]
    lease_at = collection_source.find("const acceptanceLease = await acquireAcceptanceLease")
    mkdir_at = collection_source.find("fs.mkdirSync")
    browser_at = collection_source.find("const browser = await launchChromium")
    if min(lease_at, mkdir_at, browser_at) < 0 or not (lease_at < mkdir_at < browser_at):
        errors.append("collection browser must acquire its lease before artifact or browser side effects")
    db_entry_source = sources["scripts/dev/frontend_acceptance_db_ensure_entry.sh"]
    ci_identity_at = db_entry_source.find('validate_frontend_release_ci_identity "$ROOT_DIR"')
    ci_compose_at = db_entry_source.find("compose_dev up -d --wait db redis odoo")
    ci_ensure_at = db_entry_source.find("SC_GOVERNED_FRONTEND_DB_ENSURE_LOWER_ENTRY=1")
    if min(ci_identity_at, ci_compose_at, ci_ensure_at) < 0 or not (ci_identity_at < ci_compose_at < ci_ensure_at):
        errors.append("isolated frontend release must validate identity before compose or database side effects")
    dev_test = (ROOT / "make/dev_test.mk").read_text(encoding="utf-8")
    if "test.safe: guard.prod.forbid environment.capability.inventory" not in dev_test:
        errors.append("make/dev_test.mk: test.safe must inventory before execution")
    target_sources = "\n".join((ROOT / path).read_text(encoding="utf-8") for path in ("make/dev.mk", "make/runtime_ops.mk", "make/ci.mk", "make/frontend.mk"))
    governed_targets = (
        "acceptance.runtime.preflight", "acceptance.runtime.infrastructure.restore",
        "frontend.acceptance.up", "frontend.acceptance.down", "frontend.acceptance.health",
        "backend.acceptance.up", "backend.acceptance.down", "backend.acceptance.health",
        "backend.collection.acceptance.up", "backend.collection.acceptance.down",
        "frontend.collection.acceptance.up", "frontend.collection.acceptance.down",
        "acceptance.module.upgrade", "acceptance.baseline.upgrade",
        "mod.install", "mod.upgrade", "verify.p0.flow", "gate.business_baseline", "prod.upgrade.core",
        "db.frontend.acceptance.ensure", "acceptance.frontend.fixture",
        "acceptance.frontend.release_snapshot", "test-install-gate", "test-upgrade-gate",
        "verify.frontend.collection_view_semantics.browser",
    )
    for target in governed_targets:
        match = re.search(rf"(?m)^{re.escape(target)}:[^\n]*$", target_sources)
        if not match or "environment.capability.inventory" not in match.group(0):
            errors.append(f"governed target missing inventory prerequisite: {target}")
    operational_suffixes = {".mk", ".sh", ".mjs", ".js", ".ts", ".py", ".json", ".yml", ".yaml"}
    scan_files = [ROOT / "Makefile"]
    for base in (ROOT / "make", ROOT / "scripts", ROOT / "frontend/apps/web/scripts", ROOT / ".github"):
        scan_files.extend(path for path in base.rglob("*") if path.is_file() and path.suffix in operational_suffixes)
    scan_files.extend(path for path in (ROOT / "frontend/package.json", ROOT / "frontend/apps/web/package.json") if path.is_file())
    scan_files = sorted(set(scan_files))
    for path in scan_files:
        relative = path.relative_to(ROOT).as_posix()
        if "/tests/" in relative or path.name.startswith("test_") or relative in {
            "scripts/verify/execution_environment_reuse_guard.py",
            "scripts/verify/test_execution_environment_reuse_guard.py",
        }:
            continue
        text = path.read_text(encoding="utf-8")
        for forbidden in ("18102", "5192", "sc-backend-odoo-collection-view-semantics", "sc-collection-view-semantics"):
            if forbidden in text:
                errors.append(f"{relative}: retains parallel acceptance topology: {forbidden}")
        for line in text.splitlines():
            invocation = r"(?:\b(?:bash|sh)\b|subprocess|Popen|execFile|spawn|(?:^|[\s@])(?:\./)?scripts/)"
            if re.search(invocation + r".*run_ci\.sh", line):
                allowed = (
                    relative == "make/ci.mk" and "SC_GOVERNED_CI_ENTRY=1" in line
                ) or (
                    relative == "scripts/ci/upgrade_gate.sh" and "SC_GOVERNED_CI_ENTRY=1" in line
                )
                if not allowed:
                    errors.append(f"ungoverned run_ci call: {relative}: {line.strip()}")
            if re.search(invocation + r".*(?:install|upgrade)_gate\.sh", line):
                if relative != "make/ci.mk" or "SC_GOVERNED_GATE_ENTRY=1" not in line:
                    errors.append(f"ungoverned install/upgrade gate call: {relative}: {line.strip()}")
            if re.search(invocation + r".*frontend_acceptance_runtime\.sh", line):
                if relative not in {"make/dev.mk", "make/runtime_ops.mk", "scripts/dev/frontend_acceptance_db_ensure_entry.sh", "scripts/dev/frontend_acceptance_operation_entry.sh"} or "SC_GOVERNED_ACCEPTANCE_ENTRY=1" not in line:
                    errors.append(f"ungoverned acceptance runtime call: {relative}: {line.strip()}")
            if re.search(r"(?:\b(?:bash|sh)\b|subprocess|Popen|execFile|spawn).*frontend_acceptance_db_ensure\.sh", line):
                if relative not in {"scripts/dev/frontend_acceptance_runtime.sh", "scripts/dev/frontend_acceptance_db_ensure_entry.sh"} or "SC_GOVERNED_FRONTEND_DB_ENSURE_LOWER_ENTRY=1" not in line:
                    errors.append(f"ungoverned frontend database ensure call: {relative}: {line.strip()}")
            if re.search(invocation + r".*(?:backend|frontend)_acceptance_(?:up|down)\.sh", line):
                if relative not in {"scripts/dev/frontend_acceptance_runtime.sh", "scripts/dev/frontend_acceptance_operation_entry.sh"} or "SC_GOVERNED_ACCEPTANCE_LOWER_ENTRY=1" not in line:
                    errors.append(f"ungoverned lower acceptance call: {relative}: {line.strip()}")
            if re.search(invocation + r".*scripts/mod/(?:install|upgrade)\.sh", line):
                allowed_module_callers = {"make/runtime_ops.mk", "scripts/dev/frontend_acceptance_runtime.sh", "scripts/verify/p0_flow.sh", "scripts/verify/frontend_acceptance_environment_source_guard.py"}
                if relative not in allowed_module_callers or "SC_GOVERNED_MODULE_LIFECYCLE_ENTRY=1" not in line:
                    errors.append(f"ungoverned module lifecycle call: {relative}: {line.strip()}")
            if re.search(invocation + r".*scripts/test/frontend_productization_fixture\.sh", line):
                allowed_fixture_callers = {"scripts/dev/frontend_acceptance_runtime.sh", "scripts/dev/frontend_acceptance_operation_entry.sh"}
                if relative not in allowed_fixture_callers or "SC_GOVERNED_FRONTEND_FIXTURE_LOWER_ENTRY=1" not in line:
                    errors.append(f"ungoverned frontend fixture call: {relative}: {line.strip()}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--inventory", action="store_true")
    mode.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.inventory:
        print(json.dumps(inventory(), ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    errors = verify()
    if errors:
        print("[execution_environment_reuse_guard] FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("[execution_environment_reuse_guard] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
