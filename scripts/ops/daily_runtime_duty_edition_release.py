#!/usr/bin/env python3
"""Publish a declared product edition into a declared daily duty.

A released edition snapshot is what a runtime actually serves, and the platform
delivery service (``EditionReleaseSnapshotService``) owns that record: this entry
never inserts a snapshot row, it drives the existing governed release scripts.
What the daily development server lacked was an *entry*: the only governed entry
that published the daily product edition was
``release.daily_product_navigation.snapshot`` and it was hard-coded to the demo
database, so a customer development tenant could not register the edition it
runs, could not be issued the narrow import grant, and could not start its own
versioned migration.

Every runtime fact (database, application role, compose project, stack,
containers, volumes, filestore scope) is resolved from
``config/ops/daily_runtime_database_duties.v1.json``: this tool carries no
database or container name of its own, and the accepted product keys come from
the duty's own ``edition`` declaration rather than from a literal here.

Two semantics are deliberate and must not be "corrected" to make a check pass:

* ``smart_core.platform_release_db`` names the database that *carries* the
  effective release snapshot of the runtime that runs there.  It is a local
  carrier, not a platform-wide publication authority: the production acceptance
  clone runtime rebinds a restored copy to itself, and the daily platform
  control duty holds neither the parameter nor a single snapshot.  Binding a
  tenant duty to itself is therefore the verified meaning of the parameter, not
  a workaround.  The platform control duty is refused outright, because holding
  an effective snapshot is not holding the platform's publication right.
* only the declared ``construction.standard``-style editions are published and
  ``preview`` is never widened automatically.

The publish action runs the *existing* governed release entries
(``scripts/release/configure_colocated_platform_core.py`` and
``scripts/release/initialize_colocated_platform_snapshot.py``) from the immutable
deployment tool tree, so the entry that publishes is pinned even though the
addons it drives come from the served product checkout.  ``readback`` runs in a
separate process afterwards so the released identity is read back from the duty
rather than from the publishing transaction.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import daily_runtime_duty_identity as duty_identity  # noqa: E402
import daily_runtime_duty_payload as duty_runtime  # noqa: E402


MARKER = "DAILY_DUTY_EDITION_REPORT="
READBACK_MARKER = "DAILY_DUTY_EDITION_READBACK="
ACTIONS = ("readback", "publish")
CONFIRMATIONS = {
    "publish": (
        "CONFIRM_DAILY_DUTY_EDITION_RELEASE",
        "RELEASE_DECLARED_EDITION_INTO_DAILY_DUTY",
    )
}
PLATFORM_CONTROL_PURPOSE = "platform_control"
SNAPSHOT_CARRIER_PURPOSES = ("customer", "demo")
CARRIER_SEMANTIC = "effective_release_snapshot"
SAFE_DUTY_NAME = re.compile(r"^[a-z][a-z0-9_]*$")
PRODUCT_KEY = re.compile(r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$")
VERSION_PREFIX = re.compile(r"^[a-z][a-z0-9-]*$")
SOURCE_REVISION = re.compile(r"^[0-9a-f]{40}$")

PARAMETER = "smart_core.platform_release_db"
TENANT_PARAMETER = "sc.tenant.bound_tenant_key"
# The ORM model and its physical table are different names: the dotted model
# name is only valid through env[...], never in raw SQL.
SNAPSHOT_MODEL = "sc.edition.release.snapshot"
SNAPSHOT_TABLE = "sc_edition_release_snapshot"
SNAPSHOT_APPLY_ACK = "I_ACKNOWLEDGE_COLOCATED_PLATFORM_SNAPSHOT_INITIALIZATION"
CONFIG_APPLY_ACK = "I_ACKNOWLEDGE_COLOCATED_PLATFORM_CONFIGURATION"

RELEASE_ENTRY_DIRECTORY = "scripts/release"
RELEASE_ENTRY_MOUNT = "/mnt/release-entry"
RELEASE_ENTRY_SCRIPTS = (
    "configure_colocated_platform_core.py",
    "initialize_colocated_platform_snapshot.py",
)

APPLICATION_ENTRY = duty_runtime.APPLICATION_ENTRY
ODOO_CONF = duty_runtime.ODOO_CONF

# The readback script must be able to prove it wrote nothing, so it only reads
# the release identity, the tenant binding and the snapshot rows.
READBACK_SCRIPT = """
import json

