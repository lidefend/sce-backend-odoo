from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.verify import frontend_split_usage_guard as guard


class FrontendSplitUsageGuardTest(unittest.TestCase):
    def make_root(self, files: dict[str, str], registered: dict[str, dict]) -> Path:
        root = Path(tempfile.mkdtemp())
        web = root / "frontend/apps/web/src"
        web.mkdir(parents=True)
        for relative, content in files.items():
            path = web / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        allowlist = root / "docs/architecture/split_usage_allowlist.json"
        allowlist.parent.mkdir(parents=True)
        allowlist.write_text(json.dumps({
            "schema_version": 1,
            "scope": "frontend/apps/web/src",
            "mechanisms": {
                "route_protocol": {
                    "owner": "frontend.test",
                    "reason": "route protocol fixture",
                },
                "record_identity_contract_gap": {
                    "owner": "frontend.test",
                    "contract_defect": "CD-TEST",
                    "reason": "contract gap fixture",
                },
            },
            "files": {
                f"frontend/apps/web/src/{relative}": record
                for relative, record in registered.items()
            },
        }), encoding="utf-8")
        return root

    def test_registered_counts_pass(self) -> None:
        root = self.make_root(
            {"route.ts": "const x = value.split('?');\n"},
            {"route.ts": {"count": 1, "mechanism": "route_protocol"}},
        )
        self.assertEqual(guard.inspect(root)["errors"], [])

    def test_unregistered_split_fails(self) -> None:
        root = self.make_root(
            {"route.ts": "const x = value.split('?');\n"},
            {},
        )
        errors = guard.inspect(root)["errors"]
        self.assertTrue(any("unregistered split site" in error for error in errors))

    def test_count_drift_fails(self) -> None:
        root = self.make_root(
            {"route.ts": "a.split('?'); b.split('#');\n"},
            {"route.ts": {"count": 1, "mechanism": "route_protocol"}},
        )
        errors = guard.inspect(root)["errors"]
        self.assertTrue(any("split count drift" in error for error in errors))

    def test_stale_entry_and_unknown_mechanism_fail(self) -> None:
        root = self.make_root(
            {"empty.ts": "export const value = 1;\n"},
            {"empty.ts": {"count": 1, "mechanism": "unknown"}},
        )
        errors = guard.inspect(root)["errors"]
        self.assertTrue(any("stale split allowlist entry" in error for error in errors))
        self.assertTrue(any("unknown split mechanism" in error for error in errors))

    def test_record_identity_gap_requires_contract_defect(self) -> None:
        root = self.make_root(
            {"identity.ts": "const x = label.split(' / ');\n"},
            {"identity.ts": {"count": 1, "mechanism": "record_identity_contract_gap"}},
        )
        allowlist = root / "docs/architecture/split_usage_allowlist.json"
        payload = json.loads(allowlist.read_text(encoding="utf-8"))
        payload["mechanisms"]["record_identity_contract_gap"].pop("contract_defect")
        allowlist.write_text(json.dumps(payload), encoding="utf-8")
        errors = guard.inspect(root)["errors"]
        self.assertTrue(any("must name a contract defect" in error for error in errors))

    def test_non_split_string_methods_do_not_match(self) -> None:
        root = self.make_root(
            {"plain.ts": "const value = text.replaceAll('?', '');\n"},
            {},
        )
        self.assertEqual(guard.inspect(root)["errors"], [])


if __name__ == "__main__":
    unittest.main()
