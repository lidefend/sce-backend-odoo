#!/usr/bin/env python3
"""Delete only one validated demo database's isolated runtime state."""

import argparse
from pathlib import Path
import re
import shutil


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--database", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"sc_demo(?:_[a-z0-9_]+)?", args.database):
        raise SystemExit("DEMO_RUNTIME_DATABASE_INVALID")
    root = args.data_root.resolve(strict=True)
    if root != Path("/var/lib/odoo"):
        raise SystemExit("DEMO_RUNTIME_DATA_ROOT_INVALID")
    for target in (root / "filestore" / args.database, root / "sessions"):
        if target.is_symlink():
            raise SystemExit("DEMO_RUNTIME_SYMLINK_FORBIDDEN")
        if target.exists():
            shutil.rmtree(target)
    print("[demo.runtime.purge] PASS database=%s" % args.database)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
