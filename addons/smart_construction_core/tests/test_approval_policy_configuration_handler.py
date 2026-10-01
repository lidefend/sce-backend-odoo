# -*- coding: utf-8 -*-
import ast
import importlib.util
import sys
import types
import unittest
from pathlib import Path


class _BaseIntentHandler:
    def __init__(self, env=None, params=None, payload=None, context=None):
        self.env = env or {}
        self.params = params or {}
        self.payload = payload or {}
        self.context = context or {}


def _install_module(name, **attrs):
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


def _load_handler_module():
    root = Path(__file__).resolve().parents[1]
    exc_mod = _install_module(
        "odoo.exceptions",
        AccessError=type("AccessError", (Exception,), {}),
        ValidationError=type("ValidationError", (Exception,), {}),
    )
    _install_module("odoo", exceptions=exc_mod)
    _install_module("odoo.addons")
    smart_core_mod = _install_module("odoo.addons.smart_core")
    core_mod = _install_module("odoo.addons.smart_core.core")
    smart_core_mod.__path__ = [str(root.parent / "smart_core")]
    core_mod.__path__ = [str(root.parent / "smart_core" / "core")]
    _install_module("odoo.addons.smart_core.core.base_handler", BaseIntentHandler=_BaseIntentHandler)

    module_name = "odoo.addons.smart_construction_core.handlers.approval_policy_configuration"
    sys.modules.pop(module_name, None)
    spec = importlib.util.spec_from_file_location(
        module_name,
        root / "handlers" / "approval_policy_configuration.py",
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class _User:
    id = 9

    def has_group(self, xmlid):
        return xmlid in {
            "smart_core.group_smart_core_business_config_admin",
            "smart_construction_core.group_sc_cap_business_config_admin",
        }


class _PolicyRecord:
    def __init__(self, **vals):
        self.id = vals.get("id", 1)
        self.name = vals.get("name", "付款审批规则")
        self.target_model = vals.get("target_model", "payment.request")
        self.approval_required = vals.get("approval_required", True)
        self.mode = vals.get("mode", "linear")
        self.trigger = vals.get("trigger", "submit")
        self.runtime_state = vals.get("runtime_state", "policy_only")
        self.manager_scope_key = vals.get("manager_scope_key", "finance_manager")
        self.step_count = vals.get("step_count", 2)
        self.step_ids = vals.get("step_ids", [])
        self.active = vals.get("active", True)
        self.company_id = vals.get("company_id", types.SimpleNamespace(id=7))
        self.write_calls = []
        self.synced = False

    def write(self, vals):
        self.write_calls.append(dict(vals))
        for key, value in vals.items():
            setattr(self, key, value)
        return True

    def with_context(self, **kwargs):
        self.context = kwargs
        return self

    def sync_tier_definitions(self):
        self.synced = True


class _StepRecord:
    def __init__(self, **vals):
        self.id = vals.get("id", 1)
        self.policy_id = vals.get("policy_id")
        self.name = vals.get("name", "财务审核")
        self.approval_scope_key = vals.get("approval_scope_key", "finance_manager")
        self.sequence = vals.get("sequence", 10)
        self.active = vals.get("active", True)
        self.amount_min = vals.get("amount_min", False)
        self.amount_max = vals.get("amount_max", False)
        self.condition_note = vals.get("condition_note", "")
        self.note = vals.get("note", "")
        self.write_calls = []

    def write(self, vals):
        self.write_calls.append(dict(vals))
        for key, value in vals.items():
            setattr(self, key, value)
        return True

    def with_context(self, **kwargs):
        self.context = kwargs
        return self


class _EmptyRecord:
    id = 0

    def __bool__(self):
        return False


class _PolicyModel:
    def __init__(self, rows=None):
        self.rows = list(rows or [])
        self.created = []
        self.last_search_domain = None
        self.last_search_order = ""

    def sudo(self):
        return self

    def with_context(self, **kwargs):
        self.context = kwargs
        return self

    def browse(self, *args):
        return _EmptyRecord()

    def fields_get(self, fields):
        return {
            "target_model": {"selection": [("payment.request", "付款/收款申请"), ("sc.expense.claim", "费用/保证金")]},
            "mode": {"selection": [("none", "无需审核"), ("single", "单级审核"), ("linear", "多级顺序审核")]},
            "trigger": {"selection": [("submit", "提交时"), ("confirm", "确认时")]},
        }

    def _selection_approval_scope(self):
        return [("finance_manager", "财务审核人"), ("executive", "管理层/总经理终审")]

    def search(self, domain, order=None, limit=None):
        self.last_search_domain = domain
        self.last_search_order = order or ""
        target_model = next((value for field, op, value in domain if field == "target_model" and op == "="), "")
        rows = [row for row in self.rows if row.target_model == target_model]
        if not rows:
            return _EmptyRecord()
        return rows[0] if limit == 1 else rows

    def create(self, vals):
        record = _PolicyRecord(id=88, **vals)
        self.rows.append(record)
        self.created.append(dict(vals))
        return record

    def _amount_condition_authority(self, model):
        path = Path(__file__).resolve().parents[1] / "models/support/approval_policy.py"
        method = next(node for node in ast.walk(ast.parse(path.read_text()))
                      if isinstance(node, ast.FunctionDef) and node.name == "_amount_condition_authority")
        method.decorator_list = []
        namespace = {"_": lambda text: text}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), "exec"), namespace)
        registry = {model: types.SimpleNamespace(fields_get=lambda names: {name: {"string": "单据金额"} for name in names})}
        return namespace["_amount_condition_authority"](types.SimpleNamespace(env=registry), model)

    def is_approval_required(self, model, company=None):
        del company
        for row in self.rows:
            if row.target_model == model and row.active and row.approval_required and row.mode != "none":
                return True
        return False


