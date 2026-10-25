#!/usr/bin/env python3
"""Resolve the governed daily-runtime acceptance record identity.

Every browser acceptance lane must bind the *served* identity of its fixture
carrier, never a locally guessed database id: the daily runtime (``ENV=dev``,
database ``sc_demo``) rebuilds its fixture rows whenever the lifecycle carrier
is recreated, so a previously captured numeric id becomes stale silently.

The deployed daily runtime is an external revision whose checkout carries the
resolver that was current when it was deployed. This entry therefore drives the
*working tree's* governed resolver through the existing ``make odoo.shell.exec``
entry: the resolver source is sent on the standard input of the duty-bound shell
carrier, so that carrier executes exactly the branch's resolver without
rewriting a deployed checkout, restarting the service, or touching any
credential file.  A database *name* is not the target: the rebuilt demo duty and
the preserved pre-governance source both answer to ``sc_demo``, so the command
names the compose project the declaration binds instead of a bare ``DB_NAME``.

It writes only the resolved-identity artifact plus its own report, and it writes
the artifact in the canonical governed envelope (``schema``/``producer``/
``expected_sha``/``targets``) that the repository's resolution consumers read. It
never writes product code, schema, volumes, fixture rows or tenant business data,
and it fails closed on any revision, database or payload disagreement.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import daily_runtime_duty_identity as duty_identity  # noqa: E402

RESOLVER = ROOT / "scripts" / "verify" / "frontend_delivery_hardening_runtime_ids.py"
REMOTE_ROOT = "/opt/projects/repos/sce-product-odoo"
REMOTE_TMP = "/tmp/sc-daily-record-identity-resolve.py"
DEFAULT_DATABASE = ""
CONFIRMATION = "RESOLVE_DAILY_SC_DEMO_RECORD_IDENTITY"
SCHEMA = "acceptance.record_identity_resolution.v1"
PAYLOAD_PREFIX = "FRONTEND_DELIVERY_HARDENING_TARGETS_JSON="
LANDED_PREFIX = "RECORD_IDENTITY_DATABASE="
#: The resolver reads its own governance inputs from the process environment.
RESOLVER_ENV = {"SC_ENVIRONMENT": "dev", "SC_ALLOW_DEMO_DATA": "1"}
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
SSH_HOST = re.compile(r"^[A-Za-z0-9._-]+$")
DATABASE_NAME = re.compile(r"^[A-Za-z0-9_]+$")
REQUIRED_TARGET_KEYS = ("menu_id", "action_id", "model", "record_id", "record_xmlid", "record_identity")


class ResolveError(RuntimeError):
    pass


def run(command, *, input_bytes=None):
    return subprocess.run(
        command,
        cwd=ROOT,
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def decode(result):
    return (result.stdout + result.stderr).decode(errors="replace").strip()


def ssh(ssh_host, remote_command, *, input_bytes=None):
    return run(
        [
            "ssh",
            "-o", "BatchMode=yes",
            "-o", "ConnectTimeout=10",
            "-o", "ServerAliveInterval=15",
            "-o", "ServerAliveCountMax=4",
            ssh_host,
            remote_command,
        ],
        input_bytes=input_bytes,
    )


def served_identity(base_url):
    if not base_url:
        return {}
    try:
        with urllib.request.urlopen(base_url.rstrip("/") + "/api/runtime-version", timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, ValueError, OSError):
        return {}


def resolver_program() -> bytes:
    """Return the governed resolver exactly as it exists in this working tree."""
    if not RESOLVER.exists():
        raise ResolveError("governed resolver is missing: %s" % RESOLVER)
    program = RESOLVER.read_bytes()
    try:
        compile(program.decode("utf-8"), str(RESOLVER), "exec")
    except (SyntaxError, UnicodeDecodeError) as error:
        raise ResolveError("governed resolver is not executable as a shell program: %s" % error)
    return program


def carrier_program() -> bytes:
    """The resolver verbatim, plus the landed-database probe the lane asserts.

    The resolver is executed exactly as this working tree ships it; the probe is
    appended so the entry can prove *which* carrier answered.  A database name is
    not a target identity: the rebuilt demo duty and the preserved pre-governance
    source both answer to ``sc_demo``.
    """
    return resolver_program() + (
        '\nprint("%s%%s" %% env.cr.dbname)\n' % LANDED_PREFIX
    ).encode("utf-8")


def resolver_environment(binding):
    values = dict(RESOLVER_ENV)
    if binding.get("duty") == "demo":
        values["SC_ACCEPTANCE_RECORD_AUTHORITY"] = "daily_demo"
    return values


def remote_shell(ssh_host, binding, *, stdin_path):
    """Run the resolver inside the *bound duty's own* application container."""
    return ssh(
        ssh_host,
        duty_identity.odoo_shell_command(binding, program_path=stdin_path, env=resolver_environment(binding)),
    )


def parse_payload(output: str) -> dict:
    """Extract and validate the resolver payload from the engine output."""
    payload = ""
    for line in output.splitlines():
        if line.startswith(PAYLOAD_PREFIX):
            payload = line[len(PAYLOAD_PREFIX):].strip()
    if not payload:
        raise ResolveError("resolver payload missing: %s" % output[-800:])
    try:
        decoded = json.loads(payload)
    except ValueError as error:
        raise ResolveError("resolver payload is not JSON: %s" % error)
    if not isinstance(decoded, dict) or not decoded:
        raise ResolveError("resolver payload is not a non-empty object")
    companies = decoded.get("companies")
    if not isinstance(companies, dict) or not companies:
        raise ResolveError("resolver payload is missing the declared companies map")
    for key, value in decoded.items():
        if key == "companies":
            continue
        if not isinstance(value, dict):
            raise ResolveError("resolver payload target %s is not an object" % key)
        for required in REQUIRED_TARGET_KEYS:
            if value.get(required) in (None, ""):
                raise ResolveError("resolver payload target %s is missing %s" % (key, required))
        if not (int(value["record_id"]) > 0 and int(value["menu_id"]) > 0 and int(value["action_id"]) > 0):
            raise ResolveError("resolver payload target %s carries a non-positive identity" % key)
    return decoded


