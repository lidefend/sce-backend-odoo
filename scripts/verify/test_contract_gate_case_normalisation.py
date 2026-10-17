#!/usr/bin/env python3
"""Unit lock on the contract gate's declared per-case volatile response keys.

The gate compares a regenerated snapshot against the tracked reference. A case
whose response carries a value assigned by the producing environment (for
example a database row handle) may declare that member name under
``volatile_keys``. The declaration is *per case* and must stay discriminating:
it may only suppress the declared member, never anything else, and a malformed
declaration must fail closed.

These tests drive the real ``scripts/contract/gate_contract.sh`` with a stub
export command, so they need no database and prove the declared semantics
deterministically. The product-side assertions at the end pin the declaration
to the single preference case and prove that the tracked reference no longer
carries the environment-assigned handle.
"""
from __future__ import annotations

import json
import os
import re
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GATE = ROOT / "scripts/contract/gate_contract.sh"
CASES_FILE = ROOT / "docs/contract/cases.yml"
SNAPSHOTS = ROOT / "docs/contract/snapshots"

CASE = "user_view_preference_set_resolved_intent_admin"
PREFERENCE_CASES = (
    "user_view_preference_get_intent_admin",
    "user_view_preference_set_intent_admin",
    "user_view_preference_get_resolved_intent_admin",
    "user_view_preference_set_resolved_intent_admin",
)

_SCOPE_KEY = "ui:list_columns:list:model:res.partner"
_PREFERENCE = {
    "column_order": [],
    "column_widths": {},
    "hidden_columns": [],
    "visible_columns": [],
}


def _snapshot(scope_key: str = _SCOPE_KEY, with_id: bool = True, trace_id: str = "t") -> dict:
    data: dict = {}
    if with_id:
        data["id"] = 1
    data["scope_key"] = scope_key
    data["preference"] = dict(_PREFERENCE)
    return {
        "case": CASE,
        "op": "intent.invoke",
        "trace_id": trace_id,
        "ui_contract_raw": data,
    }


def _case_entry(volatile_keys=None) -> dict:
    entry = {
        "case": CASE,
        "user": "admin",
        "op": "intent.invoke",
        "intent": "user.view.preference.set",
        "intent_params": {"model": "res.partner", "preference_key": "list_columns", "view_type": "list"},
    }
    if volatile_keys is not None:
        entry["volatile_keys"] = volatile_keys
    return entry


