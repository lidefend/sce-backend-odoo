#!/usr/bin/env python3
"""Run one signed tenant payload action against a declared daily duty.

This is the daily-runtime counterpart of the production acceptance payload
runner, and the only governed entry that may take a historical payload into a
daily duty database.  Every runtime fact (database, role, container, volumes,
compose project, filestore, storage scopes) comes from
``config/ops/daily_runtime_database_duties.v1.json`` through the shared
identity module: this tool carries no database, container or volume name of its
own.

What it does *not* do is decide business facts.  The customer module owns the
source mapping and the versioned migration; this entry presents a signed
payload to that module inside the duty's own definition and reports the result.
Ownership is never defaulted here, and a missing declaration stops the run.

Three properties are deliberate:

* the maintenance process runs inside the duty's own rendered stack, as the
  duty application's own user, so the filestore it writes stays owned by the
  identity that the live application runs as;
* the payload and its verification key are exposed as verified read-only
  copies, because the payload store is the operator's private area (0700) and
  loosening it, or reading it as root, would either weaken evidence custody or
  hand the duty root-owned filestore files;
* ``plan`` proves it wrote nothing: the database digest and the protected
  business counts must be identical before and after.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import shutil
import stat
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import daily_runtime_duty_identity as duty_identity  # noqa: E402


MARKER = "DAILY_RUNTIME_DUTY_PAYLOAD="
ACTIONS = ("plan", "import", "verify")
CONFIRMATIONS = {
    "import": (
        "CONFIRM_DAILY_DUTY_PAYLOAD_IMPORT",
        "IMPORT_SIGNED_PAYLOAD_INTO_DAILY_DUTY",
    )
}
DUTY_ENV_KEYS = (
    "DUTY_NAME",
    "COMPOSE_PROJECT_NAME",
    "DB_NAME",
    "DB_USER",
    "DB_DATA",
    "ODOO_DATA",
    "ODOO_IMAGE",
)
ENV_LINE = re.compile(r"^([A-Z][A-Z0-9_]*)=(.*)$")
SAFE_DUTY_NAME = re.compile(r"^[a-z][a-z0-9_]*$")
PAYLOAD_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{2,127}$")
CHECKSUM = re.compile(r"^[0-9a-f]{64}$")
PAYLOAD_STORE = "/data/backups/production_acceptance/payloads"
PUBLIC_KEY_STORE = "/data/backups/production_acceptance/rehearsal-keys"
STAGE_ROOT = "/opt/sce/payload-staging"
KEY_STAGE_ROOT = "/opt/sce/payload-keys"
TENANT_PAYLOAD_MOUNT = "/mnt/tenant-payload"
PUBLIC_KEY_MOUNT = "/mnt/tenant-payload-public-key"
ACTION_SCRIPT = "scripts/tenant_payload/odoo_action.py"
OPERATOR_IDENTITY_TYPE = "external_xmlid"
OPERATOR_IDENTITY_KEY = "base.user_admin"
IMPORTER_GROUP = "smart_core.group_smart_core_tenant_payload_importer"
APPLICATION_ENTRY = "odoo"
ODOO_CONF = "/var/lib/odoo/odoo.conf"


class PayloadEntryError(RuntimeError):
    """A stop: the entry refuses to continue rather than guess a fact."""


def _fail(message: str) -> None:
    raise PayloadEntryError(message)


def run(command: list[str], *, stdin=None, input: str | None = None, cwd: str | None = None) -> str:
    """Run one governed helper command and stop on a non-zero exit."""
    completed = subprocess.run(
        command,
        stdin=stdin,
        input=input,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
        cwd=cwd,
    )
    if completed.returncode:
        detail = (completed.stderr or completed.stdout or "").strip()
        _fail("command failed: %s" % ((detail.splitlines() or ["<no output>"])[-1][:400]))
    return completed.stdout


def resolve_duty(duty_name: str, declaration: Path | None = None) -> dict:
    """Resolve a duty that is allowed to hold customer business data."""
    try:
        identity = duty_identity.resolve(duty_name, declaration)
    except duty_identity.DutyIdentityError as exc:
        _fail(str(exc))
    if not SAFE_DUTY_NAME.fullmatch(identity["duty"]):
        _fail("duty name is not a safe identifier")
    if identity["data_purpose"] != "customer":
        _fail(
            "duty %s is declared %s, not customer: a signed payload may only be "
            "imported into a customer duty"
            % (identity["duty"], identity["data_purpose"])
        )
    if not identity["tenant_key"]:
        _fail("customer duty %s declares no tenant_key" % identity["duty"])
    return identity


def assert_private_file(path: Path, what: str) -> None:
    """A file that carries a duty fact is readable only by its owner."""
    if path.is_symlink() or not path.is_file():
        _fail("%s %s is unavailable" % (what, path))
    info = path.stat()
    if stat.S_IMODE(info.st_mode) != 0o600 or info.st_uid != 0:
        _fail("%s %s is not root-owned mode 0600" % (what, path))


def read_duty_env(path: Path, duty: dict) -> dict:
    """Read the rendered duty environment, never fabricating a value."""
    assert_private_file(path, "duty environment")
    values: dict[str, str] = {}
    for row in path.read_text(encoding="utf-8").splitlines():
        row = row.strip()
        if not row or row.startswith("#"):
            continue
        match = ENV_LINE.match(row)
        if match:
            values[match.group(1)] = match.group(2)
    assert_env_declares_duty(values, duty)
    return values


def assert_env_declares_duty(values: dict, duty: dict) -> None:
    """The rendered environment must be complete and agree with the declaration.

    The declaration is the authority; a rendered file is evidence about it.  A
    mismatch is refused rather than corrected so the entry can never operate on
    a database the declaration does not name for this duty.
    """
    for key in DUTY_ENV_KEYS:
        if not values.get(key):
            _fail("duty environment lacks %s" % key)
    expected = {
        "DUTY_NAME": duty["duty"],
        "COMPOSE_PROJECT_NAME": duty["compose_project"],
        "DB_NAME": duty["database"],
        "DB_USER": duty["database_role"],
        "DB_DATA": duty["database_volume"],
        "ODOO_DATA": duty["odoo_data_volume"],
    }
    for key, value in expected.items():
        if values.get(key) != value:
            _fail(
                "duty environment %s disagrees with the declaration (expected %s)"
                % (key, value)
            )


def stack_compose_path(ops_root: Path) -> Path:
    """The reviewed stack definition, found by shape rather than by a literal."""
    candidates = sorted(ops_root.glob("duty-stack-*.yml"))
    if len(candidates) != 1:
        _fail(
            "expected exactly one rendered duty stack under %s, found %d"
            % (ops_root, len(candidates))
        )
    if candidates[0].is_symlink():
        _fail("rendered duty stack is a symlink")
    return candidates[0]


def payload_paths(payload_id: str) -> tuple[Path, Path]:
    if not PAYLOAD_ID.fullmatch(payload_id or ""):
        _fail("payload identity is not a safe identifier")
    root = Path(PAYLOAD_STORE) / payload_id
    key = Path(PUBLIC_KEY_STORE) / payload_id / "public.pem"
    for path in (root, root / "manifest.json", key):
        if path.is_symlink():
            _fail("payload path %s is a symlink" % path)
    if not root.is_dir() or not (root / "manifest.json").is_file():
        _fail("signed payload root %s is unavailable" % root)
    if not (root / "checksums.sha256").is_file():
        _fail("payload checksum manifest is unavailable")
    if not key.is_file():
        _fail("payload verification key is unavailable")
    return root, key


def load_manifest(root: Path, tenant_key: str, approved_checksum: str) -> dict:
    if not CHECKSUM.fullmatch(approved_checksum or ""):
        _fail("an approved 64-hex payload checksum is required")
    try:
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _fail("payload manifest is unreadable: %s" % exc)
    if not isinstance(manifest, dict):
        _fail("payload manifest is not an object")
    if manifest.get("tenant_key") != tenant_key:
        _fail(
            "payload tenant %r is not duty tenant %r"
            % (manifest.get("tenant_key"), tenant_key)
        )
    if manifest.get("payload_checksum") != approved_checksum:
        _fail("payload checksum does not match the approved checksum")
    return manifest


def _assert_source_tree_is_sound(root: Path) -> None:
    for path in root.rglob("*"):
        if path.is_symlink():
            _fail("payload source contains a symlink: %s" % path.relative_to(root))


def _stage_payload(payload_root: Path, duty: dict, approved_checksum: str) -> dict:
    """Expose a verified read-only copy the duty's own user can read.

    The copy is created once per (duty, payload, checksum) and reused, and both
    the source and the copy are verified against the payload's own checksum
    manifest, so the staged tree cannot drift from the evidence it represents.
    """
    _assert_source_tree_is_sound(payload_root)
    stage_root = Path(STAGE_ROOT) / duty["duty"]
    stage_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    if stage_root.is_symlink() or stat.S_IMODE(stage_root.stat().st_mode) != 0o700:
        _fail("payload staging root is not root-owned mode 0700")
    staged = stage_root / payload_root.name
    marker = stage_root / ("%s.stage.json" % payload_root.name)
    source_digest = hashlib.sha256(
        (payload_root / "checksums.sha256").read_bytes()
    ).hexdigest()
    if staged.is_dir() and marker.is_file():
        try:
            recorded = json.loads(marker.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            recorded = {}
        if (
            recorded.get("approved_payload_checksum") == approved_checksum
            and recorded.get("checksums_sha256") == source_digest
        ):
            return {
                "root": staged,
                "reused": True,
                "checksums_sha256": source_digest,
                "files": int(recorded.get("files") or 0),
            }
        _fail("a different staged copy of this payload already exists")
    if staged.exists():
        _fail("payload staging path exists without a usable stage marker")

    staging = stage_root / (".incomplete-%s" % payload_root.name)
    if staging.exists():
        _fail("an incomplete payload staging directory already exists")
    staging.mkdir(mode=0o700)
    try:
        _copy_tree(payload_root, staging)
        run(
            ["sha256sum", "-c", "--strict", "checksums.sha256"],
            cwd=str(staging),
        )
        files = len(list(staging.rglob("*")))
        os.replace(staging, staged)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    marker.write_text(
        json.dumps(
            {
                "approved_payload_checksum": approved_checksum,
                "checksums_sha256": source_digest,
                "payload_id": payload_root.name,
                "files": files,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    os.chmod(marker, 0o600)
    return {
        "root": staged,
        "reused": False,
        "checksums_sha256": source_digest,
        "files": files,
    }


def _copy_tree(source: Path, destination: Path) -> None:
    shutil.copytree(source, destination, dirs_exist_ok=True, symlinks=False)
    subprocess.run(["chmod", "-R", "a+rX", str(destination)], check=True)
    for path in destination.rglob("*"):
        if path.is_symlink():
            _fail("staged payload contains a symlink")


def _stage_public_key(key: Path, duty: dict) -> dict:
    """Expose the verification key as a read-only copy the duty user can read."""
    stage_root = Path(KEY_STAGE_ROOT) / duty["duty"]
    stage_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    if stage_root.is_symlink() or stat.S_IMODE(stage_root.stat().st_mode) != 0o700:
        _fail("payload key staging root is not root-owned mode 0700")
    content = key.read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    target = stage_root / ("%s.pem" % key.parent.name)
    if target.exists() and target.read_bytes() != content:
        _fail("a different payload key is already staged for this duty")
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(content)
    return {"path": target, "sha256": digest}


def compose_base(duty: dict, ops_root: Path, env_path: Path, stack: Path) -> list[str]:
    return [
        "docker", "compose",
        "--project-name", duty["compose_project"],
        "--env-file", str(env_path),
        "--project-directory", str(ops_root),
        "-f", str(stack),
    ]


def inspect_odoo_container(duty: dict, values: dict) -> dict:
    """Read the duty application's own identity back before touching it."""
    name = duty["odoo_container"]
    try:
        record = json.loads(run(["docker", "inspect", name]))[0]
    except (IndexError, json.JSONDecodeError) as exc:
        _fail("duty application %s cannot be inspected: %s" % (name, exc))
    if record.get("State", {}).get("Running") is not True:
        _fail("duty application %s is not running" % name)
    config = record.get("Config") or {}
    labels = config.get("Labels") or {}
    if labels.get("com.docker.compose.project") != duty["compose_project"]:
        _fail("duty application belongs to another compose project")
    image = str(config.get("Image") or "")
    if image != values["ODOO_IMAGE"]:
        _fail("duty application image differs from the rendered environment")
    networks = set((record.get("NetworkSettings", {}).get("Networks") or {}).keys())
    expected_network = "%s_default" % duty["compose_project"]
    if networks != {expected_network}:
        _fail("duty application network identity differs: %s" % sorted(networks))
    for destination in ("/var/lib/odoo", "/opt/sce-runtime"):
        if destination not in {
            row.get("Destination") for row in record.get("Mounts") or []
        }:
            _fail("duty application lacks its %s mount" % destination)
    return {
        "container": name,
        "container_id": str(record.get("Id") or ""),
        "image": image,
        "user": str(config.get("User") or ""),
        "network": expected_network,
        "started_at": str(record.get("State", {}).get("StartedAt") or ""),
    }


