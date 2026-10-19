# -*- coding: utf-8 -*-
"""Hermetic guard: demo funding baselines must respect the controlled lifecycle.

project.funding.baseline.create() rejects non-draft states (and requires
period_start/period_end), so scenario XML must only create drafts with
planning lines whose planned_amount sums equal total_amount; activation is
delegated to scenario_loader._ensure_funding_baseline -> action_activate().

This test parses the scenario XML statically (no Odoo runtime) and pins the
loader wiring, so a fresh-install demo.load.release cannot regress into the
UserError("资金基线必须先创建为草稿...") path.
"""

import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

DEMO_ROOT = Path(__file__).resolve().parents[1]

SCENARIO_FILES = [
    DEMO_ROOT
    / "data/scenario/s65_cost_budget_funding_surface/10_cost_budget_funding_records.xml",
    DEMO_ROOT
    / "data/scenario/s69_payment_ledger_surface/10_payment_ledger_records.xml",
]

LOADER_PATH = DEMO_ROOT / "tools" / "scenario_loader.py"

BASELINE_MODEL = "project.funding.baseline"
LINE_MODEL = "project.funding.baseline.line"

_MODULE_PREFIX = "smart_construction_demo."


def _field_text(record, name):
    for field in record.findall("field"):
        if field.get("name") == name:
            return (field.text or "").strip()
    return None


def _records(root, model):
    return [
        record
        for record in root.iter("record")
        if record.get("model") == model
    ]


