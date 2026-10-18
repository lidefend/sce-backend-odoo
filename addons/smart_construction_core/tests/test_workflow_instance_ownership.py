# -*- coding: utf-8 -*-
"""Owner-boundary checks for sc.workflow.instance company attribution.

The workflow instance company fact must be inherited from the business document
the instance is about. It must never be inferred from the workflow definition
(configuration) or from the current environment (caller context). These checks
run without an Odoo server so the ownership rule stays provable in the default
inner-loop lane.
"""
import importlib.util
import sys
import types
import unittest
from pathlib import Path

MODULE_PATH = (
    Path(__file__).resolve().parents[1] / "models" / "support" / "sc_workflow.py"
)


class _Stub(object):
    """Placeholder for any Odoo attribute reached at import time."""

    def __init__(self, *args, **kwargs):
        pass

    def __getattr__(self, name):
        return _Stub()

    def __call__(self, *args, **kwargs):
        if len(args) == 1 and not kwargs and callable(args[0]) and not isinstance(args[0], _Stub):
            return args[0]
        return _Stub()


def _load_workflow_module():
    """Load sc_workflow from the real package when Odoo is installed.

    Inside an Odoo runtime the module is imported normally so the test never
    replaces ``sys.modules['odoo']``.  In the dependency-free inner loop the
    Odoo imports are stubbed and restored afterwards.
    """
    try:  # pragma: no cover - depends on the running lane
        from odoo.addons.smart_construction_core.models.support import sc_workflow

        return sc_workflow
    except Exception:
        pass

    stubbed = (
        "odoo",
        "odoo.exceptions",
        "odoo.addons",
        "odoo.addons.smart_core",
        "odoo.addons.smart_core.security",
        "odoo.addons.smart_core.security.platform_admin",
    )
    saved = {name: sys.modules.get(name) for name in stubbed}
    odoo = types.ModuleType("odoo")
    odoo._ = lambda text: text
    odoo.api = _Stub()
    odoo.fields = _Stub()
    base_model = type("BaseModel", (object,), {})
    odoo.models = types.SimpleNamespace(
        Model=base_model, AbstractModel=base_model, TransientModel=base_model
    )
    odoo.exceptions = types.SimpleNamespace(UserError=type("UserError", (Exception,), {}))
    addons = types.ModuleType("odoo.addons")
    smart_core = types.ModuleType("odoo.addons.smart_core")
    smart_core_security = types.ModuleType("odoo.addons.smart_core.security")
    platform_admin = types.ModuleType("odoo.addons.smart_core.security.platform_admin")
    platform_admin.user_is_tenant_config_admin = lambda user, **_kwargs: False
    odoo.addons = addons
    smart_core.security = smart_core_security
    smart_core_security.platform_admin = platform_admin
    sys.modules["odoo"] = odoo
    sys.modules["odoo.exceptions"] = odoo.exceptions
    sys.modules["odoo.addons"] = addons
    sys.modules["odoo.addons.smart_core"] = smart_core
    sys.modules["odoo.addons.smart_core.security"] = smart_core_security
    sys.modules["odoo.addons.smart_core.security.platform_admin"] = platform_admin
    try:
        spec = importlib.util.spec_from_file_location(
            "sc_workflow_ownership", MODULE_PATH
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.UserError
        return module
    finally:
        for name, previous in saved.items():
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous


WORKFLOW = _load_workflow_module()
UserError = WORKFLOW.UserError


class _Company(object):
    def __init__(self, company_id):
        self.id = company_id

    def __bool__(self):
        return bool(self.id)


class _Record(object):
    def __init__(self, company_id, has_company_field=True, exists=True):
        self._company = _Company(company_id)
        self._has_company_field = has_company_field
        self._exists = exists
        self.sudo_calls = 0

    def sudo(self):
        self.sudo_calls += 1
        return self

    def exists(self):
        return self if self._exists else _Record(False, exists=False)

    def __contains__(self, field_name):
        return self._has_company_field and field_name == "company_id"

    def __bool__(self):
        return self._exists

    @property
    def company_id(self):
        return self._company


class _Model(object):
    def __init__(self, records):
        self._records = records

    def browse(self, res_id):
        return self._records.get(res_id) if res_id else _Record(False, exists=False)


class _Env(object):
    def __init__(self, models):
        self._models = models
        # A real environment exposes env.company too; the resolver must never use it.
        self.company = _Company(999)

    def __contains__(self, model_name):
        return model_name in self._models

    def __getitem__(self, model_name):
        if model_name not in self._models:
            raise KeyError(model_name)
        return _Model(self._models[model_name])


class _Def(object):
    def __init__(self, company_id=False, defined=True):
        self.company_id = _Company(company_id) if defined and company_id else False


def _env(company_id=7, def_company=None, defined=True, **record_kwargs):
    record = _Record(company_id, **record_kwargs)
    return _Env({"project.project": {11: record}}), record, _Def(
        def_company if def_company is not None else False, defined=True
    )


class WorkflowInstanceCompanyResolutionTests(unittest.TestCase):
    def test_business_document_company_owns_the_instance(self):
        env, _record, workflow_def = _env(company_id=7, def_company=7)
        company = WORKFLOW.resolve_workflow_instance_company(
            env, "project.project", 11, workflow_def
        )
        self.assertEqual(company.id, 7)

    def test_definition_without_company_does_not_invent_one(self):
        env, _record, workflow_def = _env(company_id=7)
        company = WORKFLOW.resolve_workflow_instance_company(
            env, "project.project", 11, workflow_def
        )
        self.assertEqual(company.id, 7)
        self.assertNotEqual(company.id, env.company.id)

    def test_definition_company_mismatch_fails_closed(self):
        env, _record, workflow_def = _env(company_id=7, def_company=9)
        with self.assertRaises(UserError) as ctx:
            WORKFLOW.resolve_workflow_instance_company(
                env, "project.project", 11, workflow_def
            )
        self.assertIn(WORKFLOW.WORKFLOW_INSTANCE_COMPANY_MISMATCH, str(ctx.exception))

    def test_missing_target_record_fails_closed(self):
        env, _record, workflow_def = _env(company_id=7, exists=False)
        with self.assertRaises(UserError) as ctx:
            WORKFLOW.resolve_workflow_instance_company(
                env, "project.project", 11, workflow_def
            )
        self.assertIn(WORKFLOW.WORKFLOW_INSTANCE_TARGET_NOT_FOUND, str(ctx.exception))

    def test_empty_res_id_fails_closed(self):
        env, _record, workflow_def = _env(company_id=7)
        with self.assertRaises(UserError) as ctx:
            WORKFLOW.resolve_workflow_instance_company(
                env, "project.project", 0, workflow_def
            )
        self.assertIn(WORKFLOW.WORKFLOW_INSTANCE_TARGET_NOT_FOUND, str(ctx.exception))

    def test_unregistered_target_model_fails_closed(self):
        env, _record, workflow_def = _env(company_id=7)
        with self.assertRaises(UserError) as ctx:
            WORKFLOW.resolve_workflow_instance_company(
                env, "sc.not.installed", 11, workflow_def
            )
        self.assertIn(WORKFLOW.WORKFLOW_INSTANCE_UNATTRIBUTED_TARGET, str(ctx.exception))

    def test_blank_target_model_fails_closed(self):
        env, _record, workflow_def = _env(company_id=7)
        for value in (None, "", "   "):
            with self.subTest(model_name=value):
                with self.assertRaises(UserError) as ctx:
                    WORKFLOW.resolve_workflow_instance_company(
                        env, value, 11, workflow_def
                    )
                self.assertIn(
                    WORKFLOW.WORKFLOW_INSTANCE_UNATTRIBUTED_TARGET, str(ctx.exception)
                )

    def test_target_without_company_field_fails_closed(self):
        env, _record, workflow_def = _env(company_id=7, has_company_field=False)
        with self.assertRaises(UserError) as ctx:
            WORKFLOW.resolve_workflow_instance_company(
                env, "project.project", 11, workflow_def
            )
        self.assertIn(WORKFLOW.WORKFLOW_INSTANCE_UNATTRIBUTED_TARGET, str(ctx.exception))

    def test_target_without_owning_company_fails_closed(self):
        env, _record, workflow_def = _env(company_id=False)
        with self.assertRaises(UserError) as ctx:
            WORKFLOW.resolve_workflow_instance_company(
                env, "project.project", 11, workflow_def
            )
        self.assertIn(WORKFLOW.WORKFLOW_INSTANCE_UNATTRIBUTED_TARGET, str(ctx.exception))

    def test_anchor_is_read_through_sudo(self):
        env, record, workflow_def = _env(company_id=7, def_company=7)
        WORKFLOW.resolve_workflow_instance_company(
            env, "project.project", 11, workflow_def
        )
        self.assertEqual(record.sudo_calls, 1)


class WorkflowInstanceOwnershipSourceTests(unittest.TestCase):
    def setUp(self):
        self.source = MODULE_PATH.read_text(encoding="utf-8")

    def test_create_instance_delegates_to_the_resolver(self):
        body = self.source.split("def create_instance(", 1)[1].split("def action_submit(", 1)[0]
        self.assertIn("resolve_workflow_instance_company(", body)
        self.assertNotIn("env.company", body)
        self.assertNotIn("workflow_def.company_id", body)

    def test_resolver_never_reads_the_callers_environment_company(self):
        body = self.source.split("def resolve_workflow_instance_company(", 1)[1].split(
            "class ScWorkflowDef", 1
        )[0]
        self.assertNotIn("env.company", body)
        self.assertIn("WORKFLOW_INSTANCE_COMPANY_MISMATCH", body)

    def test_instance_company_is_a_fail_closed_declaration(self):
        self.assertIn("def _check_company_attribution(", self.source)
        self.assertIn('@api.constrains("company_id")', self.source)
        self.assertIn("归属公司：由业务单据继承，不从流程模板或当前环境推断。", self.source)

    def test_instance_company_field_carries_no_default(self):
        """A field default would be a second ownership source.

        ``create_instance`` resolves the company from the target document, so the
        instance field itself must not fall back to the caller's environment; the
        constraint is the only thing allowed to decide a missing company.
        """
        body = self.source.split("class ScWorkflowInstance(", 1)[1].split(
            "class ScWorkflowWorkitem(", 1
        )[0]
        declaration = body.split("company_id = fields.Many2one(", 1)[1].split(")", 1)[0]
        self.assertNotIn("default=", declaration)


if __name__ == "__main__":
    unittest.main()
