from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.audit.verification_lane_coverage import (
    DEFAULT_BASELINE,
    DEFAULT_DISPOSITIONS,
    ROOT,
    SELF_DATA_FILES,
    SCRIPT_DISPOSITION_VOCABULARY,
    TARGET_DISPOSITION_VOCABULARY,
    _batch_entries,
    _entry_name,
    _retire_one,
    baseline_payload,
    cmd_record_missing_assets,
    cmd_register,
    cmd_register_batch,
    cmd_unregister_script,
    is_prose,
    missing_asset_state,
    compare,
    disposition_state,
    join_continuations,
    measure,
    parse_make,
    read_dispositions,
    resolve_module_specifier,
)

# A zero-reference target is the debt this tool exists to keep visible.  These
# tests lock the two behaviours that make the metric trustworthy: the reference
# test is token-exact (never a regex substring), and every dead name must be
# registered or it fails the ratchet.


class JoinContinuationsTest(unittest.TestCase):
    def test_backslash_continuation_folds_into_one_logical_line(self) -> None:
        lines = ["a: b \\", "   c \\", "   d", "e: f"]
        self.assertEqual(join_continuations(lines), ["a: b c d", "e: f"])

    def test_first_line_keeps_leading_tab_for_recipe_detection(self) -> None:
        self.assertEqual(join_continuations(["\techo hi \\", "\t\tmore"]), ["\techo hi more"])


class ParseMakeTest(unittest.TestCase):
    def _make(self, body: str):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "Makefile").write_text(body, encoding="utf-8")
            return parse_make(root)

    def test_prerequisites_are_not_read_from_recipes_or_directives(self) -> None:
        targets, recipes, prereqs, _phony = self._make(
            "TOP = 1\n"
            ".PHONY: build\n"
            "build: dep1 dep2\n"
            "\t@echo not-a-prereq\n"
            "dep1:\n"
            "\t@echo dep1\n"
            "dep2:\n"
            "\t@echo dep2\n"
        )
        self.assertEqual(sorted(prereqs["build"]), ["dep1", "dep2"])
        self.assertNotIn("not-a-prereq", prereqs["build"])
        self.assertEqual(prereqs["dep1"], [])
        self.assertTrue(recipes["build"])


class DispositionStateTest(unittest.TestCase):
    def test_unregistered_dead_surface_is_flagged(self) -> None:
        state = disposition_state(["dead.a"], ["scripts/dead.sh"], {"targets": set(), "scripts": set()})
        self.assertEqual(state["targets_zero_reference_unregistered"], ["dead.a"])
        self.assertEqual(state["scripts_unreferenced_unregistered"], ["scripts/dead.sh"])

    def test_registered_dead_surface_is_not_unregistered_debt(self) -> None:
        state = disposition_state(
            ["dead.a"],
            ["scripts/dead.sh"],
            {"targets": {"dead.a"}, "scripts": {"scripts/dead.sh"}},
        )
        self.assertEqual(state["targets_zero_reference_unregistered"], [])
        self.assertEqual(state["scripts_unreferenced_unregistered"], [])
        self.assertEqual(state["stale_target_dispositions"], [])

    def test_registration_of_live_surface_is_stale(self) -> None:
        state = disposition_state([], [], {"targets": {"now.wired"}, "scripts": set()})
        self.assertEqual(state["stale_target_dispositions"], ["now.wired"])


class ReadDispositionsTest(unittest.TestCase):
    def test_missing_file_reads_as_empty(self) -> None:
        self.assertEqual(read_dispositions(Path("/nonexistent/x.json")), {"targets": set(), "scripts": set()})

    def test_keys_are_loaded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "d.json"
            path.write_text(json.dumps({"targets": {"a": {}}, "scripts": {"s": {}}}), encoding="utf-8")
            self.assertEqual(read_dispositions(path), {"targets": {"a"}, "scripts": {"s"}})


