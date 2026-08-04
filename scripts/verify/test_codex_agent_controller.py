from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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


if __name__ == "__main__":
    unittest.main()
