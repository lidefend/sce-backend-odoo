#!/usr/bin/env python3
"""Navigation authorization reads ACL-visible menu carriers, not renderables.

Regression pin for a declared product carrier that carries no action (a
scene-entry page such as the role home).  Odoo's ``_visible_menu_ids`` is
action-centric: it can only ever return menus that carry a resolvable action,
or that are ancestors of one.  Using that renderable set as the *authorization*
authority made one declared menu unobservable and silently dropped it from the
delivered navigation even though the request user's groups allow the menu node.

The two questions are separate:

* rendering   -> "which action menus would Odoo show"  (``export_visible_menu_facts``)
* authorization -> "do this user's groups allow this carrier"  (``export_authorized_menu_facts``)
"""

from __future__ import annotations

import ast
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace


SMART_CORE_DIR = Path(__file__).resolve().parents[1]

CARRIER_XMLID = "smart_construction_core.menu_sc_workspace_home"
CARRIER = {
    "menu_id": 1004,
    "menu_xmlid": CARRIER_XMLID,
    "name": "角色首页",
    "action_id": None,
    "action_raw": "",
    "route": "/m/1004",
    "meta": {"menu_id": 1004, "menu_xmlid": CARRIER_XMLID, "route": "/m/1004"},
    "children": [],
}


class _FactServiceDouble:
    """Module double: the two exports deliberately answer different questions."""

    renderable_tree: list[dict] = []
    authorized_tree: list[dict] = []

    def __init__(self, env):
        self.env = env

    def export_visible_menu_facts(self):
        return SimpleNamespace(tree=[dict(node) for node in type(self).renderable_tree])

    def export_authorized_menu_facts(self):
        return SimpleNamespace(tree=[dict(node) for node in type(self).authorized_tree])


def _load_authorization_native_nav():
    """Bind ``MenuService._authorization_native_nav`` with a fact-service double."""
    path = SMART_CORE_DIR / "delivery" / "menu_service.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    cls = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "MenuService"
    )
    wanted = {"_authorization_native_nav", "_menu_fact_tree_as_native"}
    body = []
    for node in cls.body:
        if isinstance(node, ast.FunctionDef) and node.name in wanted:
            node.decorator_list = []
            body.append(node)
    assert {node.name for node in body} == wanted, "menu_service authorization methods drifted"
    scope = {"MenuFactService": _FactServiceDouble}
    exec(compile(ast.Module(body=body, type_ignores=[]), str(path), "exec"), scope)
    return type("_Authorization", (), {name: scope[name] for name in wanted})


