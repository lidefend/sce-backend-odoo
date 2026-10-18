#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Canonical scanner for backend model field declarations.

Odoo merges same-name field definitions from every class block on a model
attribute by attribute. Two declarations are therefore one hidden union, not an
override: the surviving field is the union of both classes and neither file
alone shows the effective definition. This module is the single scanner behind
the strict declaration guard and the money-fact declaration guard, so both
lanes use one definition of "duplicate".

The scanner is static. It never imports Odoo and never touches a database.
"""
from __future__ import annotations

import ast
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


EXCLUDED_PARTS = {"tests", "__pycache__", ".runtime", "node_modules"}
MIXIN_MODELS = {
    "mail.thread",
    "mail.activity.mixin",
    "mail.alias.mixin",
    "portal.mixin",
    "rating.mixin",
    "tier.validation",
}


@dataclass(frozen=True)
class FieldDeclaration:
    model: str
    field: str
    file: str
    class_name: str
    line: int
    field_type: str
    role: str


def _literal_string(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _string_values(node: ast.AST | None, constants: dict[str, str]) -> list[str]:
    if node is None:
        return []
    literal = _literal_string(node)
    if literal:
        return [literal]
    if isinstance(node, ast.Name):
        value = constants.get(node.id)
        return [value] if value else []
    if isinstance(node, (ast.List, ast.Tuple)):
        values: list[str] = []
        for element in node.elts:
            values.extend(_string_values(element, constants))
        return values
    return []


def _model_constants(root: Path, modules: Iterable[str]) -> dict[str, str]:
    table: dict[str, set[str]] = defaultdict(set)
    for module in sorted(set(modules)):
        base = root / "addons" / module
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.py")):
            if any(part in EXCLUDED_PARTS for part in path.parts):
                continue
            try:
                tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
            except SyntaxError:
                continue
            for node in tree.body:
                if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                    continue
                target = node.targets[0]
                value = _literal_string(node.value)
                if isinstance(target, ast.Name) and value and "." in value:
                    table[target.id].add(value)
    return {name: next(iter(values)) for name, values in table.items() if len(values) == 1}


def _model_names(node: ast.ClassDef, constants: dict[str, str]) -> list[str]:
    name: str | None = None
    inherit: list[str] = []
    for statement in node.body:
        if isinstance(statement, ast.Assign):
            targets = statement.targets
        elif isinstance(statement, ast.AnnAssign):
            targets = [statement.target]
        else:
            continue
        for target in targets:
            if not isinstance(target, ast.Name):
                continue
            if target.id == "_name":
                name = _literal_string(statement.value) or (
                    constants.get(statement.value.id)
                    if isinstance(statement.value, ast.Name)
                    else None
                )
            elif target.id == "_inherit":
                inherit.extend(_string_values(statement.value, constants))
    if name:
        return [name]
    return [model for model in inherit if model not in MIXIN_MODELS]


def scan(root: Path, modules: Iterable[str]) -> list[FieldDeclaration]:
    """Every field declaration in every model class of the product modules."""
    root = root.resolve()
    constants = _model_constants(root, modules)
    declarations: list[FieldDeclaration] = []
    for module in sorted(set(modules)):
        base = root / "addons" / module
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.py")):
            if any(part in EXCLUDED_PARTS for part in path.parts):
                continue
            try:
                tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
            except SyntaxError:
                continue
            relative = path.relative_to(root).as_posix()
            for node in tree.body:
                if not isinstance(node, ast.ClassDef):
                    continue
                models = _model_names(node, constants)
                if not models:
                    continue
                role = "owning class" if any(
                    isinstance(statement, ast.Assign)
                    and any(isinstance(target, ast.Name) and target.id == "_name" for target in statement.targets)
                    for statement in node.body
                ) else "extension class"
                for statement in node.body:
                    if isinstance(statement, ast.Assign):
                        targets = statement.targets
                        value = statement.value
                    elif isinstance(statement, ast.AnnAssign):
                        targets = [statement.target]
                        value = statement.value
                    else:
                        continue
                    if not isinstance(value, ast.Call):
                        continue
                    function = value.func
                    if not (
                        isinstance(function, ast.Attribute)
                        and isinstance(function.value, ast.Name)
                        and function.value.id == "fields"
                    ):
                        continue
                    for target in targets:
                        if not isinstance(target, ast.Name):
                            continue
                        for model in models:
                            declarations.append(
                                FieldDeclaration(
                                    model=model,
                                    field=target.id,
                                    file=relative,
                                    class_name=node.name,
                                    line=statement.lineno,
                                    field_type=function.attr,
                                    role=role,
                                )
                            )
    return declarations


def conflicts(declarations: Iterable[FieldDeclaration]) -> tuple[dict[str, list[dict]], list[dict]]:
    """``(cross_class_conflicts, same_class_duplicates)`` keyed by model.field."""
    grouped: dict[tuple[str, str], list[FieldDeclaration]] = defaultdict(list)
    for declaration in declarations:
        grouped[(declaration.model, declaration.field)].append(declaration)

    cross_class: dict[str, list[dict]] = {}
    same_class: list[dict] = []
    for (model, field), items in sorted(grouped.items()):
        sites = {(item.file, item.class_name) for item in items}
        ordered = sorted(items, key=lambda item: (item.file, item.line, item.class_name))
        site_count = len(sites)
        if site_count > 1:
            cross_class[f"{model}.{field}"] = [asdict(item) for item in ordered]
        elif len(items) > site_count:
            same_class.append(
                {
                    "model": model,
                    "field": field,
                    "declarations": [asdict(item) for item in ordered],
                }
            )
    return cross_class, same_class


def duplicate_fields(root: Path, modules: Iterable[str]) -> dict[str, list[dict]]:
    """Compatibility shape used by the money-fact coverage guard."""
    cross_class, _same_class = conflicts(scan(root, modules))
    return {
        key: [{"file": item["file"], "role": item["role"]} for item in items]
        for key, items in cross_class.items()
    }
