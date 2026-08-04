#!/usr/bin/env python3
"""Receive trusted Feishu app-bot commands and audit them through GitHub."""

from __future__ import annotations

import argparse
import json
import os
import queue
import re
import subprocess
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from scripts.ops.agent_progress import format_status, load_snapshot
except ModuleNotFoundError:  # installed beside the bridge
    from agent_progress import format_status, load_snapshot


FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DECISION_RE = re.compile(r"^decision-[0-9]{8}-[0-9]{3}$")
MENTION_RE = re.compile(r"@_user_[0-9]+\s*")
MAX_TEXT_CHARS = 12_000
MAX_PROCESSED_IDS = 2_000


class BridgeError(ValueError):
    pass


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw or raw.startswith("#"):
            continue
        key, separator, value = raw.partition("=")
        if separator and re.fullmatch(r"AGENT_[A-Z0-9_]+", key):
            values[key] = value
    return values


def normalize_text(text: str) -> str:
    return MENTION_RE.sub("", text).strip()


def translate_command(text: str) -> str | None:
    value = normalize_text(text)
    if not value or len(value) > MAX_TEXT_CHARS:
        return None
    if value.startswith("/agent "):
        return value
    if value in {"状态", "进度", "status", "Status", "progress", "Progress"}:
        return "/agent status"
    if value == "停止":
        return "/agent stop"
    if value.startswith("开始"):
        task = value[2:].strip()
        return f"/agent start\n{task}" if task else None
    if value.startswith("继续"):
        context = value[2:].strip()
        return f"/agent continue {context}".rstrip()
    for chinese, action in (("批准", "approve"), ("拒绝", "reject")):
        if value.startswith(chinese):
            parts = value[len(chinese) :].strip().split(maxsplit=1)
            if len(parts) == 2 and DECISION_RE.fullmatch(parts[0]):
                return f"/agent {action} {parts[0]} {parts[1]}"
            return None
    if value.startswith("部署日常"):
        sha = value[4:].strip()
        return f"/agent deploy daily {sha}" if FULL_SHA_RE.fullmatch(sha) else None
    return None


def validate_agent_command(command: str) -> None:
    first = command.strip().splitlines()[0].split()
    if len(first) < 2 or first[0] != "/agent":
        raise BridgeError("command must start with /agent")
    action = first[1]
    if action not in {"start", "status", "continue", "approve", "reject", "deploy", "stop"}:
        raise BridgeError("unsupported agent action")
    if action == "start" and not command.partition("\n")[2].strip():
        raise BridgeError("start requires a task body")


@dataclass(frozen=True)
class BridgeConfig:
    repository_root: Path
    repository: str
    issue: int
    state_root: Path
    app_id: str
    app_secret: str
    binding_path: Path

    @classmethod
    def from_environment(cls) -> "BridgeConfig":
        root = Path(os.environ["AGENT_REPOSITORY_ROOT"]).resolve()
        state_root = Path(os.environ.get("AGENT_STATE_ROOT", root / ".runtime" / "agent-controller")).resolve()
        app_id = os.environ.get("AGENT_FEISHU_APP_ID", "").strip()
        app_secret = os.environ.get("AGENT_FEISHU_APP_SECRET", "").strip()
        if not app_id or not app_secret:
            raise BridgeError("Feishu app credentials are required")
        binding_path = state_root / "feishu-pending-binding.json"
        if not binding_path.is_file() or (binding_path.stat().st_mode & 0o777) not in {0o600, 0o400}:
            raise BridgeError("a mode-0600 Feishu binding is required")
        binding = json.loads(binding_path.read_text(encoding="utf-8"))
        if not binding.get("open_id") or not binding.get("chat_id"):
            raise BridgeError("Feishu binding is incomplete")
        return cls(
            repository_root=root,
            repository=os.environ["AGENT_GITHUB_REPOSITORY"],
            issue=int(os.environ["AGENT_GITHUB_CONTROL_ISSUE"]),
            state_root=state_root,
            app_id=app_id,
            app_secret=app_secret,
            binding_path=binding_path,
        )


