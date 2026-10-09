#!/usr/bin/env python3
"""Provision the governed NAV-PRO-01 fixture on the daily runtime (sc_demo).

The route-authority browser lane (``verify.nav.pro01r.route_authority.browser``)
logs in as ``nav_pro_{finance,project_member,pm,owner,config_admin,system_admin}``
and walks the contract-driven navigation surface. Those users and the single
``NAV-PRO-01R Context {Project,Partner,Contract}`` carrier are an acceptance
fixture, and the daily runtime (``ENV=dev``, database ``sc_demo``) is a deployed
external revision whose checkout carries the fixture builder that was current
when it was deployed. ``make nav.pro01.runtime.prepare`` drives the *local*
compose stack, so it cannot land the fixture on the deployed daily database.

This entry therefore drives the *working tree's* governed fixture builder through
the same governed remote shell carrier the other ``daily.runtime.*`` entries use:
``make ENV=dev ENV_FILE=.env.dev DB_NAME=sc_demo odoo.shell.exec`` on ``sc-root``,
with the builder source sent on standard input. The deployed runtime executes
exactly the branch's fixture tooling without rewriting the deployed checkout,
restarting the service, or touching any credential file.

It writes only acceptance fixture rows inside the owner-authorized daily
acceptance scope (``sc_demo``): the six ``nav_pro_*`` users and the single
``NAV-PRO-01R`` project/partner/contract carrier. It never writes product code,
schema, volumes or credential files, and it proves the outcome with a readback of
the resolved user ids, carrier ids and the served revision the runtime declares.
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
FIXTURE_TOOL = ROOT / "scripts" / "verify" / "nav_pro_01_prepare_runtime.py"
REMOTE_ROOT = "/opt/projects/repos/sce-product-odoo"
DEFAULT_DATABASE = "sc_demo"
CONFIRMATION = "PROVISION_DAILY_SC_DEMO_NAV_PRO_FIXTURE"
EXE_LINE = "NAV_PRO_FIXTURE_READBACK="
SENTINEL = "NAV_PRO_01_RUNTIME_PREPARE=PASS"
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
SSH_HOST = re.compile(r"^[A-Za-z0-9._-]+$")
DATABASE_NAME = re.compile(r"^[A-Za-z0-9_]+$")


class PrepareError(RuntimeError):
    pass


DRIVER_TEMPLATE = """


def _daily_nav_pro_readback(_env):
    import json as _json
    _logins = ["nav_pro_%s" % _role for _role in roles]
    _users = _env["res.users"].sudo().with_context(active_test=False).search([("login", "in", _logins)])
    _found = {}
    for _user in _users:
        _found[str(_user.login)] = {
            "id": int(_user.id),
            "active": bool(_user.active),
            "company_id": int(_user.company_id.id),
        }
    _missing = [login for login in _logins if login not in _found]
    print("__EXE_LINE__" + _json.dumps({
        "database": str(_env.cr.dbname),
        "company_id": int(_env.company.id),
        "users": _found,
        "missing_users": _missing,
        "project_id": int(project.id) if project else 0,
        "partner_id": int(partner.id) if partner else 0,
        "contract_id": int(contract.id) if contract else 0,
    }, ensure_ascii=True, separators=(",", ":"), sort_keys=True))


if "env" not in globals():
    raise SystemExit("daily nav_pro fixture entry must run through odoo shell")
try:
    _daily_nav_pro_readback(env)
except SystemExit:
    raise
except Exception:
    import traceback
    traceback.print_exc()
    raise SystemExit(1)
