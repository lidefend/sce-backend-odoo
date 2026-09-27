"""Boundary tests for the Gitee check-run id discovery entry.

The CI ledger and the platform are fakes: these tests prove refusal semantics
(missing, queued, wrong base, wrong commit, unconfirmed id) and that a usable set
is only reported when every required run is a success bound to this commit and
this target baseline.
"""
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.ops import gitee_check_run_ids as ids

HEAD = "a" * 40
MAIN = "b" * 40
OTHER = "c" * 40
REQUIRED = ids.REQUIRED_CHECKS


def delivered(*, head=HEAD, base=MAIN, conclusion="success", status="completed", pr=42):
    return json.dumps({"head_sha": head, "status": status, "conclusion": conclusion,
                       "output": {"summary": f"sce-formal-x; base={base}; pr={pr}; integration_eligible=false"}})


def row(name, ident, **kwargs):
    return {"name": name, "remote_id": ident, "delivered": delivered(**kwargs)}


def full_rows():
    return [row(name, index + 1) for index, name in enumerate(REQUIRED)]


class SelectTests(unittest.TestCase):
    def test_complete_success_set_is_selected(self):
        checks = ids.select_latest(full_rows(), head=HEAD, main=MAIN)
        self.assertEqual(set(checks), set(REQUIRED))
        self.assertTrue(all(item["conclusion"] == "success" for item in checks.values()))

    def test_the_newest_run_id_per_name_wins(self):
        rows = full_rows() + [row(REQUIRED[0], 99), row(REQUIRED[0], 7)]
        checks = ids.select_latest(rows, head=HEAD, main=MAIN)
        self.assertEqual(checks[REQUIRED[0]]["check_run_id"], 99)

    def test_a_newer_queued_run_is_not_masked_by_an_older_success(self):
        rows = full_rows() + [row(REQUIRED[1], 98, status="queued", conclusion=None)]
        with self.assertRaises(ids.Denied) as ctx:
            ids.select_latest(rows, head=HEAD, main=MAIN)
        self.assertIn("check_run_pending:" + REQUIRED[1], str(ctx.exception))

    def test_a_newer_failing_run_is_not_masked_by_an_older_success(self):
        rows = full_rows() + [row(REQUIRED[2], 97, conclusion="failure")]
        with self.assertRaises(ids.Denied) as ctx:
            ids.select_latest(rows, head=HEAD, main=MAIN)
        self.assertIn("check_run_not_success:" + REQUIRED[2], str(ctx.exception))

    def test_a_run_created_against_another_base_is_refused(self):
        rows = [row(name, index + 1, base=OTHER) if name == REQUIRED[0] else row(name, index + 1)
                for index, name in enumerate(REQUIRED)]
        with self.assertRaises(ids.Denied) as ctx:
            ids.select_latest(rows, head=HEAD, main=MAIN)
        self.assertIn("check_run_base_mismatch:" + REQUIRED[0], str(ctx.exception))

    def test_a_run_for_another_commit_is_ignored_not_reused(self):
        rows = [row(name, index + 1, head=OTHER) for index, name in enumerate(REQUIRED)]
        with self.assertRaises(ids.Denied) as ctx:
            ids.select_latest(rows, head=HEAD, main=MAIN)
        self.assertIn("check_run_missing", str(ctx.exception))

    def test_a_missing_required_name_refuses(self):
        with self.assertRaises(ids.Denied) as ctx:
            ids.select_latest(full_rows()[:3], head=HEAD, main=MAIN)
        self.assertIn("check_run_missing:" + REQUIRED[3], str(ctx.exception))

    def test_an_empty_ledger_refuses_rather_than_passing(self):
        with self.assertRaises(ids.Denied) as ctx:
            ids.select_latest([], head=HEAD, main=MAIN)
        self.assertIn("check_run_missing", str(ctx.exception))

    def test_a_missing_delivered_payload_counts_as_pending(self):
        rows = full_rows() + [{"name": REQUIRED[0], "remote_id": 96, "delivered": None}]
        with self.assertRaises(ids.Denied) as ctx:
            ids.select_latest(rows, head=HEAD, main=MAIN)
        self.assertIn("check_run_pending:" + REQUIRED[0], str(ctx.exception))

    def test_a_run_without_a_base_binding_refuses(self):
        bad = json.dumps({"head_sha": HEAD, "status": "completed", "conclusion": "success",
                          "output": {"summary": "sce-formal-x; integration_eligible=false"}})
        rows = [{"name": name, "remote_id": index + 1, "delivered": bad} for index, name in enumerate(REQUIRED)]
        with self.assertRaises(ids.Denied) as ctx:
            ids.select_latest(rows, head=HEAD, main=MAIN)
        self.assertIn("check_run_base_unknown", str(ctx.exception))

    def test_an_unusable_id_counts_as_missing(self):
        rows = [{"name": name, "remote_id": bad, "delivered": delivered()}
                for name, bad in zip(REQUIRED, (0, -1, None, "9"))]
        with self.assertRaises(ids.Denied) as ctx:
            ids.select_latest(rows, head=HEAD, main=MAIN)
        self.assertIn("check_run_missing", str(ctx.exception))

    def test_an_unknown_check_name_is_ignored_not_selected(self):
        checks = ids.select_latest(full_rows() + [row("smoke_gate", 500)], head=HEAD, main=MAIN)
        self.assertEqual(set(checks), set(REQUIRED))


