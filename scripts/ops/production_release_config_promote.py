#!/usr/bin/env python3
"""Atomically promote production runtime and pre-replacement identity config."""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SSH_TARGET = "sc-prod"
CONFIRMATION = "YES_PROMOTE_VERIFIED_PRODUCTION_RELEASE_CONFIG"
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
HASH = re.compile(r"^[0-9a-f]{64}$")
VERSION = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+-rc\.[0-9]+$")


class PromoteError(RuntimeError):
    pass


REMOTE_PROMOTE = r'''
import hashlib, json, os, re, shutil, stat, subprocess, sys, tempfile
from datetime import datetime, timezone
from pathlib import Path

current_source, current_digest, next_source, next_digest, version, next_image_id, tool_sha, acceptance_digest = sys.argv[1:]
runtime_path = Path("/opt/sce/config/sc_production/runtime.env")
promotion_path = Path("/etc/scems/production-promotion.env")
manifest_root = Path("/opt/sce/candidates") / ("v" + version)
image_ref = "ghcr.io/lidefend/sce-product@" + next_digest

def env_read(path):
    rows, values = [], {}
    for line in path.read_text().splitlines():
        rows.append(line)
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key, value = stripped.split("=", 1)
            values[key] = value
    return rows, values

def rendered(rows, updates):
    seen, output = set(), []
    for line in rows:
        stripped = line.strip()
        key = stripped.split("=", 1)[0] if stripped and not stripped.startswith("#") and "=" in stripped else ""
        if key in updates:
            output.append(key + "=" + updates[key])
            seen.add(key)
        else:
            output.append(line)
    if seen != set(updates):
        raise SystemExit("[production.release.config.promote] BLOCKED required config key missing")
    return "\n".join(output) + "\n"

for path, mode in ((runtime_path, 0o600), (promotion_path, 0o640)):
    meta = path.stat()
    if path.is_symlink() or not path.is_file() or meta.st_uid != 0 or meta.st_gid != 0 or stat.S_IMODE(meta.st_mode) != mode:
        raise SystemExit("[production.release.config.promote] BLOCKED unsafe configuration file")
runtime_rows, runtime = env_read(runtime_path)
promotion_rows, promotion = env_read(promotion_path)
if runtime.get("EXPECTED_RELEASE_SHA") != current_source or runtime.get("EXPECTED_IMAGE_DIGEST") != current_digest:
    raise SystemExit("[production.release.config.promote] BLOCKED current runtime identity differs")
if runtime.get("ODOO_IMAGE_REF") != "ghcr.io/lidefend/sce-product@" + current_digest:
    raise SystemExit("[production.release.config.promote] BLOCKED current runtime image ref differs")
running = json.loads(subprocess.run(
    ["docker", "inspect", "sc_production-odoo-1"], check=True,
    stdout=subprocess.PIPE, text=True,
).stdout)[0]
if running.get("Image") != promotion.get("DEPLOYMENT_IMAGE_REF"):
    raise SystemExit("[production.release.config.promote] BLOCKED promotion config does not match running image")
observed_next = subprocess.run(
    ["docker", "image", "inspect", image_ref, "--format", "{{.Id}}"], check=True,
    stdout=subprocess.PIPE, text=True,
).stdout.strip()
if observed_next != next_image_id:
    raise SystemExit("[production.release.config.promote] BLOCKED next image content ID differs")
image = json.loads((manifest_root / "image-manifest.json").read_text())
release = json.loads((manifest_root / "product-release-manifest.json").read_text())
if any(payload.get("source_sha") != next_source or payload.get("image_digest") != next_digest for payload in (image, release)):
    raise SystemExit("[production.release.config.promote] BLOCKED next manifest identity differs")
frontend_digest = str(image.get("frontend_build_sha256") or "").strip()
if not re.fullmatch(r"[0-9a-f]{64}", frontend_digest):
    raise SystemExit("[production.release.config.promote] BLOCKED frontend build identity is invalid")
checksum = (manifest_root / "product-release-manifest.sha256").read_text().split()[0]
if checksum != hashlib.sha256((manifest_root / "product-release-manifest.json").read_bytes()).hexdigest():
    raise SystemExit("[production.release.config.promote] BLOCKED next manifest checksum differs")

runtime_updates = {
    "APPLICATION_SOURCE_SHA": next_source,
    "DEPLOYMENT_TOOL_SHA": tool_sha,
    "VERSION_TAG": "v" + version,
    "EXPECTED_RELEASE_SHA": next_source,
    "EXPECTED_IMAGE_DIGEST": next_digest,
    "FRONTEND_BUILD_SHA256": frontend_digest,
    "ODOO_IMAGE_REF": image_ref,
    "NGINX_IMAGE_REF": image_ref,
    "CANDIDATE_IMAGE": image_ref,
    "IMAGE_MANIFEST_PATH": str(manifest_root / "image-manifest.json"),
    "RELEASE_MANIFEST_PATH": str(manifest_root / "product-release-manifest.json"),
    "RELEASE_MANIFEST_CHECKSUM_PATH": str(manifest_root / "product-release-manifest.sha256"),
}
if "FRONTEND_BUILD_SHA256" not in runtime:
    runtime_rows.append("FRONTEND_BUILD_SHA256=")
promotion_updates = {
    "ACCEPTANCE_PRODUCT_KEY": "sce-product",
    "ACCEPTANCE_PACKAGE_DIGEST": acceptance_digest,
    "DEPLOYMENT_IMAGE_REF": next_image_id,
}
new_runtime = rendered(runtime_rows, runtime_updates)
new_promotion = rendered(promotion_rows, promotion_updates)
stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
safe_version = version.replace(".", "_")
runtime_backup = runtime_path.with_name(runtime_path.name + ".pre-" + safe_version + "-" + stamp)
promotion_backup = promotion_path.with_name(promotion_path.name + ".pre-" + safe_version + "-" + stamp)
shutil.copy2(runtime_path, runtime_backup)
shutil.copy2(promotion_path, promotion_backup)

def temporary(path, content, mode):
    descriptor, name = tempfile.mkstemp(prefix="." + path.name + ".", dir=path.parent)
    with os.fdopen(descriptor, "w") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    temporary_path = Path(name)
    os.chown(temporary_path, 0, 0)
    temporary_path.chmod(mode)
    return temporary_path

runtime_temp = temporary(runtime_path, new_runtime, 0o600)
promotion_temp = temporary(promotion_path, new_promotion, 0o640)
try:
    os.replace(runtime_temp, runtime_path)
    os.replace(promotion_temp, promotion_path)
    _, observed_runtime = env_read(runtime_path)
    _, observed_promotion = env_read(promotion_path)
    if observed_runtime.get("EXPECTED_RELEASE_SHA") != next_source or observed_runtime.get("EXPECTED_IMAGE_DIGEST") != next_digest or observed_runtime.get("FRONTEND_BUILD_SHA256") != frontend_digest or observed_promotion.get("DEPLOYMENT_IMAGE_REF") != next_image_id or observed_promotion.get("ACCEPTANCE_PACKAGE_DIGEST") != acceptance_digest:
        raise RuntimeError("post-promote identity mismatch")
except Exception:
    shutil.copy2(runtime_backup, runtime_path)
    shutil.copy2(promotion_backup, promotion_path)
    raise
finally:
    runtime_temp.unlink(missing_ok=True)
    promotion_temp.unlink(missing_ok=True)
print(json.dumps({"status":"PASS","source_sha":next_source,"image_digest":next_digest,
                  "image_id":next_image_id,"frontend_build_sha256":frontend_digest,"acceptance_package_digest":acceptance_digest,"runtime_backup":str(runtime_backup),
                  "promotion_backup":str(promotion_backup)}))
'''


