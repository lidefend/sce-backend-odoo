# -*- coding: utf-8 -*-
from unittest.mock import patch

from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase, tagged

from ..tools import scenario_loader


@tagged("post_install", "-at_install", "-standard", "demo_loaded_chains")
class TestDemoLoadedChains(TransactionCase):
    def test_loaded_rental_and_invoice_keep_native_financial_sources(self):
        checker = self.env.ref('smart_construction_demo.user_sc_rental_payment_checker_demo')
        material = self.env.ref('smart_construction_demo.user_sc_material_01')
        for forbidden in ('group_sc_business_full', 'group_sc_cap_business_config_admin', 'group_sc_cap_config_admin'):
            self.assertFalse(checker.has_group('smart_construction_core.' + forbidden))
        settlement = self.env.ref('smart_construction_demo.sc_demo_material_rental_settlement_086_scaffold')
        self.assertEqual(settlement.state, 'paid')
        self.assertEqual(settlement.write_uid, checker)
        self.assertAlmostEqual(settlement.payment_paid_amount, settlement.amount_total)
        self.assertTrue(settlement.payment_request_ids)
        self.assertFalse(settlement.with_user(checker).sudo(False)._payment_confirmation_blocker())
        contract = settlement.contract_id
        self.assertTrue(contract)
        self.assertTrue(contract.with_user(checker).sudo(False).search_count([('id', '=', contract.id)]))
        with self.assertRaises(AccessError):
            contract.with_user(material).sudo(False).check_access_rights('read')
        for suffix in ('out', 'return'):
            guarantee = self.env.ref('smart_construction_demo.sc_demo_tender_guarantee_086_' + suffix)
            self.assertEqual(guarantee.state, 'confirmed')
            ledger = guarantee.treasury_ledger_id
            self.assertEqual(ledger.state, 'posted')
            self.assertEqual(ledger.source_model, guarantee._name)
            self.assertEqual(ledger.source_res_id, guarantee.id)
            self.assertAlmostEqual(ledger.amount, guarantee.amount)
        invoice = self.env.ref('smart_construction_demo.sc_demo_invoice_registration_088_output')
        self.assertEqual(invoice.source_origin, 'manual')
        self.assertEqual(invoice.state, 'registered')
        self.assertFalse(invoice.legacy_source_model or invoice.legacy_source_table or invoice.legacy_record_id)
        adjustment = self.env.ref('smart_construction_demo.sc_demo_output_invoice_adjustment_088_red_flush')
        self.assertEqual(adjustment.state, 'draft')
        self.assertEqual(adjustment.original_ledger_id.source_model, invoice._name)
        self.assertEqual(adjustment.original_ledger_id.source_record_id, invoice.id)

    def test_loaded_issue_chains_keep_native_role_and_audit_sources(self):
        import ast
        from lxml import etree
        from odoo.tools.misc import file_path

        author = self.env.ref('smart_construction_demo.user_sc_project_user')
        checker = self.env.ref('smart_construction_demo.user_sc_project_manager_cap')
        for relative in (
            's80_execution_management_surface/10_execution_management_records.xml',
            's89_quality_safety_surface/10_quality_safety_records.xml',
        ):
            tree = etree.parse(file_path('smart_construction_demo/data/scenario/' + relative))
            for call in tree.xpath('//function[@name="sc_demo_close_issue"]'):
                args = [ast.literal_eval(v.get('eval')) for v in list(call)[1:]]
                issue = self.env.ref(args[0])
                rectification = self.env.ref('smart_construction_demo.' + args[1])
                recheck = self.env.ref('smart_construction_demo.' + args[3])
                self.assertEqual(issue.state, 'closed')
                self.assertEqual(rectification.issue_id, issue)
                self.assertEqual(rectification.create_uid, author)
                self.assertEqual(rectification.handler_id, author)
                self.assertEqual(recheck.issue_id, issue)
                self.assertEqual(recheck.create_uid, checker)
                self.assertEqual(recheck.recheck_user_id, checker)
                self.assertEqual(recheck.result, 'passed')
                kind = issue._name.split('.')[1]
                for event, actor in ((kind + '_issue_submitted', author),
                                     (kind + '_recheck_requested', author),
                                     (kind + '_issue_closed', checker)):
                    logs = self.env['sc.audit.log'].search([
                        ('model', '=', issue._name), ('res_id', '=', issue.id),
                        ('event_code', '=', event),
                    ])
                    self.assertEqual(len(logs), 1)
                    self.assertEqual(logs.actor_uid, actor)
                before = (issue.rectification_ids.ids, issue.recheck_ids.ids)
                self.assertTrue(issue.sc_demo_close_issue(*args))
                self.assertEqual(before, (issue.rectification_ids.ids, issue.recheck_ids.ids))
                with self.assertRaises(AccessError):
                    issue.with_user(author).sudo(False).sc_demo_close_issue(*args)
                bad = list(args)
                bad[2] = dict(args[2], result='conflicting replay')
                with self.assertRaises(ValueError):
                    issue.sc_demo_close_issue(*bad)

    def test_loaded_payment_and_receipt_chains_retain_real_sources(self):
        from ..seed.steps.step_40_contracts_demo import _ensure_purchase_order

        settlement = self.env.ref("smart_construction_demo.sc_demo_settlement_069_payment")
        product = self.env.ref("smart_construction_demo.sc_demo_product_069_steel_batch")
        purchase = settlement.purchase_order_ids
        self.assertEqual(len(purchase), 1)
        self.assertIn(purchase.state, ("purchase", "done"))
        self.assertEqual(purchase.project_id, settlement.project_id)
        self.assertEqual(purchase.company_id, settlement.company_id)
        self.assertEqual(purchase.order_line.mapped("product_id"), product)
        self.assertIn(settlement.state, ("approve", "done"))
        request = self.env.ref("smart_construction_demo.sc_demo_payment_request_069_pay")
        ledger = self.env["payment.ledger"].search([
            ("payment_request_id", "=", request.id), ("state", "=", "posted"),
        ])
        self.assertEqual(len(ledger), 1)
        self.assertAlmostEqual(ledger.amount, 120000)
        self.assertEqual(ledger.payment_execution_id.state, "paid")
        self.assertEqual(ledger.payment_execution_id.payment_request_id, request)
        actor = self.env.ref("smart_construction_demo.user_sc_settlement_user_cap")
        author = settlement.with_user(actor).sudo(False)
        self.assertEqual(_ensure_purchase_order(self.env, author, product=product), purchase)
        wrong_product = self.env.ref("smart_construction_demo.sc_demo_product_065_rebar")
        with self.assertRaises(UserError):
            _ensure_purchase_order(self.env, author, product=wrong_product)
        self.assertEqual(purchase.order_line.mapped("product_id"), product)

        receipt = self.env.ref("smart_construction_demo.sc_demo_receipt_income_070_progress")
        reconciliation = self.env.ref("smart_construction_demo.sc_demo_treasury_reconciliation_070_daily")
        treasury = receipt.treasury_ledger_id
        self.assertEqual(receipt.state, "received")
        self.assertEqual(treasury.state, "posted")
        self.assertEqual(treasury.direction, "in")
        self.assertAlmostEqual(treasury.amount, 1200000)
        self.assertEqual(treasury.payment_request_id, receipt.payment_request_id)
        self.assertEqual(reconciliation.treasury_ledger_id, treasury)
        self.assertEqual(reconciliation.state, "confirmed")
        original = self.env.ref("smart_construction_demo.sc_demo_pay_req_010_001")
        self.assertEqual(original.state, "draft")
        self.assertAlmostEqual(original.amount, 5000000)

    def test_guidance_fixture_confirms_new_contract_and_reuses_native_soft_warning(self):
        from lxml import etree
        from odoo.tools.misc import file_path
        from ..seed.steps.step_payment_request_floorplan_demo import _guidance_fixture

        # Verify persisted actors; this test must not install missing declarations.
        for xmlid in ("user_sc_accounting_manager_demo", "user_sc_business_config_demo", "user_sc_operation_demo"):
            actor = self.env.ref("smart_construction_demo." + xmlid)
            self.assertTrue(actor.active)
            self.assertNotEqual(actor.id, 1)
            self.assertIn(self.env.ref("base.main_company").id,
                          actor.with_user(actor).sudo(False)._sc_data_company_ids())
        # Require the actual runtime declaration; never repair rules in a test.
        rules = etree.parse(file_path("smart_construction_core/security/sc_data_scope_ceiling_generated.xml"))
        rule = rules.xpath("//record[@id='rule_sc_data_scope_sc_business_category']")
        self.assertEqual(len(rule), 1)
        declared_domain = rule[0].find("field[@name='domain_force']").text.strip()
        self.assertEqual(self.env.ref("smart_construction_core.rule_sc_data_scope_sc_business_category").domain_force.strip(), declared_domain)
        # Force the first-create path without deleting pre-existing business records.
        # External-id changes and new records are all rolled back by TransactionCase.
        self.env["ir.model.data"].search([
            ("module", "=", "smart_construction_demo"),
            ("name", "in", ["payment_guidance_demo_partner", "payment_guidance_demo_contract",
                              "payment_guidance_demo_record"]),
        ]).unlink()
        result = _guidance_fixture(self.env)
        contract = self.env["construction.contract"].browse(result["contract_id"])
        payment = self.env["payment.request"].browse(result["payment_request_id"])
        self.assertEqual(contract.state, "confirmed")
        self.assertEqual(contract.create_uid, self.env.ref("smart_construction_demo.user_sc_contract_manager_cap"))
        self.assertEqual(payment.create_uid, self.env.ref("smart_construction_demo.user_demo_role_project_a_member"))
        self.assertEqual(payment.state, "draft")
        self.assertFalse(result["guidance"]["blocking"])
        self.assertTrue(result["guidance"]["requires_confirmation"])
        again = _guidance_fixture(self.env)
        for key in ("payment_request_id", "partner_id", "contract_id"):
            self.assertEqual(again[key], result[key])