def payload_action_env(
    duty: dict,
    action: str,
    approved_checksum: str,
    *,
    chunk_size: int,
    resume_failed: bool,
    capability: str,
) -> list[str]:
    """The action contract, exactly as the product service requires it.

    The maintenance capability is an ephemeral secret generated per invocation
    and presented both in the process environment and in the Odoo context.  It
    proves the caller controls the maintenance process; it is not a data-level
    permission and it grants nothing beyond the operator's own rights.
    """
    return [
        "-e", "SC_TENANT_PAYLOAD_ACTION=%s" % action,
        "-e", "SC_TENANT_PAYLOAD_TENANT_KEY=%s" % duty["tenant_key"],
        "-e", "SC_TENANT_PAYLOAD_OPERATOR_IDENTITY_TYPE=%s" % OPERATOR_IDENTITY_TYPE,
        "-e", "SC_TENANT_PAYLOAD_OPERATOR_IDENTITY_KEY=%s" % OPERATOR_IDENTITY_KEY,
        "-e", 'SC_TENANT_PAYLOAD_DIRECT_GRANT_TARGETS=["%s"]' % IMPORTER_GROUP,
        "-e", "SC_TENANT_PAYLOAD_DB_ALLOWLIST=%s" % duty["database"],
        "-e", "SC_TENANT_PAYLOAD_APPROVED_CHECKSUM=%s" % approved_checksum,
        "-e", "SC_TENANT_PAYLOAD_CHUNK_SIZE=%d" % chunk_size,
        "-e", "SC_TENANT_PAYLOAD_RESUME_FAILED=%d" % (1 if resume_failed else 0),
        "-e", "SC_TENANT_PAYLOAD_PUBLIC_KEY=%s" % PUBLIC_KEY_MOUNT,
        "-e", "SC_TENANT_PAYLOAD_MAINTENANCE_CAPABILITY=%s" % capability,
    ]