class _StepModel:
    def __init__(self, policy_model):
        self.policy_model = policy_model
        self.created = []
        self.next_id = 300

    def sudo(self):
        return self

    def create(self, vals):
        record = _StepRecord(id=self.next_id, **vals)
        self.next_id += 1
        self.created.append(dict(vals))
        for policy in self.policy_model.rows:
            if policy.id == vals.get("policy_id"):
                policy.step_ids.append(record)
                break
        return record


class _Env(dict):
    company = types.SimpleNamespace(id=7)
    user = _User()


class ApprovalPolicyConfigurationHandlerTests(unittest.TestCase):
    def setUp(self):
        self.module = _load_handler_module()

    def test_get_serializes_current_business_policy_and_options(self):
        policy = _PolicyRecord(
            target_model="payment.request",
            mode="linear",
            approval_required=True,
            step_ids=[
                _StepRecord(id=22, name="财务审核", approval_scope_key="finance_manager", sequence=20),
                _StepRecord(id=21, name="管理层终审", approval_scope_key="executive", sequence=10),
            ],
        )
        env = _Env({"sc.approval.policy": _PolicyModel([policy])})
        handler = self.module.ApprovalPolicyConfigGetHandler(env=env, params={"model": "payment.request"})

        result = handler.handle()

        self.assertTrue(result["ok"])
        data = result["data"]
        self.assertEqual(data["boundary"], "industry_policy_runtime")
        self.assertTrue(data["runtime_approval_required"])
        self.assertEqual(data["policy"]["target_model"], "payment.request")
        self.assertEqual(data["policy"]["mode"], "linear")
        self.assertEqual([step["id"] for step in data["policy"]["steps"]], [21, 22])
        self.assertEqual(data["policy"]["steps"][0]["approval_scope_label"], "管理层/总经理终审")
        self.assertIn({"value": "finance_manager", "label": "财务审核人"}, data["scope_options"])
        authority = result["meta"]["source_authority"]
        self.assertTrue(authority["projection_only"])
        self.assertEqual(authority["lowcode_boundary"], "approval_policy")
        self.assertEqual(authority["policy_source"], "sc.approval.policy")
        self.assertEqual(authority["lowcode_source"], self.module.APPROVAL_POLICY_SOURCE_TENANT_LOWCODING)

    def test_set_creates_policy_and_normalizes_disabled_mode(self):
        model = _PolicyModel([])
        env = _Env({"sc.approval.policy": model})
        handler = self.module.ApprovalPolicyConfigSetHandler(
            env=env,
            params={
                "model": "sc.expense.claim",
                "approval_required": False,
                "mode": "linear",
                "manager_scope_key": "",
            },
        )

        result = handler.handle()

        self.assertTrue(result["ok"])
        self.assertEqual(len(model.created), 1)
        self.assertEqual(model.created[0]["target_model"], "sc.expense.claim")
        self.assertFalse(model.created[0]["approval_required"])
        self.assertEqual(model.created[0]["mode"], "none")
        self.assertEqual(result["data"]["policy"]["mode"], "none")
        self.assertFalse(result["data"]["runtime_approval_required"])
        authority = result["meta"]["source_authority"]
        self.assertTrue(authority["write_proxy"])
        self.assertFalse(authority["projection_only"])
        self.assertEqual(authority["lowcode_boundary"], "approval_policy")
        self.assertEqual(authority["policy_source"], "sc.approval.policy")

    def test_set_updates_existing_policy_and_syncs_runtime(self):
        policy = _PolicyRecord(target_model="payment.request", approval_required=False, mode="none")
        model = _PolicyModel([policy])
        env = _Env({"sc.approval.policy": model})
        handler = self.module.ApprovalPolicyConfigSetHandler(
            env=env,
            params={
                "model": "payment.request",
                "approval_required": True,
                "mode": "linear",
                "manager_scope_key": "executive",
            },
        )

        result = handler.handle()

        self.assertTrue(result["ok"])
        self.assertEqual(len(model.created), 0)
        self.assertEqual(policy.write_calls[-1]["mode"], "linear")
        self.assertEqual(policy.manager_scope_key, "executive")
        self.assertTrue(policy.synced)
        self.assertTrue(result["data"]["runtime_approval_required"])

    def test_steps_set_reorders_updates_creates_and_inactivates_steps(self):
        first = _StepRecord(id=11, name="财务审核", approval_scope_key="finance_manager", sequence=10)
        second = _StepRecord(id=12, name="管理层终审", approval_scope_key="executive", sequence=20)
        policy = _PolicyRecord(target_model="payment.request", mode="linear", approval_required=True, step_ids=[first, second])
        policy_model = _PolicyModel([policy])
        step_model = _StepModel(policy_model)
        env = _Env({"sc.approval.policy": policy_model, "sc.approval.step": step_model})
        handler = self.module.ApprovalPolicyStepsSetHandler(
            env=env,
            params={
                "model": "payment.request",
                "steps": [
                    {"id": 12, "name": "总经理终审", "approval_scope_key": "executive", "active": True},
                    {"id": 0, "name": "财务复核", "approval_scope_key": "finance_manager", "active": True, "amount_min": 1000},
                ],
            },
        )

        result = handler.handle()

        self.assertTrue(result["ok"])
        self.assertEqual(second.sequence, 10)
        self.assertEqual(second.name, "总经理终审")
        self.assertFalse(first.active)
        self.assertEqual(len(step_model.created), 1)
        self.assertEqual(step_model.created[0]["sequence"], 20)
        self.assertEqual(policy.write_calls[-1]["mode"], "linear")
        self.assertTrue(policy.synced)
        self.assertEqual(result["data"]["policy"]["step_count"], 2)

    def test_steps_set_pure_reorder_only_updates_sequences(self):
        first = _StepRecord(id=11, name="合同经办确认", approval_scope_key="finance_manager", sequence=10)
        second = _StepRecord(id=12, name="合同中心审核", approval_scope_key="executive", sequence=20)
        policy = _PolicyRecord(target_model="payment.request", mode="linear", approval_required=True, step_ids=[first, second])
        policy_model = _PolicyModel([policy])
        step_model = _StepModel(policy_model)
        env = _Env({"sc.approval.policy": policy_model, "sc.approval.step": step_model})
        handler = self.module.ApprovalPolicyStepsSetHandler(
            env=env,
            params={
                "model": "payment.request",
                "steps": [
                    {"id": 12, "name": "合同中心审核", "approval_scope_key": "executive", "active": True},
                    {"id": 11, "name": "合同经办确认", "approval_scope_key": "finance_manager", "active": True},
                ],
            },
        )

        result = handler.handle()

        self.assertTrue(result["ok"])
        self.assertEqual(len(step_model.created), 0)
        self.assertTrue(first.active)
        self.assertTrue(second.active)
        self.assertEqual(second.sequence, 10)
        self.assertEqual(first.sequence, 20)
        self.assertEqual(first.write_calls[-1]["sequence"], 20)
        self.assertEqual(second.write_calls[-1]["sequence"], 10)
        self.assertEqual(result["data"]["policy"]["steps"][0]["id"], 12)
        self.assertEqual(result["data"]["policy"]["steps"][1]["id"], 11)
        self.assertTrue(policy.synced)


    def test_amount_capability_is_returned_without_a_policy_and_on_both_writes(self):
        for model, supported, field in [("payment.request", True, "amount"), ("project.project", False, ""), ("sc.project.document", False, "")]:
            Policy = _PolicyModel()
            env = _Env({"sc.approval.policy": Policy, "sc.approval.step": _StepModel(Policy)})
            for handler_cls, params in [
                (self.module.ApprovalPolicyConfigGetHandler, {}),
                (self.module.ApprovalPolicyConfigSetHandler, {"approval_required": False, "mode": "none"}),
                (self.module.ApprovalPolicyStepsSetHandler, {"steps": []}),
            ]:
                with self.subTest(model=model, handler=handler_cls.__name__):
                    result = handler_cls(env=env, params={"model": model, **params}).handle()
                    capability = result["data"]["amount_condition"]
                    self.assertEqual(capability["supported"], supported)
                    self.assertEqual(capability["field"], field)
                    self.assertTrue(capability["message"])
                    self.assertEqual(capability["reason_code"], "amount_field_declared" if supported else "amount_field_not_declared")

    def test_invalid_later_step_never_mutates_existing_or_creates_missing_policy(self):
        valid = {"name": "审核", "approval_scope_key": "executive", "active": True}
        for missing in [False, True]:
            for bad in [None, {**valid, "amount_min": 1}, {**valid, "amount_max": "nan"},
                        {**valid, "amount_max": "inf"}, {**valid, "amount_min": -1},
                        {**valid, "amount_min": 2, "amount_max": 1}, {**valid, "id": 987},
                        {**valid, "approval_scope_key": "invalid"}]:
                with self.subTest(missing=missing, bad=bad):
                    step = _StepRecord(id=21)
                    policy = _PolicyRecord(target_model="project.project", step_ids=[step])
                    Policy = _PolicyModel([] if missing else [policy])
                    Step = _StepModel(Policy)
                    env = _Env({"sc.approval.policy": Policy, "sc.approval.step": Step})
                    first = dict(valid, **({} if missing else {"id": 21}))
                    with self.assertRaises(self.module.ValidationError):
                        self.module.ApprovalPolicyStepsSetHandler(env=env, params={"model": "project.project", "steps": [first, bad]}).handle()
                    self.assertEqual(Policy.created, [])
                    self.assertEqual(Step.created, [])
                    self.assertEqual(policy.write_calls, [])
                    self.assertEqual(step.write_calls, [])

    def test_duplicate_step_identity_fails_before_first_write(self):
        step = _StepRecord(id=21)
        policy = _PolicyRecord(step_ids=[step])
        Policy = _PolicyModel([policy])
        Step = _StepModel(Policy)
        env = _Env({"sc.approval.policy": Policy, "sc.approval.step": Step})
        raw = {"id": 21, "name": "审核", "approval_scope_key": "executive"}
        with self.assertRaises(self.module.ValidationError):
            self.module.ApprovalPolicyStepsSetHandler(env=env, params={"model": "payment.request", "steps": [raw, raw]}).handle()
        self.assertEqual(step.write_calls, [])
        self.assertEqual(policy.write_calls, [])
        self.assertEqual(Step.created, [])


    def test_step_identity_rejects_boolean_fraction_and_noncanonical_strings_without_write(self):
        for bad_id in [True, False, 0.0, 1.5, 1.0, "1.5", " 1", "01", -1]:
            step = _StepRecord(id=1)
            policy = _PolicyRecord(step_ids=[step])
            Policy = _PolicyModel([policy])
            Step = _StepModel(Policy)
            env = _Env({"sc.approval.policy": Policy, "sc.approval.step": Step})
            with self.subTest(id=bad_id), self.assertRaises(self.module.ValidationError):
                self.module.ApprovalPolicyStepsSetHandler(env=env, params={"model": "payment.request", "steps": [
                    {"id": bad_id, "name": "审核", "approval_scope_key": "executive"},
                ]}).handle()
            self.assertEqual(step.write_calls, [])
            self.assertEqual(policy.write_calls, [])
            self.assertEqual(Step.created, [])


if __name__ == "__main__":
    unittest.main()