_params = env["ir.config_parameter"].sudo()  # noqa: F821
_snapshot = env["sc.edition.release.snapshot"].sudo()  # noqa: F821
_report = {
    "mode": "read_only",
    "writes": 0,
    "database": env.cr.dbname,  # noqa: F821
    "platform_release_db": str(_params.get_param("smart_core.platform_release_db", "") or ""),
    "bound_tenant_key": str(_params.get_param("sc.tenant.bound_tenant_key", "") or ""),
    "snapshot_model": "%(model)s",
    "snapshot_count": _snapshot.with_context(active_test=False).search_count([]),
    "released_active": _snapshot.search_read(
        [("state", "=", "released"), ("is_active", "=", True), ("active", "=", True)],
        ["product_key", "version", "edition_key", "channel"],
        order="product_key, id",
    ),
}
print("%(marker)s" + json.dumps(_report, ensure_ascii=False, sort_keys=True, default=str))
""" % {"marker": READBACK_MARKER, "model": SNAPSHOT_MODEL}

# The publish entry drives the two existing governed release scripts in one
# process, in the order the platform itself uses: the colocated platform
# parameter first (the snapshot entry requires the parameter to name the current
# database), then the snapshot initialization.
PUBLISH_SCRIPT = """
import pathlib

_ENTRY = pathlib.Path("%(mount)s")
for _name in %(scripts)r:
    _path = _ENTRY / _name
    exec(compile(_path.read_text(encoding="utf-8"), str(_path), "exec"), globals())
""" % {"mount": RELEASE_ENTRY_MOUNT, "scripts": list(RELEASE_ENTRY_SCRIPTS)}


class EditionReleaseEntryError(RuntimeError):
    """A stop: the entry refuses to continue rather than guess a fact."""


def _fail(message: str) -> None:
    raise EditionReleaseEntryError(message)


def _text(value) -> str:
    return str(value or "").strip()


def resolve_release_duty(duty_name: str, declaration: Path | None = None) -> dict:
    """Resolve a duty that is allowed to carry an effective release snapshot."""
    if not SAFE_DUTY_NAME.fullmatch(duty_name or ""):
        _fail("duty name is not a safe identifier")
    try:
        duty = duty_identity.resolve(duty_name, declaration)
        declared = duty_identity.load_duties(declaration).get(duty_name) or {}
    except duty_identity.DutyIdentityError as exc:
        _fail(str(exc))
    purpose = duty["data_purpose"]
    if purpose == PLATFORM_CONTROL_PURPOSE:
        _fail(
            "duty %s is the platform control plane: carrying an effective release "
            "snapshot is not holding the platform's publication authority"
            % duty_name
        )
    if purpose not in SNAPSHOT_CARRIER_PURPOSES:
        _fail(
            "duty %s is declared %s: only a customer or demo duty carries the "
            "effective release snapshot of the runtime that runs there"
            % (duty_name, purpose)
        )
    edition = declared.get("edition")
    if not isinstance(edition, dict):
        _fail("duty %s declares no edition block" % duty_name)
    if _text(edition.get("carrier")) != CARRIER_SEMANTIC:
        _fail(
            "duty %s does not declare that it carries an effective release snapshot"
            % duty_name
        )
    allowed = edition.get("allowed_product_keys")
    if not isinstance(allowed, list) or not allowed:
        _fail("duty %s declares no allowed edition product keys" % duty_name)
    for key in allowed:
        if not isinstance(key, str) or not PRODUCT_KEY.fullmatch(key):
            _fail("duty %s declares an unusable edition product key" % duty_name)
    prefix = _text(edition.get("version_prefix"))
    if not VERSION_PREFIX.fullmatch(prefix):
        _fail("duty %s declares an unusable edition version prefix" % duty_name)
    duty["edition"] = {
        "allowed_product_keys": list(allowed),
        "version_prefix": prefix,
    }
    return duty


def assert_declared_product_key(duty: dict, product_key: str) -> str:
    """Only an edition the duty itself declares may be published into it."""
    if not PRODUCT_KEY.fullmatch(product_key or ""):
        _fail("edition product key is not a safe declared key")
    if product_key not in duty["edition"]["allowed_product_keys"]:
        _fail(
            "duty %s does not declare edition %s (declared: %s)"
            % (
                duty["duty"],
                product_key,
                ",".join(duty["edition"]["allowed_product_keys"]),
            )
        )
    return product_key


def expected_version(duty: dict, product_key: str, source_revision: str) -> str:
    """Version the edition after the revision the duty actually runs."""
    if not SOURCE_REVISION.fullmatch(source_revision or ""):
        _fail("the rendered duty environment carries no usable source revision")
    edition_key = product_key.split(".", 1)[1]
    return "%s-%s-%s" % (
        duty["edition"]["version_prefix"],
        edition_key,
        source_revision[:12],
    )


def release_state(duty: dict) -> dict:
    """Read the duty's own release identity and snapshot rows back."""
    parameters = duty_runtime.psql(
        duty,
        "select key || '=' || coalesce(value, '') from ir_config_parameter "
        "where key in ('%s', '%s') order by key;" % (PARAMETER, TENANT_PARAMETER),
    )
    snapshots = duty_runtime.psql(
        duty,
        "select id || '|' || product_key || '|' || version || '|' || state "
        "|| '|' || is_active || '|' || active from %s order by id;" % SNAPSHOT_TABLE,
    )
    return {
        "parameters": [row for row in parameters.splitlines() if row.strip()],
        "snapshots": [row for row in snapshots.splitlines() if row.strip()],
    }


