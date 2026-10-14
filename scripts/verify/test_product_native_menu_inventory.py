import unittest
from scripts.verify.product_native_menu_inventory import action_identity, blocked_ancestors


class NativeInventoryTests(unittest.TestCase):
    def test_false_action_is_a_container_not_a_business_entry(self):
        self.assertIsNone(action_identity({"action": "False"}))
        self.assertIsNone(action_identity({}))
        self.assertEqual(action_identity({"action": "module.action"}), "module.action")

    def test_active_child_still_reports_inactive_ancestor(self):
        facts = {"child": {"active": "True", "parent_id": "parent"}, "parent": {"active": "False", "parent_id": "root"}, "root": {"active": "True"}}
        self.assertEqual(blocked_ancestors("child", facts), ["parent"])
        facts["root"]["parent_id"] = "child"
        with self.assertRaisesRegex(ValueError, "cycle"):
            blocked_ancestors("child", facts)
