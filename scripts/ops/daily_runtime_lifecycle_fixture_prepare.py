#!/usr/bin/env python3
"""Prepare the daily runtime acceptance fixture for the project lifecycle lane.

The governed daily runtime (``ENV=dev``, database ``sc_demo``) is a deployed
external revision. Its checkout carries the fixture builder that was current
when it was deployed, so the declared project-lifecycle carrier this lane needs
cannot be created by re-running the deployed builder.

This entry therefore drives the *working tree's* governed fixture builder into
the *bound duty's own* application container: the builder source is sent on the
standard input of the duty-bound shell carrier, so the carrier executes exactly
the branch's fixture tooling without rewriting a deployed checkout, restarting
the service, or touching any credential file.  A database *name* is not the
target: the rebuilt demo duty and the preserved pre-governance source both
answer to ``sc_demo``, and the command therefore names the compose project the
declaration binds instead of a bare ``DB_NAME``.

It writes only acceptance fixture rows inside the declared ``daily_dev`` fixture
scope (``smart_construction_acceptance_fixture``, database ``sc_demo``): the
deterministic FE dataset plus the resettable ``FE Project Lifecycle`` carrier.
It never writes product code, schema, volumes or tenant business data, and it
proves the outcome with a readback of the carrier identity and start state.
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
FIXTURE_TOOL = ROOT / "addons" / "smart_construction_acceptance_fixture" / "tools" / "frontend_productization_fixture.py"
REMOTE_ROOT = "/opt/projects/repos/sce-product-odoo"
REMOTE_TMP = "/tmp/sc-daily-lifecycle-fixture-prepare.py"
DEFAULT_DATABASE = ""
#: The fixture builder reads its own governance inputs from the process
#: environment.  They travel as explicit ``docker exec -e`` values on the bound
#: container, so the lane no longer depends on an environment file that belongs
#: to whichever checkout happened to serve the database name.
FIXTURE_ENV = {
    "SC_ACCEPTANCE_FIXTURE_SCOPE": "daily_dev",
    "SC_ENVIRONMENT": "dev",
    "SC_ALLOW_DEMO_DATA": "1",
}
CONFIRMATION = "DRIVE_DAILY_SC_DEMO_PROJECT_LIFECYCLE"
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
SSH_HOST = re.compile(r"^[A-Za-z0-9._-]+$")
DATABASE_NAME = re.compile(r"^[A-Za-z0-9_]+$")
EXE_LINE = "LIFECYCLE_FIXTURE_RESULT="


class PrepareError(RuntimeError):
    pass


DRIVER_TEMPLATE = """

def _daily_lifecycle_driver(_env):
    import json as _json
    summary = ensure_fixture(_env)
    carrier = _env.ref("%s.%s" % (MODULE, LIFECYCLE_FIXTURE_XMLID))
    _env.cr.commit()
    for field_name, expected in LIFECYCLE_FIXTURE_START_STATE.items():
        if carrier[field_name] != expected:
            raise RuntimeError(
                "carrier %s is not in the declared start state: %s=%s"
                % (carrier.id, field_name, carrier[field_name])
            )
    # A governed shell carrier writes fixture rows outside the request cycle, so
    # no worker ever sees the write and signals the invalidation itself. Without
    # this, a long-lived worker keeps the previous membership/registration answer
    # until the next restart: the deployed daily runtime denied an enrolled
    # operator exactly that way. Announce the invalidated caches once, after the
    # fixture writes are committed.
    _env.registry.clear_cache()
    _env.registry.signal_changes()
    print("__EXE_LINE__" + _json.dumps({
        "database": _env.cr.dbname,
        "carrier_id": int(carrier.id),
        "carrier_code": str(carrier.code or ""),
        "carrier_name": str(carrier.name or ""),
        "company_id": int(carrier.company_id.id),
        "company_name": str(carrier.company_id.name or ""),
        "state": {key: carrier[key] for key in LIFECYCLE_FIXTURE_START_STATE},
        "xmlid": "%s.%s" % (MODULE, LIFECYCLE_FIXTURE_XMLID),
        "reset": summary["lifecycle_carrier"]["reset"],
    }, ensure_ascii=True, separators=(",", ":"), sort_keys=True))


if "env" not in globals():
    raise SystemExit("daily lifecycle fixture entry must run through odoo shell")
try:
    _daily_lifecycle_driver(env)
except SystemExit:
    raise
except Exception:
    import traceback
    traceback.print_exc()
    raise SystemExit(1)
