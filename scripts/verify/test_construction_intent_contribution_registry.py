#!/usr/bin/env python3

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE_PATH = ROOT / "addons/smart_construction_core/core_extension_intent_handlers.py"


class ConstructionIntentContributionRegistryTest(unittest.TestCase):
    def setUp(self):
        self.source = SOURCE_PATH.read_text(encoding="utf-8")
        ast.parse(self.source, filename=str(SOURCE_PATH))

    def test_payment_continuation_handlers_are_imported(self):
        self.assertIn("PaymentRequestCreateExecutionHandler", self.source)
        self.assertIn("PaymentRequestCancelByContractHandler", self.source)

    def test_payment_continuation_intents_are_registered(self):
        self.assertIn(
            '("payment.request.create_execution", PaymentRequestCreateExecutionHandler)',
            self.source,
        )
        self.assertIn(
            '("payment.request.mark_reversed", PaymentRequestCancelByContractHandler)',
            self.source,
        )


if __name__ == "__main__":
    unittest.main()
