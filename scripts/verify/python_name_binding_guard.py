#!/usr/bin/env python3
"""Static detection of two "code exists but is silently dead" defects.

Both families shipped in this repository and only surfaced in production,
because a plain parse of the source cannot see them.

1. Names read but never bound
   A helper was called but never imported, so the path raised ``NameError``.
   ``scripts/ci/python_syntax_check.py`` only builds an AST; it never resolves
   binding, so the defect stayed invisible until a user hit it. This guard walks
   the standard-library ``symtable`` scope tree and reports names that are
   referenced, are not local, are not module-level bindings and are not Python
   builtins -- exactly the names that raise ``NameError`` at runtime.

2. ``env.get("<model>")`` used for truthiness
   On an Odoo ``Environment``, ``env.get(model)`` returns an *empty recordset*
   when the model exists and ``None`` when it does not. Both are falsy, so
   ``if env.get("res.partner"):`` is always False: the model is present and the
   branch is still dead. That silently disabled audit writes, a capability
   report and several test guards. This guard reports an ``env.get`` result that
   feeds a truthiness test, inline or via a variable.

Exemptions (each is explicit; there is no wildcard path allowlist):
* Python builtins and module dunders (``__file__``, ``__name__``, ...).
* Modules that execute ``import *`` or ``globals().update(...)``: dynamic
  binding makes static resolution unsound for family 1, so the module is
  skipped for that family and counted.
* An inline ``# noqa`` acknowledgement. Family 1 also accepts the repository's
  existing ``# noqa: F821`` spelling.
* Under ``scripts/``, the two Odoo shell injection names ``env`` and ``odoo``
  that ``odoo shell < script.py`` provides. Product code under ``addons/`` must
  import everything it uses, so this exemption never applies there.

Exit codes: 0 = clean, 1 = violations found, 2 = usage error.
"""

from __future__ import annotations

import argparse
import ast
import builtins
import re
import symtable
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

DEFAULT_SCAN_ROOTS = ("addons", "scripts")

SKIP_DIR_NAMES = frozenset({"__pycache__", "node_modules", "retired"})

# Names a plain module never has to bind: language builtins plus the module
# dunders the import machinery sets on every module object.
IMPLICIT_NAMES = frozenset(dir(builtins)) | {
    "__file__", "__name__", "__doc__", "__module__", "__qualname__",
    "__class__", "__spec__", "__package__", "__builtins__", "__loader__",
    "__debug__", "__annotations__", "__dict__", "__all__", "__version__",
    "__path__", "__cached__",
}

# `odoo shell < script.py` prepends these to the interactive namespace before
# executing the piped source. Only shell/non-product scripts may rely on them.
ODOO_SHELL_INJECTED_NAMES = frozenset({"env", "odoo"})
SCRIPTS_PREFIX = "scripts"

NOQA_RE = re.compile(r"#\s*noqa(?::\s*(?P<codes>[A-Za-z0-9, ]+))?", re.IGNORECASE)

# A module is skipped from name analysis when binding is only knowable at
# runtime. `import *` and `globals().update()` both defeat static resolution.
DYNAMIC_BINDING_MARKERS = ("import *", "globals()")

# Odoo model names look like `res.partner` / `sc.usage.counter`.
MODEL_NAME_RE = re.compile(r"^[a-z_][a-z_0-9]*(\.[a-z_0-9]+)+$")

KIND_UNBOUND = "unbound-name"
KIND_ENV_GET = "env-get-truthiness"


class Violation:
    __slots__ = ("path", "kind", "detail", "lines")

    def __init__(self, path: str, kind: str, detail: str, lines: list[int]) -> None:
        self.path = path
        self.kind = kind
        self.detail = detail
        self.lines = lines


def iter_python_files(roots: list[Path]) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        if root.is_file() and root.suffix == ".py":
            files.append(root)
            continue
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.py")):
            if any(part in SKIP_DIR_NAMES for part in path.parts):
                continue
            files.append(path)
    return files


