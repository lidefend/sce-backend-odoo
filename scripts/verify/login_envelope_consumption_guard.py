#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fail-closed guard for login-envelope token consumers under ``scripts/``.

Declared shape (addons/smart_core/handlers/login.py): the login intent publishes
the bearer token at ``data.session.token``.  The flat ``data.token`` key only
exists when ``contract_mode in {"compat", "debug"}`` and is declared deprecated
(``compat_deprecated: true``).  A consumer that reads only ``data.token``
therefore breaks under the default contract mode even with valid credentials.

This guard flags any ``scripts/**/*.py`` token read that is bound to a login
envelope but does not go through the declared ``session.token`` path (for example
``extract_login_token``).  ``session.bootstrap`` legitimately publishes a flat
``data.token``; its readers use the shared reader and are not treated as login
consumers.

The guard is intentionally fail-closed: an unparseable file is a violation.

Boundary: the analysis is static.  It flags token reads whose receiver is
login-signalled, either by name (``login*``), by an assignment whose value text
references a login call, or by an alias chain derived from either.  A token read
reached only through a fully login-agnostic indirection (no ``login`` signal
anywhere on the chain) is outside this static scope and is not claimed here.
"""

from __future__ import annotations

import ast
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "scripts"

# The shared reader home keeps the declared-path read plus its legacy fallback.
ALLOWED_FILES = {
    "scripts/verify/python_http_smoke_utils.py",
}

SKIP_DIR_NAMES = {"__pycache__", ".git", ".mypy_cache", ".pytest_cache", ".ruff_cache"}

TOKEN_KEYS = {"token"}


def _base_text(node: ast.AST) -> str:
    try:
        return ast.unparse(node)
    except Exception:  # pragma: no cover - unparse is stable on supported versions
        return ""


def _root_name(node: ast.AST) -> str:
    """Left-most Name in an attribute/subscript/call chain."""
    current: ast.AST = node
    while True:
        if isinstance(current, ast.Name):
            return current.id
        if isinstance(current, ast.Attribute):
            current = current.value
        elif isinstance(current, ast.Subscript):
            current = current.value
        elif isinstance(current, ast.Call):
            current = current.func
        else:
            return ""


def _scan_token_read(node: ast.AST) -> str | None:
    """Return the base expression text if this node reads a ``token`` key."""
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        if node.func.attr == "get" and node.args:
            first = node.args[0]
            if isinstance(first, ast.Constant) and first.value in TOKEN_KEYS:
                return _base_text(node.func.value)
    if isinstance(node, ast.Subscript):
        sl = node.slice
        if isinstance(sl, ast.Constant) and sl.value in TOKEN_KEYS:
            return _base_text(node.value)
    return None


def _assign_targets(node: ast.Assign | ast.AnnAssign) -> list[str]:
    if isinstance(node, ast.Assign):
        targets = node.targets
    else:
        targets = [node.target]
    names: list[str] = []
    for target in targets:
        if isinstance(target, ast.Name):
            names.append(target.id)
        elif isinstance(target, ast.Tuple):
            for element in target.elts:
                if isinstance(element, ast.Name):
                    names.append(element.id)
    return names


def _initial_derived(tree: ast.AST) -> tuple[set[str], set[str]]:
    login: set[str] = set()
    session: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value is not None:
            text = _base_text(node.value).lower()
            tags = []
            if "login" in text:
                tags.append(login)
            if "session" in text:
                tags.append(session)
            for target in _assign_targets(node):
                if "login" in target.lower():
                    login.add(target)
                if "session" in target.lower():
                    session.add(target)
                for tag in tags:
                    tag.add(target)
    return login, session


def _propagate(tree: ast.AST, login: set[str], session: set[str]) -> None:
    """Resolve simple alias chains: ``a = b`` / ``a = b.get("data")``."""
    changed = True
    while changed:
        changed = False
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Assign, ast.AnnAssign)) or node.value is None:
                continue
            value = node.value
            if isinstance(value, ast.Name):
                root = value.id
            else:
                root = _root_name(value)
            if not root:
                continue
            for tag in (login, session):
                if root in tag:
                    for target in _assign_targets(node):
                        if target not in tag:
                            tag.add(target)
                            changed = True


def find_violations(rel_path: str, source: str) -> list[str]:
    """Return violation descriptions for one file's source text."""
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [f"{rel_path}: cannot parse ({exc.msg} at line {exc.lineno})"]

    login, session = _initial_derived(tree)
    _propagate(tree, login, session)

    violations: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Call, ast.Subscript)):
            continue
        base = _scan_token_read(node)
        if base is None:
            continue
        lowered = base.lower()
        root = _root_name(node.func.value) if isinstance(node, ast.Call) else _root_name(node.value)
        if "session" in lowered or root in session:
            continue
        if "login" in lowered or root in login:
            line = getattr(node, "lineno", 0)
            violations.append(
                f"{rel_path}:{line}: reads deprecated login token path "
                f"(base={base!r}); use the declared data.session.token via extract_login_token"
            )
    return violations


def _iter_sources(root: Path) -> list[tuple[str, str]]:
    scripts_dir = root / "scripts"
    sources: list[tuple[str, str]] = []
    for path in sorted(scripts_dir.rglob("*.py")):
        if any(part in SKIP_DIR_NAMES for part in path.parts):
            continue
        rel = path.relative_to(root).as_posix()
        if rel in ALLOWED_FILES:
            continue
        try:
            sources.append((rel, path.read_text(encoding="utf-8")))
        except OSError as exc:  # pragma: no cover
            sources.append((rel, ""))
            print(f"[login_envelope_consumption_guard] cannot read {rel}: {exc}", file=sys.stderr)
    return sources


def scan_root(root: Path | str | None = None) -> list[str]:
    scan_root_path = Path(root) if root is not None else ROOT
    violations: list[str] = []
    for rel, source in _iter_sources(scan_root_path):
        violations.extend(find_violations(rel, source))
    return violations


def scan_repository() -> list[str]:
    return scan_root(ROOT)


def main() -> int:
    if not SCRIPTS_DIR.is_dir():
        print(f"[login_envelope_consumption_guard] missing scripts dir: {SCRIPTS_DIR}", file=sys.stderr)
        return 1
    violations = scan_repository()
    if violations:
        print("[login_envelope_consumption_guard] FAIL: deprecated login token consumers found:")
        for line in violations:
            print(f"  - {line}")
        return 1
    print("[login_envelope_consumption_guard] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
