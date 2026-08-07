from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from scripts.ops.feishu_agent_bridge import (
    BridgeConfig,
    BridgeError,
    FeishuBridge,
    translate_command,
    validate_agent_command,
)


class FeishuCommandTest(unittest.TestCase):
    def test_translates_direct_chinese_commands(self) -> None:
        self.assertEqual(translate_command("状态"), "/agent status")
        self.assertEqual(translate_command("进度"), "/agent status")
        self.assertEqual(translate_command("开始\n只读检查仓库"), "/agent start\n只读检查仓库")
        self.assertEqual(translate_command("继续 修复后重试"), "/agent continue 修复后重试")
        self.assertEqual(translate_command("停止"), "/agent stop")

    def test_strips_group_mention_and_validates_decision(self) -> None:
        self.assertEqual(translate_command("@_user_1 状态"), "/agent status")
        self.assertEqual(
            translate_command("批准 decision-20260804-001 A"),
            "/agent approve decision-20260804-001 A",
        )
        self.assertIsNone(translate_command("批准 wrong A"))

    def test_daily_deploy_requires_full_sha(self) -> None:
        self.assertEqual(translate_command("部署日常 " + "a" * 40), "/agent deploy daily " + "a" * 40)
        self.assertEqual(
            translate_command("部署日常 feature/example " + "b" * 40),
            "/agent deploy daily feature/example " + "b" * 40,
        )
        self.assertIsNone(translate_command("部署日常 main"))
        self.assertIsNone(translate_command("部署日常 main " + "b" * 40))

    def test_command_validation_is_fail_closed(self) -> None:
        validate_agent_command("/agent status")
        with self.assertRaises(BridgeError):
            validate_agent_command("/agent shell anything")
        with self.assertRaises(BridgeError):
            validate_agent_command("/agent start")

    def test_child_process_does_not_receive_feishu_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            binding = root / "binding.json"
            binding.write_text('{"open_id":"user","chat_id":"chat"}\n', encoding="utf-8")
            config = BridgeConfig(root, "owner/repo", 1, root, "app", "secret", binding)
            with mock.patch.dict(
                "os.environ",
                {
                    "AGENT_FEISHU_APP_ID": "app",
                    "AGENT_FEISHU_APP_SECRET": "secret",
                    "AGENT_GH_BIN": "/opt/gh/bin/gh",
                },
                clear=True,
            ):
                environment = FeishuBridge(config).child_environment()
            self.assertNotIn("AGENT_FEISHU_APP_ID", environment)
            self.assertNotIn("AGENT_FEISHU_APP_SECRET", environment)
            self.assertEqual(
                environment["PATH"].split(":"),
                ["/opt/gh/bin", "/usr/local/bin", "/usr/bin", "/bin"],
            )

    def test_status_query_replies_directly_without_github_audit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run_dir = root / "runs" / "task-1"
            run_dir.mkdir(parents=True)
            (run_dir / "codex-events.jsonl").write_text(
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {"type": "agent_message", "text": "正在检查浏览器证据"},
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            (root / "state.json").write_text(
                json.dumps(
                    {
                        "status": "RUNNING",
                        "task": {
                            "id": "task-1",
                            "branch": "codex/test",
                            "run_dir": str(run_dir),
                        },
                    }
                ),
                encoding="utf-8",
            )
            binding = root / "binding.json"
            binding.write_text('{"open_id":"user","chat_id":"chat"}\n', encoding="utf-8")
            bridge = FeishuBridge(BridgeConfig(root, "owner/repo", 1, root, "app", "secret", binding))
            bridge.reply = mock.Mock()
            bridge.submit_audit = mock.Mock()
            message = SimpleNamespace(
                message_type="text",
                message_id="message-1",
                chat_id="chat",
                content=json.dumps({"text": "状态"}, ensure_ascii=False),
            )
            sender = SimpleNamespace(sender_id=SimpleNamespace(open_id="user"))
            bridge.receive(SimpleNamespace(event=SimpleNamespace(message=message, sender=sender)))
            bridge.submit_audit.assert_not_called()
            reply = bridge.reply.call_args.args[1]
            self.assertIn("任务实时状态", reply)
            self.assertIn("正在检查浏览器证据", reply)


if __name__ == "__main__":
    unittest.main()
