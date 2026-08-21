#!/usr/bin/env python3

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EXPORT_ALL = ROOT / "scripts" / "contract" / "export_all.sh"


class ContractExportResumeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.work = Path(self.tmp.name)
        script_dir = self.work / "scripts" / "contract"
        script_dir.mkdir(parents=True)
        stub = script_dir / "snapshot_export.sh"
        stub.write_text(
            """#!/usr/bin/env bash
set -euo pipefail
case_name=''
outdir='snapshots'
while [ "$#" -gt 0 ]; do
  case "$1" in
    --case) case_name="$2"; shift 2 ;;
    --outdir) outdir="$2"; shift 2 ;;
    *) shift ;;
  esac
done
mkdir -p "$outdir"
printf '{"case":"%s"}\n' "$case_name" > "$outdir/$case_name.json"
""",
            encoding="utf-8",
        )
        stub.chmod(0o755)
        (self.work / "cases.json").write_text(
            json.dumps([{"case": name, "user": "admin"} for name in ("alpha", "beta", "gamma")]),
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def run_export(self, **selectors):
        env = {
            **os.environ,
            "DB": "test_db",
            "CASES_FILE": "cases.json",
            "OUTDIR": "snapshots",
            **selectors,
        }
        return subprocess.run(
            ["bash", str(EXPORT_ALL)],
            cwd=self.work,
            env=env,
            text=True,
            capture_output=True,
        )

    def snapshot_names(self):
        directory = self.work / "snapshots"
        return sorted(path.stem for path in directory.glob("*.json")) if directory.exists() else []

    def test_start_case_exports_selected_case_and_tail(self):
        result = self.run_export(START_CASE="beta")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.snapshot_names(), ["beta", "gamma"])

    def test_case_only_exports_exact_case(self):
        result = self.run_export(CASE_ONLY="beta")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.snapshot_names(), ["beta"])

    def test_unknown_and_conflicting_selectors_fail_closed(self):
        unknown = self.run_export(CASE_ONLY="missing")
        self.assertEqual(unknown.returncode, 2)
        self.assertIn("CASE_ONLY not found", unknown.stderr)
        conflict = self.run_export(START_CASE="beta", CASE_ONLY="beta")
        self.assertEqual(conflict.returncode, 2)
        self.assertIn("mutually exclusive", conflict.stderr)


if __name__ == "__main__":
    unittest.main()