# --------------------------------------------------------------------------
# Family 1: names read but never bound
# --------------------------------------------------------------------------

def module_bindings(table: symtable.SymbolTable) -> set[str]:
    """Names bound at module scope: imports, assignments, def/class, params."""
    names: set[str] = set()
    for symbol in table.get_symbols():
        if (
            symbol.is_assigned()
            or symbol.is_imported()
            or symbol.is_namespace()
            or symbol.is_parameter()
        ):
            names.add(symbol.get_name())
    return names


def walk_tables(table: symtable.SymbolTable):
    yield table
    for child in table.get_children():
        yield from walk_tables(child)


def unbound_module_names(table: symtable.SymbolTable) -> set[str]:
    """Names read from an enclosing scope but never bound anywhere in module."""
    bound = module_bindings(table)
    found: set[str] = set()
    for scope in walk_tables(table):
        if scope.get_type() == "module":
            continue
        for symbol in scope.get_symbols():
            name = symbol.get_name()
            if not symbol.is_referenced() or not symbol.is_global():
                continue
            if name in bound or name in IMPLICIT_NAMES:
                continue
            found.add(name)
    return found


def _noqa_acknowledges(line: str, codes: tuple[str, ...]) -> bool:
    """True when an inline ``# noqa`` suppresses one of ``codes``.

    A bare ``# noqa`` suppresses everything; ``# noqa: E501, F821`` only the
    codes it lists. An empty ``codes`` tuple accepts any acknowledgement.
    """
    match = NOQA_RE.search(line)
    if not match:
        return False
    listed = match.group("codes")
    if listed is None or not listed.strip():
        return True
    if not codes:
        return True
    acknowledged = {item.strip().upper() for item in listed.split(",") if item.strip()}
    return any(code.upper() in acknowledged for code in codes)


def _load_lines_to_acknowledge(
    lines: list[str],
    uses: dict[str, set[int]],
    names: set[str],
    exempt: set[str],
    codes: tuple[str, ...],
) -> list[Violation]:
    violations: list[Violation] = []
    for name in sorted(names):
        if name in exempt:
            continue
        unacknowledged = [
            lineno
            for lineno in sorted(uses.get(name, ()))
            if not (
                0 < lineno <= len(lines)
                and _noqa_acknowledges(lines[lineno - 1], codes)
            )
        ]
        if unacknowledged:
            violations.append(Violation("", KIND_UNBOUND, name, unacknowledged))
    return violations


def _unbound_violations(tree: ast.AST, table: symtable.SymbolTable, source: str, exempt: set[str]) -> list[Violation]:
    names = unbound_module_names(table)
    if not names:
        return []
    lines = source.splitlines()
    uses: dict[str, set[int]] = defaultdict(set)
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id in names:
            uses[node.id].add(node.lineno)
    return _load_lines_to_acknowledge(lines, uses, names, exempt, ("F821",))


# --------------------------------------------------------------------------
# Family 2: `env.get("<model>")` used for truthiness
# --------------------------------------------------------------------------

def _is_odoo_env(node: ast.AST) -> bool:
    """`env` or any `<expr>.env` (typically ``self.env``)."""
    if isinstance(node, ast.Name):
        return node.id == "env"
    if isinstance(node, ast.Attribute):
        return node.attr == "env"
    return False


def _is_env_get_model_call(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "get"
        and _is_odoo_env(node.func.value)
        and len(node.args) == 1
        and isinstance(node.args[0], ast.Constant)
        and isinstance(node.args[0].value, str)
        and bool(MODEL_NAME_RE.match(node.args[0].value))
    )


ASSERT_TRUTHINESS_METHODS = frozenset({"assertTrue", "assertFalse"})


def _is_assert_truthiness_call(node: ast.AST) -> bool:
    """``self.assertTrue(x)`` / ``self.assertFalse(x)`` evaluate truthiness."""
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in ASSERT_TRUTHINESS_METHODS
        and len(node.args) >= 1
    )


