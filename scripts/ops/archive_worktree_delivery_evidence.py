#!/usr/bin/env python3
"""Archive a bounded delivery evidence set outside its linked worktree."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path


CONFIRMATION = "ARCHIVE_DELIVERY_EVIDENCE"
REQUIRED_ROLES = {"summary", "identity", "screenshot", "review"}
INTEGRATION_PURPOSE = "nonvisual-integration"
INTEGRATION_ROLES = {"summary", "identity", "artifact", "review"}
TEXT_ROLE_SUFFIXES = {
    "summary": {".json", ".md"},
    "identity": {".json"},
    "review": {".json", ".md"},
}
SCREENSHOT_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


class ArchiveError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git(root: Path, *args: str) -> str:
    process = subprocess.run(
        ["git", *args], cwd=root, check=False, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    if process.returncode:
        raise ArchiveError(f"git {' '.join(args)} failed: {process.stdout.strip()}")
    return process.stdout.strip()


def validate_evidence_file(role: str, path: Path, candidate_head: str) -> None:
    """Reject role labels that do not carry the required candidate-bound evidence."""
    suffix = path.suffix.lower()
    if role in TEXT_ROLE_SUFFIXES:
        if suffix not in TEXT_ROLE_SUFFIXES[role]:
            raise ArchiveError(f"{role} evidence needs a supported document type: {path.name}")
        try:
            text = path.read_text(encoding="utf-8")
            if suffix == ".json":
                json.loads(text)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ArchiveError(f"{role} evidence is unreadable: {path.name}") from exc
        if candidate_head not in text:
            raise ArchiveError(f"{role} evidence is not bound to candidateHead: {path.name}")
        return
    if role != "screenshot" or suffix not in SCREENSHOT_SUFFIXES:
        raise ArchiveError(f"screenshot evidence needs a supported image type: {path.name}")
    data = path.read_bytes()
    signatures = {
        ".png": data.startswith(b"\x89PNG\r\n\x1a\n"),
        ".jpg": data.startswith(b"\xff\xd8\xff"),
        ".jpeg": data.startswith(b"\xff\xd8\xff"),
        ".webp": len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP",
    }
    if not signatures[suffix]:
        raise ArchiveError(f"screenshot evidence has invalid image content: {path.name}")


def load_plan(worktree: Path, manifest_path: Path, archive_root: Path) -> dict:
    worktree = worktree.resolve()
    manifest_path = manifest_path.resolve()
    archive_root = archive_root.resolve()
    if not worktree.is_dir() or Path(git(worktree, "rev-parse", "--show-toplevel")).resolve() != worktree:
        raise ArchiveError("worktree must be an existing git worktree root")
    if worktree == archive_root or worktree in archive_root.parents or archive_root in worktree.parents:
        raise ArchiveError("archive root must be outside the candidate worktree")
    if worktree not in manifest_path.parents:
        raise ArchiveError("evidence manifest must be inside the candidate worktree")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ArchiveError(f"cannot read evidence manifest: {exc}") from exc
    version = manifest.get("schemaVersion")
    if version == 1:
        required_roles = REQUIRED_ROLES
    elif (version == 2 and manifest.get("purpose") == INTEGRATION_PURPOSE
          and isinstance(manifest.get("nonvisualReason"), str)
          and manifest["nonvisualReason"].strip()):
        required_roles = INTEGRATION_ROLES
    else:
        raise ArchiveError("unsupported evidence schema/purpose or missing nonvisualReason")
    topic = manifest.get("topic")
    if not isinstance(topic, str) or not topic or any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for ch in topic):
        raise ArchiveError("manifest topic must use lowercase letters, digits, hyphens or underscores")
    head = git(worktree, "rev-parse", "HEAD")
    if manifest.get("candidateHead") != head:
        raise ArchiveError("manifest candidateHead does not match worktree HEAD")
    rows = manifest.get("files")
    if not isinstance(rows, list) or not rows:
        raise ArchiveError("manifest files must be a non-empty list")
    roles = {row.get("role") for row in rows if isinstance(row, dict)}
    missing = sorted(required_roles - roles)
    if missing:
        raise ArchiveError("manifest missing required roles: " + ", ".join(missing))

    sources = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or row.get("role") not in required_roles:
            raise ArchiveError("every evidence file needs a supported role")
        relative = Path(str(row.get("path") or ""))
        if relative.is_absolute() or not relative.parts or ".." in relative.parts:
            raise ArchiveError(f"evidence path must be worktree-relative: {relative}")
        unresolved = worktree / relative
        source = unresolved.resolve()
        if (worktree not in source.parents or not source.is_file()
                or any(path.is_symlink() for path in (unresolved, *unresolved.parents))):
            raise ArchiveError(f"evidence file is missing or unsafe: {relative}")
        if source.stat().st_size <= 0:
            raise ArchiveError(f"evidence file is empty: {relative}")
        digest = sha256(source)
        if row["role"] == "artifact":
            if row.get("sha256") != digest or not isinstance(row.get("provenance"), str) or not row["provenance"].strip():
                raise ArchiveError("artifact requires exact sha256 and provenance")
            try:
                payload = json.loads(source.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ArchiveError("artifact must be readable JSON") from exc
            if source.suffix.lower() != ".json" or not isinstance(payload, dict) or not payload:
                raise ArchiveError("artifact must be a nonempty JSON object")
        else:
            validate_evidence_file(row["role"], source, head)
        if relative.as_posix() in seen:
            raise ArchiveError(f"duplicate evidence path: {relative}")
        seen.add(relative.as_posix())
        sources.append({"role": row["role"], "relative": relative, "source": source,
                        "sha256": digest, "provenance": row.get("provenance")})

    destination = archive_root / date.today().isoformat().replace("-", "") / topic / head
    return {
        "worktree": worktree,
        "schemaVersion": version,
        "purpose": manifest.get("purpose"),
        "nonvisualReason": manifest.get("nonvisualReason"),
        "head": head,
        "topic": topic,
        "manifest": manifest_path,
        "manifestSha256": sha256(manifest_path),
        "destination": destination,
        "sources": sources,
    }


def archive(plan: dict, *, apply: bool, confirmation: str) -> Path:
    receipt_path = plan["destination"] / "archive-receipt.json"
    if not apply:
        return receipt_path
    if confirmation != CONFIRMATION:
        raise ArchiveError(f"apply requires --confirm {CONFIRMATION}")
    if (git(plan["worktree"], "rev-parse", "HEAD") != plan["head"]
            or sha256(plan["manifest"]) != plan["manifestSha256"]):
        raise ArchiveError("candidate or manifest changed after planning")
    if plan["destination"].exists():
        raise ArchiveError(f"archive destination already exists: {plan['destination']}")
    plan["destination"].mkdir(parents=True)
    archived = []
    try:
        for row in plan["sources"]:
            target = plan["destination"] / row["relative"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(row["source"], target)
            source_sha = sha256(row["source"])
            archived_sha = sha256(target)
            if archived_sha != source_sha or source_sha != row["sha256"] or target.stat().st_size <= 0:
                raise ArchiveError(f"archive verification failed: {row['relative']}")
            archived.append({
                "role": row["role"],
                "sourcePath": row["relative"].as_posix(),
                "archivePath": str(target.resolve()),
                "sha256": archived_sha,
                "size": target.stat().st_size,
                "provenance": row["provenance"],
            })
        receipt = {
            "schemaVersion": plan["schemaVersion"],
            "purpose": plan["purpose"],
            "nonvisualReason": plan["nonvisualReason"],
            "status": "verified",
            "archivedAt": datetime.now(timezone.utc).isoformat(),
            "topic": plan["topic"],
            "candidateWorktree": str(plan["worktree"]),
            "candidateHead": plan["head"],
            "manifestPath": str(plan["manifest"]),
            "manifestSha256": plan["manifestSha256"],
            "files": archived,
        }
        receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        json.loads(receipt_path.read_text(encoding="utf-8"))
    except Exception:
        shutil.rmtree(plan["destination"], ignore_errors=True)
        raise
    return receipt_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worktree", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--archive-root", default="")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm", default="")
    args = parser.parse_args()
    try:
        worktree = Path(args.worktree).resolve()
        archive_root = (
            Path(args.archive_root).resolve()
            if args.archive_root
            else worktree.parent / ".codex-evidence" / "workspace-archives"
        )
        plan = load_plan(worktree, Path(args.manifest), archive_root)
        receipt = archive(plan, apply=args.apply, confirmation=args.confirm)
    except (ArchiveError, OSError) as exc:
        print(f"[workspace.evidence.archive] DENY {exc}", file=sys.stderr)
        return 2
    mode = "APPLIED" if args.apply else "DRY_RUN"
    print(
        f"[workspace.evidence.archive] {mode} topic={plan['topic']} "
        f"head={plan['head']} files={len(plan['sources'])} receipt={receipt}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