def released_active(duty: dict) -> list[dict]:
    """List the snapshots the duty would actually serve, product by product."""
    rows = duty_runtime.psql(
        duty,
        "select product_key || '|' || version from %s "
        "where state = 'released' and is_active and active order by product_key, id;"
        % SNAPSHOT_TABLE,
    )
    entries = []
    for row in rows.splitlines():
        row = row.strip()
        if not row:
            continue
        product_key, _, version = row.partition("|")
        entries.append({"product_key": product_key, "version": version})
    return entries


def release_mount(entry_root: Path) -> str:
    return "%s:%s:ro" % (entry_root, RELEASE_ENTRY_MOUNT)


def release_run_command(duty: dict, base: list[str], entry_root: Path, extra_env: list[str]):
    """A one-off run of the duty's own definition with the release entry exposed."""
    return base + [
        "run", "--rm", "--no-deps", "-T",
        "--label", "sc.daily-duty-edition-release=true",
        "--label", "sc.daily-duty=%s" % duty["duty"],
        "--volume", release_mount(entry_root),
        *extra_env,
        "--entrypoint", APPLICATION_ENTRY,
        "odoo", "shell", "-c", ODOO_CONF,
        "-d", duty["database"],
        "--no-http", "--log-level=error",
    ]


def readback_command(duty: dict, base: list[str], entry_root: Path):
    return release_run_command(duty, base, entry_root, [])


def publish_command(
    duty: dict,
    base: list[str],
    entry_root: Path,
    *,
    product_key: str,
    version: str,
):
    return release_run_command(
        duty,
        base,
        entry_root,
        [
            "-e", "PLATFORM_RELEASE_DB=%s" % duty["database"],
            "-e", "PLATFORM_RELEASE_PRODUCT_KEY=%s" % product_key,
            "-e", "PLATFORM_RELEASE_VERSION=%s" % version,
            "-e", "SC_COLOCATED_PLATFORM_CONFIG_APPLY=%s" % CONFIG_APPLY_ACK,
            "-e", "SC_COLOCATED_PLATFORM_SNAPSHOT_APPLY=%s" % SNAPSHOT_APPLY_ACK,
        ],
    )


def run_script(command: list[str], script: str, ops_root: Path) -> str:
    """Present one release entry script to the duty's own definition on stdin."""
    with tempfile.TemporaryDirectory() as workspace:
        stub = Path(workspace) / "release_entry.py"
        stub.write_text(script, encoding="utf-8")
        try:
            with stub.open("r", encoding="utf-8") as source:
                return duty_runtime.run(command, stdin=source, cwd=str(ops_root))
        except duty_runtime.PayloadEntryError as exc:
            _fail(str(exc))


def json_objects(output: str) -> list[dict]:
    found = []
    for line in output.splitlines():
        line = line.strip()
        if not line.startswith("{") or not line.endswith("}"):
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            found.append(parsed)
    return found


