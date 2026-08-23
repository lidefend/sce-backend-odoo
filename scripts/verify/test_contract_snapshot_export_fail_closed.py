from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_EXPORT = ROOT / "scripts" / "contract" / "snapshot_export.sh"
EXPORT_ALL = ROOT / "scripts" / "contract" / "export_all.sh"
SNAPSHOT_EXPORT_PY = ROOT / "scripts" / "contract" / "snapshot_export.py"
INTENT_CASE_GUARD = ROOT / "scripts" / "verify" / "intent_cases_integrity_guard.py"


class ContractSnapshotExportFailClosedTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.repo = Path(self.temporary.name)
        (self.repo / "scripts" / "contract").mkdir(parents=True)
        (self.repo / "docs" / "contract" / "snapshots").mkdir(parents=True)
        shutil.copy2(SNAPSHOT_EXPORT, self.repo / "scripts" / "contract" / "snapshot_export.sh")
        shutil.copy2(EXPORT_ALL, self.repo / "scripts" / "contract" / "export_all.sh")
        (self.repo / "scripts" / "contract" / "snapshot_export.py").write_text(
            "# consumed by the fake docker executable\n", encoding="utf-8"
        )

    def _fake_docker(self, *, output: str, exit_code: int = 0) -> dict[str, str]:
        bin_dir = self.repo / "bin"
        bin_dir.mkdir(exist_ok=True)
        docker = bin_dir / "docker"
        docker.write_text(
            "#!/usr/bin/env bash\n"
            "if [[ \"$1 $2\" == \"compose version\" ]]; then exit 0; fi\n"
            "shift 2\n"
            "previous=''\n"
            "for argument in \"$@\"; do\n"
            "  if [[ \"$previous $argument\" == \"docker compose\" ]]; then exit 23; fi\n"
            "  previous=\"$argument\"\n"
            "done\n"
            "cat >/dev/null\n"
            "printf '%s' \"${FAKE_SNAPSHOT_OUTPUT:-}\"\n"
            "exit \"${FAKE_SNAPSHOT_EXIT:-0}\"\n",
            encoding="utf-8",
        )
        docker.chmod(0o755)
        return {
            **os.environ,
            "PATH": f"{bin_dir}:{os.environ['PATH']}",
            "SC_FORCE_DOCKER": "1",
            "FAKE_SNAPSHOT_OUTPUT": output,
            "FAKE_SNAPSHOT_EXIT": str(exit_code),
        }

    def _run_snapshot(self, *, output: str, exit_code: int = 0) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                "bash",
                "scripts/contract/snapshot_export.sh",
                "--db",
                "test_db",
                "--user",
                "admin",
                "--case",
                "atomic_case",
            ],
            cwd=self.repo,
            env=self._fake_docker(output=output, exit_code=exit_code),
            text=True,
            capture_output=True,
            check=False,
        )

    def test_valid_json_atomically_replaces_target(self) -> None:
        target = self.repo / "docs" / "contract" / "snapshots" / "atomic_case.json"
        target.write_text('{"old": true}\n', encoding="utf-8")
        result = self._run_snapshot(output='{"ok": true}\n')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(target.read_text(encoding="utf-8")), {"ok": True})

    def test_internal_compose_selector_is_not_forwarded_to_exporter(self) -> None:
        result = self._run_snapshot(output='{"ok": true}\n')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_failed_export_preserves_existing_target(self) -> None:
        target = self.repo / "docs" / "contract" / "snapshots" / "atomic_case.json"
        target.write_text('{"old": true}\n', encoding="utf-8")
        result = self._run_snapshot(output="", exit_code=7)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(json.loads(target.read_text(encoding="utf-8")), {"old": True})

    def test_empty_export_preserves_existing_target(self) -> None:
        target = self.repo / "docs" / "contract" / "snapshots" / "atomic_case.json"
        target.write_text('{"old": true}\n', encoding="utf-8")
        result = self._run_snapshot(output="")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(json.loads(target.read_text(encoding="utf-8")), {"old": True})

    def test_invalid_json_preserves_existing_target(self) -> None:
        target = self.repo / "docs" / "contract" / "snapshots" / "atomic_case.json"
        target.write_text('{"old": true}\n', encoding="utf-8")
        result = self._run_snapshot(output="not-json")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(json.loads(target.read_text(encoding="utf-8")), {"old": True})

    def _run_export_all(self, case: dict[str, object], payload: dict[str, object]) -> subprocess.CompletedProcess[str]:
        cases = self.repo / "cases.json"
        cases.write_text(json.dumps([case]), encoding="utf-8")
        exporter = self.repo / "scripts" / "contract" / "snapshot_export.sh"
        exporter.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "case_name=''\n"
            "outdir='docs/contract/snapshots'\n"
            "args=(\"$@\")\n"
            "for ((i=0; i<${#args[@]}; i++)); do\n"
            "  [[ \"${args[$i]}\" == '--case' ]] && case_name=\"${args[$((i+1))]}\"\n"
            "  [[ \"${args[$i]}\" == '--outdir' ]] && outdir=\"${args[$((i+1))]}\"\n"
            "done\n"
            "mkdir -p \"$outdir\"\n"
            "printf '%s' \"$FAKE_CASE_PAYLOAD\" > \"$outdir/$case_name.json\"\n",
            encoding="utf-8",
        )
        exporter.chmod(0o755)
        return subprocess.run(
            ["bash", "scripts/contract/export_all.sh"],
            cwd=self.repo,
            env={
                **os.environ,
                "CASES_FILE": str(cases),
                "DB": "test_db",
                "FAKE_CASE_PAYLOAD": json.dumps(payload),
            },
            text=True,
            capture_output=True,
            check=False,
        )

    def test_export_all_rejects_unexpected_record_error(self) -> None:
        result = self._run_export_all({"case": "record"}, {"record_error": "denied"})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unexpected record_error", result.stderr)

    def test_export_all_accepts_declared_record_error(self) -> None:
        result = self._run_export_all(
            {"case": "missing", "allow_record_error": True},
            {"record_error": "missing"},
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_export_all_rejects_unexpected_error_response(self) -> None:
        result = self._run_export_all({"case": "error"}, {"error": {"code": "DENIED"}})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unexpected error response", result.stderr)

    def test_export_all_accepts_declared_error_response(self) -> None:
        result = self._run_export_all(
            {"case": "error", "allow_error_response": True},
            {"error": {"code": "EXPECTED"}},
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_snapshot_schema_uses_semver_without_legacy_contract_marker(self) -> None:
        source = SNAPSHOT_EXPORT_PY.read_text(encoding="utf-8")
        self.assertIn('SNAPSHOT_SCHEMA_VERSION = "1.0.0"', source)
        self.assertIn('"snapshot_schema_version": SNAPSHOT_SCHEMA_VERSION', source)
        self.assertNotIn('"contract_version": "v1"', source)

    def test_case_integrity_guard_accepts_declared_record_error_policy(self) -> None:
        cases = self.repo / "record-error-cases.json"
        cases.write_text(
            json.dumps(
                [
                    {
                        "case": "record_error_case",
                        "user": "admin",
                        "op": "model",
                        "model": "project.project",
                        "allow_record_error": True,
                    }
                ]
            ),
            encoding="utf-8",
        )
        result = subprocess.run(
            ["python3", str(INTENT_CASE_GUARD), "--cases-file", str(cases)],
            cwd=self.repo,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_case_integrity_guard_rejects_fixed_ids_for_execute_authority(self) -> None:
        cases = self.repo / "fixed-authority-cases.json"
        cases.write_text(
            json.dumps(
                [
                    {
                        "case": "fixed_authority_case",
                        "user": "sc_test_admin",
                        "op": "intent.invoke",
                        "intent": "execute_button",
                        "intent_params": {"res_id": 41, "action_id": 52, "menu_id": 63},
                        "intent_authority": {
                            "source": "ui.contract.v2",
                            "record_xmlid": "demo.record",
                            "action_xmlid": "core.action",
                            "menu_xmlid": "core.menu",
                            "view_type": "form",
                            "button_type": "object",
                            "method": "action_submit",
                        },
                    }
                ]
            ),
            encoding="utf-8",
        )
        result = subprocess.run(
            ["python3", str(INTENT_CASE_GUARD), "--cases-file", str(cases)],
            cwd=self.repo,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("forbids static intent_params", result.stderr)

    def test_case_integrity_guard_rejects_top_level_fixed_record_carrier(self) -> None:
        cases = self.repo / "fixed-record-carrier-cases.json"
        cases.write_text(
            json.dumps(
                [
                    {
                        "case": "fixed_record_carrier_case",
                        "user": "sc_test_admin",
                        "op": "intent.invoke",
                        "intent": "execute_button",
                        "id": 41,
                        "intent_authority": {
                            "source": "ui.contract.v2",
                            "record_xmlid": "demo.record",
                            "action_xmlid": "core.action",
                            "menu_xmlid": "core.menu",
                            "view_type": "form",
                            "button_type": "object",
                            "method": "action_submit",
                        },
                    }
                ]
            ),
            encoding="utf-8",
        )
        result = subprocess.run(
            ["python3", str(INTENT_CASE_GUARD), "--cases-file", str(cases)],
            cwd=self.repo,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("forbids static carriers: id", result.stderr)


if __name__ == "__main__":
    unittest.main()
