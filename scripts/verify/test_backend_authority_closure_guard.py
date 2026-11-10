from __future__ import annotations

import copy
import json
import unittest

from scripts.verify import backend_authority_closure_guard as guard


class BackendAuthorityClosureGuardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mapping = json.loads(guard.MAP_PATH.read_text(encoding="utf-8"))

    def test_repository_authority_map_passes(self):
        self.assertEqual(guard.validate(self.mapping), [])

    def test_missing_source_symbol_fails_closed(self):
        mapping = copy.deepcopy(self.mapping)
        mapping["samples"][0]["stages"][0]["refs"][0]["value"] = "missing_menu_xmlid"
        errors = guard.validate(mapping)
        self.assertTrue(any("XML record is missing" in item for item in errors), errors)

    def test_duplicate_fact_maintainer_fails_closed(self):
        mapping = copy.deepcopy(self.mapping)
        sample = mapping["samples"][0]
        fact = sample["required_facts"][0]
        next(stage for stage in sample["stages"] if stage.get("maintains"))["maintains"].append(fact)
        errors = guard.validate(mapping)
        self.assertTrue(any("exactly one maintainer" in item for item in errors), errors)

    def test_projection_cannot_authorize_fails_closed(self):
        mapping = copy.deepcopy(self.mapping)
        stage = next(
            stage
            for sample in mapping["samples"]
            for stage in sample["stages"]
            if stage.get("role") == "page_projection"
        )
        stage["authorizes"] = ["record_write"]
        errors = guard.validate(mapping)
        self.assertTrue(any("must not authorize" in item for item in errors), errors)

    def test_execution_requires_rechecks_fails_closed(self):
        mapping = copy.deepcopy(self.mapping)
        stage = next(
            stage
            for sample in mapping["samples"]
            for stage in sample["stages"]
            if stage.get("role") == "business_transition"
        )
        stage["execution_rechecks"] = []
        errors = guard.validate(mapping)
        self.assertTrue(any("execution rechecks are required" in item for item in errors), errors)

    def test_known_gap_requires_owned_follow_up_card_fails_closed(self):
        mapping = copy.deepcopy(self.mapping)
        mapping["known_gaps"] = [
            gap for gap in mapping["known_gaps"] if gap.get("owner_card") != "BE-U02"
        ]
        errors = guard.validate(mapping)
        self.assertTrue(any("follow-up cards" in item for item in errors), errors)


if __name__ == "__main__":
    unittest.main()