class CompareTest(unittest.TestCase):
    def _result(self, **overrides):
        result = {
            "schema_version": "verification-lane-coverage/v1",
            "targets_defined": 0,
            "targets_unreached_from_anchor": 0,
            "anchor_union_targets": 0,
            "targets_zero_reference": [],
            "scripts_unreferenced_anywhere": [],
            "targets_zero_reference_unregistered": [],
            "scripts_unreferenced_unregistered": [],
            "stale_target_dispositions": [],
            "stale_script_dispositions": [],
            "local_only_scripts": [],
            "remote_only_scripts": [],
            "unregistered_local_only_scripts": [],
            "unregistered_remote_only_scripts": [],
            "stale_local_only_exemptions": [],
            "stale_remote_only_exemptions": [],
        }
        result.update(overrides)
        return result

    def test_growth_past_frozen_raw_count_fails(self) -> None:
        regressions = compare(
            self._result(targets_zero_reference=["a", "b"]),
            {"max_targets_zero_reference": 1},
        )
        self.assertTrue(any("targets_zero_reference:" in r for r in regressions))

    def test_unregistered_dead_surface_fails_even_under_raw_allowance(self) -> None:
        regressions = compare(
            self._result(
                targets_zero_reference=["a"],
                targets_zero_reference_unregistered=["a"],
            ),
            {"max_targets_zero_reference": 5, "max_targets_zero_reference_unregistered": 0},
        )
        self.assertEqual(regressions, ["targets_zero_reference_unregistered: 1 > frozen baseline 0"])

    def test_baseline_payload_pins_unregistered_and_stale_to_zero(self) -> None:
        payload = baseline_payload(self._result())
        self.assertEqual(payload["max_targets_zero_reference_unregistered"], 0)
        self.assertEqual(payload["max_scripts_unreferenced_unregistered"], 0)
        self.assertEqual(payload["max_stale_target_dispositions"], 0)


class RepositoryInvariantTest(unittest.TestCase):
    """The live repository must always be fully dispositioned.

    This is the protection that makes the registry honest: a new dead make
    target or guard script fails here (and in `--check`) until someone wires it,
    retires it, or registers it with a reason.
    """

    def test_every_dead_surface_name_is_registered(self) -> None:
        result = measure(ROOT)
        self.assertEqual(result["targets_zero_reference_unregistered"], [])
        self.assertEqual(result["scripts_unreferenced_unregistered"], [])
        self.assertEqual(result["stale_target_dispositions"], [])
        self.assertEqual(result["stale_script_dispositions"], [])

    def test_raw_debt_never_exceeds_the_frozen_baseline(self) -> None:
        result = measure(ROOT)
        baseline = json.loads(DEFAULT_BASELINE.read_text(encoding="utf-8"))
        self.assertEqual(compare(result, baseline), [])

    def test_registered_script_dispositions_use_the_closed_vocabulary(self) -> None:
        doc = json.loads(DEFAULT_DISPOSITIONS.read_text(encoding="utf-8"))
        unknown = {
            name: entry.get("disposition")
            for name, entry in (doc.get("scripts") or {}).items()
            if entry.get("disposition") not in SCRIPT_DISPOSITION_VOCABULARY
        }
        self.assertEqual(unknown, {})

    def test_registered_target_dispositions_use_the_closed_vocabulary(self) -> None:
        doc = json.loads(DEFAULT_DISPOSITIONS.read_text(encoding="utf-8"))
        unknown = {
            name: entry.get("disposition")
            for name, entry in (doc.get("targets") or {}).items()
            if entry.get("disposition") not in TARGET_DISPOSITION_VOCABULARY
        }
        self.assertEqual(unknown, {})

    def test_verify_registry_lifecycle_is_not_double_counted(self) -> None:
        """scripts/verify py/sh belong to the R7 registry, not this instrument."""
        result = measure(ROOT)
        self.assertGreater(result["scripts_verify_lifecycle_owned"], 0)
        self.assertEqual(
            result["scripts_on_disk"],
            result["scripts_owned_surface"] + result["scripts_verify_lifecycle_owned"],
        )
        for name in result["scripts_unreferenced_anywhere"]:
            self.assertFalse(
                name.startswith("scripts/verify/") and name.endswith((".py", ".sh")),
                f"{name} must be owned by guard_registry_audit, not counted here",
            )

    def test_the_auditor_registries_narrate_and_never_consume(self) -> None:
        """A committed registry lists every registered name.

        If it counted as a consumer, one `git add` would revive the entire
        registered surface - the same defect class already fixed for prose docs,
        measured here as all registered targets and scripts going stale at once.
        """
        for rel in SELF_DATA_FILES:
            self.assertTrue(is_prose(rel), rel)
        self.assertFalse(is_prose("scripts/audit/verification_lane_coverage.py"))
        self.assertFalse(is_prose("make/ci.mk"))
        self.assertTrue(is_prose("docs/ops/iterations/example.md"))
        self.assertTrue(is_prose(".agent/runs/example/run.json"))

    def test_registries_are_tracked_so_measurement_matches_delivery(self) -> None:
        """The metric reads `git ls-files`; an untracked registry is a blind spot.

        While these files were untracked, --check passed on a registry the
        scanner could not see; the first commit turned every registered entry
        stale at once. Measuring the committed state is the only honest reading,
        so a registry that is not tracked must fail here rather than flatter the
        metric during iteration.
        """
        tracked = subprocess.run(
            ["git", "-C", str(ROOT), "ls-files", "--", *SELF_DATA_FILES],
            check=True, capture_output=True, text=True,
        ).stdout.split()
        self.assertEqual(sorted(tracked), sorted(SELF_DATA_FILES))