def run(command: list[str]) -> str:
    completed = subprocess.run(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, text=True)
    if completed.returncode:
        raise PromoteError(f"command failed ({command[0]}): {completed.stderr.strip()[:600]}")
    return completed.stdout.strip()


def git(*arguments: str) -> str:
    return run(["git", *arguments])


def preflight(expected_main_sha: str) -> None:
    if not FULL_SHA.fullmatch(expected_main_sha):
        raise PromoteError("expected live main SHA must be a full lowercase SHA")
    if git("rev-parse", "HEAD") != expected_main_sha or git("branch", "--show-current") != "main":
        raise PromoteError("promotion must run from the approved main SHA")
    if git("status", "--porcelain"):
        raise PromoteError("promotion worktree must be clean")
    for remote in ("origin", "gitee-mirror"):
        lines = git("ls-remote", remote, "refs/heads/main").splitlines()
        if len(lines) != 1 or lines[0].split()[0] != expected_main_sha:
            raise PromoteError(f"{remote} main identity differs")


def promote(args: argparse.Namespace) -> dict:
    if os.environ.get("ENV") != "prod" or os.environ.get("PROD_DANGER") != "1":
        raise PromoteError("ENV=prod and PROD_DANGER=1 are required")
    if os.environ.get("CONFIRM_PRODUCTION_RELEASE_CONFIG_PROMOTE") != CONFIRMATION:
        raise PromoteError("exact production release config promotion confirmation is required")
    preflight(args.expected_live_main_sha)
    if not all(FULL_SHA.fullmatch(value) for value in (args.current_source_sha, args.next_source_sha)):
        raise PromoteError("release source identity is invalid")
    if not all(DIGEST.fullmatch(value) for value in (args.current_image_digest, args.next_image_digest, args.next_image_id)):
        raise PromoteError("release image identity is invalid")
    if not HASH.fullmatch(args.acceptance_package_digest):
        raise PromoteError("acceptance package identity is invalid")
    if not VERSION.fullmatch(args.version):
        raise PromoteError("release version is invalid")
    remote = " ".join(shlex.quote(item) for item in (
        "python3", "-c", REMOTE_PROMOTE, args.current_source_sha,
        args.current_image_digest, args.next_source_sha, args.next_image_digest,
        args.version, args.next_image_id, args.expected_live_main_sha,
        args.acceptance_package_digest,
    ))
    output = run(["ssh", "-o", "BatchMode=yes", SSH_TARGET, remote])
    try:
        result = json.loads(output.splitlines()[-1])
    except (IndexError, json.JSONDecodeError) as exc:
        raise PromoteError("remote promotion evidence is invalid") from exc
    if result.get("status") != "PASS" or result.get("source_sha") != args.next_source_sha:
        raise PromoteError("remote promotion evidence differs")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-live-main-sha", required=True)
    parser.add_argument("--current-source-sha", required=True)
    parser.add_argument("--current-image-digest", required=True)
    parser.add_argument("--next-source-sha", required=True)
    parser.add_argument("--next-image-digest", required=True)
    parser.add_argument("--next-image-id", required=True)
    parser.add_argument("--acceptance-package-digest", required=True)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    try:
        result = promote(args)
    except PromoteError as exc:
        raise SystemExit(f"[production.release.config.promote] BLOCKED: {exc}") from exc
    print("[production.release.config.promote] PASS " + json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
