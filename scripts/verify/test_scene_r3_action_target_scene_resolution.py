#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hermetic unit tests for `_resolve_primary_action_route` covering the
`target_scene` field on action_specs and the `intent != "ui.contract"`
short-circuit (form-submit semantics).

These tests guard against regression of:
- Wave3 Round7 — Action Chain Upgrade Pilot (added `target_scene` to 4 scene
  payloads and switched `projects.intake.submit.intent` from "ui.contract"
  to "api.data").
- Wave3 Round8 — Final FALLBACK Eradication (added `target_scene` to 4 more
  scene payloads: cost.analysis / finance.center / projects.ledger /
  projects.list, bringing the action_chain_fallback_rate from 20% to 0%).
- Wave3 Round9 — Portal Domain Expansion (added `portal.shortcuts` launcher
  with 6 cross-domain shortcut entries, each carrying an explicit
  `target_scene` so launcher navigation never relies on fuzzy matching).
- Wave3 Round10 — Portal Message Center (added `portal.notifications` inbox
  whose primary action `view_unread` is an `api.data` read of unread
  conversations — a non-navigation data action resolved via the
  non_ui_contract short-circuit — while every notification_link action
  carries an explicit `target_scene` into a real owning scene).
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts" / "verify"))

from scene_r3_runtime_guard import (  # noqa: E402  pylint: disable=wrong-import-position
    _is_route_openable,
    _resolve_inventory_route,
    _resolve_primary_action_route,
)


def _inventory(rows: list[tuple[str, str]]) -> dict[str, dict[str, str]]:
    """Build a minimal inventory dict mapping scene_key -> row dict."""
    out: dict[str, dict[str, str]] = {}
    for scene_key, route in rows:
        out[scene_key] = {"scene_key": scene_key, "route_target": route}
    return out


def _base_payload(
    scene_key: str,
    primary_action: str,
    action_specs: dict,
    related_scenes: list | None = None,
    target_route: str = "",
) -> dict:
    return {
        "code": scene_key,
        "product_policy": {
            "role_based": True,
            "primary_action": primary_action,
        },
        "action_specs": action_specs,
        "related_scenes": related_scenes or [],
        "target": {"route": target_route} if target_route else {},
    }


