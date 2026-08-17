#!/usr/bin/env python3
"""Static scope and architecture guard for the isolated UI5 scene spike."""

from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GENERIC_ROOT = ROOT / "frontend/packages/ui"
SPIKE_ROOT = ROOT / "frontend/apps/scene-ui5-spike"

ALLOWED_PREFIXES = (
    "frontend/packages/ui/",
    "frontend/apps/scene-ui5-spike/",
    "frontend/pnpm-lock.yaml",
    "make/frontend.mk",
    "scripts/verify/frontend_ui5_scene_spike_",
)

FORBIDDEN_GENERIC_TERMS = (
    "payment.request",
    "sc.payment.execution",
    "action_create_payment_execution",
    "fixture_role_finance",
    "FE Company A",
    "华东智造中心",
)

FORBIDDEN_RUNTIME_TERMS = (
    "fetch(",
    "axios",
    "/api/",
    "xmlrpc",
    "jsonrpc",
    "localStorage",
    "sessionStorage",
)


def fail(message: str) -> None:
    raise SystemExit(f"[verify.frontend.ui5_scene_spike.guard] FAIL {message}")


def changed_paths() -> list[str]:
    result = subprocess.run(
        ["git", "status", "--short"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    paths: list[str] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        paths.append(path)
    return paths


def read_sources(root: Path) -> str:
    suffixes = {".ts", ".vue", ".js", ".mjs", ".css", ".html", ".json"}
    return "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.suffix in suffixes and "node_modules" not in path.parts
    )


def main() -> None:
    if not GENERIC_ROOT.is_dir() or not SPIKE_ROOT.is_dir():
        fail("expected generic UI package and isolated spike app")

    outside = [
        path
        for path in changed_paths()
        if not any(path == prefix or path.startswith(prefix) for prefix in ALLOWED_PREFIXES)
    ]
    if outside:
        fail(f"change outside spike allowlist: {outside}")

    generic = read_sources(GENERIC_ROOT)
    fixture = read_sources(SPIKE_ROOT)

    leaked = [term for term in FORBIDDEN_GENERIC_TERMS if term in generic]
    if leaked:
        fail(f"industry facts leaked into generic package: {leaked}")

    runtime_calls = [term for term in FORBIDDEN_RUNTIME_TERMS if term in generic or term in fixture]
    if runtime_calls:
        fail(f"spike must remain static and side-effect free: {runtime_calls}")

    component = GENERIC_ROOT / "src/components/SceneObjectPage.vue"
    contract = GENERIC_ROOT / "src/contracts/sceneObjectPage.ts"
    payment_fixture = SPIKE_ROOT / "src/fixtures/paymentRequestScene.ts"
    for expected in (component, contract, payment_fixture):
        if not expected.is_file():
            fail(f"missing {expected.relative_to(ROOT)}")

    component_text = component.read_text(encoding="utf-8")
    required_markers = (
        "data-task-canvas",
        "data-context-rail",
        "data-activity-tabs",
        "scene-worktabs",
        "@media (max-width: 640px)",
    )
    missing = [marker for marker in required_markers if marker not in component_text]
    if missing:
        fail(f"missing scene foundation markers: {missing}")

    print(
        "[verify.frontend.ui5_scene_spike.guard] PASS "
        "scope=isolated generic_contract=true runtime_io=0"
    )


if __name__ == "__main__":
    main()