def maintenance_command(
    duty: dict,
    base: list[str],
    *,
    action: str,
    approved_checksum: str,
    chunk_size: int,
    resume_failed: bool,
    capability: str,
    staged_payload: Path,
    staged_key: Path,
) -> list[str]:
    """A one-off run of the duty's own definition with the payload exposed."""
    return base + [
        "run", "--rm", "--no-deps", "-T",
        "--label", "sc.daily-duty-payload=true",
        "--label", "sc.daily-duty=%s" % duty["duty"],
        "--volume", "%s:%s:ro" % (staged_payload, TENANT_PAYLOAD_MOUNT),
        "--volume", "%s:%s:ro" % (staged_key, PUBLIC_KEY_MOUNT),
        *payload_action_env(
            duty,
            action,
            approved_checksum,
            chunk_size=chunk_size,
            resume_failed=resume_failed,
            capability=capability,
        ),
        "--entrypoint", APPLICATION_ENTRY,
        "odoo",
        "shell", "-c", ODOO_CONF,
        "-d", duty["database"],
        "--no-http", "--log-level=error",
    ]


def psql(duty: dict, sql: str) -> str:
    """Read one scalar back from the duty's own cluster (public reuse point)."""
    return run(
        [
            "docker", "exec", duty["database_container"],
            "psql", "-X", "-U", duty["database_role"], "-d", duty["database"],
            "-At", "-v", "ON_ERROR_STOP=1", "-c", sql,
        ]
    ).strip()