def _truthiness_operands(test: ast.AST):
    """Nodes whose truth value a test expression evaluates."""
    if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
        yield test.operand
    elif isinstance(test, ast.BoolOp):
        yield from test.values
    else:
        yield test


def _env_get_violations(tree: ast.AST, source: str) -> list[Violation]:
    assigned: dict[str, tuple[int, str]] = {}
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and _is_env_get_model_call(node.value)
        ):
            assigned[node.targets[0].id] = (node.lineno, node.value.args[0].value)

    lines = source.splitlines()

    def acknowledged(lineno: int) -> bool:
        return 0 < lineno <= len(lines) and _noqa_acknowledges(lines[lineno - 1], ())

    violations: list[Violation] = []
    for node in ast.walk(tree):
        tests: list[ast.AST] = []
        if isinstance(node, (ast.If, ast.While, ast.IfExp, ast.Assert)):
            tests = [node.test]
        elif _is_assert_truthiness_call(node):
            tests = list(node.args[:1])
        for test in tests:
            for operand in _truthiness_operands(test):
                if _is_env_get_model_call(operand):
                    lineno, model = operand.lineno, operand.args[0].value
                elif isinstance(operand, ast.Name) and operand.id in assigned:
                    lineno, model = assigned[operand.id]
                else:
                    continue
                if not acknowledged(lineno):
                    violations.append(Violation("", KIND_ENV_GET, model, [lineno]))
    return violations


# --------------------------------------------------------------------------

def analyze_file(path: Path, rel_path: str) -> tuple[list[Violation], bool]:
    """Return (violations, skipped_name_analysis_for_dynamic_binding)."""
    try:
        source = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return [], False

    try:
        tree = ast.parse(source)
    except SyntaxError:
        # Syntax problems are owned by python_syntax_check.py; do not double-report.
        return [], False

    violations: list[Violation] = []
    if not any(marker in source for marker in DYNAMIC_BINDING_MARKERS):
        try:
            table = symtable.symtable(source, rel_path, "exec")
        except SyntaxError:
            table = None
        if table is not None:
            exempt = ODOO_SHELL_INJECTED_NAMES if rel_path.startswith(SCRIPTS_PREFIX) else set()
            violations.extend(_unbound_violations(tree, table, source, exempt))
    skipped = any(marker in source for marker in DYNAMIC_BINDING_MARKERS)

    violations.extend(_env_get_violations(tree, source))
    for item in violations:
        item.path = rel_path
    return violations, skipped


def _describe(item: Violation) -> str:
    lines = ", ".join(str(lineno) for lineno in item.lines)
    if item.kind == KIND_UNBOUND:
        return f"{item.path}: {item.detail} read but never bound (lines {lines})"
    return (
        f"{item.path}: env.get(\"{item.detail}\") used for truthiness (line {lines}); "
        f"env.get returns an empty recordset, which is always falsy"
    )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "roots",
        nargs="*",
        default=list(DEFAULT_SCAN_ROOTS),
        help="files or directories to scan (default: addons scripts)",
    )
    args = parser.parse_args(argv)

    roots = [ROOT / item for item in args.roots]
    files = iter_python_files(roots)

    violations: list[Violation] = []
    skipped = 0
    for path in files:
        rel_path = path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else path.as_posix()
        file_violations, dynamic = analyze_file(path, rel_path)
        violations.extend(file_violations)
        skipped += 1 if dynamic else 0

    if violations:
        print("[FAIL] Python name-binding check failed", file=sys.stderr)
        for item in sorted(violations, key=lambda v: (v.path, v.kind, v.detail)):
            print(f"  {_describe(item)}", file=sys.stderr)
        print(
            f"[python-name-binding] {len(violations)} violation(s) across "
            f"{len(files)} files; fix the binding/condition or add an explicit "
            f"'# noqa' acknowledgement.",
            file=sys.stderr,
        )
        return 1

    print(
        f"[OK] Python name-binding check passed "
        f"({len(files)} files, {skipped} dynamic-binding module(s) skipped)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
