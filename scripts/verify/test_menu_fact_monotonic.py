import copy
import unittest
from scripts.verify.menu_fact_monotonic import compare


class MenuMonotonicTests(unittest.TestCase):
    def setUp(self):
        self.before = {"status":"passed","database":"sc_dev_demo","principals":[{
            "user_id":7,"company_id":1,"groups":[4],"nodes":[
                {"key":"menu:1","label_path":["中心","原有入口"],"target":{"action_id":10}},
                {"key":"menu:2","label_path":["中心","另一入口"],"target":{"action_id":11}},
            ]}]}
        self.after = copy.deepcopy(self.before)

    def test_addition_keeps_existing_entries(self):
        self.after["principals"][0]["nodes"].insert(1,{"key":"menu:3","label_path":["中心","新增"]})
        self.assertEqual(compare(self.before,self.after)["status"],"passed")

    def test_larger_count_does_not_mask_removed_identity(self):
        nodes=self.after["principals"][0]["nodes"]
        nodes.pop(0)
        nodes.extend([{"key":"menu:3"},{"key":"menu:4"}])
        self.assertEqual(compare(self.before,self.after)["status"],"failed")

    def test_same_identity_cannot_move_or_change_target(self):
        for field,value in (("label_path",["另一个中心","原有入口"]),("target",{"action_id":99})):
            changed=copy.deepcopy(self.after)
            changed["principals"][0]["nodes"][0][field]=value
            self.assertEqual(compare(self.before,changed)["status"],"failed")

    def test_original_order_preserved(self):
        self.after["principals"][0]["nodes"].reverse()
        self.assertEqual(compare(self.before,self.after)["status"],"failed")

    def test_missing_actor_or_changed_permission_invalidates_comparison(self):
        self.after["principals"][0]["groups"].append(5)
        self.assertEqual(compare(self.before,self.after)["status"],"failed")
        self.after["principals"]=[]
        self.assertEqual(compare(self.before,self.after)["status"],"failed")

    def test_failure_or_database_drift_not_reusable(self):
        self.after["status"]="failed"
        self.assertEqual(compare(self.before,self.after)["status"],"failed")
        self.after["status"]="passed"
        self.after["database"]="other"
        self.assertEqual(compare(self.before,self.after)["status"],"failed")
