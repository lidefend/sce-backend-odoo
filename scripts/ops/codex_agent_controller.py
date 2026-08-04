#!/usr/bin/env python3
"""Long-running Codex controller driven by trusted GitHub Issue comments.

GitHub is the audited command channel. Feishu is notification-only. The
controller never evaluates comment text as shell input and launches at most one
Codex worker for a repository at a time.
"""

from __future__ import annotations

import argparse
import base64
import dataclasses
import datetime as dt
import fcntl
import hashlib
import hmac
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "sce.codex_agent_controller.v1"
ALLOWED_BRANCH_RE = re.compile(r"^(feature|fix|refactor|audit|release|codex)/.+$")
FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DECISION_ID_RE = re.compile(r"^decision-[0-9]{8}-[0-9]{3}$")
GITHUB_REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
GITHUB_LOGIN_RE = re.compile(r"^[A-Za-z0-9-]{1,39}$")
FEISHU_WEBHOOK_RE = re.compile(
    r"^https://open\.feishu\.cn/open-apis/bot/v2/hook/[A-Za-z0-9-]+$"
)
ACTIVE_STATUSES = {"RUNNING", "STOP_REQUESTED"}
RESUMABLE_STATUSES = {"DECISION_REQUIRED", "FAILED_RECOVERABLE", "PAUSED_RECOVERABLE"}
TERMINAL_STATUSES = {"IDLE", "COMPLETED", "STOPPED"}
MAX_TASK_CHARS = 12_000
MAX_NOTIFICATION_CHARS = 8_000
STARTUP_RECOVERY_GENERATION = "systemd-bwrap-pty-v4"


class ConfigurationError(ValueError):
    """Configuration is incomplete or violates a fail-closed boundary."""


class CommandRejected(ValueError):
    """A syntactically invalid or state-incompatible owner command."""


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def env_required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ConfigurationError(f"{name} is required")
    return value


@dataclasses.dataclass(frozen=True)
class Config:
    repository_root: Path
    github_repository: str
    github_issue: int
    allowed_sender: str
    state_root: Path
    poll_seconds: int
    max_runtime_seconds: int
    codex_bin: str
    gh_bin: str
    feishu_webhook_url: str
    feishu_webhook_secret: str
    notification_prefix: str

    @classmethod
    def from_env(cls, *, require_notification: bool = True) -> "Config":
        root = Path(env_required("AGENT_REPOSITORY_ROOT")).resolve()
        if not (root / ".git").exists():
            raise ConfigurationError("AGENT_REPOSITORY_ROOT must be a Git checkout root")
        repository = env_required("AGENT_GITHUB_REPOSITORY")
        if not GITHUB_REPOSITORY_RE.fullmatch(repository):
            raise ConfigurationError("AGENT_GITHUB_REPOSITORY must be owner/repository")
        sender = env_required("AGENT_GITHUB_ALLOWED_SENDER")
        if not GITHUB_LOGIN_RE.fullmatch(sender):
            raise ConfigurationError("AGENT_GITHUB_ALLOWED_SENDER is invalid")
        try:
            issue = int(env_required("AGENT_GITHUB_CONTROL_ISSUE"))
        except ValueError as exc:
            raise ConfigurationError("AGENT_GITHUB_CONTROL_ISSUE must be an integer") from exc
        if issue < 1:
            raise ConfigurationError("AGENT_GITHUB_CONTROL_ISSUE must be positive")
        state_root = Path(
            os.environ.get("AGENT_STATE_ROOT", str(root / ".runtime" / "agent-controller"))
        ).resolve()
        try:
            state_root.relative_to(root)
        except ValueError as exc:
            raise ConfigurationError("AGENT_STATE_ROOT must stay inside AGENT_REPOSITORY_ROOT") from exc
        try:
            poll_seconds = int(os.environ.get("AGENT_POLL_SECONDS", "20"))
            max_runtime_seconds = int(os.environ.get("AGENT_MAX_RUNTIME_SECONDS", "21600"))
        except ValueError as exc:
            raise ConfigurationError(
                "AGENT_POLL_SECONDS and AGENT_MAX_RUNTIME_SECONDS must be integers"
            ) from exc
        if not 5 <= poll_seconds <= 300:
            raise ConfigurationError("AGENT_POLL_SECONDS must be between 5 and 300")
        if not 300 <= max_runtime_seconds <= 86_400:
            raise ConfigurationError("AGENT_MAX_RUNTIME_SECONDS must be between 300 and 86400")
        webhook = os.environ.get("AGENT_FEISHU_WEBHOOK_URL", "").strip()
        webhook_secret = os.environ.get("AGENT_FEISHU_WEBHOOK_SECRET", "").strip()
        if require_notification and not webhook:
            raise ConfigurationError("AGENT_FEISHU_WEBHOOK_URL is required")
        if webhook and not FEISHU_WEBHOOK_RE.fullmatch(webhook):
            raise ConfigurationError("AGENT_FEISHU_WEBHOOK_URL must use the official Feishu bot endpoint")
        if require_notification and not webhook_secret:
            raise ConfigurationError("AGENT_FEISHU_WEBHOOK_SECRET is required")
        return cls(
            repository_root=root,
            github_repository=repository,
            github_issue=issue,
            allowed_sender=sender,
            state_root=state_root,
            poll_seconds=poll_seconds,
            max_runtime_seconds=max_runtime_seconds,
            codex_bin=os.environ.get("AGENT_CODEX_BIN", "codex").strip() or "codex",
            gh_bin=os.environ.get("AGENT_GH_BIN", "gh").strip() or "gh",
            feishu_webhook_url=webhook,
            feishu_webhook_secret=webhook_secret,
            notification_prefix=os.environ.get("AGENT_NOTIFICATION_PREFIX", "SCE Codex").strip()
            or "SCE Codex",
        )