class TestDemoFundingBaselineLifecycle(unittest.TestCase):
    def test_supplemental_seeds_share_declared_review_driver(self):
        source = (DEMO_ROOT / "seed/tier_flow.py").read_text()
        self.assertIn("_demo_finish_reviews(record.env, record)", source)
        self.assertNotIn("candidates[0]", source)
        self.assertNotIn("fallback_xmlid", source)
        for path in (DEMO_ROOT / "seed").rglob("*.py"):
            with self.subTest(path=str(path.relative_to(DEMO_ROOT))):
                self.assertNotRegex(path.read_text(), r"\.action_on_tier_approved\s*\(")

    def test_baseline_records_create_draft_with_periods(self):
        for path in SCENARIO_FILES:
            with self.subTest(file=path.name):
                root = ET.parse(path).getroot()
                baselines = _records(root, BASELINE_MODEL)
                self.assertTrue(
                    baselines, f"{path.name}: expected funding baseline records"
                )
                for record in baselines:
                    xmlid = record.get("id")
                    state = _field_text(record, "state")
                    self.assertIsNone(
                        state,
                        f"{path.name}#{xmlid}: scenario XML must not set state "
                        f"(got {state!r}); create() only accepts drafts and "
                        "activation belongs to _ensure_funding_baseline",
                    )
                    self.assertTrue(
                        _field_text(record, "period_start"),
                        f"{path.name}#{xmlid}: period_start is required by create()",
                    )
                    self.assertTrue(
                        _field_text(record, "period_end"),
                        f"{path.name}#{xmlid}: period_end is required by create()",
                    )

    def test_baseline_lines_sum_equals_total_amount(self):
        for path in SCENARIO_FILES:
            with self.subTest(file=path.name):
                root = ET.parse(path).getroot()
                totals = {}
                for record in _records(root, BASELINE_MODEL):
                    xmlid = record.get("id")
                    total = float(_field_text(record, "total_amount"))
                    totals[_MODULE_PREFIX + xmlid] = total
                line_sums = {}
                for record in _records(root, LINE_MODEL):
                    baseline_ref = None
                    for field in record.findall("field"):
                        if field.get("name") == "baseline_id":
                            baseline_ref = field.get("ref") or (field.text or "").strip()
                    self.assertTrue(
                        baseline_ref,
                        f"{path.name}#{record.get('id')}: line misses baseline_id",
                    )
                    amount = float(_field_text(record, "planned_amount"))
                    line_sums.setdefault(baseline_ref, 0.0)
                    line_sums[baseline_ref] += amount
                for xmlid, total in totals.items():
                    self.assertIn(
                        xmlid,
                        line_sums,
                        f"{path.name}#{xmlid}: baseline has no planning lines; "
                        "action_activate() requires at least one line",
                    )
                    self.assertAlmostEqual(
                        line_sums[xmlid],
                        total,
                        places=2,
                        msg=(
                            f"{path.name}#{xmlid}: planned line sum "
                            f"{line_sums[xmlid]} != total_amount {total}; "
                            "action_activate() enforces equality"
                        ),
                    )

    def test_scenario_loader_activates_demo_funding_baselines(self):
        source = LOADER_PATH.read_text(encoding="utf-8")
        self.assertIn(
            "def _ensure_funding_baseline(",
            source,
            "scenario_loader must keep the post-load activation helper",
        )
        for scenario in (
            "s65_cost_budget_funding_surface",
            "s69_payment_ledger_surface",
        ):
            self.assertIn(
                f'"{scenario}"',
                source,
                f"scenario_loader must wire activation for {scenario}",
            )
        for xmlid in (
            "sc_demo_funding_baseline_065",
            "sc_demo_funding_baseline_069_payment",
        ):
            self.assertIn(
                f'"{xmlid}"',
                source,
                f"scenario_loader must reference baseline {xmlid}",
            )
        self.assertRegex(
            source,
            re.escape("action_activate()"),
        )

    def test_cockpit_receipt_create_leaves_the_migration_carrier_authority(self):
        """New-system receipts use the declared operator, never a carrier."""
        source = (DEMO_ROOT / "models/project_demo_cockpit_seed.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('_demo_action_record(self.env, self.env["sc.receipt.income"], "action_confirm")', source)
        self.assertNotIn('"sc.receipt.income"].sudo()', source)
        self.assertNotIn("sc_receipt_fact_authority_token", source)
        self.assertIn("_demo_finish_reviews(self.env, receipt)", source)

    def test_finance_fact_records_pin_identity_state(self):
        """Carrier-context side effect guard.

        The scenario loader loads demo XML with the governed-migration carrier
        context (all authority sentinel tokens). In create() of
        sc.expense.claim / sc.receipt.income / sc.self.funding.registration /
        sc.tax.deduction.registration the authority token switches
        finance_identity_state from the field default to
        vals.get("finance_identity_state"), so a missing value becomes NULL
        and violates the NOT NULL constraint. Every demo record of these
        models must therefore pin the field explicitly.
        """
        affected_models = {
            "sc.expense.claim",
            "sc.receipt.income",
            "sc.self.funding.registration",
            "sc.tax.deduction.registration",
        }
        scenario_root = DEMO_ROOT / "data" / "scenario"
        for path in sorted(scenario_root.glob("*/*.xml")):
            root = ET.parse(path).getroot()
            for record in root.iter("record"):
                if record.get("model") not in affected_models:
                    continue
                xmlid = record.get("id")
                identity = _field_text(record, "finance_identity_state")
                self.assertEqual(
                    identity,
                    "normalized",
                    (
                        f"{path.name}#{xmlid}: {record.get('model')} records "
                        "must pin finance_identity_state=normalized; the "
                        "carrier context disables the create() default "
                        "backfill and a missing value fails NOT NULL"
                    ),
                )

    def test_s69_activates_baseline_mid_file_for_funding_gate(self):
        """S69 payment requests need the active baseline during XML load.

        The <function> activation tag must sit after the baseline lines and
        before any payment.request record in the same document.

        Odoo's convert._tag_function silently skips <function> tags inside
        noupdate data blocks when mode != 'init' (the scenario loader always
        loads with mode='update'), so the tag must live in its own
        <data noupdate="0"> block (precedent: s00/s80/s89).
        """
        path = DEMO_ROOT / (
            "data/scenario/s69_payment_ledger_surface/"
            "10_payment_ledger_records.xml"
        )
        source = path.read_text(encoding="utf-8")
        activate_pos = source.find("sc_demo_activate")
        self.assertGreater(
            activate_pos,
            0,
            "S69 XML must call sc_demo_activate mid-file (funding gate)",
        )
        self.assertGreater(
            activate_pos,
            source.find("sc_demo_funding_baseline_069_payment_line_material"),
            "activation must come after the planning lines are defined",
        )
        request_pos = source.find('model="payment.request"')
        self.assertGreater(
            request_pos,
            activate_pos,
            "activation must precede the payment.request record",
        )
        root = ET.parse(path).getroot()
        for data_block in root.findall("data"):
            for func in data_block.findall("function"):
                noupdate = data_block.get("noupdate", "0")
                self.assertEqual(
                    noupdate,
                    "0",
                    "<function> tags must sit in a noupdate=\"0\" data block; "
                    "Odoo convert silently skips functions inside noupdate "
                    "blocks when mode != 'init' (scenario loader uses "
                    "mode='update')",
                )

    def test_tender_guarantee_records_stay_draft_in_xml(self):
        """Absolute create() guard: tender.guarantee rejects confirmed at load.

        tender.guarantee.create() raises UserError("投标保证金不能直接创建为
        已确认...") for any non-draft state, with no carrier-token bypass, so
        scenario XML must load drafts and confirmation is delegated to
        scenario_loader._ensure_s86_tender_guarantee_lifecycle ->
        action_confirm() (which also seeds the treasury ledger).
        """
        scenario_root = DEMO_ROOT / "data" / "scenario"
        for path in sorted(scenario_root.glob("*/*.xml")):
            root = ET.parse(path).getroot()
            for record in root.iter("record"):
                if record.get("model") != "tender.guarantee":
                    continue
                xmlid = record.get("id")
                state = _field_text(record, "state")
                self.assertIsNone(
                    state,
                    (
                        f"{path.name}#{xmlid}: tender.guarantee records must "
                        "not set state (create() only accepts drafts; "
                        "confirmation belongs to "
                        "_ensure_s86_tender_guarantee_lifecycle)"
                    ),
                )
        source = LOADER_PATH.read_text(encoding="utf-8")
        self.assertIn(
            "def _ensure_s86_tender_guarantee_lifecycle(",
            source,
            "scenario_loader must keep the S86 guarantee confirm helper",
        )
        self.assertIn(
            '"s86_tender_rental_finance_surface"',
            source,
            "scenario_loader must wire guarantee confirmation for s86",
        )
        self.assertIn(
            "sc_demo_tender_guarantee_086_out",
            source,
            "scenario_loader must reference the S86 out guarantee",
        )


class TestDemoMaterialLifecycleUsesProductActions(unittest.TestCase):
    """S80 material facts advance through the product's own public actions.

    The demo seed used to reach the issued/confirmed states by writing the
    guarded cost-source state field directly under sudo, which skipped the
    material manager role check, the one-step approval handling, the quantity
    validation and the downstream effects (project cost ledger, transfer
    inbound, settlement downstream sync, audit trail). The states now belong to
    the generic governed chain in scenario_loader, so a fresh-install demo
    reaches them exactly the way an operator does.
    """

    S80_XML = (
        DEMO_ROOT
        / "data/scenario/s80_execution_management_surface/10_execution_management_records.xml"
    )
    GUARDED_RECORDS = {
        "sc_demo_material_outbound_080_steel": "sc.material.outbound",
        "sc_demo_material_settlement_080_steel": "sc.material.settlement",
    }

    def test_s80_material_xml_creates_legal_drafts(self):
        root = ET.parse(self.S80_XML).getroot()
        seen = set()
        for record in root.iter("record"):
            xmlid = record.get("id")
            if xmlid not in self.GUARDED_RECORDS:
                continue
            seen.add(xmlid)
            state = _field_text(record, "state")
            self.assertIsNone(
                state,
                (
                    f"{xmlid}: scenario XML must not set state (got {state!r}); "
                    "the record is created as a draft and advanced by the "
                    "governed action chain"
                ),
            )
        self.assertEqual(
            seen,
            set(self.GUARDED_RECORDS),
            "the guarded S80 material records must stay in the scenario XML",
        )

    def test_loader_declares_the_governed_action_chain(self):
        source = LOADER_PATH.read_text(encoding="utf-8")
        self.assertIn(
            '("sc.material.outbound", "issued"): ("action_issue",)',
            source,
            "sc.material.outbound must reach issued through action_issue()",
        )
        self.assertIn(
            '("sc.material.settlement", "confirmed"): ("action_confirm",)',
            source,
            "sc.material.settlement must reach confirmed through action_confirm()",
        )
        for xmlid in self.GUARDED_RECORDS:
            self.assertIn(
                f'"{xmlid}"',
                source,
                f"scenario_loader must declare the S80 target for {xmlid}",
            )

    def test_loader_never_writes_the_guarded_state_field(self):
        source = LOADER_PATH.read_text(encoding="utf-8")
        self.assertNotIn(
            "_write_cost_source_state",
            source,
            "the demo loader must not write the cost-source state field: "
            "terminal states belong to the models' public actions",
        )
        self.assertNotIn(
            "def _ensure_s80_material_lifecycle",
            source,
            "the direct-state helper must stay retired",
        )


class TestDemoActionIdentity(unittest.TestCase):
    """Execute the real resolver with identity-aware doubles, without Odoo."""

    def setUp(self):
        import ast
        from types import SimpleNamespace
        from unittest.mock import MagicMock
        tree = ast.parse(LOADER_PATH.read_text(encoding="utf-8"))
        selected = [node for node in tree.body if (
            isinstance(node, ast.FunctionDef) and node.name == "_demo_action_record"
        ) or (isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "_DEMO_LIFECYCLE_ACTION_ACTORS"
            for target in node.targets
        ))]
        scope = {}
        exec(compile(ast.Module(body=selected, type_ignores=[]), str(LOADER_PATH), "exec"), scope)
        self.resolve = scope["_demo_action_record"]
        self.env = MagicMock()
        self.actor = SimpleNamespace(id=52, active=True)
        self.env.ref.return_value = self.actor
        self.record = MagicMock()
        self.record._name = "sc.material.outbound"
        self.acting = self.record.with_user.return_value.sudo.return_value
        self.acting.env.su = False

    def test_declared_actor_clears_superuser_mode(self):
        result = self.resolve(self.env, self.record, "action_issue")
        self.env.ref.assert_called_once_with(
            "smart_construction_demo.user_sc_material_mgr_01", raise_if_not_found=False
        )
        self.record.with_user.assert_called_once_with(self.actor)
        self.record.with_user.return_value.sudo.assert_called_once_with(False)
        self.assertIs(result, self.acting)

    def test_unknown_action_never_uses_loader_authority(self):
        with self.assertRaisesRegex(ValueError, "declaration missing"):
            self.resolve(self.env, self.record, "action_unknown")
        self.record.with_user.assert_not_called()

    def test_missing_inactive_or_root_seat_is_refused(self):
        from types import SimpleNamespace
        for actor in (None, SimpleNamespace(id=52, active=False), SimpleNamespace(id=1, active=True)):
            with self.subTest(actor=actor):
                self.env.ref.return_value = actor
                with self.assertRaisesRegex(ValueError, "active non-superuser"):
                    self.resolve(self.env, self.record, "action_issue")
        self.record.with_user.assert_not_called()

    def test_uncleared_superuser_mode_is_refused(self):
        self.acting.env.su = True
        with self.assertRaisesRegex(ValueError, "superuser authority"):
            self.resolve(self.env, self.record, "action_issue")

    def test_explicit_seat_still_has_to_pass_identity_checks(self):
        self.actor.id = 1
        with self.assertRaisesRegex(ValueError, "active non-superuser"):
            self.resolve(self.env, self.record, "action_issue", "demo.explicit_actor")

    def test_demo_loader_imports_no_product_authority_tokens(self):
        import ast
        tree = ast.parse(LOADER_PATH.read_text(encoding="utf-8"))
        imports = [alias.name for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
                   for alias in node.names]
        self.assertFalse([name for name in imports if "TOKEN" in name.upper()])