class GateCaseNormalisationTest(unittest.TestCase):
    def _run_gate(self, *, cases, ref, cur, extra_fixtures=None, case_filter=None):
        """Run the real gate with a stub export that emits the fixtures.

        ``cur`` is the single regenerated snapshot used by the normalisation
        tests; ``extra_fixtures`` adds further ``{name: payload}`` pairs for the
        narrowing tests. The stub records every ``CASE_ONLY`` it receives so a
        test can prove the export itself was narrowed.
        """
        workdir = Path(tempfile.mkdtemp(prefix="gate-normalisation-"))
        fixtures = workdir / "fixtures"
        fixtures.mkdir()
        payloads = {CASE: cur}
        payloads.update(extra_fixtures or {})
        for name, payload in payloads.items():
            (fixtures / f"{name}.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )

        ref_dir = workdir / "ref"
        ref_dir.mkdir()
        (ref_dir / f"{CASE}.json").write_text(json.dumps(ref, ensure_ascii=False, indent=2), encoding="utf-8")

        cases_path = workdir / "cases.json"
        cases_path.write_text(json.dumps(cases, ensure_ascii=False, indent=2), encoding="utf-8")

        export_log = workdir / "export_log.txt"
        stub = workdir / "stub_export.sh"
        stub.write_text(
            "#!/usr/bin/env bash\nset -euo pipefail\n"
            f'printf "%s\\n" "${{CASE_ONLY:-<all>}}" >> "{export_log}"\n'
            f'cp "{fixtures}"/*.json "$OUTDIR/"\n',
            encoding="utf-8",
        )
        stub.chmod(stub.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        env = dict(os.environ)
        env.update({
            "DB": "gate_normalisation_unit",
            "CASES_FILE": str(cases_path),
            "REF_DIR": str(ref_dir),
            "TMP_DIR": str(workdir / "run"),
            "EXPORT_ALL_CMD": str(stub),
        })
        if case_filter is not None:
            env["CASE_FILTER"] = case_filter
        completed = subprocess.run(
            ["bash", str(GATE)], cwd=str(ROOT), env=env,
            capture_output=True, text=True, check=False,
        )
        completed.export_log = export_log.read_text(encoding="utf-8").split() if export_log.exists() else []
        return completed

    # ------------------------------------------------ declared normalisation
    def test_declared_volatile_key_tolerates_the_environment_assigned_handle(self):
        result = self._run_gate(
            cases=[_case_entry(["id"])],
            ref=_snapshot(with_id=True, trace_id="ref"),
            cur=_snapshot(with_id=False, trace_id="cur"),
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS", result.stdout)
        self.assertIn("volatile=id", result.stdout)

    # ------------------------------------------- still discriminating
    def test_without_the_declaration_the_same_drift_fails(self):
        result = self._run_gate(
            cases=[_case_entry()],
            ref=_snapshot(with_id=True, trace_id="ref"),
            cur=_snapshot(with_id=False, trace_id="cur"),
        )
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("FAIL", result.stdout)
        self.assertIn('"id"', result.stdout)

    def test_declared_volatile_key_does_not_hide_another_drift(self):
        result = self._run_gate(
            cases=[_case_entry(["id"])],
            ref=_snapshot(with_id=True, trace_id="ref"),
            cur=_snapshot(scope_key="ui:list_columns:list:model:res.company", with_id=False, trace_id="cur"),
        )
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("FAIL", result.stdout)
        self.assertIn("res.company", result.stdout)

    def test_undeclared_sibling_key_still_compares_strictly(self):
        ref = _snapshot(with_id=True, trace_id="ref")
        cur = _snapshot(with_id=False, trace_id="cur")
        cur["ui_contract_raw"]["preference"] = {"kit": "moved"}
        result = self._run_gate(cases=[_case_entry(["id"])], ref=ref, cur=cur)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("FAIL", result.stdout)
        self.assertIn("moved", result.stdout)

    # ------------------------------------------------------- fail closed
    def test_wildcard_declaration_fails_closed(self):
        result = self._run_gate(
            cases=[_case_entry(["*"])],
            ref=_snapshot(with_id=True, trace_id="ref"),
            cur=_snapshot(with_id=False, trace_id="cur"),
        )
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("wildcard", result.stdout)

    def test_empty_and_duplicate_declarations_fail_closed(self):
        for declared in ([], ["id", "id"], ["  "]):
            with self.subTest(declared=declared):
                result = self._run_gate(
                    cases=[_case_entry(declared)],
                    ref=_snapshot(with_id=True, trace_id="ref"),
                    cur=_snapshot(with_id=False, trace_id="cur"),
                )
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)

    # ------------------------------------------------- global list untouched
    def test_default_global_ignore_keys_do_not_contain_a_bare_id(self):
        text = GATE.read_text(encoding="utf-8")
        match = re.search(r"IGNORE_KEYS=\$\{IGNORE_KEYS:-([^}]*)\}", text)
        self.assertIsNotNone(match, "global IGNORE_KEYS default not found")
        global_keys = [key.strip() for key in match.group(1).split(",") if key.strip()]
        self.assertNotIn("id", global_keys)

    # ------------------------------------------------- declared case narrowing
    def test_case_filter_exports_and_compares_only_the_declared_names(self):
        other = "user_view_preference_get_resolved_intent_admin"
        result = self._run_gate(
            cases=[_case_entry(["id"]), dict(_case_entry(["id"]), case=other)],
            ref=_snapshot(with_id=True, trace_id="ref"),
            cur=_snapshot(with_id=False, trace_id="cur"),
            extra_fixtures={other: _snapshot(with_id=True, trace_id="other")},
            case_filter=CASE,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.export_log, [CASE], "only the declared name may be exported")
        self.assertEqual(result.stdout.count("PASS"), 1)
        self.assertNotIn(other, result.stdout)

    def test_unfiltered_run_exports_once_without_a_case_only_binding(self):
        result = self._run_gate(
            cases=[_case_entry(["id"])],
            ref=_snapshot(with_id=True, trace_id="ref"),
            cur=_snapshot(with_id=False, trace_id="cur"),
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.export_log, ["<all>"], "the full run must export the whole declared case file exactly once")

    def test_case_filter_name_absent_from_the_declaration_fails_closed(self):
        result = self._run_gate(
            cases=[_case_entry(["id"])],
            ref=_snapshot(with_id=True, trace_id="ref"),
            cur=_snapshot(with_id=False, trace_id="cur"),
            case_filter="not_a_declared_case",
        )
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("not declared", result.stdout)


class DeclarationAndArtifactTest(unittest.TestCase):
    def test_only_the_set_resolved_case_declares_volatile_keys(self):
        cases = json.loads(CASES_FILE.read_text(encoding="utf-8"))
        declared = {
            case.get("case"): case.get("volatile_keys")
            for case in cases
            if "volatile_keys" in case
        }
        self.assertEqual(declared, {CASE: ["id"]})

    def test_tracked_preference_snapshots_carry_no_environment_handle(self):
        def named_id(node, path="", found=None):
            if found is None:
                found = []
            if isinstance(node, dict):
                for key, value in node.items():
                    if key == "id":
                        found.append(f"{path}.{key}")
                    named_id(value, f"{path}.{key}", found)
            elif isinstance(node, list):
                for index, value in enumerate(node):
                    named_id(value, f"{path}[{index}]", found)
            return found

        for name in PREFERENCE_CASES:
            with self.subTest(case=name):
                payload = json.loads((SNAPSHOTS / f"{name}.json").read_text(encoding="utf-8"))
                self.assertEqual(named_id(payload), [])

    def test_set_resolved_reference_declares_only_scope_key_and_preference(self):
        payload = json.loads((SNAPSHOTS / f"{CASE}.json").read_text(encoding="utf-8"))
        self.assertEqual(sorted(payload["ui_contract_raw"]), ["preference", "scope_key"])


if __name__ == "__main__":
    unittest.main()