class ResolveModuleSpecifierTest(unittest.TestCase):
    """A module named without its extension must resolve like the runtime.

    Path-only and basename indexes miss ``require('./x')`` / ``from x import``,
    which reported a live guard as dead surface; and a stem shared by a ``.js``
    and a ``.py`` file must resolve per the consumer's language, never by mixing
    extensions into an ambiguous match.
    """

    def setUp(self) -> None:
        self.live = {"scripts/verify/intent_smoke_utils.js", "scripts/verify/intent_smoke_utils.py"}
        self.dotted = {"scripts.verify.intent_smoke_utils": "scripts/verify/intent_smoke_utils.py"}
        self.pystem = {"intent_smoke_utils": "scripts/verify/intent_smoke_utils.py"}

    def test_relative_js_require_resolves_to_the_js_sibling(self) -> None:
        got = resolve_module_specifier(
            "./intent_smoke_utils", "scripts/verify/consumer.js", self.live, self.dotted, self.pystem
        )
        self.assertEqual(got, "scripts/verify/intent_smoke_utils.js")

    def test_relative_python_import_resolves_to_the_py_sibling(self) -> None:
        got = resolve_module_specifier(
            "./intent_smoke_utils", "scripts/verify/consumer.py", self.live, self.dotted, self.pystem
        )
        self.assertEqual(got, "scripts/verify/intent_smoke_utils.py")

    def test_bare_module_name_resolves_for_a_python_consumer(self) -> None:
        got = resolve_module_specifier(
            "intent_smoke_utils", "scripts/verify/consumer.py", self.live, self.dotted, self.pystem
        )
        self.assertEqual(got, "scripts/verify/intent_smoke_utils.py")

    def test_bare_module_name_does_not_resolve_for_a_js_consumer(self) -> None:
        got = resolve_module_specifier(
            "intent_smoke_utils", "scripts/verify/consumer.js", self.live, self.dotted, self.pystem
        )
        self.assertIsNone(got)

    def test_unknown_specifier_is_none(self) -> None:
        got = resolve_module_specifier(
            "./nope", "scripts/verify/consumer.js", self.live, self.dotted, self.pystem
        )
        self.assertIsNone(got)


