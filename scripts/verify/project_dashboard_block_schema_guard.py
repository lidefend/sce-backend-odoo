#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import ast
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BUILDERS_DIR = ROOT / "addons" / "smart_construction_core" / "services" / "project_dashboard_builders"

# block_type -> required data keys in all states (ready/empty/forbidden)
REQUIRED_KEYS = {
    "record_summary": {"summary"},
    "metric_row": {"items"},
    "progress_summary": {"task_total", "task_done", "completion_percent"},
    "record_table": {"columns", "rows"},
    "alert_panel": {"alerts"},
    "boq_import_preview": {
        "project_id",
        "batch_count",
        "fetch_intent",
        "fetch_params",
        "loading_message",
        "empty_message",
        "empty_message_no_context",
        "readonly",
    },
    "chart_dataset": {
        "project_id",
        "chart_key",
        "chart_registered",
        "fetch_intent",
        "fetch_params",
        "loading_message",
        "empty_message",
        "empty_message_no_context",
        "readonly",
    },
    "todo_list": {"items", "count", "max_items"},
    "rich_text_overview": {
        "field",
        "content",
        "overview_digest",
        "content_length",
        "max_length",
        "patch_intent",
        "can_edit",
        "empty_message",
    },
}


def _must(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit(msg)


def _dict_keys(node):
    if not isinstance(node, ast.Dict):
        return None
    out = set()
    for k in node.keys:
        if isinstance(k, ast.Constant) and isinstance(k.value, str):
            out.add(k.value)
        else:
            return None
    return out


def _walk_statements(statements):
    for stmt in statements:
        yield stmt
        if isinstance(stmt, ast.If):
            yield from _walk_statements(stmt.body)
            yield from _walk_statements(stmt.orelse)
        elif isinstance(stmt, (ast.For, ast.AsyncFor, ast.While)):
            yield from _walk_statements(stmt.body)
            yield from _walk_statements(stmt.orelse)
        elif isinstance(stmt, ast.With):
            yield from _walk_statements(stmt.body)
        elif isinstance(stmt, ast.Try):
            yield from _walk_statements(stmt.body)
            yield from _walk_statements(stmt.orelse)
            yield from _walk_statements(stmt.finalbody)
            for handler in stmt.handlers:
                yield from _walk_statements(handler.body)


def _intersection_key_sets(values):
    if not values or any(value is None for value in values):
        return None
    result = set(values[0])
    for value in values[1:]:
        result.intersection_update(value)
    return result


def _assigned_key_sets(statements, name):
    values = []
    for stmt in _walk_statements(statements):
        if isinstance(stmt, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == name for target in stmt.targets):
                values.append(_dict_keys(stmt.value))
        elif isinstance(stmt, (ast.AnnAssign, ast.AugAssign)):
            if isinstance(stmt.target, ast.Name) and stmt.target.id == name:
                values.append(None)
        elif isinstance(stmt, (ast.For, ast.AsyncFor, ast.comprehension)):
            for target in ast.walk(stmt.target):
                if isinstance(target, ast.Name) and target.id == name:
                    values.append(None)
        elif isinstance(stmt, (ast.With,)) and stmt.items:
            for item in stmt.items:
                if item.optional_vars:
                    for target in ast.walk(item.optional_vars):
                        if isinstance(target, ast.Name) and target.id == name:
                            values.append(None)
    return values


def _projection_return_keys(function: ast.FunctionDef):
    data_values = _assigned_key_sets(function.body, "data")
    results = []
    for stmt in _walk_statements(function.body):
        if not isinstance(stmt, ast.Return):
            continue
        keys = _dict_keys(stmt.value)
        if keys is None and isinstance(stmt.value, ast.Name) and stmt.value.id == "data":
            keys = _intersection_key_sets(data_values)
        results.append(keys)
    return _intersection_key_sets(results)


def _resolved_state_values(node, statements):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return {node.value}
    if isinstance(node, ast.IfExp):
        return (
            _resolved_state_values(node.body, statements)
            | _resolved_state_values(node.orelse, statements)
        )
    if isinstance(node, ast.Name):
        values = set()
        for assigned in _walk_statements(statements):
            if isinstance(assigned, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == node.id
                for target in assigned.targets
            ):
                values |= _resolved_state_values(assigned.value, ())
        return values
    return set()


def _resolved_data_keys(node, statements, projection_keys):
    keys = _dict_keys(node)
    if keys is not None:
        return keys
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "dict" and not node.args:
        return set()
    if isinstance(node, ast.Name) and node.id == "data":
        return _intersection_key_sets(_assigned_key_sets(statements, "data"))
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "_projection_data"
    ):
        return projection_keys
    return None


