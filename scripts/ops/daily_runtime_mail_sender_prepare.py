#!/usr/bin/env python3
"""Declare the daily runtime outgoing-mail sender.

The governed daily runtime (ENV=dev, database sc_demo) has no default
``ir.mail_server`` and every ``res.company.email`` is empty. Product transitions
that notify a reviewer therefore fail inside Odoo's ``mail.mail._send`` with
``UserError('Unable to send message, please configure the sender's email
address.')``; the whole transaction rolls back and a valid business transition
looks broken.

Odoo also authors every posted message from the acting user's partner, so an
internal account with no address makes the same business transitions raise
``UserError('Unable to send message, please configure the sender's email
address.')`` inside ``mail.thread._message_compute_author`` and roll the
transition back. ``mail.default.from``/``res.company.email`` govern the SMTP
envelope only and do not clear that raise, so the declared sender domain is also
applied to active internal accounts that carry no address.

This entry writes exactly one declared sender identity through the existing
governed ``make odoo.shell.exec`` entry (stdin Python -- never an ad-hoc docker
exec), then proves it with the same read-only
``scripts/prod/guard_mail_from.py`` program run inside that same bound
carrier. It writes only outgoing-mail sender configuration: ``ir.mail_server.smtp_user``,
``ir.config_parameter`` ``mail.default.from``, ``res.company.email`` and the
``res.partner.email`` of active internal accounts that had none. It never
overwrites an existing address, and never touches the code tree, schema, volumes,
credentials or tenant business data.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import urllib.request
import urllib.error
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import daily_runtime_duty_identity as duty_identity  # noqa: E402


REMOTE_ROOT = "/opt/projects/repos/sce-product-odoo"
REMOTE_TMP = "/tmp/sc-daily-mail-sender-prepare.py"
REMOTE_GUARD_TMP = "/tmp/sc-daily-guard-mail-from.py"
GUARD_PROGRAM = ROOT / "scripts" / "prod" / "guard_mail_from.py"
CONFIRMATION = "PREPARE_DAILY_RUNTIME_OUTGOING_MAIL_SENDER"
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
SSH_HOST = re.compile(r"^[A-Za-z0-9._-]+$")
DATABASE_NAME = re.compile(r"^[A-Za-z0-9_]+$")
SENDER_ADDRESS = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


class PrepareError(RuntimeError):
    pass


def odoo_shell_program(sender: str) -> str:
    """Return the odoo-shell program that declares the outgoing-mail sender."""
    return (
        "import sys\n"
        f"SENDER = {json.dumps(sender)}\n"
        "\n"
        "\n"
        "def main():\n"
        "    if 'env' not in globals():\n"
        "        print('ERROR: Odoo env not found. Run via odoo shell.', file=sys.stderr)\n"
        "        raise SystemExit(1)\n"
        "    print('PREPARE_MAIL_SENDER database=%s' % env.cr.dbname)\n"
        "    MailServer = env['ir.mail_server'].sudo()\n"
        "    server = MailServer.search([('active', '=', True)], order='sequence,id', limit=1)\n"
        "    if not server:\n"
        "        server = MailServer.search([], order='sequence,id', limit=1)\n"
        "    created = False\n"
        "    if not server:\n"
        "        server = MailServer.create({\n"
        "            'name': 'Daily development sender',\n"
        "            'smtp_host': 'localhost',\n"
        "            'smtp_port': 25,\n"
        "            'smtp_user': SENDER,\n"
        "            'smtp_encryption': 'none',\n"
        "            'sequence': 1,\n"
        "            'active': True,\n"
        "        })\n"
        "        created = True\n"
        "    elif (server.smtp_user or '').strip() != SENDER or not server.active:\n"
        "        server.write({'smtp_user': SENDER, 'active': True})\n"
        "    icp = env['ir.config_parameter'].sudo()\n"
        "    before_from = (icp.get_param('mail.default.from') or '').strip()\n"
        "    icp.set_param('mail.default.from', SENDER)\n"
        "    companies = env['res.company'].sudo().search([])\n"
        "    before_email = {c.id: (c.email or '').strip() for c in companies}\n"
        "    if companies:\n"
        "        companies.write({'email': SENDER})\n"
        "    env.cr.commit()\n"
        "    print('PREPARE_MAIL_SENDER server_id=%s created=%s' % (server.id, created))\n"
        "    print('PREPARE_MAIL_SENDER default_from %r -> %r' % (before_from, icp.get_param('mail.default.from')))\n"
        "    for company in companies:\n"
        "        print('PREPARE_MAIL_SENDER company %s %s %r -> %r' % (company.id, company.name, before_email.get(company.id, ''), company.email))\n"
        "    # Odoo authors every posted message from the acting user's partner, so an\n"
        "    # internal account without an address makes request_validation()/message_post()\n"
        "    # raise UserError('Unable to send message, please configure the sender's email\n"
        "    # address.') and rolls the business transition back. Declare the same sender\n"
        "    # domain on active internal accounts that have no address, without overwriting\n"
        "    # any existing one.\n"
        "    user_domain = SENDER.split('@', 1)[1]\n"
        "    users = env['res.users'].sudo().search([('share', '=', False), ('active', '=', True)])\n"
        "    addressed = []\n"
        "    for user in users:\n"
        "        login = (user.login or '').strip()\n"
        "        if (user.email or '').strip() or not login or '@' in login:\n"
        "            continue\n"
        "        if not all(ch.isalnum() or ch in '._-' for ch in login):\n"
        "            print('PREPARE_MAIL_SENDER user_skipped_unusable_login id=%s' % user.id)\n"
        "            continue\n"
        "        user.partner_id.write({'email': '%s@%s' % (login, user_domain)})\n"
        "        addressed.append((user.id, login, user.partner_id.email))\n"
        "    env.cr.commit()\n"
        "    print('PREPARE_MAIL_SENDER users_addressed=%s of=%s' % (len(addressed), len(users)))\n"
        "    for user_id, login, email in addressed:\n"
        "        print('PREPARE_MAIL_SENDER user %s %s -> %r' % (user_id, login, email))\n"
        "    remaining = env['res.users'].sudo().search([('share', '=', False), ('active', '=', True), ('email', '=', False)])\n"
        "    print('PREPARE_MAIL_SENDER users_still_without_email=%s' % len(remaining))\n"
        "    raise SystemExit(0)\n"
        "\n"
        "\n"
        "try:\n"
        "    main()\n"
        "except SystemExit:\n"
        "    raise\n"
        "except Exception:\n"
        "    import traceback\n"
        "    traceback.print_exc()\n"
        "    raise SystemExit(1)\n"
    )


def run(command: list[str], *, input_bytes: bytes | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        command,
        cwd=ROOT,
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def ssh(ssh_host: str, remote_command: str, *, input_bytes: bytes | None = None) -> subprocess.CompletedProcess:
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


def bind_target(options, *, instances_reader=None) -> dict:
    """Bind the target duty, its cluster, its database and its storage, or stop.

    A database *name* is not a target identity.  The rebuilt demo carrier and the
    preserved pre-governance source both answer to ``sc_demo``, so an entry that
    received only ``--database`` used to configure whichever cluster happened to
    serve that name -- before the 2026-10-16 ruling, the historic source the
    owner protects from every governed write.  Naming the duty is the strong
    form and is what the entry now requires.
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


