#!/usr/bin/env python3
"""Static regression: project-close existence guards use internal privilege.

The close guards answer one question -- does an unfinished settlement/payment
row exist -- and never return that row to the operator. Reading it as the
operator made a finance read capability a hidden prerequisite of closing a
project. The guard must therefore count through ``.sudo()`` while still
returning no record.
"""
from __future__ import annotations

import ast
import unittest
from pathlib import Path


SOURCE = (
    Path(__file__).resolve().parents[3]
    / "addons"
    / "smart_construction_core"
    / "models"
    / "core"
    / "project_core.py"
)

GUARDS = {
    "_guard_project_close_by_settlement": "project.settlement",
    "_guard_project_close_by_payment": "payment.request",
}


def _class(name):
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == name:
            return node
    raise AssertionError("class %s not found in %s" % (name, SOURCE))


def _method(class_node, name):
    for node in class_node.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    raise AssertionError("method %s not found" % (name,))


def _sudo_model(node):
    """The model named by ``self.env["model"].sudo()``; None for a plain env read."""
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
        return None
    if node.func.attr != "sudo" or node.args:
        return None
    inner = node.func.value
    if not isinstance(inner, ast.Subscript):
        return None
    value = inner.value
    if (
        isinstance(value, ast.Attribute)
        and value.attr == "env"
        and isinstance(value.value, ast.Name)
        and value.value.id == "self"
        and isinstance(inner.slice, ast.Constant)
        and isinstance(inner.slice.value, str)
    ):
        return inner.slice.value
    return None


def _sudo_bindings(method):
    """``{local_name: model}`` for every ``name = self.env[model].sudo()``."""
    bindings = {}
    for node in ast.walk(method):
        if not isinstance(node, ast.Assign):
            continue
        model = _sudo_model(node.value)
        if model is None:
            continue
        target = node.targets[0]
        if isinstance(target, ast.Name):
            bindings[target.id] = model
    return bindings


def _search_count_receivers(method):
    receivers = []
    for node in ast.walk(method):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "search_count"
            and isinstance(node.func.value, ast.Name)
        ):
            receivers.append(node.func.value.id)
    return receivers


class ProjectCloseGuardInternalPrivilegeTests(unittest.TestCase):
    def setUp(self):
        self.project = _class("ProjectProject")

    def test_each_guard_counts_through_sudo_on_its_own_model(self):
        for name, model in GUARDS.items():
            with self.subTest(guard=name):
                method = _method(self.project, name)
                self.assertIn(
                    model, _sudo_bindings(method).values(),
                    "%s must call self.env[%r].sudo()" % (name, model),
                )

    def test_search_count_receiver_is_the_sudo_binding(self):
        for name, model in GUARDS.items():
            with self.subTest(guard=name):
                method = _method(self.project, name)
                bindings = _sudo_bindings(method)
                privileged = {
                    local for local, bound in bindings.items() if bound == model
                }
                receivers = _search_count_receivers(method)
                self.assertTrue(receivers, "%s must count rows" % name)
                self.assertTrue(
                    set(receivers) <= privileged,
                    "%s reads search_count as %s, not through sudo()"
                    % (name, ", ".join(sorted(set(receivers) - privileged))),
                )

    def test_a_guard_returns_no_record_to_the_operator(self):
        for name in GUARDS:
            with self.subTest(guard=name):
                method = _method(self.project, name)
                returned = [
                    node for node in ast.walk(method)
                    if isinstance(node, ast.Return) and node.value is not None
                ]
                self.assertEqual(returned, [], "%s must not return a recordset" % name)

if __name__ == "__main__":
    unittest.main()
