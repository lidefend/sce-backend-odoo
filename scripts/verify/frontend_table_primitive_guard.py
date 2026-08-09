#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend/apps/web/src"
PRIMITIVE = FRONTEND / "components/design-system/ScDataTable.vue"


def main() -> int:
    violations = [
        path.relative_to(ROOT).as_posix()
        for path in FRONTEND.rglob("*.vue")
        if path != PRIMITIVE and "<table" in path.read_text(encoding="utf-8")
    ]
    if violations:
        print("[frontend-table-primitive] FAIL")
        for path in violations:
            print(f"- raw table outside ScDataTable: {path}")
        return 1
    print("[frontend-table-primitive] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
