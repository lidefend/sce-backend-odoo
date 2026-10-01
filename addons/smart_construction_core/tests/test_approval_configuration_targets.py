"""Pure projection tests: no database, menu synthesis, or policy writes."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest

path = Path(__file__).resolve().parents[1] / "services/approval_configuration_targets.py"
spec = importlib.util.spec_from_file_location("approval_configuration_targets", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Model:
    def __init__(self, readable=True, fields=None):
        self.readable, self._fields = readable, fields or {}

    def check_access_rights(self, operation, raise_exception=True):
        assert operation == "read" and raise_exception is False
        return self.readable


class ApprovalTargetsTest(unittest.TestCase):
    def setUp(self):
        self.env = {
            "parent": Model(fields={
                "versions": SimpleNamespace(type="one2many", comodel_name="version"),
                "other": SimpleNamespace(type="many2one", comodel_name="unrelated"),
            }),
            "version": Model(), "unrelated": Model(),
            "sc.approval.policy": SimpleNamespace(fields_get=lambda fields: {
                "target_model": {"selection": [("version", "版本"), ("unrelated", "其他")]}}),
        }

    def targets(self):
        return module.approval_configuration_targets(self.env, "parent")

    def test_owned_supported_child_uses_policy_label_and_real_field(self):
        self.assertEqual(self.targets(), [{"value": "version", "label": "版本", "relation_field": "versions"}])

    def test_supported_self_does_not_need_a_menu(self):
        self.assertEqual(module.approval_configuration_targets(self.env, "version"),
                         [{"value": "version", "label": "版本", "relation_field": ""}])

    def test_denied_parent_does_not_expose_children(self):
        self.env["parent"].readable = False
        self.assertEqual(self.targets(), [])

    def test_denied_child_is_not_a_configuration_target(self):
        self.env["version"].readable = False
        self.assertEqual(self.targets(), [])

    def test_unsupported_child_is_not_inferred_from_relation(self):
        self.env["parent"]._fields["versions"].comodel_name = "unsupported"
        self.env["unsupported"] = Model()
        self.assertEqual(self.targets(), [])

    def test_duplicate_relation_is_one_target(self):
        self.env["parent"]._fields["versions_copy"] = self.env["parent"]._fields["versions"]
        self.assertEqual(len(self.targets()), 1)

    def test_no_recursive_or_many2one_authority(self):
        self.env["version"]._fields["children"] = SimpleNamespace(type="one2many", comodel_name="unrelated")
        self.assertEqual([row["value"] for row in self.targets()], ["version"])

    def test_missing_modules_or_model_fail_closed(self):
        self.assertEqual(module.approval_configuration_targets(self.env, "missing"), [])
        self.env.pop("sc.approval.policy")
        self.assertEqual(self.targets(), [])


if __name__ == "__main__":
    unittest.main()
