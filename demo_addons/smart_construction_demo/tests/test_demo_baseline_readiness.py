# -*- coding: utf-8 -*-
"""Read-only demo baseline readiness probe for G0-G4 (runtime readback).

This test never writes. It probes presence facts declared by
``scripts/verify/baseline_readiness_manifest.json`` for the main company and
the primary execution project (``DEMO-PJ-EXEC``) and fails closed when any
hard G0-G4 requirement is absent.

``HARD_KEYS`` must stay in sync with the manifest; the offline guard
``scripts/verify/test_baseline_readiness_verifier.py`` enforces that parity.
"""
from __future__ import annotations

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged

from ..hooks import demo_admin_record


HARD_KEYS = frozenset([
    # G0 tenant_and_company
    "company_identity",
    "company_currency",
    "accounting_year_chart",
    "data_space_scope",
    "admin_separation",
    # G1 organization_and_identity
    "department_tree",
    "job_positions",
    "employee_records",
    "business_users_roles",
    "approval_positions",
    "project_role_owners",
    # G2 business_master_data (hard only)
    "partners",
    "taxes_units_payment_terms",
    "project_dictionaries",
    "cost_structure_templates",
    # G3 governance_and_runtime_config (hard only)
    "approval_policy",
    "numbering_rules",
    "data_permissions",
    # G4 project_baseline
    "project_basic",
    "project_parties",
    "project_membership_scope",
    "funding_baseline",
    "budget_boq_wbs",
    "settlement_anchor",
])


@tagged("post_install", "-at_install", "-standard", "demo_baseline_readiness")
class TestDemoBaselineReadiness(TransactionCase):
    def _company(self):
        return self.env.ref("base.main_company")

    def _exec_project(self):
        return (
            self.env["project.project"]
            .sudo()
            .search([("project_code", "=", "DEMO-PJ-EXEC")], limit=1)
        )

    def _admin_separation(self, company) -> bool:
        admin = demo_admin_record(self.env)
        full_group = self.env.ref(
            "smart_construction_core.group_sc_business_full", raise_if_not_found=False
        )
        principal = (
            self.env["res.users"].sudo().search([("login", "=", "wutao")], limit=1)
        )
        return bool(
            admin
            and principal
            and admin.id != principal.id
            and full_group
            and full_group in principal.groups_id
        )

    def _probes(self) -> dict[str, bool]:
        env = self.env
        company = self._company()
        project = self._exec_project()
        return {
            "company_identity": bool(company.name)
            and bool(company.partner_id)
            and company.partner_id.name == company.name,
            "company_currency": bool(company.currency_id)
            and company.currency_id.name == "CNY",
            "accounting_year_chart": env["account.account"]
            .sudo()
            .search_count([("company_id", "=", company.id)])
            > 0,
            "data_space_scope": env["sc.tenant.company.registration"]
            .sudo()
            .search_count(
                [
                    ("company_id", "=", company.id),
                    ("data_purpose", "=", "demo"),
                    ("active", "=", True),
                ]
            )
            >= 1,
            "admin_separation": self._admin_separation(company),
            "department_tree": env["hr.department"]
            .sudo()
            .search_count([("company_id", "=", company.id)])
            > 0,
            "job_positions": env["hr.job"]
            .sudo()
            .search_count([("company_id", "=", company.id)])
            > 0,
            "employee_records": env["hr.employee"]
            .sudo()
            .search_count([("company_id", "=", company.id)])
            > 0,
            "business_users_roles": env["res.users"]
            .sudo()
            .search_count([("share", "=", False), ("active", "=", True)])
            >= 5,
            "approval_positions": env["sc.approval.policy"].sudo().search_count([]) > 0
            and env["sc.approval.step"].sudo().search_count([]) > 0,
            "project_role_owners": bool(project)
            and bool(project.manager_id)
            and bool(project.cost_manager_id)
            and bool(project.doc_manager_id),
            "partners": env["res.partner"]
            .sudo()
            .search_count(
                [("is_company", "=", True), ("id", "!=", company.partner_id.id)]
            )
            > 0,
            "partner_categories": env["sc.business.category"].sudo().search_count([]) > 0,
            "taxes_units_payment_terms": env["account.tax"]
            .sudo()
            .search_count([("company_id", "=", company.id)])
            > 0,
            "material_catalog": env["sc.material.catalog"].sudo().search_count([]) > 0,
            "project_dictionaries": env["sc.dictionary"].sudo().search_count([]) > 0
            and env["project.dictionary"].sudo().search_count([]) > 0,
            "cost_structure_templates": env["project.cost.code"]
            .sudo()
            .search_count([])
            > 0,
            "approval_policy": env["sc.approval.policy"].sudo().search_count([]) > 0,
            "numbering_rules": env["ir.sequence"].sudo().search_count([]) > 0,
            "menus_actions_capabilities": env["sc.scene"].sudo().search_count([]) > 0,
            "view_policies": env["ir.ui.view"]
            .sudo()
            .search_count([("model", "=", "project.project"), ("type", "=", "form")])
            > 0,
            "data_permissions": env["ir.rule"].sudo().search_count([]) > 0,
            "project_basic": bool(project)
            and bool(project.stage_id)
            and bool(project.company_id),
            "project_parties": bool(project)
            and bool(project.partner_id)
            and bool(project.manager_id),
            "project_membership_scope": bool(project)
            and env["project.task"]
            .sudo()
            .search_count(
                [("project_id", "=", project.id), ("user_ids", "!=", False)]
            )
            > 0,
            "funding_baseline": bool(project)
            and env["project.funding.baseline"]
            .sudo()
            .search_count([("project_id", "=", project.id), ("state", "=", "active")])
            > 0,
            "budget_boq_wbs": bool(project)
            and env["project.budget"]
            .sudo()
            .search_count([("project_id", "=", project.id)])
            > 0
            and env["project.boq.line"]
            .sudo()
            .search_count([("project_id", "=", project.id)])
            > 0
            and env["construction.work.breakdown"]
            .sudo()
            .search_count([("project_id", "=", project.id)])
            > 0,
            "settlement_anchor": bool(project)
            and (
                env["construction.contract"]
                .sudo()
                .search_count([("project_id", "=", project.id)])
                > 0
                or env["tender.bid"]
                .sudo()
                .search_count([("project_id", "=", project.id)])
                > 0
            ),
        }

    def test_g0_g4_hard_baseline_ready(self):
        probes = self._probes()
        missing = sorted(key for key in HARD_KEYS if not probes.get(key))
        if missing:
            raise UserError(
                "Demo baseline readiness missing (G0-G4 hard): %s" % ", ".join(missing)
            )