@dataclasses.dataclass(frozen=True)
class OwnerCommand:
    action: str
    argument: str = ""
    decision_id: str = ""
    choice: str = ""
    sha: str = ""


def parse_owner_command(body: str) -> OwnerCommand | None:
    text = body.strip()
    if not text.startswith("/agent"):
        return None
    head, _, tail = text.partition("\n")
    tokens = head.split()
    if len(tokens) < 2 or tokens[0] != "/agent":
        raise CommandRejected("expected /agent <command>")
    action = tokens[1].lower()
    remainder = " ".join(tokens[2:]).strip()
    if tail.strip():
        remainder = f"{remainder}\n{tail.strip()}".strip()
    if len(remainder) > MAX_TASK_CHARS:
        raise CommandRejected("command payload is too long")
    if action == "start":
        if not remainder:
            raise CommandRejected("/agent start requires a task description")
        return OwnerCommand(action="start", argument=remainder)
    if action in {"status", "stop"}:
        if remainder:
            raise CommandRejected(f"/agent {action} does not accept arguments")
        return OwnerCommand(action=action)
    if action == "continue":
        return OwnerCommand(action=action, argument=remainder or "Continue the task from the saved checkpoint.")
    if action in {"approve", "reject"}:
        parts = remainder.split(maxsplit=1)
        if len(parts) != 2 or not DECISION_ID_RE.fullmatch(parts[0]):
            raise CommandRejected(f"/agent {action} requires <decision-id> <choice-or-reason>")
        return OwnerCommand(
            action=action,
            decision_id=parts[0],
            choice=parts[1].strip(),
        )
    if action == "deploy":
        parts = remainder.split()
        if len(parts) != 2 or parts[0] != "daily" or not FULL_SHA_RE.fullmatch(parts[1]):
            raise CommandRejected("/agent deploy requires: daily <full-40-character-sha>")
        return OwnerCommand(action="deploy_daily", sha=parts[1])
    raise CommandRejected(f"unsupported command: {action}")