class RetireOneTest(unittest.TestCase):
    """Retirement must park, record and de-register, and refuse live surface."""

    def _repo(self):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        for cmd in (
            ["git", "init", "-q"],
            ["git", "config", "user.email", "t@example.com"],
            ["git", "config", "user.name", "t"],
        ):
            subprocess.run(cmd, cwd=root, check=True)
        (root / "scripts" / "ops").mkdir(parents=True)
        (root / "scripts" / "ops" / "dead.sh").write_text("echo hi\n", encoding="utf-8")
        dispositions = root / "dispositions.json"
        dispositions.write_text(
            json.dumps({"scripts": {"scripts/ops/dead.sh": {"disposition": "cli-manual"}}}),
            encoding="utf-8",
        )
        subprocess.run(["git", "add", "-A"], cwd=root, check=True)
        subprocess.run(["git", "commit", "-qm", "init"], cwd=root, check=True)
        return tmp, root, dispositions

    def test_retire_parks_records_and_de_registers(self) -> None:
        tmp, root, dispositions = self._repo()
        self.addCleanup(tmp.cleanup)
        rc = _retire_one(root, dispositions, "scripts/ops/dead.sh", "dead runbook", {"scripts/ops/dead.sh"})
        self.assertEqual(rc, 0)
        self.assertFalse((root / "scripts" / "ops" / "dead.sh").exists())
        self.assertTrue((root / "scripts" / "retired" / "ops" / "dead.sh").is_file())
        log = json.loads((root / "scripts" / "retired" / "retirements.json").read_text(encoding="utf-8"))
        self.assertEqual(log["scripts/ops/dead.sh"]["reason"], "dead runbook")
        self.assertNotIn(
            "scripts/ops/dead.sh", json.loads(dispositions.read_text(encoding="utf-8"))["scripts"]
        )

    def test_retire_refuses_a_referenced_script(self) -> None:
        tmp, root, dispositions = self._repo()
        self.addCleanup(tmp.cleanup)
        rc = _retire_one(root, dispositions, "scripts/ops/dead.sh", "reason", set())
        self.assertEqual(rc, 3)
        self.assertTrue((root / "scripts" / "ops" / "dead.sh").is_file())

    def test_retire_requires_a_reason_via_the_wrapper(self) -> None:
        from scripts.audit.verification_lane_coverage import cmd_retire

        self.assertEqual(cmd_retire(ROOT, Path("/nonexistent/dispositions.json"), "scripts/x.sh", "  "), 2)


class RegisterScriptTest(unittest.TestCase):
    """Registration must classify (closed vocabulary) and carry an audit trail."""

    def test_missing_disposition_is_rejected(self) -> None:
        self.assertEqual(
            cmd_register(ROOT, Path("/nonexistent/d.json"), "scripts/x.sh", "", "r", "o", "2027-01-01"),
            2,
        )

    def test_unknown_disposition_is_rejected(self) -> None:
        self.assertEqual(
            cmd_register(ROOT, Path("/nonexistent/d.json"), "scripts/x.sh", "made_up", "r", "o", "2027-01-01"),
            2,
        )

    def test_missing_reason_is_rejected(self) -> None:
        self.assertEqual(
            cmd_register(ROOT, Path("/nonexistent/d.json"), "scripts/x.sh", "retain", "  ", "o", "2027-01-01"),
            2,
        )

    def test_missing_owner_or_review_date_is_rejected(self) -> None:
        self.assertEqual(
            cmd_register(ROOT, Path("/nonexistent/d.json"), "scripts/x.sh", "retain", "r", "", "2027-01-01"),
            2,
        )
        self.assertEqual(
            cmd_register(ROOT, Path("/nonexistent/d.json"), "scripts/x.sh", "retain", "r", "o", ""),
            2,
        )


