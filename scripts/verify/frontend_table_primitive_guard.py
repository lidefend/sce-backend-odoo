#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend/apps/web/src"
PRIMITIVE = FRONTEND / "components/design-system/ScTable.vue"


def main() -> int:
    violations = [
        path.relative_to(ROOT).as_posix()
        for path in FRONTEND.rglob("*.vue")
        if "<table" in path.read_text(encoding="utf-8")
    ]
    if violations:
        print("[frontend-table-primitive] FAIL")
        for path in violations:
            print(f"- raw table bypasses ScTable TDesign adapter: {path}")
        return 1
    primitive = PRIMITIVE.read_text(encoding="utf-8") if PRIMITIVE.is_file() else ""
    for marker in ("<TDesignTable", 'data-semantic-driver="tdesign-table"', "typeof value === 'function' ? value"):
        if marker not in primitive:
            print(f"[frontend-table-primitive] FAIL\n- ScTable missing {marker}")
            return 1
    legacy = FRONTEND / "components/design-system/ScDataTable.vue"
    if legacy.exists():
        print("[frontend-table-primitive] FAIL\n- parallel ScDataTable authority still exists")
        return 1
    print("[frontend-table-primitive] PASS authority=ScTable driver=tdesign")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
