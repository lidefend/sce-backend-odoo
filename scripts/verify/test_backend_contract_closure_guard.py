#!/usr/bin/env python3
from __future__ import annotations

import contextlib
import io
import unittest
from unittest import mock

from scripts.verify import backend_contract_closure_guard as guard


class BackendContractClosureGuardTest(unittest.TestCase):
    def test_capability_delivery_tokens_follow_split_owner(self) -> None:
        token_check = next(
            (path, tokens)
            for path, tokens in guard.CHECKS
            if '"delivery_level"' in tokens
        )
        path, tokens = token_check
        self.assertEqual(path.name, "contract_governance_capabilities.py")
        self.assertEqual(tokens, ['"delivery_level"', '"target_scene_key"', '"entry_kind"'])
        source = path.read_text(encoding="utf-8")
        for token in tokens:
            self.assertIn(token, source)

    def test_current_structure_passes(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = guard.main()
        self.assertEqual(result, 0)
        self.assertIn("[backend_contract_closure_guard] PASS", output.getvalue())

    def test_missing_token_fails_closed(self) -> None:
        target_path, tokens = guard.CHECKS[0]
        source = target_path.read_text(encoding="utf-8").replace(tokens[0], "missing-marker")
        original_read = guard._read

        def fake_read(path):
            return source if path == target_path else original_read(path)

        output = io.StringIO()
        with mock.patch.object(guard, "_read", side_effect=fake_read), contextlib.redirect_stdout(output):
            result = guard.main()
        self.assertEqual(result, 2)
        self.assertIn("missing token", output.getvalue())
        self.assertIn("[backend_contract_closure_guard] FAIL", output.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
