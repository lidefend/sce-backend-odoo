import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.ci import contract_only_scope


class ContractOnlyScopeTests(unittest.TestCase):
    def _scope_file(self):
        temp = tempfile.NamedTemporaryFile("w", delete=False)
        with temp:
            json.dump({
                "schema_version": 1,
                "scopes": [{
                    "id": "scope",
                    "branch": "feature/test",
                    "base_sha": "a" * 40,
                    "allowed_paths": ["a.py", "b.py"],
                    "targets": ["verify.a.unit"],
                    "excluded_targets": ["verify.a.orm"],
                }],
            }, temp)
        self.addCleanup(Path(temp.name).unlink)
        return Path(temp.name)

    def test_exact_branch_base_and_path_subset_are_required(self):
        scopes = contract_only_scope.load_scopes(self._scope_file())
        self.assertEqual(
            contract_only_scope.match_scope(
                ["a.py"],
                branch="feature/test",
                base_sha="a" * 40,
                scopes=scopes,
            )["id"],
            "scope",
        )
        self.assertIsNone(contract_only_scope.match_scope(
            ["a.py"],
            branch="feature/other",
            base_sha="a" * 40,
            scopes=scopes,
        ))
        self.assertIsNone(contract_only_scope.match_scope(
            ["outside.py"],
            branch="feature/test",
            base_sha="a" * 40,
            scopes=scopes,
        ))

    def test_wildcards_and_invalid_paths_fail_closed(self):
        path = self._scope_file()
        data = json.loads(path.read_text())
        data["scopes"][0]["allowed_paths"] = ["addons/**"]
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(
            ValueError,
            "CONTRACT_ONLY_SCOPE_WILDCARD_FORBIDDEN",
        ):
            contract_only_scope.load_scopes(path)


if __name__ == "__main__":
    unittest.main()