class TestDemoReviewExecution(unittest.TestCase):
    def setUp(self):
        import ast
        from unittest.mock import MagicMock
        tree = ast.parse(LOADER_PATH.read_text(encoding="utf-8"))
        method = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                      and n.name == "_demo_finish_reviews")
        self.actor_record = MagicMock()
        self.resolve = MagicMock(return_value=self.actor_record)
        namespace = {
            "_demo_action_record": self.resolve,
            "_DEMO_APPROVAL_ACTORS": {"demo.reviewer_group": "demo.reviewer"},
        }
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(LOADER_PATH), "exec"), namespace)
        self.finish = namespace["_demo_finish_reviews"]
        self.record = MagicMock()
        self.record._fields = {"validation_status": object()}
        self.record._name = "sc.settlement.order"
        self.record.validation_status = "pending"
        pending = self.record.review_ids.filtered.return_value.sorted.return_value.__getitem__.return_value
        pending.reviewer_group_id.id = 7
        pending.reviewer_group_id.get_external_id.return_value = {7: "demo.reviewer_group"}
        self.actor_record.can_review = True
        self.actor_record.validate_tier.side_effect = lambda: setattr(self.record, "validation_status", "validated")

    def test_pending_instance_uses_real_reviewer_public_action(self):
        env = object()
        self.finish(env, self.record)
        self.resolve.assert_called_once_with(env, self.record, "validate_tier", "demo.reviewer")
        self.actor_record.validate_tier.assert_called_once()

    def test_non_reviewer_cannot_advance(self):
        self.actor_record.can_review = False
        with self.assertRaisesRegex(ValueError, "cannot review"):
            self.finish(object(), self.record)
        self.actor_record.validate_tier.assert_not_called()

    def test_completed_review_does_not_replay(self):
        self.record.validation_status = "validated"
        self.finish(object(), self.record)
        self.resolve.assert_not_called()

    def test_no_progress_cannot_be_reported_complete(self):
        self.actor_record.validate_tier.side_effect = None
        with self.assertRaisesRegex(ValueError, "did not converge"):
            self.finish(object(), self.record)

    def test_approval_driver_cannot_change_project_membership(self):
        import ast
        tree = ast.parse(LOADER_PATH.read_text(encoding="utf-8"))
        methods = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                   and node.name in ("_demo_drive_approval", "_demo_finish_reviews")]
        self.assertEqual(len(methods), 2)
        for method in methods:
            for node in ast.walk(method):
                if isinstance(node, ast.Call):
                    name = getattr(node.func, "id", getattr(node.func, "attr", ""))
                    self.assertNotIn(name, ("message_subscribe", "_demo_project_members", "_demo_scope_record_actors_to_project"))


