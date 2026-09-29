#!/usr/bin/env python3
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend/apps/web/src"
PRIMITIVE = FRONTEND / "components/design-system/ScTable.vue"

# Page markup can live in SFCs as well as in side-car templates pulled in with
# `<template src="./x/template.html">`. Both render into the product, so both
# must consume the shared table authority; scanning only *.vue is exactly how a
# hand-rolled table survived in the menu configuration surface.
SOURCE_SUFFIXES = (".vue", ".html")


def raw_table_violations(frontend: Path) -> list[Path]:
    violations = []
    for suffix in SOURCE_SUFFIXES:
        for path in sorted(frontend.rglob(f"*{suffix}")):
            if "<table" in path.read_text(encoding="utf-8"):
                violations.append(path)
    return violations


def negative_self_test() -> list[str]:
    errors = []
    with TemporaryDirectory() as tmp:
        fixture = Path(tmp)
        (fixture / "surface.vue").write_text("<template><table><tr><td>x</td></tr></table></template>", encoding="utf-8")
        (fixture / "template.html").write_text("<table><thead><tr><th>x</th></tr></thead></table>", encoding="utf-8")
        (fixture / "adopted.vue").write_text('<template><ScTable :data="rows" /></template>', encoding="utf-8")
        flagged = {path.name for path in raw_table_violations(fixture)}
        if flagged != {"surface.vue", "template.html"}:
            errors.append(f"negative_self_test: expected SFC and side-car template detection, got {sorted(flagged)}")
    return errors


def main() -> int:
    errors = negative_self_test()
    for path in raw_table_violations(FRONTEND):
        if path == PRIMITIVE:
            continue
        errors.append(f"{path.relative_to(ROOT).as_posix()}: raw table bypasses ScTable TDesign adapter")
    primitive = PRIMITIVE.read_text(encoding="utf-8") if PRIMITIVE.is_file() else ""
    for marker in ("<TDesignTable", 'data-semantic-driver="tdesign-table"', "typeof value === 'function' ? value"):
        if marker not in primitive:
            errors.append(f"ScTable missing {marker}")
    if (FRONTEND / "components/design-system/ScDataTable.vue").exists():
        errors.append("parallel ScDataTable authority still exists")
    if errors:
        print("[frontend-table-primitive] FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    scanned = sum(len(list(FRONTEND.rglob(f"*{suffix}"))) for suffix in SOURCE_SUFFIXES)
    print(f"[frontend-table-primitive] PASS authority=ScTable driver=tdesign scanned={scanned} suffixes={','.join(SOURCE_SUFFIXES)} negative_self_test=pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