def envelope(targets: dict, expected_sha: str) -> dict:
    """Return the canonical governed envelope every consumer reads."""
    return {
        "schema": SCHEMA,
        "producer": str(RESOLVER.relative_to(ROOT)),
        "expected_sha": expected_sha,
        "targets": targets,
    }


def preflight(expected_sha, database, ssh_host):
    if not FULL_SHA.fullmatch(expected_sha or ""):
        raise ResolveError("expected SHA must be a full lowercase commit identity")
    if not DATABASE_NAME.fullmatch(database or ""):
        raise ResolveError("database must be a plain database name")
    if not SSH_HOST.fullmatch(ssh_host or ""):
        raise ResolveError("SSH host must be a configured host alias")
    if not (ROOT / ".git").exists():
        raise ResolveError("must run from the governed repository")
    if not RESOLVER.exists():
        raise ResolveError("governed resolver is missing: %s" % RESOLVER)


def resolve(expected_sha, binding, ssh_host, base_url, output_path, report_path):
    database = str(binding["database"])
    preflight(expected_sha, database, ssh_host)

    head = ssh(ssh_host, "cd %s && git rev-parse HEAD" % shlex.quote(REMOTE_ROOT))
    if head.returncode:
        raise ResolveError("remote revision read failed: %s" % decode(head)[:400])
    remote_head = head.stdout.decode().strip()
    if remote_head != expected_sha:
        raise ResolveError(
            "remote HEAD %s != declared served revision %s" % (remote_head or "<unknown>", expected_sha)
        )

    identity = served_identity(base_url)
    served_revision = str(identity.get("git_sha") or identity.get("source_revision") or "")
    served_database = str(identity.get("database") or "")
    if base_url:
        if served_revision and served_revision != expected_sha:
            raise ResolveError("served revision %s != declared %s" % (served_revision, expected_sha))
        if served_database and served_database != database:
            raise ResolveError("served database %s != declared %s" % (served_database, database))

    upload = ssh(ssh_host, "cat > %s" % shlex.quote(REMOTE_TMP), input_bytes=carrier_program())
    if upload.returncode:
        raise ResolveError("remote resolver upload failed: %s" % decode(upload)[:400])
    applied = remote_shell(ssh_host, binding, stdin_path=REMOTE_TMP)
    ssh(ssh_host, "rm -f %s" % shlex.quote(REMOTE_TMP))
    output = decode(applied)
    if applied.returncode:
        raise ResolveError("daily record identity resolution failed: %s" % output[-1200:])
    landed = ""
    for line in output.splitlines():
        if line.startswith(LANDED_PREFIX):
            landed = line[len(LANDED_PREFIX):].strip()
    if landed != database:
        raise ResolveError(
            "the resolver ran in database %s, not the bound %s" % (landed or "<unknown>", database)
        )
    targets = parse_payload(output)

    documented = envelope(targets, expected_sha)
    artifact = Path(output_path)
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(
        json.dumps(documented, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    evidence = {
        "schema": "daily.runtime.record_identity.resolve.v1",
        "status": "PASS",
        "ssh_host": ssh_host,
        "remote_head": remote_head,
        "expected_sha": expected_sha,
        "database": database,
        "database_binding": binding,
        "landed_database": landed,
        "served_revision": served_revision,
        "served_database": served_database,
        "resolver": str(RESOLVER.relative_to(ROOT)),
        "artifact": str(artifact),
        "artifact_schema": SCHEMA,
        "targets": sorted(key for key in targets if key != "companies"),
        "company_ids": targets.get("companies"),
        "engine_output_tail": output.splitlines()[-4:],
    }
    report = Path(report_path)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return evidence


def bind_target(options, *, instances_reader=None) -> dict:
    """Bind the target duty, its cluster, its database and its storage, or stop.

    The browser lanes bind the identity of one served carrier; a name two
    carriers share would bind whichever one happened to answer.
    """
    try:
        reader = instances_reader
        if reader is None:
            reader = duty_identity.ssh_instances_reader(options.ssh_host)
        return duty_identity.bind_duty_database(
            getattr(options, "duty", ""), options.database, instances_reader=reader,
        )
    except duty_identity.DutyIdentityError as error:
        raise ResolveError(str(error))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--duty", default="", help="the declared duty this entry binds; a database name alone is not a target identity")
    parser.add_argument("--database", default=DEFAULT_DATABASE)
    parser.add_argument("--ssh-host", required=True)
    parser.add_argument("--base-url", default="")
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    options = parser.parse_args()

    try:
        if (os.environ.get("CONFIRM_DAILY_RUNTIME_RECORD_IDENTITY") or "") != CONFIRMATION:
            raise ResolveError("exact daily runtime record identity confirmation is required")
        binding = bind_target(options)
        evidence = resolve(
            options.expected_sha,
            binding,
            options.ssh_host,
            options.base_url,
            options.output,
            options.report,
        )
    except ResolveError as error:
        print("[daily.runtime.record_identity.resolve] BLOCKED %s" % error, file=sys.stderr)
        return 2

    print(json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if evidence.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
