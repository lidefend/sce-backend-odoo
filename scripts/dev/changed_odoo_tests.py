#!/usr/bin/env python3
"""Select test classes from the current run's changed Odoo test files.

The local iteration lane runs only the affected test-only surface. Full owning
module baselines remain the remote integration authority unless a production
model, handler, security or workflow input changed in the same module.
"""
from __future__ import annotations

import argparse
import ast
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.ops.agent_run_context import delta_paths, resolve_run


def classes(path: Path, module: str) -> list[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError) as exc:
        raise ValueError(f"unreadable test source: {path}") from exc
    names = sorted({
        node.name
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name.startswith("Test")
    })
    if not names:
        raise ValueError(f"changed test file declares no Test class: {path}")
    return [f"/{module}:{name}" for name in names]


def selection(root: Path, module: str) -> list[str]:
    if not re.fullmatch(r"[a-z][a-z0-9_]*", str(module or "")):
        raise ValueError("invalid Odoo module")
    selected = resolve_run(root)
    if selected is None:
        raise ValueError("no registered run")
    _, run = selected
    prefix = f"addons/{module}/tests/"
    paths = [
        path for path in delta_paths(root, run["baseline_sha"])
        if path.startswith(prefix)
        and Path(path).name.startswith("test_")
        and path.endswith(".py")
    ]
    if not paths:
        raise ValueError(f"no changed test files for module: {module}")
    tags: list[str] = []
    for relative in paths:
        tags.extend(classes(root / relative, module))
    return sorted(set(tags))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--module", required=True)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    try:
        tags = selection(args.root.resolve(), args.module)
    except (OSError, ValueError, TypeError) as exc:
        print(f"[changed-odoo-tests] BLOCKED {exc}", file=sys.stderr)
        return 2
    print(",".join(tags))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