def database_fingerprint(duty: dict) -> str:
    command = [
        "docker", "exec", duty["database_container"],
        "pg_dump", "-U", duty["database_role"], "-d", duty["database"],
        "--no-owner", "--no-privileges",
    ]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if process.stdout is None or process.stderr is None:
        process.kill()
        _fail("database fingerprint stream is unavailable")
    digest = hashlib.sha256()
    for row in process.stdout:
        if row.startswith((b"\\restrict ", b"\\unrestrict ")):
            continue
        digest.update(row.rstrip(b"\r\n"))
        digest.update(b"\n")
    stderr = process.stderr.read()
    if process.wait():
        detail = stderr.decode("utf-8", errors="replace").strip()
        _fail((detail.splitlines() or ["database fingerprint failed"])[-1][:400])
    return digest.hexdigest()


def protected_counts(duty: dict) -> dict:
    """Count the business facts the payload mechanism itself owns."""
    rows = {}
    for key, table in (
        ("import_batches", "sc_tenant_payload_import_batch"),
        ("historical_payment_facts", "sc_historical_payment_fact"),
    ):
        value = psql(
            duty,
            "select coalesce((select count(*) from %s),0);" % table,
        )
        if not value.isdigit():
            _fail("protected business count %s is invalid" % key)
        rows[key] = int(value)
    return rows


