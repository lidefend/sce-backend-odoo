"""Stable inputs that can change an Odoo test verdict."""
from __future__ import annotations

import hashlib
import ast
import os
from pathlib import Path
import re
import subprocess


INCLUDE_PATHS = {
    "config/requirements-test.txt",
    "scripts/test/odoo_ordered_tests.py",
    "scripts/test/payment_approval_upgrade_rehearsal.py",
}


def module_dependencies(root: Path, module: str) -> set[str]:
    seen: set[str] = set()
    pending = [module]
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        if not re.fullmatch(r"[a-z][a-z0-9_]*", current):
            raise ValueError("invalid module identity")
        seen.add(current)
        manifest = next(
            (
                root / folder / current / "__manifest__.py"
                for folder in ("addons", "demo_addons", "addons_external")
                if (root / folder / current / "__manifest__.py").is_file()
            ),
            None,
        )
        if manifest is None:
            continue
        payload = ast.literal_eval(manifest.read_text(encoding="utf-8"))
        depends = payload.get("depends", [])
        if not isinstance(depends, (list, tuple)) or any(
            not isinstance(dep, str) for dep in depends
        ):
            raise ValueError("invalid module dependencies")
        pending.extend(depends)
    return seen


def fingerprint(root: Path, module: str) -> str:
    result = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    digest = hashlib.sha256()
    modules = module_dependencies(root, module)
    for raw in sorted(set(result.stdout.split(b"\0")) - {b""}):
        name = raw.decode("utf-8", errors="surrogateescape")
        match = re.match(
            r"(addons|demo_addons|addons_external)/([a-z][a-z0-9_]*)/(.*)$",
            name,
        )
        include = name in INCLUDE_PATHS
        if match:
            folder, owner, relative = match.groups()
            if owner == module:
                include = True
            elif owner in modules and not relative.startswith("tests/"):
                include = True
        if not include:
            continue
        digest.update(owner.encode() + b"\0" if match else b"\0")
        path = root / name
        digest.update(raw + b"\0")
        if path.is_symlink():
            digest.update(b"link:" + os.readlink(path).encode())
        elif path.is_file():
            digest.update(
                str(path.stat().st_mode & 0o777).encode()
                + path.read_bytes()
            )
        else:
            digest.update(b"missing")
    return digest.hexdigest()
