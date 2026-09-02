#!/usr/bin/env python3
"""Guard relation read-visibility contract stays closed-loop (backend -> frontend)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND_PATH = ROOT / "addons/smart_core/app_config_engine/services/assemblers/page_assembler.py"
FRONTEND_PATHS = [
    ROOT / "frontend/apps/web/src/pages/ContractFormPage.vue",
    ROOT / "frontend/apps/web/src/pages/contractForm/relationDescriptor.ts",
    ROOT / "frontend/apps/web/src/pages/contractForm/useRecordRelationshipFields.ts",
    ROOT / "frontend/apps/web/src/pages/contractForm/useRecordRelationships.ts",
    ROOT / "frontend/apps/web/src/pages/contractForm/useRelationRuntime.ts",
    ROOT / "frontend/apps/web/src/pages/contractForm/useRecordRelationshipNavigation.ts",
    ROOT / "frontend/apps/web/src/pages/contractForm/useRecordPageLifecycle.ts",
]


def _read(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(str(path))
    return path.read_text(encoding="utf-8")


def _fail(lines: list[str]) -> int:
    print("[FAIL] relation_read_closure_guard")
    for line in lines:
        print(f"- {line}")
    return 1


def main() -> int:
    try:
        backend = _read(BACKEND_PATH)
        frontend = "\n".join(_read(path) for path in FRONTEND_PATHS)
    except FileNotFoundError as exc:
        return _fail([str(exc)])

    errors: list[str] = []

    backend_required = [
        "def _safe_can_read(model_name):",
        'check_access_rights("read", raise_exception=False)',
        '"can_read": _safe_can_read(relation)',
        'reason_code = "RELATION_READ_FORBIDDEN"',
        '"can_read": can_read',
        "def _apply_access_policy(self, data, model_name=\"\"):",
        'mode = "block"',
        'mode = "degrade"',
        'reason_code = "RELATION_READ_FORBIDDEN_CORE"',
        'data["access_policy"] = {',
    ]
    for marker in backend_required:
        if marker not in backend:
            errors.append(f"backend missing marker: {marker}")

    frontend_required = [
        "canRead: row.can_read === true,",
        "canOpen: row.can_open === true,",
        "if (entry?.canRead !== true)",
        "if (relationEntry(descriptor)?.canRead !== true) return [];",
        "if (entry?.canRead !== true) return [];",
        "if (relationEntry(resolvedDescriptor)?.canRead !== true) return;",
        "if (!params.canRead) {",
        "if (!relation || !params.canRead || deniedRelationModels.has(relation)) return [];",
        "const contractAccessPolicy = computed<ContractAccessPolicy>(() => {",
        "if (policy.mode === 'block') {",
        "throw new ContractAccessPolicyError(",
    ]
    for marker in frontend_required:
        if marker not in frontend:
            errors.append(f"frontend missing marker: {marker}")

    # Both candidate-query callsites must pass the backend projection into the
    # shared runtime, whose query and fetch paths each fail closed before I/O.
    if frontend.count("canRead: entry?.canRead === true,") < 2:
        errors.append("frontend missing canRead propagation in one of relation query paths")

    frontend_forbidden = [
        "canRead: row.can_read !== false,",
        "canOpen: row.can_open !== false,",
        "canRead: entry?.canRead !== false,",
        "if (entry && entry.canRead === false)",
    ]
    for marker in frontend_forbidden:
        if marker in frontend:
            errors.append(f"frontend contains fail-open relation authority: {marker}")

    # Frontend must not re-introduce hardcoded model-level ACL inference.
    frontend_acl_forbidden = [
        "function canReadRelationModel(",
    ]
    for marker in frontend_acl_forbidden:
        if marker in frontend:
            errors.append(f"frontend contains forbidden hardcoded ACL inference: {marker}")

    if errors:
        return _fail(errors)

    print("[OK] relation_read_closure_guard")
    print(f"- backend: {BACKEND_PATH}")
    print(f"- frontend modules: {len(FRONTEND_PATHS)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