def feishu_signature(timestamp: int, secret: str) -> str:
    signing_key = f"{timestamp}\n{secret}".encode("utf-8")
    digest = hmac.new(signing_key, digestmod=hashlib.sha256).digest()
    return base64.b64encode(digest).decode("ascii")


class FeishuNotifier:
    def __init__(self, config: Config):
        self.config = config

    def notify(self, title: str, body: str) -> None:
        if not self.config.feishu_webhook_url:
            return
        timestamp = int(time.time())
        text = f"[{self.config.notification_prefix}] {title}\n\n{body}"[:MAX_NOTIFICATION_CHARS]
        payload: dict[str, Any] = {"msg_type": "text", "content": {"text": text}}
        if self.config.feishu_webhook_secret:
            payload.update(
                {
                    "timestamp": str(timestamp),
                    "sign": feishu_signature(timestamp, self.config.feishu_webhook_secret),
                }
            )
        request = urllib.request.Request(
            self.config.feishu_webhook_url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
        last_error: Exception | None = None
        for delay in (0, 1, 2):
            if delay:
                time.sleep(delay)
            try:
                with urllib.request.urlopen(request, timeout=10) as response:
                    result = json.loads(response.read().decode("utf-8"))
                if int(result.get("code", 0)) != 0:
                    raise RuntimeError(f"Feishu rejected notification: {result.get('msg', 'unknown')}")
                return
            except (OSError, ValueError, RuntimeError, urllib.error.URLError) as exc:
                last_error = exc
        raise RuntimeError(f"Feishu notification failed after retries: {last_error}")


class StateStore:
    def __init__(self, root: Path):
        self.root = root
        self.path = root / "state.json"
        self.events_path = root / "events.jsonl"

    def default(self) -> dict[str, Any]:
        now = utc_now()
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "IDLE",
            "last_comment_id": 0,
            "task": None,
            "initialized_at": now,
            "updated_at": now,
        }

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return self.default()
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        if payload.get("schema_version") != SCHEMA_VERSION:
            raise RuntimeError("agent controller state schema mismatch")
        return payload

    def save(self, payload: dict[str, Any]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        payload["updated_at"] = utc_now()
        fd, raw_path = tempfile.mkstemp(prefix="state-", suffix=".json", dir=self.root)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(raw_path, self.path)
        finally:
            if os.path.exists(raw_path):
                os.unlink(raw_path)

    def event(self, kind: str, **details: Any) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        record = {"at": utc_now(), "kind": kind, **details}
        with self.events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def run_checked(command: list[str], *, cwd: Path) -> str:
    result = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=60,
    )
    if result.returncode != 0:
        detail = result.stderr.strip().splitlines()[-1:] or ["unknown error"]
        raise RuntimeError(f"command failed: {command[0]}: {detail[0]}")
    return result.stdout


class GitHubIssueReader:
    def __init__(self, config: Config):
        self.config = config

    def comments(self) -> list[dict[str, Any]]:
        raw = run_checked(
            [
                self.config.gh_bin,
                "api",
                "--method",
                "GET",
                f"repos/{self.config.github_repository}/issues/{self.config.github_issue}/comments",
                "-f",
                "per_page=100",
                "--paginate",
                "--slurp",
            ],
            cwd=self.config.repository_root,
        )
        pages = json.loads(raw)
        rows = [row for page in pages for row in page] if pages and isinstance(pages[0], list) else pages
        return sorted(rows, key=lambda row: int(row.get("id", 0)))


def git_context(root: Path) -> dict[str, str]:
    top = run_checked(["git", "rev-parse", "--show-toplevel"], cwd=root).strip()
    branch = run_checked(["git", "branch", "--show-current"], cwd=root).strip()
    head = run_checked(["git", "rev-parse", "HEAD"], cwd=root).strip()
    status = run_checked(["git", "status", "--short"], cwd=root).strip()
    if Path(top).resolve() != root:
        raise ConfigurationError("configured repository root differs from Git top-level")
    if not ALLOWED_BRANCH_RE.fullmatch(branch):
        raise ConfigurationError(f"controller requires an allowed write branch, got {branch}")
    return {"top": top, "branch": branch, "head": head, "status": status}


