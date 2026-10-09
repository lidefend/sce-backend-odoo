#!/usr/bin/env python3
"""Focused behaviour tests for the reuse-first business-entry matrix entry.

They lock the evidence-locality contract: the governed Make target forwards
``SC_ACCEPTANCE_OUTPUT_DIR`` even when the caller left it unset, so the entry
must treat an empty or blank value as "unset" and keep writing evidence into the
declared default directory instead of resolving to the repository root
(``Path('') == '.'``) and leaking ``summary.json`` into the worktree.

They also lock the immutability contract: the ledger records the ``summary.json``
each unit was folded from, so the default must be a per-run subdirectory of the
declared location. A fixed default would let a later, narrower run overwrite an
earlier run's evidence and break the ledger's source pointers, which is precisely
the failure a targeted reverification would otherwise cause.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.verify import business_entry_matrix_incremental as incremental

REPO_ROOT = Path(incremental.__file__).resolve().parents[2]
SCOPE_ADAPTER = REPO_ROOT / "scripts" / "verify" / "business_entry_matrix_scope.mjs"

_CSV = (
    "menu_xmlid,action_xmlid,label,domain,model,scope_disposition,batch,role_authority,rendering_path,acceptance_status\n"
    'menu.a,action.a,A,core,res.partner,,b1,"{}",list,pending\n'
    'menu.b,action.b,B,core,res.partner,,b1,"{}",list,pending\n'
)


class EmitResultsStatusTests(unittest.TestCase):
    """A surface verdict must never rewrite a sibling entry's own outcome.

    The probe aggregates ``summary.ok`` / ``summary.fatal`` for its process exit
    code. Folding that aggregate into every executed unit once stamped all 87
    passing siblings as ``checked=failed`` because two unrelated entries timed
    out, which poisoned the reuse ledger. Per-unit status must come only from
    ``summary.entries[]``; a selected key with no per-entry observation carries
    no proof and stays non-reusable.
    """

    def _run(self, summary: dict) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            (tmpdir / "matrix.csv").write_text(_CSV, encoding="utf-8")
            (tmpdir / "overlay.json").write_text(
                json.dumps({"denied_role_candidates": [], "entries": {}, "defaults": {}}), encoding="utf-8"
            )
            (tmpdir / "closures.json").write_text(
                json.dumps({"schema": "business_entry_negative_closures.v1", "candidates": {}}), encoding="utf-8"
            )
            (tmpdir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
            (tmpdir / "plan.json").write_text(json.dumps({"affected": ["menu.a", "menu.b"]}), encoding="utf-8")
            out = tmpdir / "results.json"
            env = dict(os.environ)
            env.update(
                {
                    "SC_ACCEPTANCE_TARGET_SHA": "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
                    "SC_ENTRY_MATRIX_CSV": str(tmpdir / "matrix.csv"),
                    "SC_ENTRY_MATRIX_OVERLAY": str(tmpdir / "overlay.json"),
                    "SC_ENTRY_MATRIX_CLOSURES": str(tmpdir / "closures.json"),
                }
            )
            result = subprocess.run(
                [
                    "node",
                    str(SCOPE_ADAPTER),
                    "--emit-results",
                    str(out),
                    "--summary",
                    str(tmpdir / "summary.json"),
                    "--plan",
                    str(tmpdir / "plan.json"),
                ],
                cwd=REPO_ROOT,
                env=env,
                check=False,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(out.read_text(encoding="utf-8"))

    def test_one_failing_entry_does_not_rewrite_its_siblings(self) -> None:
        document = self._run(
            {
                "ok": False,
                "selection": {"keys": ["menu.a", "menu.b"]},
                "entries": [{"entry": "menu.a", "status": "exception"}, {"entry": "menu.b"}],
            }
        )
        self.assertEqual(document["results"], {"menu.a": "exception", "menu.b": "checked"})
        self.assertFalse(document["surface_ok"])
        self.assertFalse(document["surface_fatal"])

    def test_no_unit_is_ever_recorded_with_a_surface_derived_suffix(self) -> None:
        document = self._run(
            {
                "ok": False,
                "selection": {"keys": ["menu.a", "menu.b"]},
                "entries": [{"entry": "menu.a", "status": "exception"}, {"entry": "menu.b"}],
            }
        )
        offenders = {key: value for key, value in document["results"].items() if "=failed" in value}
        self.assertEqual(offenders, {})

    def test_fatal_probe_without_observations_keeps_every_unit_unproven(self) -> None:
        document = self._run({"ok": False, "fatal": True, "selection": {"keys": ["menu.a", "menu.b"]}})
        self.assertEqual(document["results"], {"menu.a": "failed", "menu.b": "failed"})
        self.assertTrue(document["surface_fatal"])
        self.assertEqual(sorted(unit["id"] for unit in document["executed_units"]), ["menu.a", "menu.b"])

    def test_a_partial_run_keeps_unreached_units_unrecorded(self) -> None:
        """An interrupted probe proves only what it concluded.

        The run reached ``menu.a`` and declared ``completeness:partial``;
        ``menu.b`` was never executed. Recording ``menu.b`` as a failure would
        make the next incremental pass refuse to resume it as an unchanged
        failure, so the unreached unit must stay unrecorded — neither passed nor
        failed — and the declared plan must be narrowed to what was reached.
        """
        document = self._run(
            {
                "ok": False,
                "completeness": "partial",
                "selection": {"keys": ["menu.a", "menu.b"]},
                "entries": [{"entry": "menu.a", "status": "checked"}],
            }
        )
        self.assertTrue(document["partial"])
        self.assertEqual(document["results"], {"menu.a": "checked"})
        self.assertEqual([unit["id"] for unit in document["executed_units"]], ["menu.a"])
        self.assertEqual(document["planned_affected"], ["menu.a"])

    def test_a_partial_run_with_no_conclusion_records_nothing(self) -> None:
        """An interrupted run that reached no entry folds no unit at all."""
        document = self._run(
            {
                "ok": False,
                "completeness": "partial",
                "selection": {"keys": ["menu.a", "menu.b"]},
            }
        )
        self.assertTrue(document["partial"])
        self.assertEqual(document["results"], {})
        self.assertEqual(document["executed_units"], [])
        self.assertEqual(document["planned_affected"], [])

    def test_successful_surface_records_every_entry_as_checked(self) -> None:
        document = self._run(
            {
                "ok": True,
                "selection": {"keys": ["menu.a", "menu.b"]},
                "entries": [{"entry": "menu.a"}, {"entry": "menu.b"}],
            }
        )
        self.assertEqual(document["results"], {"menu.a": "checked", "menu.b": "checked"})
        self.assertTrue(document["surface_ok"])


class PartialFoldPlanTests(unittest.TestCase):
    """Lock the fold decision for an interrupted observation.

    ``partial_fold_plan`` is the single place that decides what a probe
    observation may be folded into. It must never turn an unreached unit into a
    recorded failure, and it must never fold an observation that concluded
    nothing.
    """

    def test_a_partial_observation_folds_only_its_conclusions(self) -> None:
        plan = incremental.partial_fold_plan(
            {"partial": True, "executed_units": [{"id": "menu.a"}]}, selected_count=3
        )
        self.assertTrue(plan["partial"])
        self.assertTrue(plan["record"])
        self.assertEqual(plan["folded"], 1)
        self.assertEqual(plan["unreached"], 2)

    def test_a_partial_observation_without_conclusions_folds_nothing(self) -> None:
        plan = incremental.partial_fold_plan({"partial": True, "executed_units": []}, selected_count=3)
        self.assertFalse(plan["record"])
        self.assertEqual(plan["folded"], 0)
        self.assertEqual(plan["unreached"], 3)

    def test_a_complete_observation_reports_no_unreached_units(self) -> None:
        plan = incremental.partial_fold_plan(
            {"executed_units": [{"id": "menu.a"}, {"id": "menu.b"}]}, selected_count=2
        )
        self.assertFalse(plan["partial"])
        self.assertTrue(plan["record"])
        self.assertEqual(plan["unreached"], 0)


class EmitUnitsIdentityTests(unittest.TestCase):
    """The declared surface must bind the served bundle, not the deploying commit.

    Binding the deployed commit made every mainline merge re-open all declared
    entries, including merges that never rebuilt the frontend. The identity must
    therefore carry the served artifact fingerprint, keep the deployment
    revision as provenance only, and degrade visibly when the runtime publishes
    no fingerprint.
    """

    BUNDLE = "c" * 64

    def _emit(self, tmpdir: Path, env_extra: dict) -> dict:
        (tmpdir / "matrix.csv").write_text(_CSV, encoding="utf-8")
        (tmpdir / "overlay.json").write_text(
            json.dumps({"denied_role_candidates": [], "entries": {}, "defaults": {}}), encoding="utf-8"
        )
        (tmpdir / "closures.json").write_text(
            json.dumps({"schema": "business_entry_negative_closures.v1", "candidates": {}}), encoding="utf-8"
        )
        out = tmpdir / "units.json"
        env = dict(os.environ)
        env.update(
            {
                "SC_ACCEPTANCE_TARGET_SHA": "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
                "SC_ENTRY_MATRIX_CSV": str(tmpdir / "matrix.csv"),
                "SC_ENTRY_MATRIX_OVERLAY": str(tmpdir / "overlay.json"),
                "SC_ENTRY_MATRIX_CLOSURES": str(tmpdir / "closures.json"),
            }
        )
        for key in ("SC_ACCEPTANCE_FRONTEND_BUILD_SHA",):
            env.pop(key, None)
        env.update(env_extra)
        result = subprocess.run(
            ["node", str(SCOPE_ADAPTER), "--emit-units", str(out)],
            cwd=REPO_ROOT, env=env, check=False, text=True, capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(out.read_text(encoding="utf-8"))

    def test_the_declared_identity_binds_the_served_artifact_fingerprint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            document = self._emit(Path(tmp), {"SC_ACCEPTANCE_FRONTEND_BUILD_SHA": self.BUNDLE})
        self.assertEqual(document["identity"]["frontend_build_sha256"], self.BUNDLE)
        self.assertNotIn("served_revision", document["identity"])
        self.assertEqual(document["provenance"]["reuse_identity_key"], "frontend_build_sha256")
        self.assertEqual(document["provenance"]["served_revision"],
                         "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef")

    def test_a_runtime_without_a_fingerprint_degrades_to_the_deployment_revision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            document = self._emit(Path(tmp), {})
        self.assertNotIn("frontend_build_sha256", document["identity"])
        self.assertEqual(document["identity"]["served_revision"],
                         "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef")
        self.assertEqual(document["provenance"]["reuse_identity_key"], "served_revision")

    def test_a_malformed_declared_fingerprint_degrades_instead_of_binding(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            document = self._emit(Path(tmp), {"SC_ACCEPTANCE_FRONTEND_BUILD_SHA": "not-a-fingerprint"})
        self.assertNotIn("frontend_build_sha256", document["identity"])
        self.assertEqual(document["provenance"]["reuse_identity_key"], "served_revision")


class ReuseBundleResolutionTests(unittest.TestCase):
    """The resolved artifact fingerprint decides whether reuse is incremental."""

    def _response(self, payload) -> mock.MagicMock:
        response = mock.MagicMock()
        response.read.return_value = json.dumps(payload).encode("utf-8")
        response.__enter__ = lambda instance: instance
        response.__exit__ = lambda instance, *args: False
        return response

    def test_the_published_fingerprint_is_adopted(self) -> None:
        with mock.patch.object(incremental.urllib.request, "urlopen",
                               return_value=self._response({"frontend_build_sha256": "D" * 64})) as called:
            resolved = incremental.resolve_reuse_bundle_identity("http://runtime.invalid:18081/")
        self.assertEqual(resolved, "d" * 64)
        self.assertEqual(called.call_args.args[0], "http://runtime.invalid:18081/api/runtime-version")

    def test_a_runtime_without_a_fingerprint_degrades(self) -> None:
        with mock.patch.object(incremental.urllib.request, "urlopen",
                               return_value=self._response({"source_revision": "e" * 40})):
            self.assertEqual(incremental.resolve_reuse_bundle_identity("http://runtime.invalid:18081"), "")

    def test_a_malformed_fingerprint_is_not_adopted(self) -> None:
        with mock.patch.object(incremental.urllib.request, "urlopen",
                               return_value=self._response({"frontend_build_sha256": "unknown"})):
            self.assertEqual(incremental.resolve_reuse_bundle_identity("http://runtime.invalid:18081"), "")

    def test_an_unreachable_runtime_degrades_instead_of_failing(self) -> None:
        with mock.patch.object(incremental.urllib.request, "urlopen",
                               side_effect=incremental.urllib.error.URLError("refused")):
            self.assertEqual(incremental.resolve_reuse_bundle_identity("http://runtime.invalid:18081"), "")

    def test_a_blank_base_url_degrades_without_calling_the_runtime(self) -> None:
        with mock.patch.object(incremental.urllib.request, "urlopen") as called:
            self.assertEqual(incremental.resolve_reuse_bundle_identity("   "), "")
        called.assert_not_called()


class OutputDirResolutionTests(unittest.TestCase):
    def test_missing_env_falls_back_under_the_default_directory(self) -> None:
        resolved = incremental.resolve_output_dir({}, stamp='20260101T000000Z', selection='a,b')
        self.assertEqual(resolved.parent, Path(incremental.DEFAULT_OUTPUT_DIR))

    def test_empty_env_falls_back_under_the_default_directory(self) -> None:
        self.assertEqual(
            incremental.resolve_output_dir({'SC_ACCEPTANCE_OUTPUT_DIR': ''}, stamp='20260101T000000Z', selection='').parent,
            Path(incremental.DEFAULT_OUTPUT_DIR),
        )

    def test_blank_env_falls_back_under_the_default_directory(self) -> None:
        self.assertEqual(
            incremental.resolve_output_dir({'SC_ACCEPTANCE_OUTPUT_DIR': '   '}, stamp='20260101T000000Z', selection='').parent,
            Path(incremental.DEFAULT_OUTPUT_DIR),
        )

    def test_explicit_env_is_used_verbatim(self) -> None:
        self.assertEqual(
            incremental.resolve_output_dir({'SC_ACCEPTANCE_OUTPUT_DIR': 'artifacts/x'}),
            Path('artifacts/x'),
        )

    def test_default_directory_is_not_the_repository_root(self) -> None:
        self.assertNotEqual(incremental.resolve_output_dir({}, stamp='20260101T000000Z'), Path('.'))

    def test_default_is_never_the_shared_directory_itself(self) -> None:
        resolved = incremental.resolve_output_dir({}, stamp='20260101T000000Z', selection='a,b')
        self.assertNotEqual(resolved, Path(incremental.DEFAULT_OUTPUT_DIR))

    def test_distinct_runs_resolve_to_distinct_directories(self) -> None:
        first = incremental.resolve_output_dir({}, stamp='20260101T000000Z', selection='a,b')
        second = incremental.resolve_output_dir({}, stamp='20260101T000001Z', selection='a,b')
        self.assertNotEqual(first, second)

    def test_distinct_selections_at_one_stamp_stay_distinct(self) -> None:
        first = incremental.resolve_output_dir({}, stamp='20260101T000000Z', selection='a')
        second = incremental.resolve_output_dir({}, stamp='20260101T000000Z', selection='b')
        self.assertNotEqual(first, second)

    def test_recorded_evidence_of_an_earlier_run_is_not_overwritten(self) -> None:
        first = incremental.resolve_output_dir({}, stamp='20260101T000000Z', selection='a,b')
        second = incremental.resolve_output_dir({}, stamp='20260102T000000Z', selection='c')
        self.assertNotEqual(first / 'summary.json', second / 'summary.json')


class RecordExistingBindingTests(unittest.TestCase):
    """Re-folding an observation must be bound and justified, never a free pass.

    A recording bug is repaired by re-applying the corrected mapping to the
    observation that was already collected, which is why this mode exists. It
    must refuse any summary that is not bound to the exact target/database, and
    it must refuse to run without an explicit justification and plan.
    """

    TARGET = "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef"

    def _write(self, tmpdir: Path, **overrides) -> Path:
        document = {
            "schema": "business_entry_matrix_browser.v1",
            "target_sha": self.TARGET,
            "served_revision": self.TARGET,
            "database": "sc_demo",
            "selection": {"keys": ["menu.a", "menu.b"]},
            "entries": [{"entry": "menu.a"}, {"entry": "menu.b"}],
            "ok": True,
        }
        document.update(overrides)
        path = tmpdir / "summary.json"
        path.write_text(json.dumps(document), encoding="utf-8")
        return path

    def _call(self, tmpdir: Path, summary: Path, plan: Path | None = None):
        plan_path = plan if plan is not None else tmpdir / "plan.json"
        if plan is None:
            plan_path.write_text(json.dumps({"affected": []}), encoding="utf-8")
        return incremental.record_existing(
            summary,
            plan_path,
            run_dir=tmpdir,
            ledger=str(tmpdir / "ledger.json"),
            environment={"SC_ACCEPTANCE_TARGET_SHA": self.TARGET},
            database="sc_demo",
        )

    def test_a_missing_observation_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(incremental.IncrementalError):
                self._call(Path(tmp), Path(tmp) / "absent.json")

    def test_an_observation_bound_to_another_target_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(incremental.IncrementalError):
                self._call(Path(tmp), self._write(Path(tmp), target_sha="0" * 40))

    def test_an_observation_from_another_database_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(incremental.IncrementalError):
                self._call(Path(tmp), self._write(Path(tmp), database="sc_other"))

    def test_an_observation_that_names_no_entry_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(incremental.IncrementalError):
                self._call(Path(tmp), self._write(Path(tmp), selection={"keys": []}))

    def test_a_missing_plan_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            with self.assertRaises(incremental.IncrementalError):
                self._call(tmpdir, self._write(tmpdir), plan=tmpdir / "absent-plan.json")

    def test_the_reason_is_mandatory(self) -> None:
        environment = {
            "SC_ACCEPTANCE_FRONTEND_URL": "http://127.0.0.1:1",
            "SC_ACCEPTANCE_TARGET_SHA": self.TARGET,
            "ACCEPTANCE_LOGIN": "wutao",
            "ACCEPTANCE_PASSWORD": "123456",
        }
        with mock.patch.dict(os.environ, environment, clear=False):
            with self.assertRaises(incremental.IncrementalError):
                incremental.main(["--record-existing", "summary.json", "--plan", "plan.json"])


if __name__ == '__main__':
    unittest.main()