def remote_shell(ssh_host: str, binding: dict, *, stdin_path: str | None = None) -> subprocess.CompletedProcess:
    """Run the program inside the *bound duty's own* application container.

    The container comes from the declaration's compose project, so the write
    cannot land in another project that happens to serve a database of the same
    name.  ``cd`` is not needed: the target is an explicit container, not the
    shell's working tree.
    """
    return ssh(ssh_host, duty_identity.odoo_shell_command(binding, program_path=stdin_path or ""))


def remote_guard(ssh_host: str, binding: dict, *,
                guard_program: Path = GUARD_PROGRAM,
                remote_tmp: str = REMOTE_GUARD_TMP) -> subprocess.CompletedProcess:
    """Prove the written sender inside the *bound duty's own* carrier.

    The read-only guard used to be reached through the deployed checkout's
    ``make prod.guard.mail_from``, which resolves its target from a bare
    ``DB_NAME``.  That name is exactly what stopped identifying a target once the
    rebuilt demo duty and the preserved pre-governance source both answered to
    ``sc_demo``: the guard could have passed against the other cluster.  Running
    the same program through the bound container proves the carrier the entry
    actually wrote.
    """
    try:
        program = guard_program.read_bytes()
        compile(program.decode("utf-8"), str(guard_program), "exec")
    except (OSError, SyntaxError, UnicodeDecodeError) as error:
        raise PrepareError(f"the read-only mail_from guard is not usable: {error}")
    upload = ssh(ssh_host, f"cat > {shlex.quote(remote_tmp)}", input_bytes=program)
    if upload.returncode:
        raise PrepareError(f"remote guard upload failed: {decode(upload)[:400]}")
    try:
        return remote_shell(ssh_host, binding, stdin_path=remote_tmp)
    finally:
        ssh(ssh_host, f"rm -f {shlex.quote(remote_tmp)}")


def decode(result: subprocess.CompletedProcess) -> str:
    return (result.stdout + result.stderr).decode(errors="replace").strip()


