from __future__ import annotations

import tempfile
import unittest
from unittest import mock
from pathlib import Path

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
        self.assertIsNone(translate_command("部署日常 main"))

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


if __name__ == "__main__":
    unittest.main()
