#!/usr/bin/env python3
"""Block customer-module runtime coupling from the standard product domain."""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
PRODUCT_ROOTS = (
    ROOT / "addons" / "smart_core",
    ROOT / "addons" / "smart_construction_core",
)
FORBIDDEN = (
    "SC_EXTERNAL_PROJECTION",
    "sc_projection_owner_contract",
    "sce_" + "customer_" + "baosheng",
)
SUFFIXES = {".py", ".xml", ".csv", ".js", ".ts", ".vue"}


def main() -> int:
    failures = []
    scanned = 0
    for product_root in PRODUCT_ROOTS:
        for path in product_root.rglob("*"):
            if not path.is_file() or path.suffix not in SUFFIXES or "tests" in path.parts:
                continue
            scanned += 1
            source = path.read_text(encoding="utf-8")
            for token in FORBIDDEN:
                if token in source:
                    try:
                        display_path = path.relative_to(ROOT)
                    except ValueError:
                        display_path = path
                    failures.append("%s:%s" % (display_path, token))
    if failures:
        print("[product_customer_runtime_decoupling_guard] FAIL", file=sys.stderr)
        for failure in failures:
            print("- " + failure, file=sys.stderr)
        return 1
    print("[product_customer_runtime_decoupling_guard] PASS files=%s" % scanned)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
