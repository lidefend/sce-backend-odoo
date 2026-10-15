#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deliver one exact customer-tenant commit's addons tree to the daily runtime.

The daily development server serves a customer tenant duty from a *customer*
addons tree, not from the tenant-neutral product tree. That tree is P2 content
owned by the customer delivery repository, so this entry never edits it: it
delivers one exact customer commit, byte for byte, into the governed daily
namespace and proves the delivered tree is the reviewed one.

Three properties are fail-closed rather than best effort:

* the source is one exact commit of a clean customer worktree. A branch name,
  a dirty tree or an unreadable commit is a stop, because "what we installed"
  has to survive as an identity that can be rebuilt later;
* the destination is content-addressed (``<root>/<commit>``) and write-once.
  A destination that already carries the same marker and the same content is an
  idempotent no-op; a destination that carries different content is a stop, not
  an overwrite, so a released tree can never be silently replaced under a duty
  that is already serving from it;
* the tree digest computed inside the destination must equal the digest of the
  archive that was sent. Digests are computed by one shared implementation, so
  "the host has the reviewed tree" is a measurement rather than an assumption.

``--report`` writes a local file only and never mutates the host. The read-only
path is the default; only ``--apply`` writes, and only with the exact
confirmation.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import shlex
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[2]
REMOTE_TMP = "/tmp/sc-daily-tenant-addons.py"
MARKER = "DAILY_RUNTIME_TENANT_ADDONS="
#: The registered daily tenant-addons namespace. It is the daily sibling of
#: ``/opt/sce/tenant-addons/acceptance`` and keeps the same shape: one directory
#: per exact customer commit, carrying a ``TENANT_SHA`` marker, read-only.
REMOTE_ROOT = "/opt/sce/tenant-addons/daily"
CONFIRMATION = "DELIVER_EXACT_DAILY_RUNTIME_TENANT_ADDONS"
CONFIRM_ENV = "SC_CONFIRM_DAILY_RUNTIME_TENANT_ADDONS"
DEFAULT_CUSTOMER_MODULE = "sce_customer_baosheng"
SUBTREE = "addons"
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
SSH_HOST = re.compile(r"^[A-Za-z0-9._-]+$")
MODULE_NAME = re.compile(r"^[a-z][a-z0-9_]*$")

#: One implementation of the content digest, shared by the local check and the
#: remote readback. Two implementations would let "delivered" and "reviewed"
#: agree on the word and disagree on the measurement.
TREE_DIGEST_SOURCE = """
def tree_digest(root):
    import hashlib
    from pathlib import Path
    entries = []
    root = Path(root)
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        if relative == "TENANT_SHA":
            continue
        entries.append((relative, hashlib.sha256(path.read_bytes()).hexdigest()))
    digest = hashlib.sha256()
    for relative, sha in sorted(entries):
        digest.update(relative.encode("utf-8") + b"\\0" + sha.encode("ascii") + b"\\0")
    return {"digest": digest.hexdigest(), "files": len(entries)}
"""

_LOCAL = {}
exec(TREE_DIGEST_SOURCE, _LOCAL)  # noqa: S102 - one reviewed implementation
tree_digest = _LOCAL["tree_digest"]


class DeliverError(RuntimeError):
    pass


def run(command, *, input_bytes=None, cwd=None):
    return subprocess.run(
        command, cwd=cwd or ROOT, input=input_bytes,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )


def ssh(ssh_host, remote_command, *, input_bytes=None):
    return run(
        [
            "ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
            "-o", "ServerAliveInterval=15", "-o", "ServerAliveCountMax=4",
            ssh_host, remote_command,
        ],
        input_bytes=input_bytes,
    )


def decode(result):
    return (result.stdout + result.stderr).decode("utf-8", "replace")


def marker_payload(output):
    for line in reversed(output.splitlines()):
        if line.startswith(MARKER):
            try:
                return json.loads(line[len(MARKER):])
            except ValueError:
                return None
    return None


def git(repository, *arguments):
    result = run(["git", "-C", str(repository), *arguments])
    if result.returncode:
        raise DeliverError(
            "git %s failed: %s" % (arguments[0] if arguments else "", decode(result).strip()[:400])
        )
    return decode(result).strip()