def output_schema() -> dict[str, Any]:
    decision = {
        "type": ["object", "null"],
        "properties": {
            "id": {"type": "string"},
            "question": {"type": "string"},
            "options": {"type": "array", "items": {"type": "string"}},
            "recommendation": {"type": "string"},
            "risk": {"type": "string"},
        },
        "required": ["id", "question", "options", "recommendation", "risk"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["completed", "decision_required", "failed"]},
            "summary": {"type": "string"},
            "decision": decision,
            "evidence_paths": {"type": "array", "items": {"type": "string"}},
            "next_action": {"type": "string"},
        },
        "required": ["status", "summary", "decision", "evidence_paths", "next_action"],
        "additionalProperties": False,
    }


def initial_prompt(task: str, task_id: str) -> str:
    return f"""You are the long-running engineering worker for task {task_id}.

Task from the trusted repository owner:
{task}

Operate continuously inside the configured repository and obey AGENTS.md and all
repository execution policies. Resolve deterministic build, test, merge-conflict,
service-start and browser-test failures without asking for confirmation. Use the
repository Makefile for remote, runtime and PR state changes. Never access or
modify production, never weaken a gate, and never expose credentials.

Stop with status=decision_required only when the choice changes product scope or
business semantics, needs a new external dependency or credential, performs an
irreversible data action, changes production policy, or authorizes production.
Use a decision id formatted decision-YYYYMMDD-NNN and provide 2-3 concrete
options plus a recommendation. For recoverable technical failures, keep working.
When completed, include verification and evidence paths in the structured result.
"""


def continuation_prompt(command: OwnerCommand, decision: dict[str, Any] | None) -> str:
    if command.action == "approve":
        return (
            f"The trusted owner approved {command.decision_id} with: {command.choice}. "
            "Continue the task within the existing safety boundaries."
        )
    if command.action == "reject":
        return (
            f"The trusted owner rejected {command.decision_id}: {command.choice}. "
            "Do not take the rejected path; continue with a safe alternative or report a new decision."
        )
    prior = decision.get("id") if isinstance(decision, dict) else "none"
    return f"Trusted owner continuation for prior decision {prior}: {command.argument}"