def _temp_repo_with_one_dead_target(rule: str = "dead.target:\n\t@echo hi\n") -> Path:
    """A throwaway git repo holding exactly one dead target and one dead script.

    ``measure`` walks ``git ls-files`` and needs ``scripts/verify/registry.yaml``,
    so the fixture is a real (tiny) repository rather than a bare directory.
    """
    tmp = Path(tempfile.mkdtemp())
    (tmp / "Makefile").write_text(rule, encoding="utf-8")
    (tmp / "scripts" / "verify").mkdir(parents=True)
    (tmp / "scripts" / "verify" / "registry.yaml").write_text("", encoding="utf-8")
    (tmp / "scripts" / "dead.sh").write_text("#!/bin/sh\n", encoding="utf-8")
    for cmd in (
        ["git", "init", "-q"],
        ["git", "add", "-A"],
        ["git", "-c", "user.email=a@b", "-c", "user.name=t", "commit", "-qm", "x"],
    ):
        subprocess.run(cmd, cwd=tmp, check=True)
    return tmp


class BatchManifestRoutingTest(unittest.TestCase):
    """A batch manifest routes each surface to its own bucket.

    The defect this locks: an early ``--register-batch`` only ever wrote the
    ``scripts`` bucket, so registering a reviewed family of make targets would
    have silently written 400+ target names into the script registry.
    """

    def test_targets_bucket_is_not_read_as_scripts(self) -> None:
        payload = {"targets": [{"name": "a.b"}]}
        self.assertEqual(_batch_entries(payload, "targets"), [{"name": "a.b"}])
        self.assertEqual(_batch_entries(payload, "scripts"), [])

    def test_scripts_bucket_is_not_read_as_targets(self) -> None:
        payload = {"scripts": [{"script": "scripts/x.sh"}]}
        self.assertEqual(_batch_entries(payload, "scripts"), [{"script": "scripts/x.sh"}])
        self.assertEqual(_batch_entries(payload, "targets"), [])

    def test_bare_list_is_the_legacy_scripts_manifest(self) -> None:
        payload = [{"script": "scripts/x.sh"}]
        self.assertEqual(_batch_entries(payload, "scripts"), payload)
        self.assertEqual(_batch_entries(payload, "targets"), [])

    def test_entry_name_accepts_name_script_or_target(self) -> None:
        self.assertEqual(_entry_name({"name": " a.b "}), "a.b")
        self.assertEqual(_entry_name({"script": "scripts/x.sh"}), "scripts/x.sh")
        self.assertEqual(_entry_name({"target": "a.b"}), "a.b")
        self.assertEqual(_entry_name({"name": "  "}), "")


class RegisterBatchTest(unittest.TestCase):
    def test_target_entry_lands_in_the_target_bucket_only(self) -> None:
        root = _temp_repo_with_one_dead_target()
        manifest = root / "m.json"
        manifest.write_text(
            json.dumps({"targets": [{
                "name": "dead.target",
                "disposition": "diagnostic_cli",
                "owner": "o",
                "review_by": "2027-01-01",
                "reason": "r",
            }]}),
            encoding="utf-8",
        )
        dispositions = root / "d.json"
        self.assertEqual(cmd_register_batch(root, dispositions, manifest), 0)
        doc = json.loads(dispositions.read_text(encoding="utf-8"))
        self.assertIn("dead.target", doc["targets"])
        self.assertEqual(doc["scripts"], {})

    def test_a_referenced_target_is_rejected_and_nothing_is_written(self) -> None:
        root = _temp_repo_with_one_dead_target()
        manifest = root / "m.json"
        manifest.write_text(
            json.dumps({"targets": [{
                "name": "not.dead",
                "disposition": "diagnostic_cli",
                "owner": "o",
                "review_by": "2027-01-01",
                "reason": "r",
            }]}),
            encoding="utf-8",
        )
        dispositions = root / "d.json"
        self.assertEqual(cmd_register_batch(root, dispositions, manifest), 3)
        self.assertFalse(dispositions.exists())

    def test_an_unknown_target_disposition_is_rejected(self) -> None:
        root = _temp_repo_with_one_dead_target()
        manifest = root / "m.json"
        manifest.write_text(
            json.dumps({"targets": [{
                "name": "dead.target",
                "disposition": "made_up",
                "owner": "o",
                "review_by": "2027-01-01",
                "reason": "r",
            }]}),
            encoding="utf-8",
        )
        dispositions = root / "d.json"
        self.assertEqual(cmd_register_batch(root, dispositions, manifest), 3)
        self.assertFalse(dispositions.exists())



