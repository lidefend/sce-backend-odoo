#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REQUIRED = {
    "frontend/apps/web/src/stores/session.ts": (
        "sceneReadyContract: SceneReadyContract | null;",
        ").scene_ready_contract ?? null",
        "setSceneRegistryFromSceneReadyContract(this.sceneReadyContract)",
    ),
    "frontend/apps/web/src/views/SceneView.vue": (
        "session.sceneReadyContract",
        "result.scene_ready_contract",
        "usePageContract('scene')",
    ),
    "frontend/apps/web/src/views/ActionView.vue": (
        "session.sceneReadyContract",
        "result.scene_ready_contract",
    ),
    "frontend/apps/web/src/pages/contractForm/useRecordContractSemantics.ts": (
        "context.session.sceneReadyContract",
        "result.scene_ready_contract",
    ),
    "frontend/apps/web/src/app/pageContract.ts": (
        "contract.value?.page_orchestration",
        "fromCanonical.forEach",
    ),
    # Contract-declared values must be required, never defaulted: a missing or
    # invalid declaration stops the surface instead of letting the frontend guess.
    # The stop primitive lives in one shared module so every consumer stops the
    # same way (mechanism: frontend judgement -> stop -> ask the contract).
    "frontend/apps/web/src/app/contract/contractGap.ts": (
        "export class ContractGapError",
        "export function requireDeclaredNumber(",
        "requiredDeclarationLayer",
    ),
    "frontend/apps/web/src/app/action_runtime/hierarchicalWorksheetDataSource.ts": (
        "export { ContractGapError, isContractGapError } from '../contract/contractGap';",
        "export function requireDeclaredPageSize(sheet: WorksheetSheetConfig): number",
        "requireDeclaredPageSize(sheet)",
    ),
}
FORBIDDEN = (
    "scene_ready_contract_v1",
    "sceneReadyContractV1",
    "scene_contract_v1",
    "SceneContractV1",
    "sceneContractV1",
    "workspaceSceneContractV1",
    "page_orchestration_v1",
    "allowSceneContractFallback",
    "hasV1",
    # Retired frontend fallbacks for a contract-declared page size.
    "WORKSHEET_FIRST_PAGE_LIMIT",
    "WORKSHEET_FIRST_PAGE_MIN",
    "WORKSHEET_FIRST_PAGE_MAX",
    "worksheetFirstPageLimit",
)


def main() -> int:
    errors: list[str] = []
    for relative, required_tokens in REQUIRED.items():
        path = ROOT / relative
        if not path.is_file():
            errors.append(f"missing file: {relative}")
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for token in required_tokens:
            if token not in text:
                errors.append(f"{relative} missing canonical token: {token}")
        for token in FORBIDDEN:
            if token in text:
                errors.append(f"{relative} contains retired token: {token}")
    if errors:
        print("[frontend_scene_contract_consumption_guard] FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("[frontend_scene_contract_consumption_guard] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
