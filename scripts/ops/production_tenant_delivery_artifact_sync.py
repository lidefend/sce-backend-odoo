#!/usr/bin/env python3
"""Synchronize one immutable signed tenant delivery into production custody."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[2]
SSH_TARGET = "sc-prod"
REMOTE_ROOT = Path("/data/backups/production_acceptance/tenant-deliveries")
CONFIRMATION = "YES_SYNC_SIGNED_TENANT_DELIVERY_ARTIFACTS"
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
DELIVERY_ID = re.compile(r"^[a-z0-9][a-z0-9.-]{2,95}$")
CHECKSUM = re.compile(r"^[0-9a-f]{64}$")


class SyncError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(command: list[str], *, input_bytes: bytes | None = None) -> str:
    completed = subprocess.run(
        command, cwd=ROOT, input=input_bytes, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=False,
    )
    if completed.returncode:
        error = completed.stderr.decode(errors="replace").strip()[:800]
        raise SyncError(f"command failed ({command[0]}): {error}")
    return completed.stdout.decode(errors="replace").strip()


def git(*arguments: str) -> str:
    return run(["git", *arguments])


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SyncError(f"invalid JSON: {path.name}") from exc
    if not isinstance(value, dict):
        raise SyncError(f"invalid JSON object: {path.name}")
    return value


def validate_checksum_tree(root: Path, *, extra_files: set[str]) -> dict[str, str]:
    if not root.is_dir() or root.is_symlink():
        raise SyncError(f"invalid artifact root: {root}")
    checksum_path = root / "checksums.sha256"
    if not checksum_path.is_file() or checksum_path.is_symlink():
        raise SyncError("checksums.sha256 is required")
    declared: dict[str, str] = {}
    for raw in checksum_path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        parts = raw.split(None, 1)
        if len(parts) != 2 or not CHECKSUM.fullmatch(parts[0]):
            raise SyncError("invalid checksum entry")
        relative = parts[1].strip().lstrip("*")
        pure = PurePosixPath(relative)
        if pure.is_absolute() or ".." in pure.parts or relative in declared:
            raise SyncError("unsafe or duplicate checksum path")
        target = root.joinpath(*pure.parts)
        if not target.is_file() or target.is_symlink():
            raise SyncError(f"declared artifact missing: {relative}")
        if sha256_file(target) != parts[0]:
            raise SyncError(f"artifact checksum differs: {relative}")
        declared[relative] = parts[0]
    if any(item.is_symlink() for item in root.rglob("*")):
        raise SyncError("artifact symlinks are forbidden")
    actual = {
        item.relative_to(root).as_posix()
        for item in root.rglob("*") if item.is_file()
    }
    expected = set(declared) | {"checksums.sha256"} | extra_files
    if actual != expected:
        raise SyncError("artifact inventory differs from checksums")
    return declared


def preflight(args: argparse.Namespace) -> tuple[dict, Path]:
    if os.environ.get("ENV") != "prod" or os.environ.get("PROD_DANGER") != "1":
        raise SyncError("ENV=prod and PROD_DANGER=1 are required")
    if os.environ.get("CONFIRM_PRODUCTION_TENANT_ARTIFACT_SYNC") != CONFIRMATION:
        raise SyncError("exact tenant artifact synchronization confirmation is required")
    if not FULL_SHA.fullmatch(args.tool_sha) or git("rev-parse", "HEAD") != args.tool_sha:
        raise SyncError("tool SHA must equal current HEAD")
    if git("branch", "--show-current") != "main" or git("status", "--porcelain"):
        raise SyncError("sync must run from a clean main worktree")
    for remote in ("origin", "gitee-mirror"):
        rows = git("ls-remote", remote, "refs/heads/main").splitlines()
        if len(rows) != 1 or rows[0].split()[0] != args.tool_sha:
            raise SyncError(f"{remote} main identity differs")
    if not DELIVERY_ID.fullmatch(args.delivery_id):
        raise SyncError("invalid delivery id")
    package_root = args.customer_package_root.resolve()
    payload_root = args.payload_root.resolve()
    public_key = args.public_key.resolve()
    if not public_key.is_file() or public_key.is_symlink():
        raise SyncError("public key is invalid")
    package_manifest = load_json(package_root / "package-manifest.json")
    payload_manifest = load_json(payload_root / "manifest.json")
    package_entries = validate_checksum_tree(package_root, extra_files=set())
    archive_names = [name for name in package_entries if name.endswith(".tar.gz")]
    if len(archive_names) != 1 or "package-manifest.json" not in package_entries:
        raise SyncError("customer package inventory is invalid")
    validate_checksum_tree(payload_root, extra_files={"manifest.json", "signature"})
    if (
        package_manifest.get("customer_sha") != args.customer_sha
        or package_manifest.get("customer_tree") != args.customer_tree
        or package_manifest.get("product_sha") != args.product_sha
        or package_manifest.get("tenant_id") != args.tenant_key
        or package_manifest.get("modules") != args.customer_module
        or payload_manifest.get("payload_id") != args.payload_version
        or payload_manifest.get("schema_version") != args.payload_schema_version
        or payload_manifest.get("tenant_key") != args.tenant_key
        or payload_manifest.get("customer_module") not in args.customer_module
    ):
        raise SyncError("signed artifact identity differs")
    return package_manifest, package_root / archive_names[0]


def synchronize(args: argparse.Namespace) -> dict:
    package_manifest, archive = preflight(args)
    final = REMOTE_ROOT / args.delivery_id
    staging = REMOTE_ROOT / (".incomplete-" + args.delivery_id)
    remote_prepare = (
        "set -eu; install -d -m 0700 " + shlex.quote(str(REMOTE_ROOT)) + " "
        + shlex.quote(str(staging / "customer-package")) + " "
        + shlex.quote(str(staging / "payload")) + "; test ! -L "
        + shlex.quote(str(staging))
    )
    run(["ssh", "-o", "BatchMode=yes", SSH_TARGET, remote_prepare])
    rsync = ["rsync", "--archive", "--checksum", "--partial", "--delete", "--chmod=D700,F600"]
    run(rsync + [str(args.customer_package_root.resolve()) + "/", f"{SSH_TARGET}:{staging}/customer-package/"])
    run(rsync + [str(args.payload_root.resolve()) + "/", f"{SSH_TARGET}:{staging}/payload/"])
    run(rsync + [str(args.public_key.resolve()), f"{SSH_TARGET}:{staging}/tenant-payload-public-key.pem"])

    remote_script = r'''set -eu
tool="$1"; staging="$2"; final="$3"; archive_name="$4"; shift 4
test -d "$tool" && test "$(cat "$tool/DEPLOYMENT_TOOL_SHA")" = "${tool##*/}"
normalize_reader_modes() {
  python3 - "$1" "$2" <<'PY'
import pathlib, sys
payload=pathlib.Path(sys.argv[1]); public_key=pathlib.Path(sys.argv[2]); changed=0
targets=[payload, *payload.rglob('*'), public_key]
for path in targets:
    if path.is_symlink(): raise SystemExit('REMOTE_ARTIFACT_SYMLINK_FORBIDDEN')
    expected=0o750 if path.is_dir() else 0o640
    if path.stat().st_mode & 0o777 != expected:
        path.chmod(expected); changed += 1
print(changed)
PY
}
if test -e "$final"; then
  test -f "$final/production-release-set.json" || { echo EXISTING_DELIVERY_INCOMPLETE >&2; exit 2; }
  PYTHONPATH="$tool/scripts/release" python3 - "$final/production-release-set.json" <<'PY'
import pathlib, production_release_set, sys
lock=production_release_set.load_lock(pathlib.Path(sys.argv[1]))
production_release_set.verify_bound_files(lock)
PY
  mode_changes="$(normalize_reader_modes "$final/payload" "$final/tenant-payload-public-key.pem")"
  rm -rf "$staging"
  if test "$mode_changes" = 0; then changed=false; else changed=true; fi
  printf '{"status":"PASS","changed":%s,"mode_changes":%s,"root":"%s"}\n' "$changed" "$mode_changes" "$final"
  exit 0
fi
python3 - "$staging" <<'PY'
import hashlib, pathlib, sys
root=pathlib.Path(sys.argv[1])
for base in (root/'customer-package', root/'payload'):
    for raw in (base/'checksums.sha256').read_text().splitlines():
        if not raw.strip(): continue
        digest, relative=raw.split(None,1); relative=relative.strip().lstrip('*')
        path=base/relative
        if path.is_symlink() or not path.is_file(): raise SystemExit('REMOTE_ARTIFACT_INVALID')
        value=hashlib.sha256(path.read_bytes()).hexdigest()
        if value != digest: raise SystemExit('REMOTE_ARTIFACT_CHECKSUM_MISMATCH')
if any(path.is_symlink() for path in root.rglob('*')): raise SystemExit('REMOTE_ARTIFACT_SYMLINK_FORBIDDEN')
PY
mv "$staging" "$final"
rollback=1
trap 'if test "$rollback" = 1 && test -d "$final" && test ! -e "$staging"; then mv "$final" "$staging"; fi' EXIT
python3 "$tool/scripts/release/build_production_release_set.py" \
  --output "$final/production-release-set.json" "$@" \
  --customer-package "$final/customer-package/$archive_name" \
  --customer-package-manifest "$final/customer-package/package-manifest.json" \
  --payload-root "$final/payload"
chmod 0600 "$final/production-release-set.json" "$final/tenant-payload-public-key.pem"
normalize_reader_modes "$final/payload" "$final/tenant-payload-public-key.pem" >/dev/null
rollback=0
trap - EXIT
printf '{"status":"PASS","changed":true,"root":"%s"}\n' "$final"
'''
    tool = f"/opt/sce/deployment-tools/{args.tool_sha}"
    command = [
        "ssh", "-o", "BatchMode=yes", SSH_TARGET, "bash", "-s", "--",
        tool, str(staging), str(final), archive.name,
        "--release-version", args.release_version,
        "--product-sha", args.product_sha,
        "--product-tree", args.product_tree,
        "--product-image", args.product_image,
        "--product-image-digest", args.product_image_digest,
        "--customer-sha", args.customer_sha,
        "--customer-tree", args.customer_tree,
        "--tenant-key", args.tenant_key,
        "--customer-package-signature-key-id", package_manifest["signature"]["key_id"],
        "--payload-version", args.payload_version,
        "--payload-schema-version", args.payload_schema_version,
        "--operator-identity-type", "external_xmlid",
        "--operator-identity-key", "base.user_admin",
        "--operator-direct-grant-target", "smart_core.group_smart_core_tenant_payload_importer",
        "--operator-required-existing-group", "base.group_user",
        "--operator-expected-direct-addition", "smart_core.group_smart_core_tenant_payload_importer",
        "--operator-expected-effective-addition", "smart_core.group_smart_core_tenant_payload_importer",
    ]
    for module in args.customer_module:
        command.extend(["--customer-module", module])
    output = run(command, input_bytes=remote_script.encode())
    try:
        result = json.loads(output.splitlines()[-1])
    except (IndexError, json.JSONDecodeError) as exc:
        raise SyncError("remote synchronization evidence is invalid") from exc
    if result.get("status") != "PASS" or result.get("root") != str(final):
        raise SyncError("remote synchronization evidence differs")
    result.update({
        "release_set": str(final / "production-release-set.json"),
        "customer_package_root": str(final / "customer-package"),
        "payload_root": str(final / "payload"),
        "public_key": str(final / "tenant-payload-public-key.pem"),
    })
    return result


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    result.add_argument("--tool-sha", required=True)
    result.add_argument("--delivery-id", required=True)
    result.add_argument("--customer-package-root", required=True, type=Path)
    result.add_argument("--payload-root", required=True, type=Path)
    result.add_argument("--public-key", required=True, type=Path)
    result.add_argument("--release-version", required=True)
    result.add_argument("--product-sha", required=True)
    result.add_argument("--product-tree", required=True)
    result.add_argument("--product-image", required=True)
    result.add_argument("--product-image-digest", required=True)
    result.add_argument("--customer-sha", required=True)
    result.add_argument("--customer-tree", required=True)
    result.add_argument("--tenant-key", required=True)
    result.add_argument("--customer-module", required=True, action="append")
    result.add_argument("--payload-version", required=True)
    result.add_argument("--payload-schema-version", required=True)
    return result


def main() -> int:
    try:
        result = synchronize(parser().parse_args())
    except (OSError, UnicodeError, KeyError, SyncError) as exc:
        raise SystemExit(f"[production.tenant-delivery.artifact.sync] BLOCKED: {exc}") from exc
    print("[production.tenant-delivery.artifact.sync] PASS " + json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