def readback_report(output: str) -> dict:
    for line in reversed(output.splitlines()):
        row = line.strip()
        if row.startswith(READBACK_MARKER):
            try:
                report = json.loads(row[len(READBACK_MARKER):])
            except json.JSONDecodeError as exc:
                _fail("the readback report is not JSON: %s" % exc)
            if isinstance(report, dict):
                return report
            _fail("the readback report is not an object")
    _fail("the readback emitted no report")


def assert_readback(
    report: dict,
    duty: dict,
    *,
    product_key: str = "",
    version: str = "",
) -> None:
    """The duty must read back as the database that carries this release."""
    if report.get("database") != duty["database"]:
        _fail("the readback targeted another database")
    if report.get("mode") != "read_only" or int(report.get("writes") or 0) != 0:
        _fail("the readback did not declare itself read-only")
    carrier = _text(report.get("platform_release_db"))
    if carrier and carrier != duty["database"]:
        _fail(
            "%s names another database (%s) on duty %s"
            % (PARAMETER, carrier, duty["duty"])
        )
    bound = _text(report.get("bound_tenant_key"))
    if bound and duty["tenant_key"] and bound != duty["tenant_key"]:
        _fail(
            "%s names another tenant (%s) on duty %s"
            % (TENANT_PARAMETER, bound, duty["duty"])
        )
    if not product_key:
        return
    if carrier != duty["database"]:
        _fail("%s does not name the duty database after publication" % PARAMETER)
    matches = [
        row
        for row in report.get("released_active") or []
        if isinstance(row, dict) and row.get("product_key") == product_key
    ]
    if len(matches) != 1:
        _fail(
            "the duty must carry exactly one released active %s snapshot, read %d"
            % (product_key, len(matches))
        )
    if version and _text(matches[0].get("version")) != version:
        _fail("the released %s snapshot names another version" % product_key)


def publish_reports(output: str, duty: dict) -> dict:
    """The two governed release entries each print their own JSON receipt."""
    objects = json_objects(output)
    configure = [row for row in objects if "parameter" in row]
    snapshot = [row for row in objects if "snapshot_id" in row]
    if not configure:
        _fail("the platform parameter entry emitted no receipt")
    if not snapshot:
        _fail("the snapshot entry emitted no receipt")
    configure_report = configure[-1]
    snapshot_report = snapshot[-1]
    for name, report in (("platform parameter", configure_report), ("snapshot", snapshot_report)):
        if report.get("status") != "PASS":
            _fail("the %s entry did not pass: %s" % (name, report.get("status")))
        if report.get("database") != duty["database"]:
            _fail("the %s entry ran against another database" % name)
    if _text(configure_report.get("parameter")) != PARAMETER:
        _fail("the platform parameter entry wrote an unexpected parameter")
    if _text(configure_report.get("value")) != duty["database"]:
        _fail("the platform parameter entry wrote an unexpected value")
    return {"platform_parameter": configure_report, "snapshot": snapshot_report}


