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


def _test_source(path: Path) -> ast.Module:
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError) as exc:
        raise ValueError(f"unreadable test source: {path}") from exc


def _module_path(path: Path, module: str) -> Path | None:
    if not module:
        return None
    if module.startswith("."):
        level = len(module) - len(module.lstrip("."))
        target = path.parent
        for _ in range(max(0, level - 1)):
            target = target.parent
        remainder = module[level:]
        return target.joinpath(*remainder.split(".")).with_suffix(".py") if remainder else target
    if module.startswith("odoo.addons."):
        parts = module.split(".")[2:]
        candidate = ROOT.joinpath("addons", *parts).with_suffix(".py")
        return candidate if candidate.is_file() else None
    return None


def _imports(tree: ast.Module) -> tuple[dict[str, tuple[str, str]], dict[str, str]]:
    named: dict[str, tuple[str, str]] = {}
    modules: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            module = ("." * int(getattr(node, "level", 0) or 0)) + (node.module or "")
            for alias in node.names:
                local_name = alias.asname or alias.name
                if alias.name == "*":
                    continue
                if node.module is None:
                    modules[local_name] = module + alias.name
                elif module:
                    named[local_name] = (module, alias.name)
                else:
                    modules[local_name] = f".{alias.name}"
        elif isinstance(node, ast.Import):
            for alias in node.names:
                modules[alias.asname or alias.name.split(".")[0]] = alias.name
    return named, modules


def _decorated_as_odoo_test(node: ast.ClassDef) -> bool:
    for decorator in node.decorator_list:
        target = decorator.func if isinstance(decorator, ast.Call) else decorator
        if isinstance(target, ast.Name) and target.id == "tagged":
            return True
    return False


def _looks_like_test_class(node: ast.ClassDef) -> bool:
    return node.name.startswith("Test") or node.name.endswith(("Test", "Tests")) or _decorated_as_odoo_test(node)


def _class_kind(
    path: Path,
    node: ast.ClassDef,
    *,
    seen: set[tuple[Path, str]],
) -> str:
    key = (path.resolve(), node.name)
    if key in seen:
        return "unknown"
    seen = {*seen, key}
    tree = _test_source(path)
    named_imports, module_imports = _imports(tree)
    local_classes = {
        item.name: item for item in tree.body if isinstance(item, ast.ClassDef)
    }
    kinds: set[str] = set()

    def resolve_class(module: str, class_name: str) -> str:
        module_path = _module_path(path, module)
        if module_path is None or not module_path.is_file():
            return "unknown"
        module_tree = _test_source(module_path)
        target = next(
            (
                item for item in module_tree.body
                if isinstance(item, ast.ClassDef) and item.name == class_name
            ),
            None,
        )
        return _class_kind(module_path, target, seen=seen) if target is not None else "unknown"

    for base in node.bases:
        if isinstance(base, ast.Attribute) and isinstance(base.value, ast.Name):
            owner = base.value.id
            if owner == "unittest" and base.attr == "TestCase":
                kinds.add("offline")
                continue
            if owner in module_imports:
                kinds.add(resolve_class(module_imports[owner], base.attr))
                continue
            imported = named_imports.get(owner)
            if imported:
                module, _name = imported
                kinds.add(resolve_class(f"{module}.{base.attr}", "") if module else "unknown")
                continue
        if isinstance(base, ast.Name):
            if base.id in local_classes:
                kinds.add(_class_kind(path, local_classes[base.id], seen=seen))
                continue
            imported = named_imports.get(base.id)
            if imported:
                module, imported_name = imported
                if module == "unittest" and imported_name == "TestCase":
                    kinds.add("offline")
                elif module == "odoo.tests" or module.startswith("odoo.tests."):
                    kinds.add("orm")
                else:
                    kinds.add(resolve_class(module, imported_name))
                continue
            if base.id == "TestCase" and "TestCase" in module_imports:
                kinds.add("offline")
                continue
        kinds.add("unknown")

    if "orm" in kinds and "offline" in kinds:
        raise ValueError(f"ambiguous Odoo/unittest test base: {path}:{node.name}")
    if "orm" in kinds:
        return "orm"
    if "offline" in kinds:
        return "offline"
    return "unknown"


def odoo_test_classes(path: Path) -> list[ast.ClassDef]:
    tree = _test_source(path)
    class_nodes = [node for node in tree.body if isinstance(node, ast.ClassDef)]
    if not class_nodes:
        raise ValueError(f"changed test file declares no class: {path}")
    odoo_classes = []
    for node in class_nodes:
        kind = _class_kind(path, node, seen=set())
        if kind == "orm":
            odoo_classes.append(node)
        elif kind == "unknown" and _looks_like_test_class(node):
            raise ValueError(f"cannot identify Odoo or unittest test base: {path}:{node.name}")
    return odoo_classes


def classes(path: Path, module: str) -> list[str]:
    names = sorted(node.name for node in odoo_test_classes(path))
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