def _collect_builder_contract(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    block_key = ""
    block_type = ""
    state_key_sets = {}
    projection_keys = None

    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        for stmt in node.body:
            if isinstance(stmt, ast.FunctionDef) and stmt.name == "_projection_data":
                projection_keys = _projection_return_keys(stmt)
        for stmt in node.body:
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name) and target.id == "block_key":
                        if isinstance(stmt.value, ast.Constant):
                            block_key = str(stmt.value.value)
                    if isinstance(target, ast.Name) and target.id == "block_type":
                        if isinstance(stmt.value, ast.Constant):
                            block_type = str(stmt.value.value)
            if isinstance(stmt, ast.FunctionDef) and stmt.name == "_projection_data":
                projection_keys = _projection_return_keys(stmt)
            if isinstance(stmt, ast.FunctionDef) and stmt.name == "build":
                for line in _walk_statements(stmt.body):
                    if not isinstance(line, ast.Return) or not isinstance(line.value, ast.Call):
                        continue
                    call = line.value
                    if not (isinstance(call.func, ast.Attribute) and call.func.attr == "_envelope"):
                        continue
                    keywords = {kw.arg: kw.value for kw in call.keywords if kw.arg}
                    state_values = _resolved_state_values(
                        keywords.get("state"),
                        stmt.body,
                    )
                    data_keys = _resolved_data_keys(
                        keywords.get("data"),
                        stmt.body,
                        projection_keys,
                    )
                    if state_values and data_keys is not None:
                        for state in state_values:
                            state_key_sets.setdefault(state, []).append(data_keys)

    states = {
        state: _intersection_key_sets(values)
        for state, values in state_key_sets.items()
    }

    _must(bool(block_key), f"{path.name}: missing block_key")
    _must(bool(block_type), f"{path.name}: missing block_type")
    return block_key, block_type, states


def _self_test_required_key_rejection():
    source = """
class MissingEmptyDataBuilder:
    block_key = "block.project.missing"
    block_type = "boq_import_preview"

    @staticmethod
    def _projection_data():
        return {
            "project_id": 1,
            "batch_count": 1,
            "fetch_intent": "project.boq.import.preview.fetch",
            "fetch_params": {},
            "loading_message": "loading",
            "empty_message": "empty",
            "empty_message_no_context": "missing context",
            "readonly": True,
        }

    def build(self, project=None):
        if not project:
            return self._envelope(state="empty", data=dict())
        state = "ready" if project else "empty"
        return self._envelope(state=state, data=self._projection_data())
"""
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "project_missing_empty_data_builder.py"
        path.write_text(source, encoding="utf-8")
        _block_key, block_type, states = _collect_builder_contract(path)
    missing = REQUIRED_KEYS[block_type] - states.get("empty", set())
    _must(
        {"fetch_intent", "loading_message", "empty_message"} <= missing,
        f"block schema self-test did not reject missing required field: {sorted(missing)}",
    )


def main():
    _self_test_required_key_rejection()
    files = sorted(BUILDERS_DIR.glob("project_*_builder.py"))
    _must(bool(files), "project block builders not found")

    for path in files:
        block_key, block_type, states = _collect_builder_contract(path)
        required = REQUIRED_KEYS.get(block_type)
        _must(required is not None, f"{path.name}: unsupported block_type {block_type}")
        for state in ("ready", "empty", "forbidden"):
            _must(state in states, f"{block_key}: missing envelope state {state}")
            keys = states[state]
            missing = sorted(required - keys)
            _must(not missing, f"{block_key}:{state}: missing required data keys {missing}")

    print("[verify.project.dashboard.block_schema] PASS")


if __name__ == "__main__":
    main()