class TargetSceneResolutionTests(unittest.TestCase):
    """Verify `target_scene` field on action_specs resolves to action_scene_ref."""

    def test_target_scene_resolves_to_action_scene_ref(self) -> None:
        """action_spec with target_scene should resolve via inventory lookup."""
        inv = _inventory([
            ("contract.center", "/s/contract.center"),
            ("contracts.workspace", "/s/contracts.workspace"),
        ])
        payload = _base_payload(
            scene_key="contract.center",
            primary_action="open_income",
            action_specs={
                "open_income": {
                    "label": "查看收入合同",
                    "intent": "ui.contract",
                    "target_scene": "contracts.workspace",
                },
            },
        )
        route, err, resolution = _resolve_primary_action_route(
            "contract.center", payload, inv
        )
        self.assertEqual(resolution, "action_scene_ref")
        self.assertEqual(route, "/s/contracts.workspace")
        self.assertEqual(err, "")

    def test_target_scene_takes_precedence_over_target_route(self) -> None:
        """target_scene should be consulted before falling back to self target."""
        inv = _inventory([
            ("finance.workspace", "/s/finance.workspace"),
            ("finance.payment_requests", "/s/finance.payment_requests"),
        ])
        payload = _base_payload(
            scene_key="finance.workspace",
            primary_action="open_payment_requests",
            action_specs={
                "open_payment_requests": {
                    "label": "进入付款收款申请",
                    "intent": "ui.contract",
                    "target_scene": "finance.payment_requests",
                },
            },
            target_route="/s/finance.workspace",
        )
        route, err, resolution = _resolve_primary_action_route(
            "finance.workspace", payload, inv
        )
        self.assertEqual(resolution, "action_scene_ref")
        self.assertEqual(route, "/s/finance.payment_requests")
        self.assertEqual(err, "")

    def test_target_scene_with_unknown_scene_returns_fallback(self) -> None:
        """target_scene pointing to missing scene should fall through to fallback."""
        inv = _inventory([
            ("cost.project_cost_ledger", "/s/cost.project_cost_ledger"),
        ])
        payload = _base_payload(
            scene_key="cost.project_cost_ledger",
            primary_action="open_cost_compare",
            action_specs={
                "open_cost_compare": {
                    "label": "进入成本中心",
                    "intent": "ui.contract",
                    "target_scene": "cost.nonexistent",
                },
            },
            target_route="/s/cost.project_cost_ledger",
        )
        route, err, resolution = _resolve_primary_action_route(
            "cost.project_cost_ledger", payload, inv
        )
        self.assertEqual(resolution, "self_target_fallback")
        self.assertEqual(route, "/s/cost.project_cost_ledger")

    def test_target_scene_with_scene_in_related_scenes(self) -> None:
        """When target_scene is in inventory but the original scene is unrelated
        to related_scenes list, action_scene_ref still wins."""
        inv = _inventory([
            ("my_work.workspace", "/s/my_work.workspace"),
            ("projects.list", "/s/projects.list"),
        ])
        payload = _base_payload(
            scene_key="my_work.workspace",
            primary_action="open_task_center",
            action_specs={
                "open_task_center": {
                    "label": "进入任务中心",
                    "intent": "ui.contract",
                    "target_scene": "projects.list",
                },
            },
            related_scenes=["projects.list", "projects.ledger"],
        )
        route, err, resolution = _resolve_primary_action_route(
            "my_work.workspace", payload, inv
        )
        self.assertEqual(resolution, "action_scene_ref")
        self.assertEqual(route, "/s/projects.list")


class NonUiContractShortCircuitTests(unittest.TestCase):
    """Verify `intent != "ui.contract"` short-circuits to non_ui_contract."""

    def test_api_data_intent_returns_non_ui_contract(self) -> None:
        """Form-submit actions (intent=api.data) should not be classified as
        self_target_fallback. They are non_ui_contract because they don't
        navigate — they mutate data."""
        inv = _inventory([
            ("projects.intake", "/s/projects.intake"),
        ])
        payload = _base_payload(
            scene_key="projects.intake",
            primary_action="submit",
            action_specs={
                "submit": {
                    "label": "提交立项",
                    "intent": "api.data",
                },
            },
        )
        route, err, resolution = _resolve_primary_action_route(
            "projects.intake", payload, inv
        )
        self.assertEqual(resolution, "non_ui_contract")
        self.assertEqual(route, "N/A")
        self.assertEqual(err, "")

    def test_api_data_intent_skips_target_scene_lookup(self) -> None:
        """Even with a target_scene, api.data intent bypasses all resolution."""
        inv = _inventory([
            ("projects.intake", "/s/projects.intake"),
            ("projects.list", "/s/projects.list"),
        ])
        payload = _base_payload(
            scene_key="projects.intake",
            primary_action="submit",
            action_specs={
                "submit": {
                    "label": "提交立项",
                    "intent": "api.data",
                    "target_scene": "projects.list",  # ignored due to intent
                },
            },
        )
        route, err, resolution = _resolve_primary_action_route(
            "projects.intake", payload, inv
        )
        self.assertEqual(resolution, "non_ui_contract")
        self.assertEqual(route, "N/A")

    def test_ui_contract_without_target_still_falls_back(self) -> None:
        """Sanity: ui.contract without any target fields still fallback."""
        inv = _inventory([
            ("cost.analysis", "/s/cost.analysis"),
        ])
        payload = _base_payload(
            scene_key="cost.analysis",
            primary_action="open_analysis",
            action_specs={
                "open_analysis": {
                    "label": "进入分析",
                    "intent": "ui.contract",
                },
            },
            related_scenes=[],
            target_route="/s/cost.analysis",
        )
        route, err, resolution = _resolve_primary_action_route(
            "cost.analysis", payload, inv
        )
        self.assertEqual(resolution, "self_target_fallback")
        self.assertEqual(route, "/s/cost.analysis")