def source_facts(repository, tenant_sha):
    """Prove the reviewed source before anything is produced from it."""
    path = Path(repository).expanduser()
    if not (path / ".git").exists():
        raise DeliverError("customer repository is not a git worktree: %s" % (path,))
    resolved = git(path, "rev-parse", "--show-toplevel")
    if Path(resolved).resolve() != path.resolve():
        raise DeliverError("customer repository identity mismatch: %s" % (resolved,))
    if not FULL_SHA.fullmatch(tenant_sha or ""):
        raise DeliverError("tenant SHA must be a full lowercase commit identity")
    probe = run(["git", "-C", str(path), "cat-file", "-e", tenant_sha + "^{commit}"])
    if probe.returncode:
        raise DeliverError("tenant SHA is not a commit in this repository: %s" % (tenant_sha,))
    status = git(path, "status", "--porcelain")
    return {
        "repository": str(path.resolve()),
        "tenant_sha": tenant_sha,
        "head": git(path, "rev-parse", "HEAD"),
        "clean": not status,
    }


def archive_bytes(repository, tenant_sha):
    result = run(["git", "-C", str(repository), "archive", "--format=tar", tenant_sha, SUBTREE])
    if result.returncode:
        raise DeliverError("git archive failed: %s" % (decode(result).strip()[:400],))
    if not result.stdout:
        raise DeliverError("git archive produced an empty archive")
    return result.stdout


def archive_modules(archive):
    """The module directories the archive actually carries, from the archive."""
    modules = []
    with tarfile.open(fileobj=io.BytesIO(archive)) as handle:
        for member in handle.getmembers():
            if not member.isfile():
                continue
            parts = PurePosixPath(member.name).parts
            if len(parts) != 3 or parts[0] != SUBTREE or parts[2] != "__manifest__.py":
                continue
            modules.append(parts[1])
    return sorted(set(modules))


def local_tree_digest(archive):
    """The digest of the archive as it will be extracted on the host."""
    with tempfile.TemporaryDirectory(prefix="sc-tenant-addons-") as workspace:
        target = Path(workspace)
        with tarfile.open(fileobj=io.BytesIO(archive)) as handle:
            handle.extractall(target, filter="data")  # noqa: S202 - reviewed archive
        root = target / SUBTREE
        if not root.is_dir():
            raise DeliverError("the archive carries no %s subtree" % (SUBTREE,))
        return tree_digest(root)


