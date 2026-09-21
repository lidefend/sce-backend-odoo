#!/usr/bin/env python3
"""Parse first-party Node automation files without executing them.

Peer of ``python_syntax_check.py`` for the ``.mjs``/``.cjs`` delivery corpus.
Frontend acceptance runners and Node verify scripts are only executed by the
surface-specific make target that owns them, so a file that breaks
syntactically can land through any other change with no gate observing it.
This checker keeps one cheap corpus-wide gate: every tracked first-party
``.mjs``/``.cjs`` file must parse.

Usage:
    python3 scripts/ci/node_syntax_check.py             # every tracked file
    python3 scripts/ci/node_syntax_check.py <path> ...  # file or directory
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
NODE_SUFFIXES = (".mjs", ".cjs")
TRACKED_PATTERNS = ("*.mjs", "*.cjs")


def _relative(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def tracked_node_files() -> list[Path]:
    """Every tracked first-party Node file; gitignored corpora stay out."""
    result = subprocess.run(
        ["git", "ls-files", "-z", "--", *TRACKED_PATTERNS],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    names = result.stdout.decode("utf-8").split("\0")
    return sorted(ROOT / name for name in names if name)


def iter_node_files(paths: list[str]) -> list[Path]:
    out: list[Path] = []
    for raw in paths:
        candidate = Path(raw)
        path = candidate if candidate.is_absolute() else ROOT / candidate
        if path.is_file():
            if path.suffix in NODE_SUFFIXES:
                out.append(path)
            continue
        if path.is_dir():
            out.extend(
                sorted(
                    item
                    for item in path.rglob("*")
                    if item.is_file() and item.suffix in NODE_SUFFIXES
                )
            )
            continue
        raise FileNotFoundError(f"{raw}: not a file or directory")
    return out


def check_file(path: Path) -> str | None:
    """Return ``line: message`` for ``path``, or None when it parses."""
    result = subprocess.run(
        ["node", "--check", str(path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return None
    lines = [line.strip() for line in (result.stderr or result.stdout).splitlines()]
    header = next((line for line in lines if line.startswith(f"{path}:")), "")
    line_number = header.rsplit(":", 1)[-1] if header else "0"
    message = next(
        (line for line in lines if line.startswith(("SyntaxError", "Error"))),
        f"node --check exited {result.returncode}",
    )
    return f"{line_number}: {message}"


def main(argv: list[str]) -> int:
    try:
        targets = iter_node_files(argv) if argv else tracked_node_files()
    except FileNotFoundError as exc:
        print(f"[FAIL] Node syntax check: {exc}", file=sys.stderr)
        return 2
    if not targets:
        print("[FAIL] Node syntax check found no files to check", file=sys.stderr)
        return 2

    failures: list[str] = []
    for path in targets:
        try:
            detail = check_file(path)
        except FileNotFoundError:
            print("[FAIL] Node syntax check requires the node runtime on PATH", file=sys.stderr)
            return 2
        if detail:
            failures.append(f"{_relative(path)}:{detail}")
    if failures:
        print("[FAIL] Node syntax check failed", file=sys.stderr)
        for item in failures:
            print(item, file=sys.stderr)
        return 1
    print(f"[OK] Node syntax check passed ({len(targets)} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
