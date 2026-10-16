"""Explicit synthetic customer-space fixture for industry workflow tests.

This opt-in base leaves the platform bootstrap company and all production
rules intact. Each test class owns a new registered company; no customer rows
are imported and TransactionCase rolls back the complete fixture.
"""
import os
import secrets
from unittest.mock import patch

from odoo import SUPERUSER_ID, api
from odoo.tests.common import TransactionCase


class BusinessTransactionCase(TransactionCase):
    approval_models = ()
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        company = cls.env["res.company"].create({"name": "Synthetic " + cls.__name__})
        cls.register_business_company(company)
        cls.env = api.Environment(cls.env.cr, cls.env.uid,
                                  dict(cls.env.context, allowed_company_ids=company.ids),
                                  su=cls.env.su)
        for model in cls.approval_models:
            cls.env["sc.approval.policy"].create({
                "name": "Synthetic approval " + model,
                "code": "synthetic_" + str(company.id) + "_" + model,
                "target_model": model, "company_id": company.id,
                "approval_required": True, "mode": "single",
                "manager_scope_key": "executive",
                "step_ids": [(0, 0, {"name": "Synthetic approval step", "approval_scope_key": "executive",
                                      "approve_group_id": cls.env.ref("smart_construction_core.group_sc_role_executive").id})],
            })

    @classmethod
    def register_business_company(cls, company, *, tenant_key="synthetic-workflow-tests"):
        """Explicit test-only customer registration; never auto-enroll searches."""
        capability = secrets.token_hex(32)
        registration = company.env["sc.tenant.company.registration"].with_user(SUPERUSER_ID).with_context(
            sc_tenant_payload_import=True, sc_tenant_payload_maintenance_capability=capability)
        with patch.dict(os.environ, {"SC_TENANT_PAYLOAD_MAINTENANCE_CAPABILITY": capability}):
            return registration.create({
                "tenant_key": tenant_key,
                "company_id": company.id,
                "source_module": "synthetic_workflow_test",
                "source_external_key": str(company.id),
            })
