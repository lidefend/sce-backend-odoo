#!/usr/bin/env python3
"""Fail closed unless the CI host can atomically write its artifact directory."""

from __future__ import annotations

import argparse
import os
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def verify_host_write(artifact_root: Path) -> None:
    backend = artifact_root / "backend"
    backend.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".host-write-", dir=backend)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write("host-writable\n")
            stream.flush()
            os.fsync(stream.fileno())
        destination = backend / ".host-write-probe"
        os.replace(temporary_path, destination)
        destination.unlink()
    finally:
        temporary_path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", default="artifacts")
    args = parser.parse_args()
    artifact_root = Path(args.artifacts)
    if not artifact_root.is_absolute():
        artifact_root = ROOT / artifact_root
    verify_host_write(artifact_root)
    print(f"[ci_artifact_host_write_guard] PASS root={artifact_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
