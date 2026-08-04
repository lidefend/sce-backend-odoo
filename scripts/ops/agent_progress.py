#!/usr/bin/env python3
"""Read-only progress snapshots shared by the local controller surfaces."""

from __future__ import annotations

import dataclasses
import datetime as dt
import json
import re
import time
from pathlib import Path
from typing import Any


@dataclasses.dataclass(frozen=True)
class ProgressSnapshot:
    status: str
    task_id: str
    branch: str
    worker_pid: int | None
    session_id: str
    elapsed_seconds: int | None
    event_count: int
    commands_completed: int
    recoverable_failures: int
    last_activity_epoch: float | None
    last_activity_age_seconds: int | None
    last_note: str
    decision_required: bool

    def health(self, stale_seconds: int = 600) -> str:
        if self.status == "RUNNING":
            if (
                self.last_activity_age_seconds is not None
                and self.last_activity_age_seconds > stale_seconds
            ):
                return f"超过{stale_seconds // 60}分钟无新事件，需关注"
            return "正常活动"
        if self.status == "DECISION_REQUIRED":
            return "等待决策"
        if self.status == "COMPLETED":
            return "已完成"
        return "未运行"


def _parse_time(value: Any) -> float | None:
    if not value:
        return None
    try:
        return dt.datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _safe_note(value: Any, limit: int = 260) -> str:
    note = str(value or "")
    try:
        payload = json.loads(note)
        note = str(payload.get("summary") or note)
    except (json.JSONDecodeError, AttributeError):
        pass
    note = re.sub(r"[\x00-\x1f\x7f]+", " ", note)
    note = re.sub(r"\s+", " ", note).strip()
    if len(note) > limit:
        note = note[: max(1, limit - 1)].rstrip() + "…"
    return note or "-"


def snapshot_from_state(state: dict[str, Any], *, now: float | None = None) -> ProgressSnapshot:
    current = time.time() if now is None else now
    task = state.get("task") or {}
    run_dir = Path(task.get("run_dir") or "")
    events_path = run_dir / "codex-events.jsonl" if run_dir else Path()
    event_count = 0
    commands_completed = 0
    recoverable_failures = 0
    last_note = "-"
    last_activity_epoch: float | None = None
    if events_path.is_file():
        last_activity_epoch = events_path.stat().st_mtime
        with events_path.open(encoding="utf-8", errors="replace") as handle:
            for raw in handle:
                event_count += 1
                try:
                    event = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if event.get("type") != "item.completed":
                    continue
                item = event.get("item") or {}
                if item.get("type") == "command_execution":
                    commands_completed += 1
                    if item.get("exit_code") not in (None, 0):
                        recoverable_failures += 1
                elif item.get("type") == "agent_message" and item.get("text"):
                    last_note = _safe_note(item["text"])
    started_epoch = _parse_time(task.get("turn_started_at") or task.get("created_at"))
    status = str(state.get("status") or "UNKNOWN")
    finished_epoch = _parse_time(task.get("turn_finished_at"))
    elapsed_end = current
    if status != "RUNNING":
        elapsed_end = finished_epoch or last_activity_epoch or current
    elapsed = max(0, int(elapsed_end - started_epoch)) if started_epoch is not None else None
    activity_age = (
        max(0, int(current - last_activity_epoch))
        if last_activity_epoch is not None
        else None
    )
    return ProgressSnapshot(
        status=status,
        task_id=str(task.get("id") or "-"),
        branch=str(task.get("branch") or "-"),
        worker_pid=task.get("worker_pid") if isinstance(task.get("worker_pid"), int) else None,
        session_id=str(task.get("session_id") or "-"),
        elapsed_seconds=elapsed,
        event_count=event_count,
        commands_completed=commands_completed,
        recoverable_failures=recoverable_failures,
        last_activity_epoch=last_activity_epoch,
        last_activity_age_seconds=activity_age,
        last_note=last_note,
        decision_required=status == "DECISION_REQUIRED",
    )


def load_snapshot(state_root: Path, *, now: float | None = None) -> ProgressSnapshot | None:
    state_path = state_root / "state.json"
    if not state_path.is_file():
        return None
    state = json.loads(state_path.read_text(encoding="utf-8"))
    return snapshot_from_state(state, now=now)


def format_duration(seconds: int | None) -> str:
    if seconds is None:
        return "-"
    hours, remainder = divmod(max(0, seconds), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}小时{minutes:02d}分" if hours else f"{minutes}分{seconds:02d}秒"


def format_status(snapshot: ProgressSnapshot, *, include_note: bool = True) -> str:
    activity = (
        format_duration(snapshot.last_activity_age_seconds) + "前"
        if snapshot.last_activity_age_seconds is not None
        else "-"
    )
    lines = [
        "【任务实时状态】",
        f"状态：{snapshot.status} · {snapshot.health()}",
        f"任务：{snapshot.task_id}",
        f"分支：{snapshot.branch}",
        f"已运行：{format_duration(snapshot.elapsed_seconds)}",
        "执行事件："
        f"{snapshot.event_count}；完成命令：{snapshot.commands_completed}；"
        f"可恢复失败：{snapshot.recoverable_failures}",
        f"最近活动：{activity}",
        f"是否需要决策：{'是' if snapshot.decision_required else '否'}",
    ]
    if include_note:
        lines.append(f"最近阶段：{snapshot.last_note}")
    return "\n".join(lines)
