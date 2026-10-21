"""Exercise the release shell flow with isolated command doubles, without Docker."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/release/tenant_rc_profile_rehearsal.sh"


class CleanCustomerRehearsalTests(unittest.TestCase):
    def run_profile(self, *, digest="sha256:test", admitted=True, metrics="0|0|1|0"):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            commands = root / "commands.jsonl"
            profile = root / "customer.json"
            profile.write_text(json.dumps({"tenant_id": "test_tenant"}))
            payload = root / "manifest.json"
            payload.write_text("{}")
            binary = root / "bin"
            binary.mkdir()
            docker = binary / "docker"
            docker.write_text(f"#!{sys.executable}\n" + '''import json, os, sys
from pathlib import Path
a = sys.argv[1:]
with open(os.environ["TEST_COMMAND_LOG"], "a") as log:
    log.write(json.dumps(a) + "\\n")
if a[:2] == ["image", "inspect"]:
    print("sha256:test")
elif "psql" in a:
    print(os.environ["TEST_METRICS"])
''')
            python = binary / "python3"
            python.write_text(f"#!{sys.executable}\n" + '''import json, os, sys
from pathlib import Path
a = sys.argv[1:]
if a and a[0] == "scripts/release/customer_package_preflight.py":
    if os.environ["TEST_ADMITTED"] != "1":
        sys.exit("CUSTOMER_PACKAGE_REJECTED")
    report = Path(a[a.index("--report") + 1])
    report.write_text(json.dumps({"prepared_addons_root": str(report.parent), "modules": ["test_customer"]}))
else:
    os.execv(os.environ["TEST_REAL_PYTHON"], [os.environ["TEST_REAL_PYTHON"], *a])
''')
            for tool in (docker, python):
                tool.chmod(0o755)
            env = {key: value for key, value in os.environ.items()
                   if not key.startswith(("RC_", "SC_", "CANDIDATE_"))}
            env.update(PATH=f"{binary}:{os.environ['PATH']}",
                       CANDIDATE_IMAGE="test:image", CANDIDATE_IMAGE_DIGEST=digest,
                       CANDIDATE_ARTIFACTS=str(root / "artifacts"), RC_PROFILE_PATH=str(profile),
                       SC_PAYLOAD_MANIFEST=str(payload), DB_USER="odoo",
                       TEST_COMMAND_LOG=str(commands), TEST_REAL_PYTHON=sys.executable,
                       TEST_ADMITTED="1" if admitted else "0", TEST_METRICS=metrics)
            result = subprocess.run(["bash", str(SCRIPT), "customer"], env=env,
                                    capture_output=True, text=True, cwd=ROOT)
            calls = [json.loads(line) for line in commands.read_text().splitlines()]
            report = root / "artifacts/profiles/RC-C03.json"
            return result, calls, json.loads(report.read_text()) if report.exists() else None

    def test_empty_customer_database_installs_only_admitted_modules(self):
        result, calls, report = self.run_profile()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["initialization"], "clean_install")
        self.assertEqual(report["business_record_count"], 0)
        installs = [call for call in calls if "-i" in call]
        self.assertEqual(len(installs), 3)
        self.assertEqual(sum("-u" in call for call in installs), 2)
        self.assertEqual(installs[0][installs[0].index("-i") + 1].split(",")[-1], "test_customer")
        self.assertFalse(any("pg_restore" in call or "shell" in call for call in calls))

    def test_digest_mismatch_never_starts_database(self):
        result, calls, report = self.run_profile(digest="sha256:wrong")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any("up" in call for call in calls))
        self.assertIsNone(report)

    def test_rejected_package_never_starts_database(self):
        result, calls, report = self.run_profile(admitted=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any("up" in call for call in calls))
        self.assertIsNone(report)

    def test_missing_customer_module_rejects_success_report(self):
        result, _, report = self.run_profile(metrics="0|0|0|0")
        self.assertNotEqual(result.returncode, 0)
        self.assertIsNone(report)


if __name__ == "__main__":
    unittest.main()