def entry_digests(entry_root: Path) -> dict:
    digests = {}
    for name in RELEASE_ENTRY_SCRIPTS:
        path = entry_root / name
        if path.is_symlink() or not path.is_file():
            _fail("the immutable release entry %s is unavailable" % name)
        digests[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return digests


def tool_identity(root: Path) -> str:
    marker = root / "DEPLOYMENT_TOOL_SHA"
    if not marker.is_file():
        return ""
    tool_sha = marker.read_text(encoding="utf-8").strip()
    if tool_sha != root.name:
        _fail("the immutable deployment tool identity differs")
    return tool_sha


def execute(
    duty_name: str,
    *,
    action: str,
    product_key: str = "",
    declaration: Path | None = None,
    tool_root: Path | None = None,
) -> dict:
    if action not in ACTIONS:
        _fail("unsupported edition release action: %s" % action)
    duty = resolve_release_duty(duty_name, declaration)
    ops_root = Path(duty_identity.load_declaration(declaration).get("ops_root") or "")
    if not ops_root.is_absolute():
        _fail("the declaration must name an absolute ops root")
    env_path = duty_identity.duty_env_path(duty, ops_root, reading=True)
    values = duty_runtime.read_duty_env(env_path, duty)
    stack = duty_runtime.stack_compose_path(ops_root)
    application = duty_runtime.inspect_odoo_container(duty, values)
    base = duty_runtime.compose_base(duty, ops_root, env_path, stack)

    root = tool_root or ROOT
    entry_root = root / RELEASE_ENTRY_DIRECTORY
    digests = entry_digests(entry_root)
    tool_sha = tool_identity(root)

    version = ""
    if action == "publish":
        variable, expected = CONFIRMATIONS[action]
        if os.environ.get(variable) != expected:
            _fail("%s must be set to the exact confirmation value" % variable)
        assert_declared_product_key(duty, product_key)
        version = expected_version(duty, product_key, values.get("SC_SOURCE_REVISION", ""))

    before_state = release_state(duty)
    before_released = released_active(duty)
    before_digest = hashlib.sha256(
        json.dumps(before_state, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()

    publish_output = ""
    reports: dict = {}
    if action == "publish":
        publish_output = run_script(
            publish_command(
                duty, base, entry_root, product_key=product_key, version=version
            ),
            PUBLISH_SCRIPT,
            ops_root,
        )
        reports = publish_reports(publish_output, duty)

    readback_output = run_script(
        readback_command(duty, base, entry_root),
        READBACK_SCRIPT,
        ops_root,
    )
    report = readback_report(readback_output)

    after_state = release_state(duty)
    after_released = released_active(duty)
    after_digest = hashlib.sha256(
        json.dumps(after_state, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()

    if action == "readback":
        assert_readback(report, duty)
        if before_digest != after_digest or before_released != after_released:
            _fail("the readback changed the duty's release state")
    else:
        assert_readback(report, duty, product_key=product_key, version=version)
        if not any(
            row["product_key"] == product_key and row["version"] == version
            for row in after_released
        ):
            _fail("the published edition is not the one the duty reports as released")

    return {
        "schema_version": "daily_runtime_duty_edition_release.v1",
        "action": action,
        "duty": duty["duty"],
        "database": duty["database"],
        "database_role": duty["database_role"],
        "environment_id": duty["environment_id"],
        "tenant_key": duty["tenant_key"],
        "data_purpose": duty["data_purpose"],
        "edition_carrier": CARRIER_SEMANTIC,
        "declared_allowed_product_keys": duty["edition"]["allowed_product_keys"],
        "product_key": product_key,
        "version": version,
        "source_revision": values.get("SC_SOURCE_REVISION", ""),
        "application": application,
        "stack_compose": str(stack),
        "duty_environment": str(env_path),
        "release_entry_scripts": digests,
        "tool_sha": tool_sha,
        "readback_report": report,
        "release_state_before": before_state,
        "release_state_after": after_state,
        "release_state_digest_before": before_digest,
        "release_state_digest_after": after_digest,
        "released_active_before": before_released,
        "released_active_after": after_released,
        "publish_reports": reports,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=list(ACTIONS))
    parser.add_argument("--duty", required=True)
    parser.add_argument("--product-key", default="")
    parser.add_argument("--declaration", default="")
    parser.add_argument("--evidence", default="")
    parser.add_argument(
        "--emit-refresh-json",
        action="store_true",
        help="also print the released snapshot as a raw refresh JSON line consumed by the published-face convergence",
    )
    args = parser.parse_args(argv)
    try:
        evidence = execute(
            args.duty,
            action=args.action,
            product_key=args.product_key,
            declaration=Path(args.declaration) if args.declaration else None,
        )
    except (
        EditionReleaseEntryError,
        duty_identity.DutyIdentityError,
        duty_runtime.PayloadEntryError,
        OSError,
    ) as exc:
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
    if args.emit_refresh_json and args.action == "publish":
        snapshot = (evidence.get("publish_reports") or {}).get("snapshot") or {}
        print(
            json.dumps(
                {
                    "status": "PASS" if snapshot.get("status") == "PASS" else "FAIL",
                    "product_key": snapshot.get("product_key") or evidence.get("product_key") or "",
                    "snapshot_id": int(snapshot.get("snapshot_id") or 0),
                    "policy_menu_count": int(snapshot.get("policy_menu_count") or 0),
                    "snapshot_menu_count": int(snapshot.get("snapshot_menu_count") or 0),
                    "changed": bool(snapshot.get("changed")),
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