"""


def fixture_program() -> bytes:
    """Return the shell program: the working-tree fixture builder plus its readback."""
    source = FIXTURE_TOOL.read_text(encoding="utf-8")
    program = source + DRIVER_TEMPLATE.replace("__EXE_LINE__", EXE_LINE)
    try:
        compile(program, str(FIXTURE_TOOL), "exec")
    except SyntaxError as error:
        raise PrepareError("nav_pro fixture cannot be driven as a shell program: %s" % error)
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
        raise PrepareError("the nav_pro fixture password must be supplied")
    if not (ROOT / ".git").exists():
        raise PrepareError("must run from the governed repository")
    if not FIXTURE_TOOL.exists():
        raise PrepareError("nav_pro fixture tool is missing: %s" % FIXTURE_TOOL)


def remote_command(database, password):
    """Return the governed remote shell entry that carries the fixture builder."""
    return (
        "cd %s && NAV_PRO_PASSWORD=%s SC_ENVIRONMENT=dev SC_ALLOW_DEMO_DATA=1 "
        "make ENV=dev ENV_FILE=.env.dev DB_NAME=%s odoo.shell.exec"
        % (
            shlex.quote(REMOTE_ROOT),
            shlex.quote(password),
            shlex.quote(database),
        )
    )


def parse_readback(output: str) -> dict:
    payload = ""
    for line in output.splitlines():
        if line.startswith(EXE_LINE):
            payload = line[len(EXE_LINE):].strip()
    if not payload:
        raise PrepareError("daily nav_pro fixture readback missing: %s" % output[-800:])
    try:
        decoded = json.loads(payload)
    except ValueError as error:
        raise PrepareError("daily nav_pro fixture readback is not JSON: %s" % error)
    if not isinstance(decoded, dict) or not decoded:
        raise PrepareError("daily nav_pro fixture readback is not a non-empty object")
    return decoded


def prepare(expected_sha, database, ssh_host, base_url, password):
    preflight(expected_sha, database, ssh_host, password)

    head = ssh(ssh_host, "cd %s && git rev-parse HEAD" % shlex.quote(REMOTE_ROOT))
    if head.returncode:
        raise PrepareError("remote revision read failed: %s" % decode(head)[:400])
    remote_head = head.stdout.decode().strip()
    if remote_head != expected_sha:
        raise PrepareError("remote HEAD %s != declared served revision %s" % (remote_head or "<unknown>", expected_sha))

    program = fixture_program()
    applied = ssh(ssh_host, remote_command(database, password), input_bytes=program)
    output = decode(applied)
    if applied.returncode:
        raise PrepareError("daily nav_pro fixture preparation failed: %s" % output[-1200:])
    if SENTINEL not in output:
        raise PrepareError("daily nav_pro fixture did not report its success sentinel: %s" % output[-1200:])
    readback = parse_readback(output)

    identity = served_identity(base_url)
    served_revision = str(identity.get("git_sha") or identity.get("source_revision") or "")
    served_database = str(identity.get("database") or "")

    evidence = {
        "schema": "daily.runtime.nav_pro_fixture.prepare.v1",
        "status": "PASS",
        "ssh_host": ssh_host,
        "remote_head": remote_head,
        "expected_sha": expected_sha,
        "database": database,
        "readback": readback,
        "served_revision": served_revision,
        "served_database": served_database,
        "fixture_tool": str(FIXTURE_TOOL.relative_to(ROOT)),
        "engine_output_tail": output.splitlines()[-8:],
    }
    missing = readback.get("missing_users") or []
    if missing:
        evidence["status"] = "FAIL"
        evidence["reason"] = "declared nav_pro users are missing after prepare: %s" % missing
    elif not readback.get("project_id") or not readback.get("partner_id") or not readback.get("contract_id"):
        evidence["status"] = "FAIL"
        evidence["reason"] = "NAV-PRO-01R carrier did not read back"
    elif base_url and served_database and served_database != database:
        evidence["status"] = "FAIL"
        evidence["reason"] = "served database %s != %s" % (served_database, database)
    elif base_url and served_revision and served_revision != expected_sha:
        evidence["status"] = "FAIL"
        evidence["reason"] = "served revision %s != %s" % (served_revision, expected_sha)
    return evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--database", default=DEFAULT_DATABASE)
    parser.add_argument("--ssh-host", required=True)
    parser.add_argument("--base-url", default="")
    parser.add_argument("--password", default="")
    parser.add_argument("--report", required=True)
    options = parser.parse_args()

    try:
        if (os.environ.get("CONFIRM_DAILY_RUNTIME_NAV_PRO_FIXTURE") or "") != CONFIRMATION:
            raise PrepareError("exact daily runtime nav_pro fixture confirmation is required")
        evidence = prepare(
            options.expected_sha,
            options.database,
            options.ssh_host,
            options.base_url,
            options.password,
        )
    except PrepareError as error:
        print("[daily.runtime.nav_pro_fixture.prepare] BLOCKED %s" % error, file=sys.stderr)
        return 2

    report_path = Path(options.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if evidence["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
