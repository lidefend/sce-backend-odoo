#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pure guard for the scenario-center navigation projection.

Exercises ``project_authorized_nav_with_env`` against a fake Odoo environment:
centers come from scenario-entry composition metadata, with delivery-policy
grouping as the fallback for unconfigured entries.
"""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "scenario_surface_projection",
    ROOT / "addons/smart_construction_core/services/scenario_surface_projection.py",
)
PROJ = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROJ)


class _Menu:
    def __init__(self, menu_id, parent, name, xmlid, sequence=10):
        self.id = menu_id
        self.parent_id = parent
        self.name = name
        self.xmlid = xmlid
        self.sequence = sequence
        self.sc_product_center_id = None

    def get_external_id(self):
        return {self.id: self.xmlid}


class _Menus:
    def __init__(self, by_id):
        self.by_id = by_id

    def sudo(self):
        return self

    def browse(self, ids):
        return _Recordset(self.by_id[int(i)] for i in ids if int(i) in self.by_id)

    def search(self, domain):
        out = []
        for menu in self.by_id.values():
            ok = True
            for field, op, value in domain:
                if field == "parent_id":
                    parent = menu.parent_id
                    pid = parent.id if parent else 0
                    target = value.id if hasattr(value, "id") else value
                    if op == "=" and pid != target:
                        ok = False
            if ok:
                out.append(menu)
        return _Recordset(out)


class _Recordset(list):
    def exists(self):
        return self


class _Entry:
    def __init__(
        self,
        menu,
        scenario,
        sequence=10,
        *,
        center_key="",
        center_name="",
        center_sequence=10,
    ):
        self.menu_id = menu
        self.scenario_id = scenario
        self.sequence = sequence
        self.center_key = center_key
        self.center_name = center_name
        self.center_sequence = center_sequence

    @property
    def intent(self):
        return "handle"


class _Entries:
    def __init__(self, entries):
        self.entries = entries

    def sudo(self):
        return self

    def search(self, _domain):
        return self.entries


class _Scenario:
    def __init__(self, code, name, active=True, sequence=10):
        self.code = code
        self.name = name
        self.active = active
        self.sequence = sequence


class _Env:
    def __init__(self):
        root = _Menu(1, None, "智慧施工管理平台", "smart_construction_core.menu_sc_root")
        finance = _Menu(10, root, "财务账款", "smart_construction_core.menu_sc_finance_center", 50)
        project = _Menu(20, root, "项目中心", "smart_construction_core.menu_sc_project_center", 20)
        self.menus = {
            1: root,
            10: finance,
            20: project,
            101: _Menu(101, finance, "付款申请", "smart_construction_core.menu_sc_user_payment_apply"),
            201: _Menu(201, project, "未配置入口", "smart_construction_core.menu_sc_unconfigured"),
        }
        payment = _Scenario("payment.capital", "付款与资金办理")
        self.entries = _Entries([
            _Entry(
                self.menus[101],
                payment,
                center_key="smart_construction_core.menu_sc_finance_center",
                center_name="财务账款",
                center_sequence=50,
            )
        ])

    def __getitem__(self, key):
        if key == "ir.ui.menu":
            return _Menus(self.menus)
        if key == "sc.product.scenario.entry":
            return self.entries
        raise KeyError(key)

    def ref(self, xmlid, raise_if_not_found=True):
        for menu in self.menus.values():
            if menu.xmlid == xmlid:
                return menu
        if raise_if_not_found:
            raise ValueError(xmlid)
        return None


def _leaf(
    menu_id,
    action_id,
    label,
    xmlid,
    *,
    policy_group_key="",
    policy_group_label="",
    sequence=1000,
):
    return {
        "menu_id": menu_id,
        "action_id": action_id,
        "route": f"/a/{action_id}?menu_id={menu_id}",
        "label": label,
        "menu_xmlid": xmlid,
        "model": "test.model",
        "view_modes": ["tree"],
        "sequence": sequence,
        "policy_group_key": policy_group_key,
        "policy_group_label": policy_group_label,
        "children": [],
    }


class ScenarioCenterProjectionGuard(unittest.TestCase):
    def test_center_comes_from_scenario_composition_and_policy_fallback(self):
        env = _Env()
        nav = [
            _leaf(101, 1011, "付款申请", "smart_construction_core.menu_sc_user_payment_apply"),
            _leaf(
                201,
                2011,
                "未配置入口",
                "smart_construction_core.menu_sc_unconfigured",
                policy_group_key="policy.project_center",
                policy_group_label="项目中心",
            ),
        ]
        result = PROJ.project_authorized_nav_with_env(env, nav, {})
        self.assertTrue(result["ok"])
        centers = {center["key"]: center for center in result["tree"]["centers"]}
        self.assertIn("smart_construction_core.menu_sc_finance_center", centers)
        self.assertIn("policy.project_center", centers)
        finance = centers["smart_construction_core.menu_sc_finance_center"]
        self.assertEqual(finance["scenarios"][0]["key"], "payment.capital")
        self.assertEqual(finance["scenarios"][0]["entries"][0]["configured"], True)
        project = centers["policy.project_center"]
        self.assertEqual(project["entries"][0]["configured"], False)

    def test_disabled_scenario_keeps_authorized_entry_unconfigured(self):
        env = _Env()
        env.entries = _Entries([_Entry(
            env.menus[101],
            _Scenario("payment.capital", "付款与资金办理", active=False),
            center_key="smart_construction_core.menu_sc_finance_center",
            center_name="财务账款",
            center_sequence=50,
        )])
        nav = [_leaf(101, 1011, "付款申请", "smart_construction_core.menu_sc_user_payment_apply")]
        result = PROJ.project_authorized_nav_with_env(env, nav, {})
        centers = result["tree"]["centers"]
        finance = next(c for c in centers if c["key"] == "smart_construction_core.menu_sc_finance_center")
        self.assertEqual(finance["scenarios"], [])
        self.assertEqual(finance["entries"][0]["configured"], False)

    def test_stable_center_identity_fallback_for_native_core_menus(self):
        # External menus retain a database association even after center rename
        # makes the legacy delivery group's label lookup return no center ID.
        env = _Env()
        account_root = _Menu(999, None, "Invoicing", "account.menu_finance")
        account_menu = _Menu(1001, account_root, "Journal Entries", "account.menu_action_move_journal_line_form")
        env.menus[999] = account_root
        env.menus[1001] = account_menu
        account_menu.sc_product_center_id = env.menus[10]
        env.menus[10].name = "Renamed accounting center"
        env.entries = _Entries([_Entry(
            account_menu,
            _Scenario("accounting.management", "会计核算"),
            center_key="smart_construction_core.menu_sc_finance_center",
            center_name="财务账款",
            center_sequence=50,
        )])
        leaf = dict(_leaf(1001, 10011, "日记账分录", "account.menu_action_move_journal_line_form"))
        center_group = {
            "label": "财务账款",
            "menu_id": 900,
            "canonical_navigation": {"menu_id": 0},
            "children": [leaf],
        }
        nav = [{"label": "系统菜单", "children": [center_group]}]
        result = PROJ.project_authorized_nav_with_env(env, nav, {})
        centers = result["tree"]["centers"]
        finance = next(c for c in centers if c["key"] == "smart_construction_core.menu_sc_finance_center")
        self.assertEqual(finance["scenarios"][0]["key"], "accounting.management")
        self.assertEqual(finance["name"], "财务账款")

    def test_moved_native_menu_does_not_change_composed_center(self):
        env = _Env()
        env.menus[101].parent_id = env.menus[20]
        env.menus[101].sc_product_center_id = env.menus[10]
        nav = [{"label": "System", "children": [{
            "label": "Old center", "canonical_navigation": {"menu_id": 10},
            "children": [_leaf(101, 1011, "Payment", env.menus[101].xmlid)],
        }]}]
        centers = PROJ.project_authorized_nav_with_env(env, nav, {})["tree"]["centers"]
        self.assertEqual([c["key"] for c in centers], [env.menus[10].xmlid])

    def test_entry_sequence_and_stable_tie_breaker(self):
        env = _Env()
        env.menus[201].parent_id = env.menus[10]
        scenario = env.entries.entries[0].scenario_id
        env.entries = _Entries([
            _Entry(
                env.menus[101],
                scenario,
                9,
                center_key=env.menus[10].xmlid,
                center_name=env.menus[10].name,
                center_sequence=env.menus[10].sequence,
            ),
            _Entry(
                env.menus[201],
                scenario,
                0,
                center_key=env.menus[10].xmlid,
                center_name=env.menus[10].name,
                center_sequence=env.menus[10].sequence,
            ),
        ])
        nav = [_leaf(101, 1011, "A", env.menus[101].xmlid), _leaf(201, 2011, "Z", env.menus[201].xmlid)]
        def entries():
            return PROJ.project_authorized_nav_with_env(env, nav, {})["tree"]["centers"][0]["scenarios"][0]["entries"]
        self.assertEqual([e["menu_id"] for e in entries()], [201, 101])
        self.assertEqual(entries()[0]["sequence"], 0)
        env.entries.entries[0].sequence = 0
        self.assertEqual([e["menu_id"] for e in entries()], [201, 101])  # XMLID, not label

    def test_direct_entry_order_uses_native_menu_sequence(self):
        env = _Env()
        env.entries = _Entries([])
        env.menus[201].parent_id = env.menus[10]
        env.menus[201].sequence = 0
        nav = [
            _leaf(
                101,
                1011,
                "A",
                env.menus[101].xmlid,
                policy_group_key=env.menus[10].xmlid,
                policy_group_label=env.menus[10].name,
            ),
            _leaf(
                201,
                2011,
                "Z",
                env.menus[201].xmlid,
                policy_group_key=env.menus[10].xmlid,
                policy_group_label=env.menus[10].name,
                sequence=0,
            ),
        ]
        entries = PROJ.project_authorized_nav_with_env(env, nav, {})["tree"]["centers"][0]["entries"]
        self.assertEqual([e["menu_id"] for e in entries], [201, 101])


if __name__ == "__main__":
    unittest.main(verbosity=2)