class MissingAssetTest(unittest.TestCase):
    """A recipe that calls a path absent from the tree cannot run.

    That is the cheapest dead-surface proof there is, so it is measured and
    registered rather than left to inflate a "verification" count.
    """

    def test_state_flags_an_unregistered_absent_path(self) -> None:
        measured = {"a.b": ["scripts/migration/x.py"]}
        state = missing_asset_state(measured, {})
        self.assertEqual(state["targets_missing_asset_unregistered"], ["a.b"])

    def test_state_accepts_a_matching_record(self) -> None:
        measured = {"a.b": ["scripts/migration/x.py"]}
        registered = {"a.b": {"missing_asset": ["scripts/migration/x.py"]}}
        state = missing_asset_state(measured, registered)
        self.assertEqual(state["targets_missing_asset_unregistered"], [])
        self.assertEqual(state["stale_missing_asset_dispositions"], [])

    def test_an_edited_recipe_invalidates_the_record(self) -> None:
        measured = {"a.b": ["scripts/migration/x.py", "scripts/migration/y.py"]}
        registered = {"a.b": {"missing_asset": ["scripts/migration/x.py"]}}
        state = missing_asset_state(measured, registered)
        self.assertEqual(state["targets_missing_asset_unregistered"], ["a.b"])

    def test_a_repaired_recipe_makes_the_record_stale(self) -> None:
        state = missing_asset_state({}, {"a.b": {"missing_asset": ["scripts/migration/x.py"]}})
        self.assertEqual(state["stale_missing_asset_dispositions"], ["a.b"])

    def test_record_command_writes_the_measured_paths_and_requires_an_owner(self) -> None:
        root = _temp_repo_with_one_dead_target("dead.target:\n\t@bash scripts/nope.sh\n")
        dispositions = root / "d.json"
        self.assertEqual(cmd_record_missing_assets(root, dispositions, "r", "", "2027-01-01"), 2)
        self.assertEqual(cmd_record_missing_assets(root, dispositions, "  ", "o", "2027-01-01"), 2)
        self.assertEqual(cmd_record_missing_assets(root, dispositions, "r", "o", "2027-01-01"), 0)
        doc = json.loads(dispositions.read_text(encoding="utf-8"))
        self.assertEqual(doc["absent_assets"]["dead.target"]["missing_asset"], ["scripts/nope.sh"])
        state = missing_asset_state(
            {"dead.target": ["scripts/nope.sh"]}, doc["absent_assets"]
        )
        self.assertEqual(state["targets_missing_asset_unregistered"], [])



class UnregisterScriptTest(unittest.TestCase):
    """Removing a registration is as argued as making one, and cannot lie."""

    def test_missing_reason_is_rejected(self) -> None:
        self.assertEqual(
            cmd_unregister_script(ROOT, Path("/nonexistent/d.json"), "scripts/x.sh", "  "), 2
        )

    def test_a_still_unreferenced_script_cannot_be_unregistered(self) -> None:
        # A temp repo whose only script is dead: unregistering it would delete a
        # true statement, so the command refuses (exit 3) and writes nothing.
        root = _temp_repo_with_one_dead_target()
        dispositions = root / "d.json"
        dispositions.write_text(
            json.dumps({"schema_version": "v1", "targets": {}, "scripts": {
                "scripts/dead.sh": {"disposition": "retain", "owner": "o",
                                    "review_by": "2027-01-01", "reason": "r"}}}),
            encoding="utf-8",
        )
        self.assertEqual(
            cmd_unregister_script(root, dispositions, "scripts/dead.sh", "no longer true"), 3
        )
        doc = json.loads(dispositions.read_text(encoding="utf-8"))
        self.assertIn("scripts/dead.sh", doc["scripts"])



if __name__ == "__main__":
    unittest.main()