@tagged("post_install", "-at_install", "demo_action_roles")
class TestDemoActionRoles(TransactionCase):
    def test_manual_boq_analysis_generates_native_cost_plan_as_cost_manager(self):
        from ..seed.business_roles import business_model, ensure_manual_boq_analysis
        from ..seed.steps.step_50_boq_wbs_demo import _ensure_cost_plan

        actor = self.env.ref("smart_construction_demo.user_sc_cost_manager_cap")
        project = self.env["project.project"].create({
            "name": "Demo manual analysis transaction fixture", "user_id": actor.id,
            "company_id": actor.company_id.id,
        })
        version = business_model(self.env, "project.boq.version").create({
            "name": "Manual analysis", "code": "TEST-MANUAL-BOQ", "project_id": project.id,
            "source_type": "contract",
        })
        line = business_model(self.env, "project.boq.line").create({
            "name": "Manual material", "code": "TEST-MATERIAL", "project_id": project.id,
            "version_id": version.id, "line_type": "item", "quantity": 10,
            "price": 120, "uom_id": self.env.ref("uom.product_uom_unit").id,
            "section_type": "building",
        })
        analysis = ensure_manual_boq_analysis(self.env, line, 120)
        version.action_validate()
        version.action_publish()
        _ensure_cost_plan(self.env, project)
        plan = business_model(self.env, "project.cost.plan").search([
            ("project_id", "=", project.id), ("version_code", "=", "DEMO-TARGET-V1"),
        ])
        self.assertEqual(len(plan), 1)
        for record in (version, analysis, plan, plan.line_ids):
            self.assertFalse(record.env.su)
            self.assertEqual(record.mapped("create_uid"), actor)
        self.assertEqual(plan.line_ids.mapped("analysis_id"), analysis)
        self.assertAlmostEqual(plan.budget_amount, 1200)
        self.assertTrue(plan.node_ids)
        self.assertFalse(line.import_batch_id)
        ids = plan.line_ids.ids
        _ensure_cost_plan(self.env, project)
        self.assertEqual(plan.line_ids.ids, ids)

    def test_wbs_normal_create_owns_plan_and_replay_respects_published_guard(self):
        from ..seed.steps.step_50_boq_wbs_demo import _ensure_wbs

        actor = self.env.ref("smart_construction_demo.user_sc_project_manager_cap")
        project = self.env["project.project"].create({
            "name": "Demo WBS transaction fixture", "user_id": actor.id,
            "company_id": actor.company_id.id,
        })
        node = _ensure_wbs(self.env, project, "TEST-WBS", "Test phase", "phase")
        self.assertEqual(node.create_uid, actor)
        self.assertFalse(node.env.su)
        self.assertTrue(node.plan_id)
        node.plan_id.action_validate_plan()
        node.plan_id.action_publish_plan()
        self.assertEqual(node.plan_id.state, "published")
        again = _ensure_wbs(self.env, project, "TEST-WBS", "Test phase", "phase")
        self.assertEqual(again.id, node.id)
        with self.assertRaises(UserError):
            _ensure_wbs(self.env, project, "TEST-WBS", "Changed phase", "phase")
        self.assertEqual(node.name, "Test phase")
        self.assertEqual(node.plan_id.node_ids, node)

    def test_material_demo_chain_generates_real_cost_without_superuser(self):
        manager = self.env.ref("smart_construction_demo.user_sc_material_mgr_01")
        project = self.env["project.project"].create({
            "name": "Demo action role transaction fixture", "user_id": manager.id,
            "company_id": manager.company_id.id,
        })
        product = self.env["product.product"].create({"name": "Demo action role material"})
        acting = scenario_loader._demo_action_record(
            self.env, self.env["sc.material.outbound"], "action_issue"
        )
        self.assertEqual(acting.env.uid, manager.id)
        self.assertFalse(acting.env.su)
        outbound = acting.create({
            "project_id": project.id,
            "line_ids": [(0, 0, {"product_id": product.id,
                                  "product_uom_id": product.uom_id.id,
                                  "qty": 2, "unit_price": 30})],
        })
        self.env["ir.model.data"].create({
            "module": "smart_construction_demo", "name": "test_role_outbound",
            "model": outbound._name, "res_id": outbound.id,
        })
        with patch.dict(scenario_loader._DEMO_LIFECYCLE_TARGETS, {
            "test_role": {"test_role_outbound": "issued"},
        }):
            scenario_loader._advance_scenario_lifecycle(self.env, "test_role")
        outbound.invalidate_recordset()
        self.assertEqual(outbound.state, "issued")
        ledger = self.env["project.cost.ledger"].search([
            ("source_model", "=", outbound._name), ("source_id", "=", outbound.id),
        ])
        self.assertEqual(len(ledger), 1)
        self.assertEqual(ledger.source_line_id, outbound.line_ids.id)
        self.assertAlmostEqual(ledger.source_amount, 60)

    def test_native_boq_import_creates_consistent_snapshot_and_reuses_result(self):
        import hashlib
        from pathlib import Path
        from odoo.tools.misc import file_path

        actor = self.env.ref("smart_construction_demo.user_sc_cost_01")
        project = self.env["project.project"].create({
            "name": "Demo native BOQ import transaction fixture", "user_id": actor.id,
            "company_id": actor.company_id.id,
        })
        version, batch = scenario_loader._import_demo_boq(self.env, project)
        raw = Path(file_path("smart_construction_demo/data/scenario/s00_min_path/contract_boq.csv")).read_bytes()
        self.assertEqual(batch.file_digest, hashlib.sha256(raw).hexdigest())
        self.assertEqual(batch.imported_by, actor)
        self.assertEqual(batch.state, "imported")
        self.assertEqual(batch.version_id, version)
        self.assertEqual(batch.project_id, project)
        self.assertEqual(batch.item_count, 2)
        self.assertIsInstance(batch.preview_payload, dict)
        self.assertEqual(batch.preview_payload["schema"], "sc.boq.import.preview.v1")
        self.assertAlmostEqual(batch.preview_payload["amount"], 762000)
        items = version.line_ids.filtered(lambda line: line.line_type == "item")
        self.assertEqual(len(items), 2)
        self.assertEqual(items.mapped("import_batch_id"), batch)
        self.assertEqual(set(items.mapped("code")), {"010101", "020202"})
        again_version, again_batch = scenario_loader._import_demo_boq(self.env, project)
        self.assertEqual((again_version.id, again_batch.id), (version.id, batch.id))

    def test_public_seed_wrappers_refuse_unprivileged_callers_before_side_effects(self):
        actor = self.env.ref("smart_construction_demo.user_sc_cost_01")
        from ..models import boq_demo_seed
        for model, method in (
            ("project.project", "sc_demo_import_boq"),
            ("project.funding.baseline", "sc_demo_activate"),
            ("payment.request", "sc_demo_drive_approval"),
            ("project.project", "sc_demo_seed_cockpit_round2"),
        ):
            with self.subTest(model=model), patch.object(boq_demo_seed, "guard_demo_data_space") as onboarding:
                with self.assertRaisesRegex(AccessError, "DEMO_SEED_PRINCIPAL_REQUIRED"):
                    getattr(self.env[model].with_user(actor).sudo(False), method)()
                onboarding.assert_not_called()

    def test_cockpit_manual_costs_are_created_by_real_cost_operator(self):
        actor = self.env.ref("smart_construction_demo.user_sc_cost_01")
        project = self.env["project.project"].create({
            "name": "Demo cockpit manual cost transaction fixture", "user_id": actor.id,
            "company_id": actor.company_id.id,
        })
        cost_code = self.env.ref("smart_construction_demo.sc_cost_code_root_material")
        partner = self.env.ref("smart_construction_demo.sc_demo_partner_vendor_steel")
        model = self.env["project.cost.ledger"].with_user(actor).sudo(False)
        self.env["project.project"]._sc_demo_seed_cost_ledger(project, partner, cost_code, model)
        rows = model.search([("project_id", "=", project.id)])
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows.mapped("create_uid"), actor)
        self.assertFalse(any(rows.mapped("source_model")))
        self.env["project.project"]._sc_demo_seed_cost_ledger(project, partner, cost_code, model)
        self.assertEqual(model.search_count([("project_id", "=", project.id)]), 4)

    def test_explicit_root_actor_is_rejected_before_action(self):
        with self.assertRaisesRegex(ValueError, "active non-superuser"):
            scenario_loader._demo_action_record(
                self.env, self.env["sc.material.outbound"], "action_issue", "base.user_root"
            )
