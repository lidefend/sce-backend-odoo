#!/usr/bin/env python3
"""Parse first-party Node sources without executing them.

Peer of ``python_syntax_check.py`` for the ``.mjs``/``.cjs``/``.js`` delivery
corpus. Frontend acceptance runners, Node verify scripts and the Odoo browser
assets under ``addons/**/static/src`` are only executed by the surface-specific
make target (or the browser) that owns them, so a file that breaks
syntactically can land through any other change with no gate observing it.
This checker keeps one cheap corpus-wide gate: every tracked first-party Node
file must parse.

``.mjs`` and ``.cjs`` declare their module format, so ``node --check <file>``
parses them directly. ``.js`` does not: the runtime resolves it to CommonJS, or
retries it as an ES module when the CommonJS parse fails on ES-module syntax.
``node --check <file>.js`` returns 0 *without parsing the file at all* whenever
that resolution picks the ES module (measured on node 22.17.0 and 24.16.0), so
trusting it would leave a detected module's syntax errors unobserved. Every
``.js`` file is therefore parsed from stdin with an explicit ``--input-type``:
CommonJS first, then the ES module. A file passes when either format parses,
which is the set the runtime itself accepts.

The runtime has to accept ``--input-type`` for both formats; node 22.17.0, the
version this repository pins, does. The checker proves that capability once and
fails closed with a single message instead of reporting every ``.js`` file as
broken.

Usage:
    python3 scripts/ci/node_syntax_check.py             # every tracked file
    python3 scripts/ci/node_syntax_check.py <path> ...  # file or directory
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
NODE_SUFFIXES = (".mjs", ".cjs", ".js")
TRACKED_PATTERNS = ("*.mjs", "*.cjs", "*.js")
# A ``.js`` file is CommonJS unless its CommonJS parse rejects ES-module syntax,
# which is exactly when the runtime retries it as a module; keep that order.
JS_INPUT_TYPES = ("commonjs", "module")
# Stand-in sources that must parse when the runtime can check both ``.js`` formats.
NODE_FORMAT_PROBES = (
    ("commonjs", b"module.exports = 1;\n"),
    ("module", b"export const ok = 1;\n"),
)


def _relative(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def tracked_node_files() -> list[Path]:
    """Every tracked first-party Node file; gitignored corpora stay out."""
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z", "--", *TRACKED_PATTERNS],
            cwd=ROOT,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError:
        raise RuntimeError("git is required to enumerate the tracked Node corpus") from None
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", "replace").strip().splitlines()
        raise RuntimeError(
            f"git ls-files failed ({detail[0] if detail else result.returncode})"
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


def check_plans(path: Path) -> list[tuple[list[str], bytes | None, str, str]]:
    """``(argv, stdin source, message prefix, format label)`` per node invocation."""
    if path.suffix == ".js":
        source = path.read_bytes()
        return [
            (
                ["node", "--input-type", input_type, "--check"],
                source,
                "[stdin]:",
                input_type,
            )
            for input_type in JS_INPUT_TYPES
        ]
    return [(["node", "--check", str(path)], None, f"{path}:", "")]


def _detail(result: subprocess.CompletedProcess, prefix: str) -> str:
    stderr = result.stderr.decode("utf-8", "replace")
    stdout = result.stdout.decode("utf-8", "replace")
    lines = [line.strip() for line in (stderr or stdout).splitlines()]
    header = next((line for line in lines if line.startswith(prefix)), "")
    line_number = header.rsplit(":", 1)[-1] if header else "0"
    message = next(
        (line for line in lines if line.startswith(("SyntaxError", "Error"))),
        f"node --check exited {result.returncode}",
    )
    return f"{line_number}: {message}"


def check_file(path: Path) -> str | None:
    """Return ``line: message`` for ``path``, or None when it parses."""
    failures: list[str] = []
    for argv, stdin_source, prefix, label in check_plans(path):
        result = subprocess.run(
            argv,
            cwd=ROOT,
            capture_output=True,
            input=stdin_source,
        )
        if result.returncode == 0:
            return None
        detail = _detail(result, prefix)
        failures.append(f"{detail} (as {label})" if label else detail)
    return " / ".join(failures)


def _node_version() -> str:
    try:
        result = subprocess.run(
            ["node", "--version"], cwd=ROOT, capture_output=True, text=True
        )
    except FileNotFoundError:
        return "unknown"
    return result.stdout.strip() or "unknown"


def format_capability_failure() -> str | None:
    """Reason this runtime cannot parse ``.js`` sources through ``--input-type``."""
    for input_type, source in NODE_FORMAT_PROBES:
        try:
            result = subprocess.run(
                ["node", "--input-type", input_type, "--check"],
                cwd=ROOT,
                capture_output=True,
                input=source,
            )
        except FileNotFoundError:
            return "the node runtime is not on PATH"
        if result.returncode != 0:
            detail = [
                line.strip()
                for line in result.stderr.decode("utf-8", "replace").splitlines()
                if line.strip()
            ]
            return (
                f"node {_node_version()} cannot parse {input_type} sources through "
                f"--input-type ({detail[0] if detail else result.returncode}); "
                "node 22.17.0 or newer is required"
            )
    return None


def main(argv: list[str]) -> int:
    try:
        targets = iter_node_files(argv) if argv else tracked_node_files()
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"[FAIL] Node syntax check: {exc}", file=sys.stderr)
        return 2
    if not targets:
        print("[FAIL] Node syntax check found no files to check", file=sys.stderr)
        return 2

    if any(path.suffix == ".js" for path in targets):
        capability = format_capability_failure()
        if capability:
            print(f"[FAIL] Node syntax check: {capability}", file=sys.stderr)
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