class Controller:
    def __init__(self, config: Config):
        self.config = config
        self.store = StateStore(config.state_root)
        self.github = GitHubIssueReader(config)
        self.notifier = FeishuNotifier(config)
        self.worker: subprocess.Popen[str] | None = None
        self.worker_files: tuple[Any, Any] | None = None
        self.shutdown_requested = False

    def safe_notify(self, title: str, body: str) -> None:
        self.store.event("notification", title=title, body=body[:1000])
        try:
            self.notifier.notify(title, body)
        except Exception as exc:  # notification failure must not corrupt task state
            self.store.event("notification_failed", error=str(exc)[:500])

    def initialize(self, state: dict[str, Any]) -> dict[str, Any]:
        comments = self.github.comments()
        if not self.store.path.exists():
            state["last_comment_id"] = max((int(row.get("id", 0)) for row in comments), default=0)
            self.store.save(state)
            self.store.event("initialized", cursor=state["last_comment_id"])
            self.safe_notify(
                "控制器已就绪",
                f"仓库：{self.config.github_repository}\n控制 Issue：#{self.config.github_issue}\n"
                "请在 Issue 中发送 /agent start <任务>。",
            )
        elif state.get("status") in ACTIVE_STATUSES:
            state["status"] = "PAUSED_RECOVERABLE"
            if state.get("task"):
                state["task"]["worker_pid"] = None
            self.store.save(state)
            self.safe_notify("任务可恢复", "控制器重启后发现未完成任务，请发送 /agent continue。")
        elif state.get("status") == "FAILED_RECOVERABLE" and state.get("task"):
            task = state["task"]
            prior_generation = str(task.get("startup_recovery_generation") or "")
            if prior_generation != STARTUP_RECOVERY_GENERATION:
                task["startup_recovery_generation"] = STARTUP_RECOVERY_GENERATION
                task["startup_retry_count"] = int(task.get("startup_retry_count", 0)) + 1
                self.store.save(state)
                self.safe_notify("自动恢复技术失败", f"任务：{task['id']}\n正在执行一次受限自动重试。")
                if task.get("session_id"):
                    prompt = "本地控制器运行环境已经修复。继续原只读任务并重新执行失败的检查。"
                    self.launch(state, prompt, resume=True)
                else:
                    self.launch(state, initial_prompt(task["description"], task["id"]))
        return state

    def worker_environment(self) -> dict[str, str]:
        environment = dict(os.environ)
        for name in (
            "AGENT_FEISHU_WEBHOOK_URL",
            "AGENT_FEISHU_WEBHOOK_SECRET",
            "GH_TOKEN",
            "GITHUB_TOKEN",
        ):
            environment.pop(name, None)
        environment["CODEX_MODE"] = "fast"
        environment["ENV"] = "dev"
        executable_dirs = [
            str(Path(self.config.codex_bin).expanduser().absolute().parent),
            str(Path(self.config.gh_bin).expanduser().absolute().parent),
        ]
        inherited_path = environment.get("PATH", "/usr/local/bin:/usr/bin:/bin")
        environment["PATH"] = os.pathsep.join(dict.fromkeys([*executable_dirs, inherited_path]))
        return environment

    def _worker_command(self, task: dict[str, Any], prompt: str, *, resume: bool) -> list[str]:
        run_dir = Path(task["run_dir"])
        schema_path = run_dir / "result-schema.json"
        final_path = run_dir / "final.json"
        schema_path.write_text(
            json.dumps(output_schema(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        if resume:
            return [
                self.config.codex_bin,
                "exec",
                "resume",
                "--strict-config",
                "-c",
                'approval_policy="never"',
                task["session_id"],
                prompt,
                "--json",
                "--output-schema",
                str(schema_path),
                "-o",
                str(final_path),
            ]
        return [
            self.config.codex_bin,
            "exec",
            "--strict-config",
            "-c",
            'approval_policy="never"',
            "--json",
            "--sandbox",
            "workspace-write",
            "-C",
            str(self.config.repository_root),
            "--output-schema",
            str(schema_path),
            "-o",
            str(final_path),
            prompt,
        ]

    def launch(self, state: dict[str, Any], prompt: str, *, resume: bool = False) -> None:
        task = state["task"]
        run_dir = Path(task["run_dir"])
        run_dir.mkdir(parents=True, exist_ok=True)
        events_handle = (run_dir / "codex-events.jsonl").open("a", encoding="utf-8")
        stderr_handle = (run_dir / "codex-stderr.log").open("a", encoding="utf-8")
        command = self._worker_command(task, prompt, resume=resume)
        self.worker = subprocess.Popen(
            command,
            cwd=self.config.repository_root,
            env=self.worker_environment(),
            text=True,
            stdout=events_handle,
            stderr=stderr_handle,
            start_new_session=True,
        )
        self.worker_files = (events_handle, stderr_handle)
        state["status"] = "RUNNING"
        task["worker_pid"] = self.worker.pid
        task["turn_started_at"] = utc_now()
        task["deadline_epoch"] = int(time.time()) + self.config.max_runtime_seconds
        self.store.save(state)
        self.store.event("worker_started", task_id=task["id"], pid=self.worker.pid, resume=resume)
        self.safe_notify(
            "任务开始" if not resume else "任务继续",
            f"任务：{task['id']}\n分支：{task['branch']}\nIssue：#{self.config.github_issue}",
        )

    def start_task(self, state: dict[str, Any], command: OwnerCommand, comment_id: int) -> None:
        if state["status"] not in TERMINAL_STATUSES and state["status"] != "FAILED_RECOVERABLE":
            raise CommandRejected(f"a task already exists in state {state['status']}")
        context = git_context(self.config.repository_root)
        if context["status"]:
            raise CommandRejected("repository worktree must be clean before /agent start")
        task_id = f"issue-{self.config.github_issue}-{comment_id}-{uuid.uuid4().hex[:8]}"
        run_dir = self.config.state_root / "runs" / task_id
        state["task"] = {
            "id": task_id,
            "description": command.argument,
            "branch": context["branch"],
            "starting_head": context["head"],
            "session_id": None,
            "decision": None,
            "result": None,
            "run_dir": str(run_dir),
            "worker_pid": None,
            "created_at": utc_now(),
            "startup_retry_count": 0,
            "startup_recovery_generation": None,
        }
        self.launch(state, initial_prompt(command.argument, task_id))

    def start_daily_deploy(self, state: dict[str, Any], command: OwnerCommand, comment_id: int) -> None:
        task = (
            f"Deploy exact main SHA {command.sha} to the daily development environment only. "
            "Run all repository preflights, preserve sc_demo user data, use Makefile runtime targets, "
            "perform real Playwright browser acceptance, and stop before any production action."
        )
        self.start_task(state, OwnerCommand(action="start", argument=task), comment_id)

    def resume_task(self, state: dict[str, Any], command: OwnerCommand) -> None:
        if state["status"] not in RESUMABLE_STATUSES:
            raise CommandRejected(f"task cannot resume from {state['status']}")
        task = state.get("task") or {}
        session_id = str(task.get("session_id") or "")
        if not session_id:
            if state["status"] == "FAILED_RECOVERABLE":
                task["startup_retry_count"] = int(task.get("startup_retry_count", 0)) + 1
                self.launch(state, initial_prompt(task["description"], task["id"]))
                return
            raise CommandRejected("task has no resumable Codex session id")
        decision = task.get("decision")
        if command.action in {"approve", "reject"}:
            if not isinstance(decision, dict) or command.decision_id != decision.get("id"):
                raise CommandRejected("decision id does not match the active decision")
        self.launch(state, continuation_prompt(command, decision), resume=True)

    def request_stop(self, state: dict[str, Any]) -> None:
        if state["status"] not in ACTIVE_STATUSES or self.worker is None:
            state["status"] = "STOPPED"
            self.store.save(state)
            self.safe_notify("任务已停止", "当前没有运行中的 worker。")
            return
        os.killpg(self.worker.pid, signal.SIGINT)
        state["status"] = "STOP_REQUESTED"
        self.store.save(state)
        self.store.event("stop_requested", pid=self.worker.pid)
        self.safe_notify("已请求安全停止", "已向 Codex worker 发送 SIGINT；不会自动升级为强制杀进程。")

    def status_text(self, state: dict[str, Any]) -> str:
        task = state.get("task") or {}
        return (
            f"状态：{state['status']}\n"
            f"任务：{task.get('id', '-')}\n"
            f"分支：{task.get('branch', '-')}\n"
            f"起始 SHA：{task.get('starting_head', '-')}\n"
            f"会话：{task.get('session_id', '-')}"
        )

    def handle_comment(self, state: dict[str, Any], comment: dict[str, Any]) -> None:
        comment_id = int(comment.get("id", 0))
        login = str((comment.get("user") or {}).get("login") or "")
        body = str(comment.get("body") or "")
        try:
            command = parse_owner_command(body)
            if command is None:
                return
            if login != self.config.allowed_sender:
                self.store.event("unauthorized_command", comment_id=comment_id, sender=login)
                self.safe_notify("拒绝未授权命令", f"Issue 评论 #{comment_id} 来自 {login or 'unknown'}。")
                return
            if command.action == "start":
                self.start_task(state, command, comment_id)
            elif command.action == "deploy_daily":
                self.start_daily_deploy(state, command, comment_id)
            elif command.action in {"continue", "approve", "reject"}:
                self.resume_task(state, command)
            elif command.action == "stop":
                self.request_stop(state)
            elif command.action == "status":
                self.safe_notify("任务状态", self.status_text(state))
            self.store.event("command_accepted", comment_id=comment_id, action=command.action)
        except CommandRejected as exc:
            self.store.event("command_rejected", comment_id=comment_id, reason=str(exc))
            if login == self.config.allowed_sender:
                self.safe_notify("命令被拒绝", f"评论 #{comment_id}\n原因：{exc}")
        finally:
            state["last_comment_id"] = max(int(state.get("last_comment_id", 0)), comment_id)
            self.store.save(state)

    def poll_comments(self, state: dict[str, Any]) -> None:
        cursor = int(state.get("last_comment_id", 0))
        for comment in self.github.comments():
            if int(comment.get("id", 0)) > cursor:
                self.handle_comment(state, comment)

    def capture_session_id(self, state: dict[str, Any]) -> None:
        task = state.get("task") or {}
        if task.get("session_id") or not task.get("run_dir"):
            return
        path = Path(task["run_dir"]) / "codex-events.jsonl"
        if not path.exists():
            return
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("type") == "thread.started" and event.get("thread_id"):
                task["session_id"] = event["thread_id"]
                self.store.save(state)
                self.store.event("session_captured", session_id=event["thread_id"])
                return

    def finish_worker(self, state: dict[str, Any], returncode: int) -> None:
        task = state.get("task") or {}
        if self.worker_files:
            for handle in self.worker_files:
                handle.close()
        self.worker = None
        self.worker_files = None
        task["worker_pid"] = None
        final_path = Path(task["run_dir"]) / "final.json"
        result: dict[str, Any] | None = None
        if final_path.exists():
            try:
                result = json.loads(final_path.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                result = None
        task["result"] = result
        if returncode != 0 or result is None:
            state["status"] = "STOPPED" if state["status"] == "STOP_REQUESTED" else "FAILED_RECOVERABLE"
            self.store.save(state)
            self.safe_notify(
                "任务已停止" if state["status"] == "STOPPED" else "任务失败，可恢复",
                f"任务：{task.get('id')}\n退出码：{returncode}\n发送 /agent continue 可恢复。",
            )
            return
        result_status = result.get("status")
        if result_status == "decision_required":
            decision = result.get("decision")
            if not isinstance(decision, dict) or not DECISION_ID_RE.fullmatch(str(decision.get("id", ""))):
                state["status"] = "FAILED_RECOVERABLE"
                self.store.save(state)
                self.safe_notify("任务结果无效", "Codex 返回了无效 decision id，可发送 /agent continue 重试。")
                return
            task["decision"] = decision
            state["status"] = "DECISION_REQUIRED"
            self.store.save(state)
            options = "\n".join(f"- {item}" for item in decision.get("options", []))
            self.safe_notify(
                f"需要决策：{decision['id']}",
                f"{decision.get('question', '')}\n\n{options}\n\n推荐：{decision.get('recommendation', '')}\n"
                f"风险：{decision.get('risk', '')}\n\n"
                f"在 GitHub Issue #{self.config.github_issue} 回复：\n"
                f"/agent approve {decision['id']} <选择>",
            )
        elif result_status == "completed":
            task["decision"] = None
            state["status"] = "COMPLETED"
            self.store.save(state)
            evidence = "\n".join(result.get("evidence_paths", [])) or "-"
            self.safe_notify(
                "任务完成",
                f"{result.get('summary', '')}\n\n证据：\n{evidence}\n\nIssue：#{self.config.github_issue}",
            )
        else:
            state["status"] = "FAILED_RECOVERABLE"
            self.store.save(state)
            self.safe_notify("任务失败，可恢复", str(result.get("summary", "unknown failure")))

    def check_worker(self, state: dict[str, Any]) -> None:
        if self.worker is None:
            return
        self.capture_session_id(state)
        task = state.get("task") or {}
        if int(time.time()) > int(task.get("deadline_epoch", 0)) and state["status"] == "RUNNING":
            os.killpg(self.worker.pid, signal.SIGINT)
            state["status"] = "STOP_REQUESTED"
            self.store.save(state)
            self.safe_notify("任务达到时间上限", "已请求安全停止；可检查状态后继续。")
        returncode = self.worker.poll()
        if returncode is not None:
            self.capture_session_id(state)
            self.finish_worker(state, returncode)

    def run_once(self, state: dict[str, Any]) -> None:
        self.poll_comments(state)
        self.check_worker(state)

    def run(self) -> None:
        context = git_context(self.config.repository_root)
        self.config.state_root.mkdir(parents=True, exist_ok=True)
        lock_path = self.config.state_root / "controller.lock"
        with lock_path.open("w", encoding="utf-8") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise RuntimeError("another controller instance holds the repository lease") from exc
            state = self.initialize(self.store.load())
            self.store.event("controller_started", **context)

            def request_shutdown(_signum: int, _frame: Any) -> None:
                self.shutdown_requested = True

            signal.signal(signal.SIGTERM, request_shutdown)
            signal.signal(signal.SIGINT, request_shutdown)
            while not self.shutdown_requested:
                try:
                    self.run_once(state)
                except Exception as exc:
                    self.store.event("poll_failed", error=str(exc)[:1000])
                time.sleep(self.config.poll_seconds)
            self.store.event("controller_stopped")


def config_summary(config: Config) -> dict[str, Any]:
    context = git_context(config.repository_root)
    run_checked([config.gh_bin, "auth", "status"], cwd=config.repository_root)
    issue = json.loads(
        run_checked(
            [
                config.gh_bin,
                "api",
                "--method",
                "GET",
                f"repos/{config.github_repository}/issues/{config.github_issue}",
            ],
            cwd=config.repository_root,
        )
    )
    if issue.get("pull_request") or issue.get("state") != "open":
        raise ConfigurationError("AGENT_GITHUB_CONTROL_ISSUE must reference an open Issue")
    run_checked(
        [config.gh_bin, "api", "--method", "GET", f"users/{config.allowed_sender}"],
        cwd=config.repository_root,
    )
    run_checked([config.codex_bin, "--version"], cwd=config.repository_root)
    return {
        "status": "PASS",
        "repository_root": str(config.repository_root),
        "github_repository": config.github_repository,
        "github_issue": config.github_issue,
        "github_issue_url": str(issue.get("html_url") or ""),
        "allowed_sender": config.allowed_sender,
        "state_root": str(config.state_root),
        "branch": context["branch"],
        "head": context["head"],
        "worktree_clean": not bool(context["status"]),
        "feishu_configured": bool(config.feishu_webhook_url),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("run", "config-check", "notify-test", "status"))
    args = parser.parse_args()
    config = Config.from_env(require_notification=args.command not in {"config-check", "status"})
    if args.command == "config-check":
        print("AGENT_CONTROLLER_CONFIG=" + json.dumps(config_summary(config), ensure_ascii=False, sort_keys=True))
        return 0
    if args.command == "notify-test":
        FeishuNotifier(config).notify("通知测试", "飞书通知链路已配置成功。")
        print("[agent-controller] Feishu notification PASS")
        return 0
    controller = Controller(config)
    if args.command == "status":
        state = controller.store.load()
        print("AGENT_CONTROLLER_STATUS=" + json.dumps(state, ensure_ascii=False, sort_keys=True))
        return 0
    controller.run()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ConfigurationError, RuntimeError) as exc:
        print(f"AGENT_CONTROLLER_ERROR={exc}", file=sys.stderr)
        raise SystemExit(2)
