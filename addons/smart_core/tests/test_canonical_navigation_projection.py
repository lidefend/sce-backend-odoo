# -*- coding: utf-8 -*-
"""Lock on the server-owned canonical navigation projection.

``MenuService.project_canonical_navigation`` is the single projection that turns
the authorized delivery tree into the client's ``canonical_navigation`` v1
carrier.  The client resolves a node without an action target and without a
container authority to ``state="container"``.  The projection used to read
``is_clickable=False`` as "explicitly disabled" on every node, while the
delivery engine marks each published directory group with exactly that flag and
``reason_code=DIRECTORY_ONLY``.  Publishing any product policy that grouped menu
leaves therefore made ``system.init`` fail closed for every user of that policy.
"""

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.smart_core.delivery.menu_service import MenuService


@tagged("post_install", "-at_install", "canonical_navigation_projection")
class TestCanonicalNavigationProjection(TransactionCase):

    @staticmethod
    def _authority(menu_id, action_id, route):
        return {
            "primary_actions": [{
                "menu_id": menu_id,
                "action_id": action_id,
                "route_kind": "menu_action",
                "menu_xmlid": "test.menu_%s" % menu_id,
                "action_xmlid": "test.action_%s" % action_id,
                "source": "unit-test",
                "route": route,
            }],
            "menu_containers": [],
        }

    def test_declared_directory_group_is_a_container_not_a_disabled_entry(self):
        nav = [{
            "key": "root:system_menu",
            "label": "系统菜单",
            "menu_id": 0,
            "children": [{
                "key": "group:catalog.cost.center.budget",
                "label": "项目预算",
                "menu_id": 0,
                "is_clickable": False,
                "availability_status": "ok",
                "reason_code": "DIRECTORY_ONLY",
                "target_type": "directory",
                "delivery_mode": "none",
                "children": [{
                    "key": "system.policy.385",
                    "label": "预算清单",
                    "menu_id": 385,
                    "action_id": 620,
                    "children": [],
                }],
            }],
        }]
        projected = MenuService.project_canonical_navigation(
            nav, self._authority(385, 620, "/a/620?menu_id=385")
        )
        directory = projected[0]["children"][0]
        self.assertEqual(directory["canonical_navigation"]["state"], "container")
        self.assertIsNone(directory["canonical_navigation"]["disabled_reason"])
        self.assertEqual(
            directory["children"][0]["canonical_navigation"]["state"], "enabled"
        )

    def test_action_entry_marked_non_clickable_still_requires_a_server_reason(self):
        nav = [{
            "key": "system.policy.385",
            "label": "预算清单",
            "menu_id": 385,
            "action_id": 620,
            "is_clickable": False,
            "children": [],
        }]
        with self.assertRaises(ValueError) as caught:
            MenuService.project_canonical_navigation(
                nav, self._authority(385, 620, "/a/620?menu_id=385")
            )
        self.assertIn("385/620", str(caught.exception))

    def test_action_entry_marked_non_clickable_with_reason_projects_disabled(self):
        nav = [{
            "key": "system.policy.385",
            "label": "预算清单",
            "menu_id": 385,
            "action_id": 620,
            "is_clickable": False,
            "disabled_reason": "当前账号无权执行此操作",
            "children": [],
        }]
        projected = MenuService.project_canonical_navigation(
            nav, self._authority(385, 620, "/a/620?menu_id=385")
        )
        carrier = projected[0]["canonical_navigation"]
        self.assertEqual(carrier["state"], "disabled")
        self.assertEqual(carrier["disabled_reason"], "当前账号无权执行此操作")

    def test_directory_declaring_blocked_availability_still_requires_a_reason(self):
        nav = [{
            "key": "group:catalog.report.center",
            "label": "报表中心",
            "menu_id": 0,
            "is_clickable": False,
            "availability_status": "blocked",
            "children": [{
                "key": "system.policy.591",
                "label": "库存统计表",
                "menu_id": 591,
                "action_id": 825,
                "children": [],
            }],
        }]
        with self.assertRaises(ValueError):
            MenuService.project_canonical_navigation(
                nav, self._authority(591, 825, "/a/825?menu_id=591")
            )
