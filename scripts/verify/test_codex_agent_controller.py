from __future__ import annotations

import base64
import dataclasses
import datetime as dt
import hashlib
import hmac
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.ops.agent_progress import snapshot_from_state
from scripts.ops.codex_agent_controller import (
    CommandRejected,
    Config,
    Controller,
    FeishuNotifier,
    GitHubIssueReader,
    OwnerCommand,
    StateStore,
    feishu_signature,
    output_schema,
    parse_owner_command,
)


class CommandParserTest(unittest.TestCase):
    def test_start_accepts_multiline_task_without_shell_interpretation(self) -> None:
        command = parse_owner_command("/agent start\n修复列表页；$(touch /tmp/never-run)")
        self.assertEqual(command.action, "start")
        self.assertIn("$(touch", command.argument)

    def test_decision_and_daily_deploy_are_strict(self) -> None:
        approved = parse_owner_command("/agent approve decision-20260804-001 A")
        self.assertEqual(approved.decision_id, "decision-20260804-001")
        deployed = parse_owner_command("/agent deploy daily " + "a" * 40)
        self.assertEqual(deployed, OwnerCommand(action="deploy_daily", sha="a" * 40))
        with self.assertRaises(CommandRejected):
            parse_owner_command("/agent deploy production " + "a" * 40)

    def test_unknown_and_argument_smuggling_are_rejected(self) -> None:
        with self.assertRaises(CommandRejected):
            parse_owner_command("/agent status now")
        with self.assertRaises(CommandRejected):
            parse_owner_command("/agent shell rm -rf something")
        self.assertIsNone(parse_owner_command("ordinary discussion"))


class FeishuTest(unittest.TestCase):
    def test_signature_matches_official_algorithm(self) -> None:
        timestamp = 1_599_360_473
        secret = "test-secret"
        expected = base64.b64encode(
            hmac.new(f"{timestamp}\n{secret}".encode(), digestmod=hashlib.sha256).digest()
        ).decode()
        self.assertEqual(feishu_signature(timestamp, secret), expected)

    @mock.patch("scripts.ops.codex_agent_controller.urllib.request.urlopen")
    def test_notifier_uses_utf8_and_does_not_put_webhook_in_message(self, urlopen: mock.Mock) -> None:
        response = mock.MagicMock()
        response.__enter__.return_value.read.return_value = b'{"code":0,"msg":"success"}'
        urlopen.return_value = response
        config = Config(
            repository_root=Path("/tmp/repo"),
            github_repository="owner/repo",
            github_issue=1,
            allowed_sender="owner",
            state_root=Path("/tmp/repo/.runtime/controller"),
            poll_seconds=20,
            max_runtime_seconds=3600,
            codex_bin="codex",
            gh_bin="gh",
            feishu_webhook_url="https://open.feishu.cn/open-apis/bot/v2/hook/test",
            feishu_webhook_secret="secret",
            notification_prefix="SCE Codex",
        )
        FeishuNotifier(config).notify("需要决策", "中文消息")
        request = urlopen.call_args.args[0]
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["msg_type"], "text")
        self.assertIn("中文消息", payload["content"]["text"])
        self.assertNotIn(config.feishu_webhook_url, payload["content"]["text"])


