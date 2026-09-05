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


if __name__ == "__main__":
    unittest.main()