"""


def fixture_driver() -> str:
    """Return the readback driver appended to the working-tree fixture builder."""
    return DRIVER_TEMPLATE.replace("__EXE_LINE__", EXE_LINE)


def fixture_program() -> bytes:
    """Return the shell program: the working-tree fixture builder plus its driver.

    The builder is a self-contained module of standard-library imports, so it is
    prepended verbatim - its ``from __future__`` import must stay at the top of
    the program - and driven through the same ``ensure_fixture`` entry the
    isolated acceptance lane uses.
    """
    source = FIXTURE_TOOL.read_text(encoding="utf-8")
    program = source + fixture_driver()
    try:
        compile(program, str(FIXTURE_TOOL), "exec")
    except SyntaxError as error:
        raise PrepareError("fixture tool cannot be driven as a shell program: %s" % error)
    return program.encode("utf-8")


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


def remote_shell(ssh_host, binding, *, stdin_path, env=None):
    """Run a program inside the *bound duty's own* application container.

    The container comes from the declaration's compose project, so the write
    cannot land in another project that happens to serve a database of the same
    name.
    """
    return ssh(
        ssh_host,
        duty_identity.odoo_shell_command(binding, program_path=stdin_path, env=env or {}),
    )


def served_identity(base_url):
    if not base_url:
        return {}
    try:
        with urllib.request.urlopen(base_url.rstrip("/") + "/api/runtime-version", timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, ValueError, OSError):
        return {}


def preflight(expected_sha, database, ssh_host, password):
    if not FULL_SHA.fullmatch(expected_sha or ""):
        raise PrepareError("expected SHA must be a full lowercase commit identity")
    if not DATABASE_NAME.fullmatch(database or ""):
        raise PrepareError("database must be a plain database name")
    if not SSH_HOST.fullmatch(ssh_host or ""):
        raise PrepareError("SSH host must be a configured host alias")
    if not password:
        raise PrepareError("the fixture password must be supplied")
    if not (ROOT / ".git").exists():
        raise PrepareError("must run from the governed repository")
    if not FIXTURE_TOOL.exists():
        raise PrepareError("fixture tool is missing: %s" % FIXTURE_TOOL)


def prepare(expected_sha, binding, ssh_host, base_url, password):
    database = str(binding["database"])
    preflight(expected_sha, database, ssh_host, password)

    head = ssh(ssh_host, "cd %s && git rev-parse HEAD" % shlex.quote(REMOTE_ROOT))
    if head.returncode:
        raise PrepareError("remote revision read failed: %s" % decode(head)[:400])
    remote_head = head.stdout.decode().strip()
    if remote_head != expected_sha:
        raise PrepareError("remote HEAD %s != declared served revision %s" % (remote_head or "<unknown>", expected_sha))

    program = fixture_program()
    upload = ssh(ssh_host, "cat > %s" % shlex.quote(REMOTE_TMP), input_bytes=program)
    if upload.returncode:
        raise PrepareError("remote builder upload failed: %s" % decode(upload)[:400])
    env = dict(FIXTURE_ENV)
    env["SC_ACCEPTANCE_FIXTURE_PASSWORD"] = password
    applied = remote_shell(ssh_host, binding, stdin_path=REMOTE_TMP, env=env)
    ssh(ssh_host, "rm -f %s" % shlex.quote(REMOTE_TMP))
    output = decode(applied)
    if applied.returncode:
        raise PrepareError("daily lifecycle fixture preparation failed: %s" % output[-1200:])

    payload = ""
    for line in output.splitlines():
        if line.startswith(EXE_LINE):
            payload = line[len(EXE_LINE):].strip()
    if not payload:
        raise PrepareError("daily lifecycle fixture readback missing: %s" % output[-800:])
    try:
        carrier = json.loads(payload)
    except ValueError as error:
        raise PrepareError("daily lifecycle fixture readback is not JSON: %s" % error)

    identity = served_identity(base_url)
    served_database = str(identity.get("database") or "")
    served_revision = str(identity.get("git_sha") or identity.get("source_revision") or "")

    evidence = {
        "schema": "daily.runtime.lifecycle_fixture.prepare.v1",
        "status": "PASS",
        "ssh_host": ssh_host,
        "remote_head": remote_head,
        "expected_sha": expected_sha,
        "database": database,
        "database_binding": binding,
        "carrier": carrier,
        "served_revision": served_revision,
        "served_database": served_database,
        "fixture_tool": str(FIXTURE_TOOL.relative_to(ROOT)),
        "engine_output_tail": output.splitlines()[-8:],
    }
    declared = carrier.get("state") or {}
    landed = str(carrier.get("database") or "")
    if landed and landed != database:
        evidence["status"] = "FAIL"
        evidence["reason"] = "the fixture builder read back database %s, not the bound %s" % (landed, database)
    elif declared.get("lifecycle_state") != "draft" or declared.get("sc_approval_state") != "draft":
        evidence["status"] = "FAIL"
        evidence["reason"] = "carrier did not read back in the declared start state"
    elif base_url and served_database and served_database != database:
        evidence["status"] = "FAIL"
        evidence["reason"] = "served database %s != %s" % (served_database, database)
    elif base_url and served_revision and served_revision != expected_sha:
        evidence["status"] = "FAIL"
        evidence["reason"] = "served revision %s != %s" % (served_revision, expected_sha)
    return evidence




def bind_target(options, *, instances_reader=None) -> dict:
    """Bind the target duty, its cluster, its database and its storage, or stop.

    The fixture carrier is driven through one served face; the face has to be bound to a duty before it is driven.
    """
    try:
        reader = instances_reader
        if reader is None:
            reader = duty_identity.ssh_instances_reader(options.ssh_host)
        return duty_identity.bind_duty_database(
            getattr(options, "duty", ""), options.database, instances_reader=reader,
        )
    except duty_identity.DutyIdentityError as error:
        raise PrepareError(str(error))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--database", default=DEFAULT_DATABASE)
    parser.add_argument("--duty", default="", help="the declared duty this entry binds; a database name alone is not a target identity")
    parser.add_argument("--ssh-host", required=True)
    parser.add_argument("--base-url", default="")
    parser.add_argument("--password", default="")
    parser.add_argument("--report", required=True)
    options = parser.parse_args()

    try:
        if (os.environ.get("CONFIRM_DAILY_RUNTIME_LIFECYCLE_FIXTURE") or "") != CONFIRMATION:
            raise PrepareError("exact daily runtime lifecycle fixture confirmation is required")
        binding = bind_target(options)
        evidence = prepare(
            options.expected_sha,
            binding,
            options.ssh_host,
            options.base_url,
            options.password,
        )
    except PrepareError as error:
        print("[daily.runtime.lifecycle_fixture.prepare] BLOCKED %s" % error, file=sys.stderr)
        return 2

    report_path = Path(options.report)
    evidence["database_binding"] = binding
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if evidence.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