class TestDemoDerivedFacts(unittest.TestCase):
    def test_s65_s70_do_not_create_derived_ledgers(self):
        for scenario in ("s65_cost_budget_funding_surface", "s70_daily_business_surface"):
            for path in (DEMO_ROOT / "data/scenario" / scenario).glob("*.xml"):
                for record in ET.parse(path).iter("record"):
                    self.assertNotIn(record.get("model"), ("project.cost.ledger", "sc.treasury.ledger"))

    def test_tax_deduction_uses_draft_and_declared_public_chain(self):
        import ast
        path = DEMO_ROOT / "data/scenario/s70_daily_business_surface/10_daily_business_records.xml"
        record = next(r for r in ET.parse(path).iter("record") if r.get("id") == "sc_demo_tax_deduction_070_input")
        self.assertIn(_field_text(record, "state"), (None, "draft"))
        tree = ast.parse(LOADER_PATH.read_text(encoding="utf-8"))
        declaration = next(n for n in tree.body if isinstance(n, ast.Assign)
                           and any(getattr(t, "id", None) == "_DEMO_LIFECYCLE_CHAINS" for t in n.targets))
        self.assertEqual(ast.literal_eval(declaration.value)[("sc.tax.deduction.registration", "deducted")],
                         ("action_confirm", "action_deduct"))

    def test_every_registered_scenario_is_a_release_seed(self):
        import ast
        declarations = {}
        for node in ast.parse(LOADER_PATH.read_text(encoding="utf-8")).body:
            if isinstance(node, ast.AnnAssign) and getattr(node.target, "id", None) in ("SCENARIOS", "RELEASE_SCENARIOS"):
                declarations[node.target.id] = ast.literal_eval(node.value)
        # The demo is a tenant's full-system sample: every registered surface
        # must be seeded by the release path. A scenario may only leave the
        # release set by being removed from the registry as well.
        self.assertEqual(
            set(declarations["RELEASE_SCENARIOS"]),
            set(declarations["SCENARIOS"]),
            "release seeds must cover every registered scenario",
        )

    def test_release_seeds_do_not_handwrite_business_terminal_states(self):
        import ast
        declarations = {}
        for node in ast.parse(LOADER_PATH.read_text(encoding="utf-8")).body:
            if isinstance(node, ast.AnnAssign) and getattr(node.target, "id", None) in ("SCENARIOS", "RELEASE_SCENARIOS"):
                declarations[node.target.id] = ast.literal_eval(node.value)
        # These are ordinary editable metadata in the native models, not
        # snapshots of a protected workflow or a generated accounting result.
        ordinary_states = {
            ("tender.doc.review", "approved"),
            ("sc.fund.account", "active"),
            ("sc.subcontract.price", "active"),
            ("sc.labor.price", "active"),
            ("sc.equipment.price", "active"),
            # Publication switches on configuration records, not workflow results.
            ("sc.scene", "published"),
            ("sc.workflow.def", "published"),
            # Historical compatibility snapshot of a legacy running approval;
            # this surface exists to show already-running instances, and the
            # record is never advanced by the current approval runtime.
            ("sc.workflow.instance", "running"),
        }
        for scenario in declarations["RELEASE_SCENARIOS"]:
            spec = declarations["SCENARIOS"][scenario]
            files = spec["files"] if isinstance(spec, dict) else spec
            for relative in files:
                for record in ET.parse(DEMO_ROOT / relative).iter("record"):
                    state = _field_text(record, "state")
                    if state and state != "draft":
                        with self.subTest(scenario=scenario, record=record.get("id")):
                            self.assertIn((record.get("model"), state), ordinary_states)

    def test_rental_payment_checker_is_an_explicit_minimal_role_combination(self):
        tree = ET.parse(DEMO_ROOT / "data/demo/sc_demo_users.xml")
        user = next(r for r in tree.iter("record") if r.get("id") == "user_sc_rental_payment_checker_demo")
        groups = user.find("field[@name='groups_id']").get("eval")
        declared = set(re.findall(r"ref\('([^']+)'\)", groups))
        self.assertEqual(declared, {
            "base.group_user", "smart_construction_core.group_sc_role_material_user",
            "smart_construction_core.group_sc_role_temporary_finance",
        })
        material = next(r for r in tree.iter("record") if r.get("id") == "user_sc_material_01")
        self.assertNotIn("finance", material.find("field[@name='groups_id']").get("eval"))

    def test_s85_office_and_payroll_inputs_match_native_requirements(self):
        path = DEMO_ROOT / "data/scenario/s85_admin_finance_surface/10_admin_finance_records.xml"
        rows = {r.get("id"): r for r in ET.parse(path).iter("record")}
        for name in ("leave", "seal"):
            field = rows["sc_demo_office_admin_085_" + name].find("field[@name='department_id']")
            self.assertEqual(field.get("ref"), "smart_construction_demo.sc_demo_department_001")
        for name, actor in (("salary", "user_sc_project_user"), ("bonus", "user_demo_role_project_a_member")):
            field = rows["sc_demo_hr_payroll_085_" + name].find("field[@name='requester_id']")
            self.assertEqual(field.get("ref"), "smart_construction_demo." + actor)

    def test_s88_invoice_is_manual_input_not_invented_migration(self):
        path = DEMO_ROOT / "data/scenario/s88_output_invoice_surface/10_output_invoice_records.xml"
        records = list(ET.parse(path).iter("record"))
        source = next(r for r in records if r.get("model") == "sc.invoice.registration")
        self.assertEqual(_field_text(source, "source_origin"), "manual")
        self.assertFalse(any(f.get("name", "").startswith("legacy_") for f in source))
        self.assertFalse(any(r.get("model") == "sc.output.invoice.ledger" for r in records))

    def test_every_declared_action_has_an_explicit_actor(self):
        import ast
        names = {"_DEMO_LIFECYCLE_CHAINS", "_DEMO_LIFECYCLE_TARGETS", "_DEMO_LIFECYCLE_REVIEWER",
                 "_DEMO_LIFECYCLE_ACTION_ACTORS", "_DEMO_LIFECYCLE_FACT_WRITES", "_DEMO_LIFECYCLE_XML_ACTIONS"}
        declarations = {}
        for node in ast.parse(LOADER_PATH.read_text(encoding="utf-8")).body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if getattr(target, "id", None) in names:
                        declarations[target.id] = ast.literal_eval(node.value)
        models = {r.get("id"): r.get("model") for p in (DEMO_ROOT / "data/scenario").glob("*/*.xml")
                  for r in ET.parse(p).iter("record")}
        for scenario, targets in declarations["_DEMO_LIFECYCLE_TARGETS"].items():
            for xmlid, state in targets.items():
                model = models[xmlid]
                if xmlid in declarations["_DEMO_LIFECYCLE_XML_ACTIONS"]:
                    method = declarations["_DEMO_LIFECYCLE_XML_ACTIONS"][xmlid]
                    calls = [f for p in (DEMO_ROOT / "data/scenario").glob("*/*.xml")
                             for data in ET.parse(p).iter("data") if data.get("noupdate") == "0"
                             for f in data.findall("function") if f.get("model") == model
                             and f.get("name") == method
                             and xmlid in f.find("value").get("eval", "")]
                    self.assertEqual(len(calls), 1)
                    self.assertEqual(state, "closed")
                    continue  # Role execution is verified by the dedicated ORM chain test.
                actions = (("write",) if xmlid in declarations["_DEMO_LIFECYCLE_FACT_WRITES"]
                           else declarations["_DEMO_LIFECYCLE_CHAINS"][(model, state)])
                for action in actions:
                    with self.subTest(scenario=scenario, xmlid=xmlid, action=action):
                        self.assertTrue((model, action) in declarations["_DEMO_LIFECYCLE_ACTION_ACTORS"]
                                        or (xmlid, action) in declarations["_DEMO_LIFECYCLE_REVIEWER"])


if __name__ == "__main__":
    unittest.main()
