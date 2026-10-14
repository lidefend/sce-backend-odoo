#!/usr/bin/env python3
"""Verify or restore the tracked evidence archive's artifacts.

Ledger claims bind to an archived identity (``sha256`` + schema + gate counts)
recorded in ``docs/frontend_productization/rendering-detail/evidence-archive/manifest.v1.json``.
The guards read that manifest, so they never depend on a machine-local working
path. This entry is the retrieval half:

* ``--verify``: hash every archived artifact that exists locally and report drift;
  a missing local copy is not a failure (the archive is the authority).
* ``--archive-root DIR --apply``: restore the artifacts from an external archive
  root, verifying each file's sha256 before it is written into the working path.
  A missing or mismatched file is refused, never written.

Read-only unless ``--apply`` is passed with ``--archive-root``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs/frontend_productization/rendering-detail/evidence-archive/manifest.v1.json"
ARCHIVE_SCHEMA = "frontend_evidence_archive.v1"


class ArchiveError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_entries() -> list[dict]:
    if not MANIFEST.is_file():
        raise ArchiveError(f"{MANIFEST.relative_to(ROOT)} is missing")
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if payload.get("schema") != ARCHIVE_SCHEMA:
        raise ArchiveError(f"{MANIFEST.name}: unexpected schema {payload.get('schema')!r}")
    entries = payload.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ArchiveError(f"{MANIFEST.name}: no archived entries")
    return entries


def verify() -> int:
    entries = load_entries()
    problems: list[str] = []
    present = 0
    for entry in entries:
        artifact = str(entry.get("artifact") or "")
        expected = str(entry.get("sha256") or "")
        local = ROOT / artifact
        if not local.is_file():
            print(f"[evidence-archive] ABSENT {artifact} (archived identity stands)")
            continue
        present += 1
        actual = sha256(local)
        if actual != expected:
            problems.append(f"{artifact}: local sha256 {actual[:16]} != archived {expected[:16]}")
    for problem in problems:
        print(f"[evidence-archive] DENY {problem}", file=sys.stderr)
    if problems:
        return 2
    print(f"[evidence-archive] OK {present}/{len(entries)} archived artifact(s) present and matching")
    return 0


def fetch(archive_root: Path) -> int:
    entries = load_entries()
    if not archive_root.is_dir():
        raise ArchiveError(f"archive root is not a directory: {archive_root}")
    restored = 0
    for entry in entries:
        artifact = str(entry.get("artifact") or "")
        expected = str(entry.get("sha256") or "")
        source = archive_root / artifact
        if not source.is_file():
            source = archive_root / Path(artifact).name
        if not source.is_file():
            raise ArchiveError(f"{artifact}: not found under {archive_root}")
        actual = sha256(source)
        if actual != expected:
            raise ArchiveError(f"{artifact}: {source} sha256 {actual[:16]} != archived {expected[:16]}")
        destination = ROOT / artifact
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        if sha256(destination) != expected:
            raise ArchiveError(f"{artifact}: restored copy does not match the archived identity")
        restored += 1
        print(f"[evidence-archive] RESTORED {artifact}")
    print(f"[evidence-archive] OK restored {restored} artifact(s) from {archive_root}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", help="hash local copies against the archive")
    parser.add_argument("--archive-root", default="", help="external directory holding the artifacts")
    parser.add_argument("--apply", action="store_true", help="restore from --archive-root")
    args = parser.parse_args(argv)
    if args.apply:
        if not args.archive_root:
            raise ArchiveError("--apply requires --archive-root")
        return fetch(Path(args.archive_root).resolve())
    return verify()


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except ArchiveError as exc:
        print(f"[evidence-archive] DENY {exc}", file=sys.stderr)
        raise SystemExit(2)