def _load_menu_fact_service():
    """Import ``menu_fact_service`` with a stubbed Odoo package."""
    for name in ("odoo", "odoo.addons", "odoo.addons.smart_core", "odoo.addons.smart_core.core"):
        sys.modules.setdefault(name, types.ModuleType(name))
    smart_core_pkg = sys.modules["odoo.addons.smart_core"]
    smart_core_pkg.__path__ = [str(SMART_CORE_DIR)]
    core_pkg = sys.modules["odoo.addons.smart_core.core"]
    core_pkg.__path__ = [str(SMART_CORE_DIR / "core")]
    for name in (
        "odoo.addons.smart_core.core.source_authority",
        "odoo.addons.smart_core.delivery.menu_fact_service",
    ):
        sys.modules.pop(name, None)
    spec = importlib.util.spec_from_file_location(
        "odoo.addons.smart_core.core.source_authority",
        SMART_CORE_DIR / "core" / "source_authority.py",
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["odoo.addons.smart_core.core.source_authority"] = module
    spec.loader.exec_module(module)
    spec = importlib.util.spec_from_file_location(
        "odoo.addons.smart_core.delivery.menu_fact_service",
        SMART_CORE_DIR / "delivery" / "menu_fact_service.py",
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["odoo.addons.smart_core.delivery.menu_fact_service"] = module
    spec.loader.exec_module(module)
    return module


class _Menu:
    def __init__(self, id, groups=(), parent_path=""):
        self.id = id
        self.groups_id = set(groups)
        self.parent_path = parent_path


class _Recordset:
    def __init__(self, rows):
        self._rows = list(rows)

    def __iter__(self):
        return iter(self._rows)

    def __len__(self):
        return len(self._rows)

    @property
    def ids(self):
        return [row.id for row in self._rows]

    def filtered(self, predicate):
        return _Recordset([row for row in self._rows if predicate(row)])

    def sudo(self):
        return self

    def with_context(self, context):
        return self


class _MenuModel:
    def __init__(self, rows):
        self._rows = rows

    def with_context(self, context):
        return self

    def search(self, domain):
        return _Recordset(self._rows)

    def sudo(self):
        return self


class _Env:
    def __init__(self, rows, groups, developer_group=(99,)):
        self._menus = _MenuModel(rows)
        self.user = SimpleNamespace(groups_id=set(groups))
        self._developer_group = set(developer_group)

    def __getitem__(self, name):
        assert name == "ir.ui.menu", "unexpected model read: %s" % name
        return self._menus

    def ref(self, xmlid):
        assert xmlid == "base.group_no_one"
        return set(self._developer_group)


class MenuAclCarrierAuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.authorization = _load_authorization_native_nav()
        self.fact_service = _load_menu_fact_service()

    # --- the consumption contract -------------------------------------------

    def test_declared_actionless_carrier_reaches_the_authorized_surface(self):
        _FactServiceDouble.renderable_tree = []
        _FactServiceDouble.authorized_tree = [CARRIER]
        instance = object.__new__(self.authorization)
        instance.env = SimpleNamespace()
        nodes = self.authorization._authorization_native_nav(
            instance, {"exposure_policy_declared": True}, []
        )
        self.assertEqual([node["menu_xmlid"] for node in nodes], [CARRIER_XMLID])

    def test_renderable_menus_are_not_the_authorization_authority(self):
        """A menu Odoo can render is not by itself an authorization grant."""
        _FactServiceDouble.renderable_tree = [CARRIER]
        _FactServiceDouble.authorized_tree = []
        instance = object.__new__(self.authorization)
        instance.env = SimpleNamespace()
        nodes = self.authorization._authorization_native_nav(
            instance, {"exposure_policy_declared": True}, []
        )
        self.assertEqual(nodes, [])

    def test_surface_without_exposure_policy_keeps_the_given_native_nav(self):
        _FactServiceDouble.renderable_tree = []
        _FactServiceDouble.authorized_tree = []
        instance = object.__new__(self.authorization)
        instance.env = SimpleNamespace()
        given = [{"menu_id": 7, "children": []}]
        nodes = self.authorization._authorization_native_nav(instance, {}, given)
        self.assertEqual(nodes, given)

    # --- the ACL filter itself ---------------------------------------------

    def _authorized_ids(self, rows, groups, developer_group=(99,)):
        service = self.fact_service.MenuFactService(_Env(rows, groups, developer_group))
        return service._authorized_menu_ids()

    def test_actionless_carrier_is_authorized_by_its_groups(self):
        rows = [
            _Menu(1, parent_path="1/"),
            _Menu(1004, parent_path="1/1004/"),
            _Menu(2000, groups=(55,), parent_path="1/2000/"),
        ]
        self.assertEqual(self._authorized_ids(rows, groups={55}), {1, 1004, 2000})

    def test_carrier_the_groups_deny_is_never_authorized(self):
        rows = [
            _Menu(1, parent_path="1/"),
            _Menu(1004, groups=(55,), parent_path="1/1004/"),
        ]
        self.assertEqual(self._authorized_ids(rows, groups={77}), {1})

    def test_granted_carrier_survives_a_folder_its_groups_deny(self):
        """A granted leaf is authorized even under a granted-to-another-role folder.

        This mirrors Odoo's own ``_visible_menu_ids``, which filters each node by
        its *own* groups and only lifts folders it also granted. Requiring the
        whole ancestor chain here would be stricter than the platform and
        silently dropped the released chart-of-accounts entry
        (``account.menu_action_account_form``), whose parent configuration folder
        is granted to the accounting manager role only.
        """
        rows = [
            _Menu(1, groups=(55,), parent_path="1/"),
            _Menu(1004, parent_path="1/1004/"),
        ]
        self.assertEqual(self._authorized_ids(rows, groups={77}), {1004})

    def test_denied_folder_itself_is_never_authorized(self):
        rows = [
            _Menu(1, groups=(55,), parent_path="1/"),
            _Menu(1004, groups=(55,), parent_path="1/1004/"),
        ]
        self.assertEqual(self._authorized_ids(rows, groups={77}), set())

    def test_developer_only_group_is_not_a_grant(self):
        rows = [_Menu(1004, groups=(99,), parent_path="1004/")]
        self.assertEqual(self._authorized_ids(rows, groups={99}), set())

    def test_export_documents_both_questions(self):
        for name, token in (
            ("export_visible_menu_facts", "action-bearing"),
            ("export_authorized_menu_facts", "groups actually authorize"),
        ):
            doc = getattr(self.fact_service.MenuFactService, name).__doc__ or ""
            self.assertIn(token, doc, "%s docstring lost its distinction" % name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
