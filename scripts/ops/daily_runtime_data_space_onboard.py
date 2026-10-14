#!/usr/bin/env python3
"""Onboard the daily runtime's environment main company as its demo data space.

The daily runtime (ENV=dev, database ``sc_demo``) carried business rows before
any data space was declared. Every company ceiling resolves row visibility
through ``user._sc_data_company_ids()``, which reads ``sc.tenant.company.registration``
and the declared environment role, so an undeclared role with no registration
made every business row invisible to every principal and made the product serve
an empty surface.

This entry performs exactly the governed onboarding the platform already owns,
through the existing governed ``make odoo.shell.exec`` entry (stdin Python --
never an ad-hoc docker exec), and never edits a business row:

* declare the environment role, so the database stops resolving to the
  strictest ``customer_production`` default;
* onboard the environment main company through the shape this database needs
  (the demo role's own rule): a database that owns no business registration yet
  retires its carrier marker, while one that already onboarded a business
  company -- the acceptance fixtures register their own test space -- adopts the
  environment main company without relabelling it;
* enroll that space's operators into its identity realm, because a registration
  whose operators were never enrolled is readable by nobody.

Invoked by ``make daily.runtime.data_space.onboard`` (apply) and by
``make daily.runtime.data_space.onboard.plan`` (read-only plan), both bound to
the same exact expected SHA.

The entry is read-only by default: without the exact confirmation it prints the
plan and rolls back. ``--plan`` forces that read-only mode.
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
REMOTE_ROOT = "/opt/projects/repos/sce-product-odoo"
REMOTE_TMP = "/tmp/sc-daily-data-space-onboard.py"
DEFAULT_DATABASE = "sc_demo"
DEFAULT_ROLE = "platform_internal_demo"
DEFAULT_TENANT_KEY = "sc-demo-main"
CONFIRMATION = "ONBOARD_DAILY_RUNTIME_DEMO_DATA_SPACE"
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
SSH_HOST = re.compile(r"^[A-Za-z0-9._-]+$")
DATABASE_NAME = re.compile(r"^[A-Za-z0-9_]+$")
ROLE_NAME = re.compile(r"^[a-z0-9_]+$")
TENANT_KEY = re.compile(r"^[A-Za-z0-9._-]+$")
MARKER = "DAILY_DATA_SPACE_ONBOARD="


class OnboardError(RuntimeError):
    pass


def odoo_shell_program(*, role: str, tenant_key: str, apply: bool) -> str:
    """Return the readback / onboarding program executed inside the container.

    The role and the tenant key are baked in so nothing depends on environment
    forwarding, and the program prints one JSON marker line the caller parses.
    """
    return (
        "import json\n"
        "import os\n"
        "\n"
        "from odoo.addons.smart_core.security import data_space_provisioning as provisioning\n"
        "\n"
        f"ROLE = {json.dumps(role)}\n"
        f"TENANT_KEY = {json.dumps(tenant_key)}\n"
        f"APPLY = {'True' if apply else 'False'}\n"
        f"MARKER = {json.dumps(MARKER)}\n"
        "\n"
        "\n"
        "def readback():\n"
        "    registrations = env['sc.tenant.company.registration'].sudo().search([])\n"
        "    report = {\n"
        "        'database': env.cr.dbname,\n"
        "        'environment_role': provisioning.environment_role(env),\n"
        "        'main_company_id': env.company.id,\n"
        "        'bootstrap_company_ids': provisioning.bootstrap_company_ids(env),\n"
        "        'registration_rows': len(registrations),\n"
        "        'database_already_owns_registration': bool(registrations),\n"
        "        'registered_company_ids': sorted(registrations.company_id.ids),\n"
        "        'registered_purposes': sorted(set(registrations.mapped('data_purpose'))),\n"
        "        'demo_registration_company_ids': provisioning.onboarded_registrations(\n"
        "            env, purpose='demo').company_id.ids,\n"
        "        'companies': [\n"
        "            {'id': company.id, 'name': company.name,\n"
        "             'bootstrap': bool(company.is_platform_bootstrap_company),\n"
        "             'registered': company.id in registrations.company_id.ids}\n"
        "            for company in env['res.company'].sudo().search([], order='id')\n"
        "        ],\n"
        "    }\n"
        "    demo = provisioning.onboarded_registrations(env, purpose='demo')\n"
        "    report['operators_pending_enrollment'] = (\n"
        "        sorted(provisioning.data_space_operators_pending_enrollment(env, purpose='demo'))\n"
        "        if demo else None\n"
        "    )\n"
        "    return report\n"
        "\n"
        "\n"
        "def main():\n"
        "    if 'env' not in globals():\n"
        "        raise SystemExit('ERROR: Odoo env not found. Run via odoo shell.')\n"
        "    before = readback()\n"
        "    if not APPLY:\n"
        "        before['writes'] = False\n"
        "        before['plan'] = [\n"
        "            'declare_environment_role(%s)' % ROLE,\n"
        "            'onboard_environment_business_company(tenant_key=%r)' % TENANT_KEY,\n"
        "            'enroll_data_space_identities(purpose=\\'demo\\')',\n"
        "        ]\n"
        "        print(MARKER + json.dumps(before, ensure_ascii=False, sort_keys=True))\n"
        "        env.cr.rollback()\n"
        "        return 0\n"
        "    provisioning.declare_environment_role(env, ROLE)\n"
        "    registration = provisioning.onboard_environment_business_company(\n"
        "        env, tenant_key=TENANT_KEY)\n"
        "    enrollment = provisioning.enroll_data_space_identities(env, purpose='demo')\n"
        "    env.cr.commit()\n"
        "    after = readback()\n"
        "    after['writes'] = True\n"
        "    after['registration_tenant_key'] = registration.tenant_key\n"
        "    after['enrollment'] = enrollment\n"
        "    after['post_conditions'] = {\n"
        "        'role_declared': after['environment_role'] == ROLE,\n"
        "        'main_company_is_not_a_carrier': after['main_company_id'] not in (\n"
        "            after['bootstrap_company_ids']),\n"
        "        'main_company_registered_as_demo': after['main_company_id'] in (\n"
        "            after['demo_registration_company_ids']),\n"
        "        'operators_pending_enrollment_is_empty': (\n"
        "            after['operators_pending_enrollment'] == []),\n"
        "    }\n"
        "    after['passed'] = all(after['post_conditions'].values())\n"
        "    print(MARKER + json.dumps(after, ensure_ascii=False, sort_keys=True))\n"
        "    return 0 if after['passed'] else 1\n"
        "\n"
        "\n"
        "try:\n"
        "    raise SystemExit(main())\n"
        "except SystemExit:\n"
        "    raise\n"
        "except Exception:\n"
        "    import traceback\n"
        "    traceback.print_exc()\n"
        "    raise SystemExit(1)\n"
    )


def run(command, *, input_bytes=None):
    return subprocess.run(
        command, cwd=ROOT, input=input_bytes,
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


def remote_make(ssh_host, database, target, *, stdin_path=None):
    redirect = f" < {shlex.quote(stdin_path)}" if stdin_path else ""
    command = (
        f"cd {shlex.quote(REMOTE_ROOT)} && "
        f"make ENV=dev ENV_FILE=.env.dev DB_NAME={shlex.quote(database)} {target}{redirect}"
    )
    return ssh(ssh_host, command)


def decode(result):
    return (result.stdout + result.stderr).decode(errors="replace").strip()


def marker_payload(text):
    for line in text.splitlines():
        if line.startswith(MARKER):
            try:
                return json.loads(line[len(MARKER):])
            except json.JSONDecodeError as error:
                raise OnboardError(f"unreadable readback payload: {error}") from error
    return None


def preflight(expected_sha, database, ssh_host, role, tenant_key):
    if not FULL_SHA.fullmatch(expected_sha or ""):
        raise OnboardError("expected SHA must be a full lowercase commit identity")
    if not DATABASE_NAME.fullmatch(database or ""):
        raise OnboardError("database must be a plain database name")
    if not SSH_HOST.fullmatch(ssh_host or ""):
        raise OnboardError("SSH host must be a configured host alias")
    if not ROLE_NAME.fullmatch(role or ""):
        raise OnboardError("environment role must be a declared role name")
    if not TENANT_KEY.fullmatch(tenant_key or ""):
        raise OnboardError("tenant key must be a plain identifier")
    if not (ROOT / ".git").exists():
        raise OnboardError("must run from the governed repository")


def onboard(expected_sha, database, ssh_host, role, tenant_key, base_url, apply):
    preflight(expected_sha, database, ssh_host, role, tenant_key)

    head = ssh(ssh_host, f"cd {shlex.quote(REMOTE_ROOT)} && git rev-parse HEAD")
    if head.returncode:
        raise OnboardError(f"remote revision read failed: {decode(head)[:400]}")
    remote_head = head.stdout.decode().strip()
    if remote_head != expected_sha:
        raise OnboardError(f"remote HEAD {remote_head or '<unknown>'} != expected {expected_sha}")

    program = odoo_shell_program(role=role, tenant_key=tenant_key, apply=apply).encode("utf-8")
    upload = ssh(ssh_host, f"cat > {shlex.quote(REMOTE_TMP)}", input_bytes=program)
    if upload.returncode:
        raise OnboardError(f"remote program upload failed: {decode(upload)[:400]}")

    executed = remote_make(ssh_host, database, "odoo.shell.exec", stdin_path=REMOTE_TMP)
    cleanup = ssh(ssh_host, f"rm -f {shlex.quote(REMOTE_TMP)}")
    output = decode(executed)
    payload = marker_payload(output)
    if payload is None:
        raise OnboardError(f"no readback payload in the odoo-shell output: {output[-800:]}")

    evidence = {
        "schema": "daily.runtime.data_space.onboard.v1",
        "ssh_host": ssh_host,
        "remote_head": remote_head,
        "expected_sha": expected_sha,
        "database": database,
        "declared_role": role,
        "tenant_key": tenant_key,
        "applied": bool(apply),
        "odoo_shell_rc": executed.returncode,
        "cleanup_rc": cleanup.returncode,
        "readback": payload,
    }
    served = served_identity(base_url)
    if served:
        evidence["served_revision"] = str(served.get("git_sha") or served.get("source_revision") or "")
        evidence["served_database"] = str(served.get("database") or "")

    if not apply:
        evidence["status"] = "PLAN"
    elif executed.returncode != 0:
        evidence["status"] = "FAIL"
        evidence["reason"] = "odoo-shell onboarding returned non-zero"
    elif payload.get("writes") and not payload.get("passed"):
        evidence["status"] = "FAIL"
        evidence["reason"] = "post-conditions did not pass"
    else:
        evidence["status"] = "PASS"
    return evidence


def served_identity(base_url):
    if not base_url:
        return {}
    try:
        with urllib.request.urlopen(base_url.rstrip("/") + "/api/runtime-version", timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, ValueError, OSError):
        return {}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--database", default=DEFAULT_DATABASE)
    parser.add_argument("--ssh-host", required=True)
    parser.add_argument("--role", default=DEFAULT_ROLE)
    parser.add_argument("--tenant-key", default=DEFAULT_TENANT_KEY)
    parser.add_argument("--base-url", default="")
    parser.add_argument("--report", required=True)
    parser.add_argument("--plan", action="store_true")
    options = parser.parse_args()

    apply = not options.plan
    try:
        if apply and (os.environ.get("CONFIRM_DAILY_RUNTIME_DATA_SPACE_ONBOARD") or "") != CONFIRMATION:
            raise OnboardError("exact daily runtime data-space onboarding confirmation is required")
        evidence = onboard(
            options.expected_sha, options.database, options.ssh_host,
            options.role, options.tenant_key, options.base_url, apply,
        )
    except OnboardError as error:
        print(f"[daily.runtime.data_space.onboard] BLOCKED {error}", file=sys.stderr)
        return 2

    report_path = Path(options.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True))
    if evidence["status"] == "PASS":
        return 0
    return 0 if evidence["status"] == "PLAN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
