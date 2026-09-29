#!/usr/bin/env python3
"""Pin the Web business-purpose derivation check to an exact predicate.

`DECLARED_BUSINESS_PURPOSES` must be the complement of `NON_BUSINESS_PURPOSES`.
Matching only the `ACTION_PURPOSES.filter(` shape would accept a widened
predicate that silently drops a purpose from the derived set while the two
literal lists still compare equal -- the drift this guard exists to catch.
"""
from __future__ import annotations

import unittest

from unified_page_contract_v2_schema_guard import ts_derives_business_list


CONTROLLED = (
    "export const ACTION_PURPOSES = Object.freeze(['save_draft', 'submit', 'return'] as const);\n"
    "export const NON_BUSINESS_PURPOSES = Object.freeze(['save_draft', 'return'] as const);\n"
    "export const DECLARED_BUSINESS_PURPOSES = Object.freeze(\n"
    "  ACTION_PURPOSES.filter((purpose) => !(NON_BUSINESS_PURPOSES as readonly string[]).includes(purpose)),\n"
    ");\n"
)

WIDENED_PREDICATE = CONTROLLED.replace(
    ".includes(purpose)),",
    ".includes(purpose) && purpose !== 'submit'),",
)
RESTATED_LIST = (
    "export const DECLARED_BUSINESS_PURPOSES = Object.freeze(['submit'] as const);\n"
)


class BusinessPurposeDerivationTest(unittest.TestCase):
    def test_the_controlled_predicate_is_accepted(self) -> None:
        self.assertTrue(ts_derives_business_list(CONTROLLED))

    def test_an_extra_predicate_is_rejected(self) -> None:
        self.assertNotEqual(WIDENED_PREDICATE, CONTROLLED)
        self.assertFalse(ts_derives_business_list(WIDENED_PREDICATE))

    def test_a_restated_list_is_rejected(self) -> None:
        self.assertFalse(ts_derives_business_list(RESTATED_LIST))


if __name__ == "__main__":
    unittest.main()