class ConfirmTests(unittest.TestCase):
    def run_collect(self, ledger_rows, platform, **kwargs):
        with patch.object(ids, "read_ledger", return_value=ledger_rows), \
             patch.object(ids, "request", platform):
            return ids.collect("token", head=HEAD, main=MAIN, **kwargs)

    def test_a_confirmed_set_is_reported_with_ready_value(self):
        runs = {item["id"]: {"name": item["name"], "head_sha": HEAD, "status": "completed",
                             "conclusion": "success"} for item in
                [{"id": index + 1, "name": name} for index, name in enumerate(REQUIRED)]}
        receipt = self.run_collect(full_rows(), lambda token, path: runs[int(path.rsplit("/", 1)[-1])])
        self.assertTrue(receipt["merge_ready"])
        self.assertFalse(receipt["merge_authorized"])
        self.assertEqual(receipt["writes"], 0)
        self.assertEqual(set(receipt["check_runs"].split()),
                         {f"{name}={index + 1}" for index, name in enumerate(REQUIRED)})

    def test_a_platform_name_mismatch_refuses(self):
        runs = {index + 1: {"name": "some_other_gate", "head_sha": HEAD} for index in range(4)}
        with self.assertRaises(ids.Denied) as ctx:
            self.run_collect(full_rows(), lambda token, path: runs[int(path.rsplit("/", 1)[-1])])
        self.assertIn("platform_name_mismatch", str(ctx.exception))

    def test_a_platform_head_mismatch_refuses(self):
        runs = {index + 1: {"name": name, "head_sha": OTHER} for index, name in enumerate(REQUIRED)}
        with self.assertRaises(ids.Denied) as ctx:
            self.run_collect(full_rows(), lambda token, path: runs[int(path.rsplit("/", 1)[-1])])
        self.assertIn("platform_stale_sha", str(ctx.exception))

    def test_a_platform_refusal_is_not_a_pass(self):
        def denied(token, path):
            raise ids.Denied("platform_failed status=404")
        with self.assertRaises(ids.Denied):
            self.run_collect(full_rows(), denied)

    def test_a_bad_sha_refuses_before_any_read(self):
        with patch.object(ids, "read_ledger", side_effect=AssertionError("must not read")):
            with self.assertRaises(ids.Denied):
                ids.collect("token", head="short", main=MAIN)
            with self.assertRaises(ids.Denied):
                ids.collect("token", head=HEAD, main="")


class LedgerTests(unittest.TestCase):
    def test_a_transport_failure_is_a_stop_not_an_empty_set(self):
        with patch.object(ids.subprocess, "run", side_effect=OSError("no route")):
            with self.assertRaises(ids.Denied) as ctx:
                ids.read_ledger(head=HEAD)
        self.assertIn("ci_ledger_unreachable", str(ctx.exception))

    def test_a_nonzero_exit_is_a_stop(self):
        class Result:
            returncode, stdout, stderr = 255, "", "denied"
        with patch.object(ids.subprocess, "run", return_value=Result()):
            with self.assertRaises(ids.Denied) as ctx:
                ids.read_ledger(head=HEAD)
        self.assertIn("ci_ledger_unreadable", str(ctx.exception))

    def test_unparsable_output_is_a_stop(self):
        class Result:
            returncode, stdout, stderr = 0, "not json", ""
        with patch.object(ids.subprocess, "run", return_value=Result()):
            with self.assertRaises(ids.Denied) as ctx:
                ids.read_ledger(head=HEAD)
        self.assertIn("ci_ledger_unreadable", str(ctx.exception))

    def test_the_commit_travels_as_an_argument_never_a_shell_string(self):
        seen = {}

        class Result:
            returncode, stdout = 0, json.dumps({"rows": []})

        def fake_run(argv, **kwargs):
            seen["argv"], seen["input"] = argv, kwargs.get("input")
            return Result()

        with patch.object(ids.subprocess, "run", fake_run):
            ids.read_ledger(head=HEAD)
        self.assertIn("python3", seen["argv"])
        self.assertIn(HEAD, seen["argv"])
        self.assertNotIn(HEAD, seen["input"])
        self.assertIn("mode=ro", seen["input"])

    def test_an_unsafe_ledger_path_refuses(self):
        with self.assertRaises(ids.Denied):
            ids.read_ledger(head=HEAD, db="/var/lib/x; rm -rf /")


class TokenTests(unittest.TestCase):
    def test_a_group_readable_token_file_is_refused(self):
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "token"
            path.write_text("x")
            path.chmod(0o644)
            self.assertEqual(path.stat().st_uid, os.getuid())
            with self.assertRaises(SystemExit):
                ids.read_token(path)


if __name__ == "__main__":
    unittest.main()