def served_identity(base_url: str) -> dict[str, object]:
    if not base_url:
        return {}
    try:
        with urllib.request.urlopen(base_url.rstrip("/") + "/api/runtime-version", timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, ValueError, OSError):
        return {}


def preflight(expected_sha: str, sender: str, database: str, ssh_host: str) -> None:
    if not FULL_SHA.fullmatch(expected_sha or ""):
        raise PrepareError("expected SHA must be a full lowercase commit identity")
    if not SENDER_ADDRESS.fullmatch(sender or ""):
        raise PrepareError("sender must be a plain e-mail address")
    if not DATABASE_NAME.fullmatch(database or ""):
        raise PrepareError("database must be a plain database name")
    if not SSH_HOST.fullmatch(ssh_host or ""):
        raise PrepareError("SSH host must be a configured host alias")
    if not (ROOT / ".git").exists():
        raise PrepareError("must run from the governed repository")


def prepare(expected_sha: str, sender: str, binding: dict, ssh_host: str, base_url: str) -> dict[str, object]:
    database = str(binding["database"])
    preflight(expected_sha, sender, database, ssh_host)

    head = ssh(ssh_host, f"cd {shlex.quote(REMOTE_ROOT)} && git rev-parse HEAD")
    if head.returncode:
        raise PrepareError(f"remote revision read failed: {decode(head)[:400]}")
    remote_head = head.stdout.decode().strip()
    if remote_head != expected_sha:
        raise PrepareError(f"remote HEAD {remote_head or '<unknown>'} != expected {expected_sha}")

    program = odoo_shell_program(sender).encode("utf-8")
    upload = ssh(ssh_host, f"cat > {shlex.quote(REMOTE_TMP)}", input_bytes=program)
    if upload.returncode:
        raise PrepareError(f"remote program upload failed: {decode(upload)[:400]}")

    applied = remote_shell(ssh_host, binding, stdin_path=REMOTE_TMP)
    cleanup = ssh(ssh_host, f"rm -f {shlex.quote(REMOTE_TMP)}")
    if applied.returncode:
        raise PrepareError(f"odoo-shell mail-sender preparation failed: {decode(applied)[:800]}")

    guard = remote_guard(ssh_host, binding)
    guard_text = decode(guard)

    identity = served_identity(base_url)
    served_database = str(identity.get("database") or "")
    served_revision = str(identity.get("git_sha") or identity.get("source_revision") or "")

    evidence: dict[str, object] = {
        "schema": "daily.runtime.mail_sender.prepare.v1",
        "status": "PASS",
        "ssh_host": ssh_host,
        "remote_head": remote_head,
        "expected_sha": expected_sha,
        "database": database,
        "database_binding": binding,
        "sender": sender,
        "odoo_shell_output": decode(applied).splitlines()[-12:],
        "guard_rc": guard.returncode,
        "guard_output": guard_text.splitlines()[-12:],
        "served_revision": served_revision,
        "served_database": served_database,
        "cleanup_rc": cleanup.returncode,
    }

    landed = ""
    for line in decode(applied).splitlines():
        if line.startswith("PREPARE_MAIL_SENDER database="):
            landed = line.split("=", 1)[1].strip()
    evidence["landed_database"] = landed
    if landed != database:
        evidence["status"] = "FAIL"
        evidence["reason"] = "the odoo shell did not land in the bound database %s" % (database,)
    elif guard.returncode != 0 or "GUARD: PASS" not in guard_text:
        evidence["status"] = "FAIL"
        evidence["reason"] = "read-only mail_from guard did not pass"
    elif base_url and served_database and served_database != database:
        evidence["status"] = "FAIL"
        evidence["reason"] = f"served database {served_database} != {database}"
    elif base_url and served_revision and served_revision != expected_sha:
        evidence["status"] = "FAIL"
        evidence["reason"] = f"served revision {served_revision} != {expected_sha}"
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--sender", required=True)
    parser.add_argument("--duty", default="", help="the declared duty this entry binds; a database name alone is not a target identity")
    parser.add_argument("--database", default="")
    parser.add_argument("--ssh-host", required=True)
    parser.add_argument("--base-url", default="")
    parser.add_argument("--report", required=True)
    options = parser.parse_args()

    try:
        if (os.environ.get("CONFIRM_DAILY_RUNTIME_MAIL_SENDER_PREPARE") or "") != CONFIRMATION:
            raise PrepareError("exact daily runtime mail-sender preparation confirmation is required")
        binding = bind_target(options)
        evidence = prepare(
            options.expected_sha, options.sender, binding, options.ssh_host, options.base_url,
        )
    except PrepareError as error:
        print(f"[daily.runtime.mail_sender.prepare] BLOCKED {error}", file=sys.stderr)
        return 2

    report_path = Path(options.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if evidence.get("status") == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