class ProcessedStore:
    def __init__(self, path: Path):
        self.path = path
        self.ids: list[str] = []
        if path.exists():
            self.ids = list(json.loads(path.read_text(encoding="utf-8")).get("message_ids", []))

    def contains(self, message_id: str) -> bool:
        return message_id in self.ids

    def add(self, message_id: str) -> None:
        if message_id in self.ids:
            return
        self.ids = [*self.ids, message_id][-MAX_PROCESSED_IDS:]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps({"message_ids": self.ids}, indent=2) + "\n", encoding="utf-8")
        os.chmod(temporary, 0o600)
        os.replace(temporary, self.path)


class FeishuBridge:
    def __init__(self, config: BridgeConfig):
        self.config = config
        self.binding = json.loads(config.binding_path.read_text(encoding="utf-8"))
        self.processed = ProcessedStore(config.state_root / "feishu-processed.json")
        self.pending: queue.Queue[tuple[str, str]] = queue.Queue()
        self.inflight: set[str] = set()
        self.inflight_lock = threading.Lock()
        self.api_client: Any = None

    def live_status_text(self) -> str:
        snapshot = load_snapshot(self.config.state_root)
        if snapshot is None:
            return "【任务状态】\n控制器尚未生成状态文件。"
        return format_status(snapshot)

    def child_environment(self) -> dict[str, str]:
        environment = dict(os.environ)
        for key in (
            "AGENT_FEISHU_APP_ID",
            "AGENT_FEISHU_APP_SECRET",
            "AGENT_FEISHU_WEBHOOK_URL",
            "AGENT_FEISHU_WEBHOOK_SECRET",
        ):
            environment.pop(key, None)
        gh_dir = str(Path(os.environ.get("AGENT_GH_BIN", "gh")).expanduser().absolute().parent)
        inherited_path = environment.get("PATH", "/usr/local/bin:/usr/bin:/bin")
        environment["PATH"] = os.pathsep.join(dict.fromkeys([gh_dir, inherited_path]))
        return environment

    def submit_audit(self, message_id: str, command: str) -> None:
        outbox = self.config.state_root / "feishu-outbox"
        outbox.mkdir(parents=True, exist_ok=True)
        safe_id = re.sub(r"[^A-Za-z0-9_-]", "_", message_id)[:120]
        path = outbox / f"{safe_id}.txt"
        path.write_text(command.rstrip() + "\n", encoding="utf-8")
        os.chmod(path, 0o600)
        result = subprocess.run(
            [
                "make",
                "--no-print-directory",
                "agent.controller.audit.command",
                f"AGENT_CONTROLLER_COMMAND_FILE={path}",
                f"AGENT_CONTROLLER_GITHUB_REPOSITORY={self.config.repository}",
                f"AGENT_CONTROLLER_GITHUB_CONTROL_ISSUE={self.config.issue}",
            ],
            cwd=self.config.repository_root,
            env=self.child_environment(),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=45,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError("GitHub audit command submission failed")
        self.processed.add(message_id)

    def worker(self) -> None:
        while True:
            message_id, command = self.pending.get()
            try:
                self.submit_audit(message_id, command)
                self.safe_reply(message_id, "指令已进入受控队列，并写入 GitHub 审计记录。")
            except Exception:
                self.safe_reply(message_id, "指令入队失败，未执行。请稍后重试。")
            finally:
                with self.inflight_lock:
                    self.inflight.discard(message_id)
                self.pending.task_done()

    def safe_reply(self, message_id: str, text: str) -> None:
        try:
            self.reply(message_id, text)
        except Exception as exc:
            print(f"FEISHU_BRIDGE_REPLY_ERROR={type(exc).__name__}", file=sys.stderr, flush=True)

    def reply(self, message_id: str, text: str) -> None:
        import lark_oapi as lark
        from lark_oapi.api.im.v1 import ReplyMessageRequest, ReplyMessageRequestBody

        body = (
            ReplyMessageRequestBody.builder()
            .content(json.dumps({"text": text}, ensure_ascii=False))
            .msg_type("text")
            .build()
        )
        request = ReplyMessageRequest.builder().message_id(message_id).request_body(body).build()
        response = self.api_client.im.v1.message.reply(request)
        if not response.success():
            raise RuntimeError(f"Feishu reply failed code={response.code}")

    def receive(self, data: Any) -> None:
        event = data.event
        message = event.message if event else None
        sender = event.sender if event else None
        sender_id = sender.sender_id if sender else None
        if not message or not sender_id or message.message_type != "text":
            return
        if getattr(sender_id, "open_id", "") != self.binding["open_id"]:
            self.safe_reply(message.message_id, "该飞书用户未获授权，指令未执行。")
            return
        if message.chat_id != self.binding["chat_id"]:
            self.safe_reply(message.message_id, "该会话未获授权，指令未执行。")
            return
        with self.inflight_lock:
            if self.processed.contains(message.message_id) or message.message_id in self.inflight:
                return
            self.inflight.add(message.message_id)
        try:
            payload = json.loads(message.content or "{}")
            text = str(payload.get("text") or "")
        except (TypeError, ValueError):
            with self.inflight_lock:
                self.inflight.discard(message.message_id)
            self.safe_reply(message.message_id, "仅支持文本指令。")
            return
        command = translate_command(text)
        if command is None:
            with self.inflight_lock:
                self.inflight.discard(message.message_id)
            self.safe_reply(message.message_id, "无法识别。可用：状态、进度、开始、继续、批准、拒绝、停止、部署日常。")
            return
        try:
            validate_agent_command(command)
        except BridgeError:
            with self.inflight_lock:
                self.inflight.discard(message.message_id)
            self.safe_reply(message.message_id, "指令格式不完整，未执行。")
            return
        if command == "/agent status":
            try:
                self.reply(message.message_id, self.live_status_text())
                self.processed.add(message.message_id)
            except Exception as exc:
                print(
                    f"FEISHU_STATUS_QUERY_ERROR={type(exc).__name__}",
                    file=sys.stderr,
                    flush=True,
                )
            finally:
                with self.inflight_lock:
                    self.inflight.discard(message.message_id)
            return
        self.pending.put((message.message_id, command))
        self.safe_reply(message.message_id, "指令已接收，正在写入受控队列。")

    def run(self) -> None:
        import lark_oapi as lark

        self.api_client = (
            lark.Client.builder()
            .app_id(self.config.app_id)
            .app_secret(self.config.app_secret)
            .log_level(lark.LogLevel.ERROR)
            .build()
        )
        threading.Thread(target=self.worker, name="feishu-command-audit", daemon=True).start()
        handler = (
            lark.EventDispatcherHandler.builder("", "")
            .register_p2_im_message_receive_v1(self.receive)
            .build()
        )
        client = lark.ws.Client(
            self.config.app_id,
            self.config.app_secret,
            event_handler=handler,
            log_level=lark.LogLevel.ERROR,
        )
        client.start()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("run", "config-check", "validate-command-file"))
    parser.add_argument("--file")
    args = parser.parse_args()
    if args.command == "validate-command-file":
        if not args.file:
            raise BridgeError("--file is required")
        path = Path(args.file).resolve()
        root = Path(os.environ["AGENT_STATE_ROOT"]).resolve() / "feishu-outbox"
        path.relative_to(root)
        if (path.stat().st_mode & 0o777) != 0o600:
            raise BridgeError("command file must use mode 0600")
        validate_agent_command(path.read_text(encoding="utf-8"))
        return 0
    config = BridgeConfig.from_environment()
    if args.command == "config-check":
        print(
            "FEISHU_BRIDGE_CONFIG="
            + json.dumps(
                {
                    "status": "PASS",
                    "repository": config.repository,
                    "issue": config.issue,
                    "binding_configured": True,
                },
                sort_keys=True,
            )
        )
        return 0
    FeishuBridge(config).run()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (BridgeError, KeyError, OSError, ValueError) as exc:
        print(f"FEISHU_BRIDGE_ERROR={exc}", file=sys.stderr)
        raise SystemExit(2)
