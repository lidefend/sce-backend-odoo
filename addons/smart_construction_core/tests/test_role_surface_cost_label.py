# -*- coding: utf-8 -*-
"""roleLabel 按成本组区分：identity_resolver role_surface 策略修正（桩加载，零 Odoo 运行时）。

G3.3-B capture 发现：成本角色（sc_cost_mgr / sc_cost_user_cap）顶栏
「当前岗位」均解析为「项目成员」——根因是 ROLE_GROUPS_EXPLICIT 无成本组
条目，成本用户经 project_member 的 group_sc_cap_project_read 基础读权限
兜底解析。本测试验证策略层修正：

1. 显式阶段（IdentityResolver.resolve_role_codes_with_evidence 的
   explicit 分支语义：按 ROLE_PRECEDENCE 顺序做组交集）命中 "cost"；
2. 标签为「成本管理」，与「项目成员」可区分；
3. 导航暴露策略与 project_member 逐字段一致（nav 不变性——本修正只
   区分标签，不改变任何菜单/动作/模型暴露）；
4. 纯 project_read 用户仍解析为 project_member（无回归）；
5. ROLE_PRECEDENCE 中 cost 位于 finance 之后，不抢占既有角色。

core_extension_policy_maps.py 为纯数据模块（无 Odoo 依赖），
spec_from_file_location 直接加载（模式仿 test_project_next_actions_builder.py）。
"""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

POLICY_MAPS = (
    Path(__file__).resolve().parents[1] / "core_extension_policy_maps.py"
)

_spec = importlib.util.spec_from_file_location(
    "sc_test_role_surface_cost_policy_maps", POLICY_MAPS
)
policy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(policy)

ROLE_GROUPS_EXPLICIT = policy.ROLE_GROUPS_EXPLICIT
ROLE_SURFACE_OVERRIDES = policy.ROLE_SURFACE_OVERRIDES
ROLE_PRECEDENCE = policy.ROLE_PRECEDENCE


def _resolve_explicit(user_xmlids: set) -> tuple[list, dict]:
    """复刻 IdentityResolver.resolve_role_codes_with_evidence 的 explicit 分支。

    仅覆盖 explicit 阶段（本修正的生效层）；project_member 兜底与
    capability_fallback 阶段与 smart_core 运行时一致，不在桩内重复。
    """
    explicit_hits = {}
    for role in ROLE_PRECEDENCE:
        hits = sorted((ROLE_GROUPS_EXPLICIT.get(role) or set()) & user_xmlids)
        if hits:
            explicit_hits[role] = hits
    if not explicit_hits:
        return [], {}
    surface_roles = [role for role in ROLE_PRECEDENCE if role in explicit_hits]
    return surface_roles, {
        "source": "explicit",
        "primary_role": surface_roles[0],
        "matched_groups_by_role": explicit_hits,
    }


CAP_PROJECT_READ = "smart_construction_core.group_sc_cap_project_read"
CAP_COST_USER = "smart_construction_core.group_sc_cap_cost_user"
CAP_COST_MANAGER = "smart_construction_core.group_sc_cap_cost_manager"
ROLE_COST_USER = "smart_construction_core.group_sc_role_cost_user"
ROLE_PROJECT_MANAGER = "smart_construction_core.group_sc_role_project_manager"


class TestCostRoleSurfaceLabel(unittest.TestCase):
    def test_cost_cap_user_resolves_cost_role(self):
        # G3.3-B fixture：sc_cost_user_cap（project_read 基础读 + cap 成本经办）
        roles, evidence = _resolve_explicit({CAP_PROJECT_READ, CAP_COST_USER})
        self.assertEqual(roles, ["cost"])
        self.assertEqual(evidence["source"], "explicit")
        self.assertEqual(
            evidence["matched_groups_by_role"]["cost"], [CAP_COST_USER]
        )

    def test_cost_cap_manager_resolves_cost_role(self):
        # G3.3-B fixture：sc_cost_mgr（project_read 基础读 + cap 成本负责人）
        roles, _ = _resolve_explicit({CAP_PROJECT_READ, CAP_COST_MANAGER})
        self.assertEqual(roles, ["cost"])

    def test_cost_role_group_holder_resolves_cost_role(self):
        # 角色组路径：group_sc_role_cost_user（implied 物化 project_read + cap_cost_user）
        roles, _ = _resolve_explicit({ROLE_COST_USER, CAP_PROJECT_READ, CAP_COST_USER})
        self.assertEqual(roles, ["cost"])

    def test_cost_label_distinct_from_project_member(self):
        cost_label = ROLE_SURFACE_OVERRIDES["cost"]["label"]
        member_label = ROLE_SURFACE_OVERRIDES["project_member"]["label"]
        self.assertEqual(cost_label, "成本管理")
        self.assertEqual(member_label, "项目成员")
        self.assertNotEqual(cost_label, member_label)

    def test_cost_navigation_policy_is_member_invariant(self):
        # nav 不变性：本修正只区分 roleLabel，导航暴露策略逐字段与
        # project_member 一致，不引入任何菜单/动作/模型暴露变化。
        member = ROLE_SURFACE_OVERRIDES["project_member"]
        cost = ROLE_SURFACE_OVERRIDES["cost"]
        nav_fields = (
            "landing_scene_candidates",
            "menu_xmlids",
            "primary_menu_xmlids",
            "role_home_menu_xmlids",
            "contextual_menu_xmlids",
            "denied_menu_xmlids",
            "menu_blocklist_xmlids",
            "action_blocklist_xmlids",
            "model_blocklist",
            "model_prefix_blocklist",
            "group_key_blocklist",
        )
        for field in nav_fields:
            with self.subTest(field=field):
                self.assertEqual(cost.get(field), member.get(field))
        # 成本角色不声明独占面/全禁导航/能力发现等特殊开关
        for flag in ("exclusive_surface", "deny_all_navigation", "discover_installed_capabilities"):
            self.assertNotIn(flag, cost)

    def test_project_read_only_user_still_project_member(self):
        # 无回归：纯 project_read 用户不命中 cost（explicit 阶段为空，
        # 运行时落入 project_member 兜底分支）。
        roles, _ = _resolve_explicit({CAP_PROJECT_READ})
        self.assertEqual(roles, [])

    def test_cost_does_not_preempt_existing_roles(self):
        # ROLE_PRECEDENCE：cost 位于 finance 之后；pm 组 + 成本组并存时 pm 胜出。
        self.assertIn("cost", ROLE_PRECEDENCE)
        self.assertGreater(
            ROLE_PRECEDENCE.index("cost"), ROLE_PRECEDENCE.index("finance")
        )
        roles, _ = _resolve_explicit(
            {ROLE_PROJECT_MANAGER, CAP_PROJECT_READ, CAP_COST_MANAGER}
        )
        self.assertEqual(roles[0], "pm")

    def test_cost_groups_are_authoritative_xmlids(self):
        explicit = ROLE_GROUPS_EXPLICIT["cost"]
        self.assertIn(CAP_COST_USER, explicit)
        self.assertIn(CAP_COST_MANAGER, explicit)
        self.assertIn(ROLE_COST_USER, explicit)
        # 显式映射内不自引用 project_member 的基础读组（避免 pm 等角色被误染）
        self.assertNotIn(CAP_PROJECT_READ, explicit)


if __name__ == "__main__":
    unittest.main(verbosity=2)
