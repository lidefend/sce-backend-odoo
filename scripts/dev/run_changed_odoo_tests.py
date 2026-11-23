#!/usr/bin/env python3
"""Run changed Odoo test classes through the governed local.test entry."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.dev import changed_odoo_tests
from scripts.dev.local_test_inputs import fingerprint as test_surface_fingerprint
from scripts.ops.agent_run_context import delta_paths, resolve_run
from scripts.verify.frontend_dev_incremental import TEST_AUXILIARY_PREFIXES


def plan(root: Path) -> dict[str, list[str]]:
    selected = resolve_run(root)
    if selected is None:
        raise ValueError("no registered run")
    _, run = selected
    paths = delta_paths(root, run["baseline_sha"])
    test_modules: set[str] = set()
    production_modules: set[str] = set()
    for path in paths:
        match = re.match(r"addons/([a-z][a-z0-9_]*)/(.+)$", path)
        if not match:
            continue
        module, relative = match.groups()
        if (
            relative.startswith("tests/")
            and Path(relative).name.startswith("test_")
            and relative.endswith(".py")
        ):
            test_modules.add(module)
        elif (
            not relative.startswith("tests/")
            and not any(
                module == owner and relative.startswith(prefix)
                for owner, prefix in TEST_AUXILIARY_PREFIXES
            )
        ):
            production_modules.add(module)
    modules = sorted(test_modules - production_modules)
    return {
        module: changed_odoo_tests.selection(root, module)
        for module in modules
    }


def run(root: Path, selection: dict[str, list[str]]) -> int:
    if not selection:
        print("[changed-tests] BLOCKED no test-only module changes", file=sys.stderr)
        return 2
    current_head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()
    for module, tags in selection.items():
        current_test_surface = test_surface_fingerprint(root, module)
        reusable = reusable_receipt(
            root,
            module,
            tags,
            head=current_head,
            test_surface_fingerprint=current_test_surface,
        )
        if reusable:
            print(
                f"[changed-tests] REUSE module={module} classes={len(tags)} "
                f"receipt={reusable}",
                flush=True,
            )
            continue
        command = [
            "make",
            "--no-print-directory",
            "local.test.test",
            f"MODULE={module}",
            "TEST_TAGS=" + ",".join(tags),
        ]
        env = dict(
            os.environ,
            LOCAL_TEST_TEMPLATE_MODULE=module,
            LOCAL_TEST_REUSE_DATABASE="1",
        )
        print(
            f"[changed-tests] module={module} classes={len(tags)}",
            flush=True,
        )
        result = subprocess.run(command, cwd=root, env=env, check=False)
        if result.returncode:
            return result.returncode
    return 0


def reusable_receipt(
    root: Path,
    module: str,
    tags: list[str],
    *,
    head: str,
    test_surface_fingerprint: str,
) -> str:
    """Return an unchanged passed local.test receipt for this exact selection."""
    for path in sorted(
        (root / ".runtime/test-baseline").glob("*/receipt.json"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    ):
        try:
            receipt = json.loads(path.read_text(encoding="utf-8"))
            if not (
                receipt.get("status") == "passed"
                and receipt.get("head") == head
                and receipt.get("test_surface_fingerprint") == test_surface_fingerprint
                and receipt.get("test_surface_unchanged") is True
                and receipt.get("source_unchanged") is True
                and receipt.get("profile_unchanged") is True
                and receipt.get("image_unchanged") is True
                and receipt.get("module") == module
                and receipt.get("tags") == ",".join(tags)
                and isinstance(receipt.get("count"), int)
                and receipt.get("count") > 0
            ):
                continue
            log = root / str(receipt["log"])
            if (
                not log.is_file()
                or hashlib.sha256(log.read_bytes()).hexdigest()
                != receipt.get("log_sha256")
            ):
                continue
        except (OSError, ValueError, TypeError, KeyError):
            continue
        return path.relative_to(root).as_posix()
    return ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    try:
        selected = plan(root)
    except (OSError, ValueError, TypeError) as exc:
        print(f"[changed-tests] BLOCKED {exc}", file=sys.stderr)
        return 2
    return run(root, selected)


if __name__ == "__main__":
    raise SystemExit(main())
