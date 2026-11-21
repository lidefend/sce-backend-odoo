from __future__ import annotations

import tempfile
import textwrap
import unittest
from pathlib import Path

from scripts.verify.smart_core_boundary_guard import _extension_provider_lines


class SmartCoreBoundaryGuardTests(unittest.TestCase):
    def test_only_hook_contract_provider_literals_are_allowed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "extension_hook_contracts.py"
            path.write_text(
                textwrap.dedent(
                    """
                    FROM_PROVIDER = HookContract(
                        mode="ordered_merge",
                        providers=(
                            "smart_construction_core",
                            "smart_construction_scene",
                        ),
                    )
                    industry_default = "construction.standard"
                    """
                ),
                encoding="utf-8",
            )

            lines = _extension_provider_lines(
                path,
                path.read_text(encoding="utf-8"),
                contract_path=path,
            )

        self.assertEqual(len(lines), 2)
        self.assertNotIn(9, lines)

    def test_non_contract_file_has_no_provider_exception(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "other.py"
            path.write_text(
                'PROVIDERS = ("smart_construction_core",)',
                encoding="utf-8",
            )

            self.assertEqual(
                _extension_provider_lines(path, path.read_text(encoding="utf-8")),
                set(),
            )


if __name__ == "__main__":
    unittest.main()
