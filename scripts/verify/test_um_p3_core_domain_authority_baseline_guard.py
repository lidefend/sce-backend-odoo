#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


VERIFY_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(VERIFY_DIR))

import um_p3_core_domain_authority_baseline_guard as guard


class CoreDomainAuthorityBaselineGuardTest(unittest.TestCase):
    def setUp(self):
        self.data = guard.load_json(guard.MATRIX)

    def test_committed_matrix_is_valid(self):
        self.assertEqual(guard.validate(self.data), [])

    def test_missing_relation_field_is_rejected(self):
        changed = copy.deepcopy(self.data)
        del changed["RELATIONS"][0]["AUTHORITY_SIDE"]
        self.assertTrue(
            any(
                "missing fields" in error
                for error in guard.validate(changed)
            )
        )

    def test_heuristic_matching_is_rejected(self):
        changed = copy.deepcopy(self.data)
        changed["RELATIONS"][0]["HEURISTIC_MATCHING_ALLOWED"] = True
        self.assertTrue(
            any(
                "permits heuristic matching" in error
                for error in guard.validate(changed)
            )
        )

    def test_summary_count_drift_is_rejected(self):
        changed = copy.deepcopy(self.data)
        changed["SUMMARY"]["CLOSED_CHAINS"] += 1
        self.assertIn(
            "CLOSED_CHAINS does not match chain statuses",
            guard.validate(changed),
        )

    def test_non_highest_gap_selection_is_rejected(self):
        changed = copy.deepcopy(self.data)
        changed["GAP_SELECTION"]["HIGHEST_PRIORITY_GAP"] = (
            "PROJECT_TO_FUND_PLAN"
        )
        self.assertIn(
            "selected gap is not a highest-priority chain",
            guard.validate(changed),
        )

    def test_s02_explicit_allocation_authority_is_frozen(self):
        changed = copy.deepcopy(self.data)
        changed["FIXED_AUTHORITIES"]["PLAN_EVENT_RELATION_AUTHORITY"] = (
            "CURRENT_ACTIVE_PLAN"
        )
        self.assertTrue(
            any(
                "PLAN_EVENT_RELATION_AUTHORITY is not frozen" in error
                for error in guard.validate(changed)
            )
        )

    def test_s05_explicit_register_relation_authority_is_frozen(self):
        changed = copy.deepcopy(self.data)
        changed["FIXED_AUTHORITIES"][
            "REGISTER_SETTLEMENT_RELATION_AUTHORITY"
        ] = "PROJECT_MATCH"
        self.assertTrue(
            any(
                "REGISTER_SETTLEMENT_RELATION_AUTHORITY is not frozen"
                in error
                for error in guard.validate(changed)
            )
        )

    def test_frozen_p2_authority_drift_is_rejected(self):
        changed = copy.deepcopy(self.data)
        changed["FIXED_AUTHORITIES"]["SETTLEMENT_CONTRACT_AUTHORITY"] = (
            "HEADER"
        )
        self.assertTrue(
            any(
                "SETTLEMENT_CONTRACT_AUTHORITY is not frozen" in error
                for error in guard.validate(changed)
            )
        )

    def test_core_035_source_evidence_blocker_cannot_be_silently_closed(self):
        changed = copy.deepcopy(self.data)
        relation = next(
            item
            for item in changed["RELATIONS"]
            if item["RELATION_ID"]
            == "CORE-035-SUBCONTRACT-HISTORICAL-REGISTER-RELATION-REMEDIATION"
        )
        relation["POLICY_STATE"] = "CLOSED"
        self.assertIn(
            "CORE-035 POLICY_STATE source evidence drift",
            guard.validate(changed),
        )

    def test_execution_rerank_cannot_invent_safe_candidate(self):
        changed = copy.deepcopy(self.data)
        changed["EXECUTION_GAP_SELECTION"]["SAFE_TO_IMPLEMENT"] = True
        self.assertIn(
            "execution matrix must not invent a safe candidate",
            guard.validate(changed),
        )

    def test_core_035_profile_cannot_invent_authoritative_candidates(self):
        profile = json.loads(guard.CORE_035_PROFILE.read_text(encoding="utf-8"))
        self.assertEqual(
            0,
            profile["RELATION_CLASSIFICATION"][
                "AUTOMATIC_MIGRATION_CANDIDATE_COUNT"
            ],
        )
        self.assertFalse(profile["SOURCE_RELATION_EVIDENCE_FOUND"])
        self.assertFalse(profile["HEURISTIC_MATCHING_USED"])

    def test_core_034_amount_policy_closure_cannot_drift(self):
        changed = copy.deepcopy(self.data)
        relation = next(
            item
            for item in changed["RELATIONS"]
            if item["RELATION_ID"]
            == "CORE-034-SUBCONTRACT-REGISTER-CUMULATIVE-AMOUNT-POLICY"
        )
        relation["COMMON_TAX_BASIS"] = "UNTAXED"
        self.assertIn(
            "CORE-034 COMMON_TAX_BASIS closure drift",
            guard.validate(changed),
        )

    def test_core_020_permission_closure_cannot_drift(self):
        changed = copy.deepcopy(self.data)
        relation = next(
            item
            for item in changed["RELATIONS"]
            if item["RELATION_ID"] == "CORE-020-PAYMENT-LEDGER-REQUEST"
        )
        relation["ALLOWED_COMPANY_RULE"] = "ALL"
        self.assertIn(
            "CORE-020 ALLOWED_COMPANY_RULE closure drift",
            guard.validate(changed),
        )


if __name__ == "__main__":
    unittest.main()