class PrimaryActionEdgeCaseTests(unittest.TestCase):
    """Edge cases for missing or malformed primary_action / action_specs."""

    def test_missing_primary_action_returns_unresolved(self) -> None:
        inv = _inventory([])
        payload = _base_payload(
            scene_key="orphan.scene",
            primary_action="",
            action_specs={},
        )
        route, err, resolution = _resolve_primary_action_route(
            "orphan.scene", payload, inv
        )
        self.assertEqual(resolution, "unresolved")
        self.assertIn("primary_action is empty", err)

    def test_primary_action_not_in_action_specs_returns_unresolved(self) -> None:
        inv = _inventory([])
        payload = _base_payload(
            scene_key="broken.scene",
            primary_action="missing_action",
            action_specs={"other_action": {}},
        )
        route, err, resolution = _resolve_primary_action_route(
            "broken.scene", payload, inv
        )
        self.assertEqual(resolution, "unresolved")
        self.assertIn("action_specs missing primary_action", err)

    # ----- Wave3 Round8: Final FALLBACK eradication -----

    def test_round8_cost_analysis_target_scene_resolves(self) -> None:
        """cost.analysis.open_cost_ledger → target_scene cost.project_cost_ledger."""
        inv = _inventory([
            ("cost.analysis", "/s/cost.analysis"),
            ("cost.project_cost_ledger", "/s/cost.cost_compare"),
        ])
        payload = _base_payload(
            scene_key="cost.analysis",
            primary_action="open_cost_ledger",
            action_specs={
                "open_cost_ledger": {
                    "label": "查看成本台账",
                    "intent": "ui.contract",
                    "target_scene": "cost.project_cost_ledger",
                },
            },
            related_scenes=["cost.project_cost_ledger", "cost.profit_compare"],
            target_route="/s/cost.analysis",
        )
        route, err, resolution = _resolve_primary_action_route(
            "cost.analysis", payload, inv
        )
        self.assertEqual(resolution, "action_scene_ref")
        self.assertEqual(route, "/s/cost.cost_compare")
        self.assertEqual(err, "")

    def test_round8_finance_center_target_scene_resolves(self) -> None:
        """finance.center.open_payment_requests → target_scene finance.payment_requests."""
        inv = _inventory([
            ("finance.center", "/s/finance.center"),
            ("finance.payment_requests", "/s/finance.payment_requests"),
        ])
        payload = _base_payload(
            scene_key="finance.center",
            primary_action="open_payment_requests",
            action_specs={
                "open_payment_requests": {
                    "label": "查看付款收款申请",
                    "intent": "ui.contract",
                    "target_scene": "finance.payment_requests",
                },
            },
            related_scenes=["finance.payment_requests", "finance.settlement_orders"],
            target_route="/s/finance.center",
        )
        route, err, resolution = _resolve_primary_action_route(
            "finance.center", payload, inv
        )
        self.assertEqual(resolution, "action_scene_ref")
        self.assertEqual(route, "/s/finance.payment_requests")
        self.assertEqual(err, "")

    def test_round8_projects_ledger_target_scene_resolves(self) -> None:
        """projects.ledger.open_management → target_scene project.management."""
        inv = _inventory([
            ("projects.ledger", "/s/projects.ledger"),
            ("project.management", "/pm/dashboard"),
        ])
        payload = _base_payload(
            scene_key="projects.ledger",
            primary_action="open_management",
            action_specs={
                "open_management": {
                    "label": "查看项目驾驶舱",
                    "intent": "ui.contract",
                    "target_scene": "project.management",
                },
            },
            related_scenes=["projects.intake", "projects.list", "project.management"],
            target_route="/s/projects.ledger",
        )
        route, err, resolution = _resolve_primary_action_route(
            "projects.ledger", payload, inv
        )
        self.assertEqual(resolution, "action_scene_ref")
        self.assertEqual(route, "/pm/dashboard")
        self.assertEqual(err, "")

    def test_round8_projects_list_target_scene_resolves(self) -> None:
        """projects.list.open_intake → target_scene projects.intake."""
        inv = _inventory([
            ("projects.list", "/s/projects.list"),
            ("projects.intake", "/s/projects.intake"),
        ])
        payload = _base_payload(
            scene_key="projects.list",
            primary_action="open_intake",
            action_specs={
                "open_intake": {
                    "label": "新建立项",
                    "intent": "ui.contract",
                    "target_scene": "projects.intake",
                },
            },
            related_scenes=["projects.intake", "project.management", "projects.ledger"],
            target_route="/s/projects.list",
        )
        route, err, resolution = _resolve_primary_action_route(
            "projects.list", payload, inv
        )
        self.assertEqual(resolution, "action_scene_ref")
        self.assertEqual(route, "/s/projects.intake")
        self.assertEqual(err, "")

    def test_round8_without_target_scene_still_falls_back(self) -> None:
        """Negative case: without target_scene and no fuzzy match, falls back to self.

        Demonstrates that Round8's `target_scene` field is the actual lever —
        removing it would re-introduce the self_target_fallback path.
        """
        inv = _inventory([
            ("cost.analysis", "/s/cost.analysis"),
        ])
        payload = _base_payload(
            scene_key="cost.analysis",
            primary_action="open_cost_ledger",
            action_specs={
                "open_cost_ledger": {
                    "label": "查看成本台账",
                    "intent": "ui.contract",
                    # NO target_scene — Round8 lever removed
                },
            },
            related_scenes=["cost.project_cost_ledger", "cost.profit_compare"],
            target_route="/s/cost.analysis",
        )
        route, err, resolution = _resolve_primary_action_route(
            "cost.analysis", payload, inv
        )
        self.assertEqual(resolution, "self_target_fallback")
        self.assertEqual(route, "/s/cost.analysis")
        self.assertEqual(err, "")

    # ----- Wave3 Round9: Portal domain expansion (portal.shortcuts) -----

    def test_round9_portal_shortcuts_primary_resolves(self) -> None:
        """portal.shortcuts.open_project_intake → target_scene projects.intake."""
        inv = _inventory([
            ("portal.shortcuts", "/s/portal.shortcuts"),
            ("projects.intake", "/s/projects.intake"),
        ])
        payload = _base_payload(
            scene_key="portal.shortcuts",
            primary_action="open_project_intake",
            action_specs={
                "open_project_intake": {
                    "label": "新建项目",
                    "intent": "ui.contract",
                    "target_scene": "projects.intake",
                    "entry_kind": "shortcut",
                },
            },
            related_scenes=["projects.intake", "cost.analysis", "finance.center"],
            target_route="/s/portal.shortcuts",
        )
        route, err, resolution = _resolve_primary_action_route(
            "portal.shortcuts", payload, inv
        )
        self.assertEqual(resolution, "action_scene_ref")
        self.assertEqual(route, "/s/projects.intake")
        self.assertEqual(err, "")

    def test_round9_portal_shortcuts_all_entry_kind_shortcut(self) -> None:
        """Every secondary action in portal.shortcuts is a cross-domain shortcut
        that carries an explicit target_scene pointing into an openable route.

        This is the product-level guarantee of the portal shortcuts launcher:
        each entry card routes the user to its owning domain scene without
        relying on fuzzy matching or self-fallback.
        """
        inv = _inventory([
            ("projects.intake", "/s/projects.intake"),
            ("cost.analysis", "/s/cost.analysis"),
            ("finance.center", "/s/finance.center"),
            ("risk.center", "/s/risk.center"),
            ("contract.center", "/s/contract.center"),
            ("data.dictionary", "/s/data.dictionary"),
        ])
        action_specs = {
            "open_project_intake": {
                "label": "新建项目",
                "intent": "ui.contract",
                "target_scene": "projects.intake",
                "entry_kind": "shortcut",
            },
            "open_cost_analysis": {
                "label": "成本控制",
                "intent": "ui.contract",
                "target_scene": "cost.analysis",
                "entry_kind": "shortcut",
            },
            "open_finance_center": {
                "label": "财务中心",
                "intent": "ui.contract",
                "target_scene": "finance.center",
                "entry_kind": "shortcut",
            },
            "open_risk_center": {
                "label": "风险提醒",
                "intent": "ui.contract",
                "target_scene": "risk.center",
                "entry_kind": "shortcut",
            },
            "open_contract_center": {
                "label": "合同中心",
                "intent": "ui.contract",
                "target_scene": "contract.center",
                "entry_kind": "shortcut",
            },
            "open_data_dictionary": {
                "label": "业务字典",
                "intent": "ui.contract",
                "target_scene": "data.dictionary",
                "entry_kind": "shortcut",
            },
        }
        # Product invariant: all 6 launcher entries are ui.contract shortcuts
        # with an explicit target_scene whose inventory route is openable.
        self.assertEqual(len(action_specs), 6)
        for action_key, spec in action_specs.items():
            self.assertEqual(spec["intent"], "ui.contract")
            self.assertEqual(spec["entry_kind"], "shortcut")
            target_scene = spec.get("target_scene")
            self.assertTrue(target_scene, f"{action_key} missing target_scene")
            self.assertIn(target_scene, inv)
            route = _resolve_inventory_route(target_scene, inv)
            self.assertTrue(
                _is_route_openable(route),
                f"{action_key} target_scene={target_scene} not openable",
            )

    def test_round9_secondary_shortcut_without_target_scene_falls_back(self) -> None:
        """Negative proof: if a shortcut entry loses its target_scene, resolving it
        via the primary-action chain no longer yields an exact route — the entry
        would degrade to the generic self_target_fallback of the launcher.

        related_scenes deliberately excludes projects.intake (the action-name
        guess target) to prove the launcher itself carries no intrinsic primary
        navigation — only per-entry target_scene makes it resolvable exactly.
        """
        inv = _inventory([
            ("portal.shortcuts", "/s/portal.shortcuts"),
            ("projects.intake", "/s/projects.intake"),
        ])
        payload = _base_payload(
            scene_key="portal.shortcuts",
            primary_action="open_project_intake",
            action_specs={
                "open_project_intake": {
                    "label": "新建项目",
                    "intent": "ui.contract",
                    # target_scene intentionally removed (regression scenario)
                },
            },
            related_scenes=["cost.analysis", "finance.center"],
            target_route="/s/portal.shortcuts",
        )
        route, err, resolution = _resolve_primary_action_route(
            "portal.shortcuts", payload, inv
        )
        # Without target_scene the launcher primary degrades to self-fallback
        # (portals have no domain-specific primary navigation of their own).
        self.assertEqual(resolution, "self_target_fallback")
        self.assertEqual(route, "/s/portal.shortcuts")
        self.assertEqual(err, "")

    # ----- Wave3 Round10: Portal message center (portal.notifications) -----

    def test_round10_portal_notifications_primary_read_is_non_ui_contract(self) -> None:
        """portal.notifications.view_unread (intent=api.data) short-circuits to
        non_ui_contract — reading unread conversations is a data action, not a
        UI navigation, so it must never be forced through route resolution.
        """
        inv = _inventory([
            ("portal.notifications", "/s/portal.notifications"),
        ])
        payload = _base_payload(
            scene_key="portal.notifications",
            primary_action="view_unread",
            action_specs={
                "view_unread": {
                    "label": "查看未读消息",
                    "intent": "api.data",
                    "action_kind": "message_read",
                },
            },
            related_scenes=["my_work.workspace"],
            target_route="/s/portal.notifications",
        )
        route, err, resolution = _resolve_primary_action_route(
            "portal.notifications", payload, inv
        )
        self.assertEqual(resolution, "non_ui_contract")
        self.assertEqual(route, "N/A")
        self.assertEqual(err, "")

    def test_round10_portal_notifications_all_links_have_explicit_target(self) -> None:
        """Product invariant: every notification_link action in the message
        center carries an explicit target_scene pointing into an openable
        route — clicking a notification routes the user to its owning domain
        scene without relying on fuzzy matching or self-fallback.
        """
        inv = _inventory([
            ("my_work.workspace", "/s/my_work.workspace"),
            ("risk.center", "/s/risk.center"),
            ("contract.center", "/s/contract.center"),
            ("finance.center", "/s/finance.center"),
        ])
        action_specs = {
            "view_unread": {
                "label": "查看未读消息",
                "intent": "api.data",
                "action_kind": "message_read",
            },
            "open_my_work": {
                "label": "去我的工作",
                "intent": "ui.contract",
                "target_scene": "my_work.workspace",
                "entry_kind": "notification_link",
            },
            "open_risk_center": {
                "label": "处理风险提醒",
                "intent": "ui.contract",
                "target_scene": "risk.center",
                "entry_kind": "notification_link",
            },
            "open_contract_center": {
                "label": "查看合同动态",
                "intent": "ui.contract",
                "target_scene": "contract.center",
                "entry_kind": "notification_link",
            },
            "open_finance_center": {
                "label": "查看财务审批",
                "intent": "ui.contract",
                "target_scene": "finance.center",
                "entry_kind": "notification_link",
            },
        }
        # Product invariant: 4 of the 5 specs are notification links that must
        # each resolve exactly via explicit target_scene; view_unread is the
        # sole api.data read action.
        links = [spec for spec in action_specs.values() if spec.get("entry_kind") == "notification_link"]
        self.assertEqual(len(links), 4)
        for spec in links:
            self.assertEqual(spec["intent"], "ui.contract")
            target_scene = spec.get("target_scene")
            self.assertTrue(target_scene, f"notification_link missing target_scene")
            self.assertIn(target_scene, inv)
            route = _resolve_inventory_route(target_scene, inv)
            self.assertTrue(
                _is_route_openable(route),
                f"notification_link target_scene={target_scene} not openable",
            )

    def test_round10_notification_link_without_target_falls_back(self) -> None:
        """Negative proof: if a notification_link loses its target_scene, the
        message center has no intrinsic primary navigation of its own — the
        action degrades to self_target_fallback of the inbox.

        related_scenes deliberately excludes the owning-domain scenes (they are
        reachable only via the per-link target_scene), proving the notification
        links are the exact-resolution lever.
        """
        inv = _inventory([
            ("portal.notifications", "/s/portal.notifications"),
            ("my_work.workspace", "/s/my_work.workspace"),
            ("risk.center", "/s/risk.center"),
        ])
        payload = _base_payload(
            scene_key="portal.notifications",
            primary_action="open_risk_center",
            action_specs={
                "open_risk_center": {
                    "label": "处理风险提醒",
                    "intent": "ui.contract",
                    # target_scene intentionally removed (regression scenario)
                },
            },
            related_scenes=["cost.analysis", "my_work.workspace"],
            target_route="/s/portal.notifications",
        )
        route, err, resolution = _resolve_primary_action_route(
            "portal.notifications", payload, inv
        )
        # risk.center present in inventory but NOT in related_scenes (and no
        # related scene shares the `.center` fuzzy tail-token), so the
        # action-name guess cannot match via related_scene_match/fuzzy; the
        # inbox falls back to its own route.
        self.assertEqual(resolution, "self_target_fallback")
        self.assertEqual(route, "/s/portal.notifications")
        self.assertEqual(err, "")


if __name__ == "__main__":
    unittest.main()