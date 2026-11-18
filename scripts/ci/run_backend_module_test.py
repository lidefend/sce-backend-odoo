#!/usr/bin/env python3
"""Run one backend module test with a hard timeout and visible heartbeat."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time


def positive_float(value: str) -> float:
    number = float(value)
    if number <= 0 or number > 86_400:
        raise argparse.ArgumentTypeError("must be between 0 and 86400 seconds")
    return number


def run_module(
    *,
    module: str,
    timeout_seconds: float,
    heartbeat_seconds: float,
    log_path: Path,
    command: list[str],
) -> int:
    if not module or any(char not in "abcdefghijklmnopqrstuvwxyz0123456789_" for char in module):
        raise ValueError("module must use lowercase identifier characters")
    if heartbeat_seconds > timeout_seconds:
        raise ValueError("heartbeat interval cannot exceed the timeout")
    if not command:
        raise ValueError("backend module command is required")

    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("", encoding="utf-8")
    lock = threading.Lock()
    started = time.monotonic()

    def emit(line: str) -> None:
        with lock:
            with log_path.open("a", encoding="utf-8") as target:
                target.write(line)
                target.flush()
            sys.stdout.write(line)
            sys.stdout.flush()

    emit(f"[backend-module] start module={module} timeout_seconds={timeout_seconds:g}\n")
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        start_new_session=True,
    )
    assert process.stdout is not None

    def pump_output() -> None:
        for line in process.stdout:
            emit(line)

    reader = threading.Thread(target=pump_output, name=f"backend-output-{module}", daemon=True)
    reader.start()
    next_heartbeat = started + heartbeat_seconds
    timed_out = False

    while process.poll() is None:
        now = time.monotonic()
        elapsed = now - started
        if elapsed >= timeout_seconds:
            timed_out = True
            emit(
                f"[backend-module-heartbeat] module={module} elapsed_seconds={elapsed:.1f} "
                f"timeout_seconds={timeout_seconds:g} status=timeout\n"
            )
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
            break
        if now >= next_heartbeat:
            emit(
                f"[backend-module-heartbeat] module={module} elapsed_seconds={elapsed:.1f} "
                f"timeout_seconds={timeout_seconds:g} status=running\n"
            )
            next_heartbeat = now + heartbeat_seconds
        time.sleep(min(0.1, max(0.01, timeout_seconds - elapsed)))

    reader.join(timeout=10)
    process.wait()
    process.stdout.close()
    exit_code = 124 if timed_out else int(process.returncode or 0)
    emit(
        f"[backend-module] finish module={module} elapsed_seconds={time.monotonic() - started:.1f} "
        f"status={'timeout' if timed_out else ('passed' if exit_code == 0 else 'failed')} "
        f"exit_code={exit_code}\n"
    )
    return exit_code


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--module", required=True)
    parser.add_argument("--timeout-seconds", required=True, type=positive_float)
    parser.add_argument("--heartbeat-seconds", type=positive_float, default=30.0)
    parser.add_argument("--log", required=True, type=Path)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    try:
        return run_module(
            module=args.module,
            timeout_seconds=args.timeout_seconds,
            heartbeat_seconds=args.heartbeat_seconds,
            log_path=args.log,
            command=command,
        )
    except (OSError, ValueError) as exc:
        print(f"[backend-module] configuration_error={exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