class StateAndGitHubTest(unittest.TestCase):
    def config(self, root: Path) -> Config:
        return Config(
            repository_root=root,
            github_repository="owner/repo",
            github_issue=9,
            allowed_sender="trusted-owner",
            state_root=root / ".runtime" / "controller",
            poll_seconds=20,
            max_runtime_seconds=3600,
            codex_bin="codex",
            gh_bin="gh",
            feishu_webhook_url="",
            feishu_webhook_secret="",
            notification_prefix="SCE Codex",
        )

    def test_state_write_is_round_trip_and_utf8(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = StateStore(Path(directory))
            state = store.default()
            state["task"] = {"description": "移动端验收"}
            store.save(state)
            self.assertEqual(store.load()["task"]["description"], "移动端验收")

    @mock.patch("scripts.ops.codex_agent_controller.run_checked")
    def test_github_reader_uses_get_and_sorts_comments(self, run: mock.Mock) -> None:
        run.return_value = json.dumps([[{"id": 3}, {"id": 1}]])
        config = mock.Mock(
            github_repository="owner/repo",
            github_issue=9,
            repository_root=Path("/tmp/repo"),
            gh_bin="gh",
        )
        rows = GitHubIssueReader(config).comments()
        self.assertEqual([row["id"] for row in rows], [1, 3])
        command = run.call_args.args[0]
        self.assertEqual(command[0:4], ["gh", "api", "--method", "GET"])

    def test_result_schema_is_closed_and_requires_decision(self) -> None:
        schema = output_schema()
        self.assertFalse(schema["additionalProperties"])
        self.assertIn("decision", schema["required"])

    def test_config_rejects_non_integer_polling_values_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".git").mkdir()
            environment = {
                "AGENT_REPOSITORY_ROOT": str(root),
                "AGENT_GITHUB_REPOSITORY": "owner/repo",
                "AGENT_GITHUB_CONTROL_ISSUE": "1",
                "AGENT_GITHUB_ALLOWED_SENDER": "owner",
                "AGENT_POLL_SECONDS": "not-a-number",
            }
            with mock.patch.dict(os.environ, environment, clear=True):
                with self.assertRaisesRegex(ValueError, "must be integers"):
                    Config.from_env(require_notification=False)

    def test_runtime_config_requires_signed_official_feishu_webhook(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".git").mkdir()
            environment = {
                "AGENT_REPOSITORY_ROOT": str(root),
                "AGENT_GITHUB_REPOSITORY": "owner/repo",
                "AGENT_GITHUB_CONTROL_ISSUE": "1",
                "AGENT_GITHUB_ALLOWED_SENDER": "owner",
                "AGENT_FEISHU_WEBHOOK_URL": "https://open.feishu.cn/open-apis/bot/v2/hook/test",
            }
            with mock.patch.dict(os.environ, environment, clear=True):
                with self.assertRaisesRegex(ValueError, "WEBHOOK_SECRET is required"):
                    Config.from_env(require_notification=True)

    def test_first_start_cursors_old_comments_without_execution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            controller = Controller(self.config(Path(directory)))
            controller.github.comments = mock.Mock(return_value=[{"id": 7}, {"id": 12}])
            controller.safe_notify = mock.Mock()
            state = controller.initialize(controller.store.default())
            self.assertEqual(state["last_comment_id"], 12)
            self.assertEqual(state["status"], "IDLE")
            controller.safe_notify.assert_called_once()

    def test_unauthorized_command_never_launches_worker(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            controller = Controller(self.config(Path(directory)))
            controller.safe_notify = mock.Mock()
            controller.start_task = mock.Mock()
            state = controller.store.default()
            controller.handle_comment(
                state,
                {"id": 20, "body": "/agent start do something", "user": {"login": "intruder"}},
            )
            controller.start_task.assert_not_called()
            self.assertEqual(state["last_comment_id"], 20)

    def test_worker_environment_strips_controller_and_github_tokens(self) -> None:
        with tempfile.TemporaryDirectory() as directory, mock.patch.dict(
            "os.environ",
            {
                "AGENT_FEISHU_WEBHOOK_URL": "secret-url",
                "AGENT_FEISHU_WEBHOOK_SECRET": "secret-key",
                "GH_TOKEN": "github-token",
                "GITHUB_TOKEN": "github-token-2",
            },
        ):
            environment = Controller(self.config(Path(directory))).worker_environment()
            self.assertNotIn("AGENT_FEISHU_WEBHOOK_URL", environment)
            self.assertNotIn("AGENT_FEISHU_WEBHOOK_SECRET", environment)
            self.assertNotIn("GH_TOKEN", environment)
            self.assertNotIn("GITHUB_TOKEN", environment)

    def test_worker_environment_exposes_codex_runtime_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            codex_bin_dir = root / "nvm" / "bin"
            codex_target = root / "nvm" / "lib" / "codex.js"
            codex_bin_dir.mkdir(parents=True)
            codex_target.parent.mkdir(parents=True)
            codex_target.touch()
            (codex_bin_dir / "codex").symlink_to(codex_target)
            config = dataclasses.replace(
                self.config(root),
                codex_bin=str(codex_bin_dir / "codex"),
                gh_bin="/opt/github-cli/bin/gh",
            )
            environment = Controller(config).worker_environment()
            path_parts = environment["PATH"].split(os.pathsep)
            self.assertEqual(path_parts[:2], [str(codex_bin_dir), "/opt/github-cli/bin"])

    def test_running_task_sends_initial_progress_heartbeat(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = dataclasses.replace(self.config(root), progress_initial_seconds=60)
            controller = Controller(config)
            controller.safe_notify = mock.Mock()
            run_dir = root / "run"
            run_dir.mkdir()
            (run_dir / "codex-events.jsonl").write_text(
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {"type": "agent_message", "text": "已完成预检"},
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            state = controller.store.default()
            state["status"] = "RUNNING"
            state["task"] = {
                "id": "task-1",
                "branch": "codex/test",
                "run_dir": str(run_dir),
                "turn_started_at": (
                    dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=61)
                ).isoformat(),
                "progress_last_notified_epoch": 0,
                "progress_stale_notified": False,
            }
            controller.maybe_notify_progress(state)
            controller.safe_notify.assert_called_once()
            title, body = controller.safe_notify.call_args.args
            self.assertEqual(title, "任务进度")
            self.assertIn("已完成预检", body)
            self.assertGreater(state["task"]["progress_last_notified_epoch"], 0)

    def test_stalled_task_alert_is_not_repeated_without_new_activity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            controller = Controller(self.config(root))
            controller.safe_notify = mock.Mock()
            run_dir = root / "run"
            run_dir.mkdir()
            events = run_dir / "codex-events.jsonl"
            events.write_text("{}\n", encoding="utf-8")
            stale_epoch = int(dt.datetime.now(dt.timezone.utc).timestamp()) - 601
            os.utime(events, (stale_epoch, stale_epoch))
            state = controller.store.default()
            state["status"] = "RUNNING"
            state["task"] = {
                "id": "task-1",
                "branch": "codex/test",
                "run_dir": str(run_dir),
                "turn_started_at": (
                    dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=700)
                ).isoformat(),
                "progress_last_notified_epoch": 0,
                "progress_stale_notified": False,
                "progress_last_activity_epoch": None,
            }
            controller.maybe_notify_progress(state)
            controller.maybe_notify_progress(state)
            controller.safe_notify.assert_called_once()
            self.assertEqual(controller.safe_notify.call_args.args[0], "任务可能停滞")

    def test_completed_snapshot_uses_last_event_as_elapsed_end(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run_dir = root / "run"
            run_dir.mkdir()
            events = run_dir / "codex-events.jsonl"
            events.write_text("{}\n", encoding="utf-8")
            os.utime(events, (1_060, 1_060))
            snapshot = snapshot_from_state(
                {
                    "status": "COMPLETED",
                    "task": {
                        "id": "task-1",
                        "run_dir": str(run_dir),
                        "turn_started_at": dt.datetime.fromtimestamp(
                            1_000, dt.timezone.utc
                        ).isoformat(),
                    },
                },
                now=2_000,
            )
            self.assertEqual(snapshot.elapsed_seconds, 60)

    def test_worker_command_uses_supported_noninteractive_approval_config(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            controller = Controller(self.config(root))
            run_dir = root / "run"
            run_dir.mkdir()
            task = {"run_dir": str(run_dir), "session_id": "session-1"}
            initial = controller._worker_command(task, "audit", resume=False)
            resumed = controller._worker_command(task, "continue", resume=True)
            for command in (initial, resumed):
                self.assertNotIn("--ask-for-approval", command)
                self.assertIn("--strict-config", command)
                self.assertIn('approval_policy="never"', command)

    def test_restart_retries_pre_session_failure_once(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            controller = Controller(self.config(Path(directory)))
            controller.github.comments = mock.Mock(return_value=[])
            controller.safe_notify = mock.Mock()
            controller.launch = mock.Mock()
            state = controller.store.default()
            state.update(
                {
                    "status": "FAILED_RECOVERABLE",
                    "task": {
                        "id": "task-1",
                        "description": "read-only audit",
                        "session_id": None,
                        "startup_retry_count": 0,
                        "startup_recovery_generation": None,
                    },
                }
            )
            controller.store.save(state)
            controller.initialize(state)
            self.assertEqual(state["task"]["startup_retry_count"], 1)
            controller.launch.assert_called_once()

            controller.launch.reset_mock()
            state["status"] = "FAILED_RECOVERABLE"
            controller.initialize(state)
            controller.launch.assert_not_called()

    def test_restart_resumes_existing_session_once_per_recovery_generation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            controller = Controller(self.config(Path(directory)))
            controller.github.comments = mock.Mock(return_value=[])
            controller.safe_notify = mock.Mock()
            controller.launch = mock.Mock()
            state = controller.store.default()
            state.update(
                {
                    "status": "FAILED_RECOVERABLE",
                    "task": {
                        "id": "task-2",
                        "description": "read-only audit",
                        "session_id": "session-2",
                        "startup_retry_count": 0,
                        "startup_recovery_generation": None,
                    },
                }
            )
            controller.store.save(state)
            controller.initialize(state)
            controller.launch.assert_called_once_with(state, mock.ANY, resume=True)

    def test_manual_continue_relaunches_failure_without_session(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            controller = Controller(self.config(Path(directory)))
            controller.launch = mock.Mock()
            state = controller.store.default()
            state.update(
                {
                    "status": "FAILED_RECOVERABLE",
                    "task": {
                        "id": "task-1",
                        "description": "read-only audit",
                        "session_id": None,
                        "startup_retry_count": 1,
                    },
                }
            )
            controller.resume_task(state, OwnerCommand(action="continue", argument="retry"))
            controller.launch.assert_called_once()


if __name__ == "__main__":
    unittest.main()
