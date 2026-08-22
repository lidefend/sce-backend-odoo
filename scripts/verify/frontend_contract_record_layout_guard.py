#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
RETIRED_TARGET = ROOT / "frontend/apps/web/src/app/contractRecordRuntime.ts"
CANONICAL_TARGET = ROOT / "frontend/apps/web/src/app/contracts/v2/store.ts"
REQUIRED_TOKENS = [
    "resolveContractV2FieldDescriptorMap",
    "resolveContractV2FieldWidgets",
    "collectContractV2FieldContainerStatusByCode",
]


def main() -> int:
    if RETIRED_TARGET.exists():
        print("[frontend_contract_record_layout_guard] FAIL")
        print(f"retired target still exists: {RETIRED_TARGET.relative_to(ROOT).as_posix()}")
        return 1
    if not CANONICAL_TARGET.is_file():
        print("[frontend_contract_record_layout_guard] FAIL")
        print(f"missing canonical target: {CANONICAL_TARGET.relative_to(ROOT).as_posix()}")
        return 1

    text = CANONICAL_TARGET.read_text(encoding="utf-8", errors="ignore")
    missing = [token for token in REQUIRED_TOKENS if token not in text]
    if missing:
        print("[frontend_contract_record_layout_guard] FAIL")
        for token in missing:
            print(f"{CANONICAL_TARGET.relative_to(ROOT).as_posix()}: missing token `{token}`")
        return 1

    print("[frontend_contract_record_layout_guard] PASS")
    print("scanned_files=1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
