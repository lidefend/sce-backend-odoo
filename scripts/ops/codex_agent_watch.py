#!/usr/bin/env python3
"""Live, read-only terminal console for the local Codex controller."""

from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
import time
from pathlib import Path

try:
    from scripts.ops.agent_progress import format_duration, load_snapshot
except ModuleNotFoundError:  # installed standalone command
    sys.path.insert(0, str(Path.home() / ".local" / "lib" / "sce-agent-controller"))
    from agent_progress import format_duration, load_snapshot


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    result.add_argument(
        "--state-root",
        type=Path,
        default=Path(
            os.environ.get(
                "AGENT_STATE_ROOT",
                Path.cwd() / ".runtime" / "agent-controller",
            )
        ),
    )
    result.add_argument("--once", action="store_true")
    result.add_argument("--interval", type=int, default=2)
    return result


def render(state_root: Path) -> str:
    snapshot = load_snapshot(state_root)
    if snapshot is None:
        return f"SCE Codex 本地任务控制台\n\n状态文件不存在：{state_root / 'state.json'}"
    activity = "-"
    if snapshot.last_activity_epoch is not None:
        activity = dt.datetime.fromtimestamp(snapshot.last_activity_epoch).astimezone().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        activity += f" · {format_duration(snapshot.last_activity_age_seconds)}前"
    return "\n".join(
        [
            "SCE Codex 本地任务控制台（Ctrl+C 退出，仅停止查看，不停止任务）",
            "",
            f"状态       {snapshot.status} · {snapshot.health()}",
            f"任务       {snapshot.task_id}",
            f"分支       {snapshot.branch}",
            f"Worker     PID {snapshot.worker_pid or '-'} · Session {snapshot.session_id}",
            f"运行时长   {format_duration(snapshot.elapsed_seconds)}",
            "执行事件   "
            f"{snapshot.event_count} 条 · 命令完成 {snapshot.commands_completed} · "
            f"可恢复失败 {snapshot.recoverable_failures}",
            f"最近活动   {activity}",
            f"最近阶段   {snapshot.last_note}",
            "",
            "飞书发送“状态”或“进度”可获取同一份即时摘要。",
        ]
    )


def main() -> int:
    args = parser().parse_args()
    if not 1 <= args.interval <= 60:
        raise SystemExit("--interval must be between 1 and 60")
    follow = not args.once and sys.stdout.isatty()
    while True:
        if follow:
            print("\033[2J\033[H", end="")
        print(render(args.state_root), flush=True)
        if not follow:
            return 0
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