def execute(
    duty_name: str,
    *,
    action: str,
    payload_id: str,
    approved_checksum: str,
    chunk_size: int,
    declaration: Path | None = None,
    tool_root: Path | None = None,
) -> dict:
    if action not in ACTIONS:
        _fail("unsupported payload action: %s" % action)
    duty = resolve_duty(duty_name, declaration)
    ops_root = Path(duty_identity.load_declaration(declaration).get("ops_root") or "")
    if not ops_root.is_absolute():
        _fail("the declaration must name an absolute ops root")
    env_path = ops_root / ("%s.env" % duty["duty"])
    values = read_duty_env(env_path, duty)
    stack = stack_compose_path(ops_root)
    application = inspect_odoo_container(duty, values)

    payload_root, public_key = payload_paths(payload_id)
    manifest = load_manifest(payload_root, duty["tenant_key"], approved_checksum)
    stage = _stage_payload(payload_root, duty, approved_checksum)
    staged_key = _stage_public_key(public_key, duty)

    root = tool_root or ROOT
    action_script = root / ACTION_SCRIPT
    if not action_script.is_file():
        _fail("the immutable tenant payload action is unavailable")
    tool_sha = ""
    marker = root / "DEPLOYMENT_TOOL_SHA"
    if marker.is_file():
        tool_sha = marker.read_text(encoding="utf-8").strip()
        if tool_sha != root.name:
            _fail("the immutable deployment tool identity differs")

    if action in CONFIRMATIONS:
        variable, expected = CONFIRMATIONS[action]
        if os.environ.get(variable) != expected:
            _fail("%s must be set to the exact confirmation value" % variable)

    before_digest = before_counts = None
    if action in ("plan", "import"):
        before_digest = database_fingerprint(duty)
        before_counts = protected_counts(duty)

    command = maintenance_command(
        duty,
        compose_base(duty, ops_root, env_path, stack),
        action=action,
        approved_checksum=approved_checksum,
        chunk_size=chunk_size,
        resume_failed=action == "import",
        capability=secrets.token_hex(32),
        staged_payload=stage["root"],
        staged_key=staged_key["path"],
    )
    with action_script.open("r", encoding="utf-8") as source:
        output = run(command, stdin=source, cwd=str(ops_root))
    reports = [row for row in output.splitlines() if row.strip().startswith("{")]
    if not reports:
        _fail("the payload action emitted no audit report")
    try:
        report = json.loads(reports[-1])
    except json.JSONDecodeError as exc:
        _fail("the payload action audit report is not JSON: %s" % exc)
    if report.get("status") != "PASS":
        reason = report.get("status_reason") or report.get("rule") or report.get("status")
        _fail("payload %s did not pass: %s" % (action, reason))

    evidence = {
        "schema_version": "daily_runtime_duty_payload.v1",
        "action": action,
        "duty": duty["duty"],
        "database": duty["database"],
        "database_role": duty["database_role"],
        "environment_id": duty["environment_id"],
        "tenant_key": duty["tenant_key"],
        "data_purpose": duty["data_purpose"],
        "payload_id": payload_id,
        "payload_source_root": str(payload_root),
        "payload_staged_root": str(stage["root"]),
        "payload_stage_reused": stage["reused"],
        "payload_files": stage["files"],
        "approved_payload_checksum": approved_checksum,
        "payload_checksums_sha256": stage["checksums_sha256"],
        "payload_tenant_key": manifest.get("tenant_key"),
        "payload_customer_module": manifest.get("customer_module"),
        "payload_customer_module_version": manifest.get("customer_module_version"),
        "payload_created_at_utc": manifest.get("created_at_utc"),
        "public_key_source": str(public_key),
        "public_key_staged": str(staged_key["path"]),
        "public_key_sha256": staged_key["sha256"],
        "tool_sha": tool_sha,
        "application": application,
        "stack_compose": str(stack),
        "duty_environment": str(env_path),
        "report": report,
    }
    if action in ("plan", "import"):
        after_digest = database_fingerprint(duty)
        after_counts = protected_counts(duty)
        evidence.update(
            {
                "business_state_digest_before": before_digest,
                "business_state_digest_after": after_digest,
                "protected_counts_before": before_counts,
                "protected_counts_after": after_counts,
            }
        )
        if action == "plan":
            if (
                str(report.get("database_write_count")) != "0"
                or str(report.get("filestore_write_count")) != "0"
                or before_digest != after_digest
                or before_counts != after_counts
            ):
                _fail("payload plan changed duty business state")
    return evidence


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=list(ACTIONS))
    parser.add_argument("--duty", required=True)
    parser.add_argument("--payload-id", required=True)
    parser.add_argument("--approved-checksum", required=True)
    parser.add_argument("--chunk-size", type=int, default=100)
    parser.add_argument("--declaration", default="")
    parser.add_argument("--evidence", default="")
    args = parser.parse_args(argv)
    try:
        evidence = execute(
            args.duty,
            action=args.action,
            payload_id=args.payload_id,
            approved_checksum=args.approved_checksum,
            chunk_size=args.chunk_size,
            declaration=Path(args.declaration) if args.declaration else None,
        )
    except (PayloadEntryError, OSError, subprocess.CalledProcessError) as exc:
        print(
            MARKER
            + json.dumps({"status": "BLOCKED", "rule": str(exc)}, ensure_ascii=False)
        )
        return 2
    if args.evidence:
        Path(args.evidence).write_text(
            json.dumps(evidence, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
    print(MARKER + json.dumps(evidence, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
