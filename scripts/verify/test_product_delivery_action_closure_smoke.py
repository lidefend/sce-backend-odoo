#!/usr/bin/env python3
from __future__ import annotations

import os
import unittest
from unittest import mock

from scripts.verify import product_delivery_action_closure_smoke as smoke


class ProductDeliveryActionClosureStateTest(unittest.TestCase):
    def test_default_state_remains_backward_compatible(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SC_PRODUCT_DELIVERY_ACTION_CLOSURE_STATE_FILE", None)
            self.assertEqual(smoke._state_path(), smoke.DEFAULT_STATE_PATH)

    def test_dedicated_role_state_can_be_selected(self) -> None:
        relative = "artifacts/backend/scene_contract_field_schema_state.action_closure_finance.json"
        with mock.patch.dict(
            os.environ,
            {"SC_PRODUCT_DELIVERY_ACTION_CLOSURE_STATE_FILE": relative},
            clear=False,
        ):
            self.assertEqual(smoke._state_path(), smoke.ROOT / relative)


if __name__ == "__main__":
    unittest.main(verbosity=2)