def render_remote_program(payload):
    """The remote half of the entry: it is the only writer of the destination."""
    program = REMOTE_PROGRAM.replace(  # noqa: S101 - reviewed template
        "__TREE_DIGEST_SOURCE__", TREE_DIGEST_SOURCE
    ).replace(
        "__REMOTE_ROOT__", repr(REMOTE_ROOT)
    ).replace(
        "__MARKER__", repr(MARKER)
    ).replace(
        "__PAYLOAD_JSON__", json.dumps(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    )
    return program


def upload_program(ssh_host, payload):
    program = render_remote_program(payload)
    upload = ssh(ssh_host, "cat > %s" % (shlex.quote(REMOTE_TMP),), input_bytes=program.encode("utf-8"))
    if upload.returncode:
        raise DeliverError("remote program upload failed: %s" % (decode(upload)[:400],))


def cleanup_program(ssh_host):
    ssh(ssh_host, "rm -f %s" % (shlex.quote(REMOTE_TMP),))


def remote_report(ssh_host, payload):
    upload_program(ssh_host, payload)
    try:
        executed = ssh(
            ssh_host,
            "python3 %s" % (shlex.quote(REMOTE_TMP),),
        )
        if executed.returncode:
            raise DeliverError("remote report failed: %s" % (decode(executed)[:600],))
        result = marker_payload(decode(executed))
        if result is None:
            raise DeliverError("no readback payload: %s" % (decode(executed)[-400:],))
        return result
    finally:
        cleanup_program(ssh_host)


def remote_apply(ssh_host, payload, archive):
    upload_program(ssh_host, payload)
    try:
        executed = ssh(
            ssh_host,
            "python3 %s" % (shlex.quote(REMOTE_TMP),),
            input_bytes=archive,
        )
        if executed.returncode:
            raise DeliverError("remote apply failed: %s" % (decode(executed)[:800],))
        result = marker_payload(decode(executed))
        if result is None:
            raise DeliverError("no readback payload: %s" % (decode(executed)[-400:],))
        return result
    finally:
        cleanup_program(ssh_host)


# ----------------------------------------------------------------------
# verdict
# ----------------------------------------------------------------------
def assertions(source, delivery, payload):
    expected = payload["expected_digest"]
    observed = delivery.get("digest")
    return [
        {
            "id": "delivered_tree_matches_the_reviewed_archive",
            "passed": bool(observed) and observed == expected,
            "detail": {"expected": expected, "observed": observed,
                       "error": delivery.get("error") or ""},
        },
        {
            "id": "destination_carries_the_reviewed_commit_marker",
            "passed": delivery.get("tenant_sha") == payload["tenant_sha"],
            "detail": {"expected": payload["tenant_sha"], "observed": delivery.get("tenant_sha")},
        },
        {
            "id": "every_required_module_is_present_in_the_destination",
            "passed": not delivery.get("missing_modules"),
            "detail": {"required": payload["require_modules"],
                       "missing": delivery.get("missing_modules") or []},
        },
        {
            "id": "delivered_module_set_is_exactly_the_archived_one",
            "passed": delivery.get("modules") == payload["modules"],
            "detail": {"archived": payload["modules"], "delivered": delivery.get("modules")},
        },
        {
            "id": "source_was_one_exact_commit",
            "passed": bool(source.get("tenant_sha")) and source.get("tenant_sha") == payload["tenant_sha"],
            "detail": {"tenant_sha": source.get("tenant_sha"), "head": source.get("head")},
        },
        {
            "id": "destination_is_read_only",
            "passed": delivery.get("writable_paths") == [],
            "detail": {"writable_paths": delivery.get("writable_paths") or []},
        },
    ]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ssh-host", required=True)
    parser.add_argument("--customer-repository", required=True)
    parser.add_argument("--tenant-sha", required=True)
    parser.add_argument("--require-module", action="append", default=[])
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--report", required=True)
    options = parser.parse_args(argv)

    try:
        if not SSH_HOST.fullmatch(options.ssh_host or ""):
            raise DeliverError("SSH host must be a configured host alias")
        source = source_facts(options.customer_repository, options.tenant_sha)
        if options.apply and not source["clean"]:
            raise DeliverError("customer worktree is not clean; an exact commit is required")
        required = sorted(set(options.require_module or [DEFAULT_CUSTOMER_MODULE]))
        malformed = [item for item in required if not MODULE_NAME.fullmatch(str(item))]
        if malformed:
            raise DeliverError("invalid required module name: %s" % (",".join(malformed),))
        archive = archive_bytes(options.customer_repository, options.tenant_sha)
        digest = local_tree_digest(archive)
        modules = archive_modules(archive)
        absent = [item for item in required if item not in modules]
        if absent:
            raise DeliverError(
                "the reviewed commit does not carry the required modules: %s" % (",".join(absent),)
            )
        payload = {
            "mode": "apply" if options.apply else "report",
            "tenant_sha": options.tenant_sha,
            "expected_digest": digest["digest"],
            "expected_files": digest["files"],
            "modules": modules,
            "require_modules": required,
        }
        if options.apply:
            confirmation = os.environ.get(CONFIRM_ENV, "").strip()
            if confirmation != CONFIRMATION:
                raise DeliverError("DAILY_TENANT_ADDONS_CONFIRMATION_REQUIRED:%s" % (CONFIRM_ENV,))
            delivery = remote_apply(options.ssh_host, payload, archive)
        else:
            delivery = remote_report(options.ssh_host, payload)
    except DeliverError as error:
        print("[daily.runtime.tenant.addons] BLOCKED %s" % (error,), file=sys.stderr)
        return 2

    rows = assertions(source, delivery, payload)
    report = {
        "status": "PASS" if all(row["passed"] for row in rows) else "FAIL",
        "mode": payload["mode"],
        "source": source,
        "destination": {"root": REMOTE_ROOT, "path": delivery.get("path")},
        "digest": {"expected": payload["expected_digest"], "observed": delivery.get("digest"),
                   "files": delivery.get("files")},
        "modules": delivery.get("modules"),
        "assertions": rows,
    }
    report_path = Path(options.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print("[daily.runtime.tenant.addons] %s %s" % (
        report["status"],
        json.dumps({"mode": report["mode"], "path": report["destination"]["path"],
                    "digest": report["digest"]["observed"], "modules": report["modules"]},
                   sort_keys=True),
    ))
    return 0 if report["status"] == "PASS" else 1


REMOTE_PROGRAM = r'''
import hashlib, json, os, stat, sys, tarfile
from pathlib import Path, PurePosixPath

__TREE_DIGEST_SOURCE__

REMOTE_ROOT = __REMOTE_ROOT__
MARKER = __MARKER__
PAYLOAD = json.loads(__PAYLOAD_JSON__)
MODE = PAYLOAD["mode"]


def fail(code, detail=""):
    print(MARKER + json.dumps({"error": code + (":" + detail if detail else ""), "mode": MODE}))
    raise SystemExit(1)


def writable_paths(root):
    bad = []
    for path in sorted(Path(root).rglob("*")):
        if path.is_symlink():
            bad.append(path.as_posix() + " (symlink)")
        elif path.stat().st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH):
            bad.append(path.relative_to(root).as_posix())
    return bad


def facts(final):
    modules = sorted({
        path.parent.name for path in Path(final).glob("*/__manifest__.py")
    })
    digest = tree_digest(final)
    marker = Path(final) / "TENANT_SHA"
    return {
        "mode": MODE,
        "path": str(final),
        "exists": True,
        "tenant_sha": marker.read_text().strip() if marker.exists() else "",
        "digest": digest["digest"],
        "files": digest["files"],
        "modules": modules,
        "missing_modules": [item for item in PAYLOAD["require_modules"] if item not in modules],
        "writable_paths": writable_paths(final),
    }


root = Path(REMOTE_ROOT)
final = root / PAYLOAD["tenant_sha"]
staging = root / (".incomplete-" + PAYLOAD["tenant_sha"])
if root.exists() and not root.is_dir():
    fail("REMOTE_ROOT_IS_NOT_A_DIRECTORY", REMOTE_ROOT)

if MODE == "report":
    if not final.is_dir():
        print(MARKER + json.dumps({"mode": MODE, "path": str(final), "exists": False,
                                   "error": "the reviewed commit is not delivered", "modules": []}))
        raise SystemExit(0)
    print(MARKER + json.dumps(facts(final), sort_keys=True))
    raise SystemExit(0)

if MODE != "apply":
    fail("UNKNOWN_MODE", MODE)

root.mkdir(parents=True, exist_ok=True, mode=0o700)
os.chmod(root, 0o700)

if final.is_dir():
    if (final / "TENANT_SHA").exists() and (final / "TENANT_SHA").read_text().strip() == PAYLOAD["tenant_sha"]:
        observed = facts(final)
        observed["already_present"] = True
        observed["writes"] = 0
        print(MARKER + json.dumps(observed, sort_keys=True))
        raise SystemExit(0)
    fail("DESTINATION_ALREADY_EXISTS_WITH_ANOTHER_IDENTITY", str(final))

if staging.exists():
    fail("STAGING_ALREADY_EXISTS", str(staging))

staging.mkdir(mode=0o755)
try:
    with tarfile.open(fileobj=sys.stdin.buffer, mode="r|") as archive:
        for member in archive:
            parts = PurePosixPath(member.name).parts
            if len(parts) < 2 or parts[0] != "addons":
                continue
            relative = PurePosixPath(*parts[1:])
            if relative.is_absolute() or ".." in relative.parts:
                fail("ARCHIVE_PATH_ESCAPES_THE_DESTINATION", member.name)
            target = staging / relative.as_posix()
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            if not member.isfile():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            source = archive.extractfile(member)
            with target.open("wb") as handle:
                while True:
                    chunk = source.read(1024 * 1024)
                    if not chunk:
                        break
                    handle.write(chunk)
except tarfile.TarError as error:
    fail("ARCHIVE_UNREADABLE", str(error)[:200])

modules = sorted({path.parent.name for path in staging.glob("*/__manifest__.py")})
if modules != PAYLOAD["modules"]:
    fail("EXTRACTED_MODULE_SET_DIFFERS_FROM_THE_ARCHIVE", json.dumps(modules))
digest = tree_digest(staging)
if digest["digest"] != PAYLOAD["expected_digest"]:
    fail("EXTRACTED_CONTENT_DIFFERS_FROM_THE_REVIEWED_ARCHIVE", digest["digest"])

(staging / "TENANT_SHA").write_text(PAYLOAD["tenant_sha"] + "\n")
for path in sorted(staging.rglob("*"), reverse=True):
    if path.is_symlink():
        path.unlink()
    elif path.is_dir():
        os.chmod(path, 0o555)
    else:
        os.chmod(path, 0o444)
os.chmod(staging, 0o555)
os.rename(staging, final)
os.chmod(final, 0o555)

observed = facts(final)
observed["already_present"] = False
observed["writes"] = 1
print(MARKER + json.dumps(observed, sort_keys=True))
'''


if __name__ == "__main__":
    raise SystemExit(main())
