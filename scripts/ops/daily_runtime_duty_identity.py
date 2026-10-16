#!/usr/bin/env python3
"""Single authority for which database, cluster and storage a duty owns.

A *duty* is one of the governed daily-runtime databases: the platform control
plane, the demo, or one customer development tenant.  Every governed entry that
reads or writes a duty resolves its runtime identity here.

Two documents are involved, and only the second one may name a customer:

* ``config/ops/daily_runtime_database_duties.v1.json`` -- the tracked *template*.
  It carries the schema, the naming rules, the generic duties and the statement
  that a customer duty is supplied from the managed directory.  It is delivered
  to every customer, so it never carries a fixed customer identity.
* the managed duty-instance document under ``ops_root`` -- the concrete binding
  of one customer tenant.  The governed entry writes it 0600 outside the git
  checkout, so the product tree stays customer-agnostic while the runtime still
  has one authoritative binding.

Resolution merges the template with the managed instances and refuses when a
required instance is missing or unreadable, still carries a placeholder, breaks
the naming rules, or disagrees with the duty it claims to be.  A placeholder is
never substituted and then executed: in an instance it is a stop, not an input.

The governed duty entry *writes* the managed document: it is created 0600 under
``ops_root`` outside the git checkout, the previous revision is kept, and the
digest is read back.  Entrypoints that run on the host read it directly; the one
workstation-side entry reads it through ssh.  ``SC_DAILY_RUNTIME_DUTY_INSTANCES``
overrides the source with an explicitly named path for the first materialisation;
it is an override, never a fallback, so an unset value reads the governed
document and a missing one stops the entry.

The declaration is an ops-side authority.  It does not replace the platform
model that owns database lifecycle registration.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DUTY_DECLARATION = ROOT / "config" / "ops" / "daily_runtime_database_duties.v1.json"
SCHEMA = "daily.runtime.database_duties.v1"
INSTANCES_SCHEMA = "daily.runtime.database_duties.instances.v1"
#: Where a host-side entry that cannot reach ``ops_root`` itself names the
#: fetched instance document.  It is an explicit override, never a fallback: an
#: unset value means "read the managed directory", not "guess".
INSTANCES_ENV = "SC_DAILY_RUNTIME_DUTY_INSTANCES"

SAFE_IDENTIFIER = re.compile(r"[a-z][a-z0-9_]*")
SAFE_COMPOSE_PROJECT = re.compile(r"[a-z0-9][a-z0-9-]*")
PLACEHOLDER = re.compile(r"<[a-z0-9_]+>")
FILESTORE_ROOT = "/var/lib/odoo/filestore"
DATABASE_MOUNT = "/var/lib/postgresql/data"
ODOO_DATA_MOUNT = "/var/lib/odoo"
DRILL_ROLE = "odoo"
#: Every key a duty instance must carry, whichever document supplied it.
INSTANCE_KEYS = (
    "duty", "database", "database_role", "dbfilter", "environment_id", "tenant_key",
    "data_purpose", "cluster", "custody", "storage", "routing", "section_11",
)
#: Duties whose concrete binding comes from the managed directory.  The template
#: names the shape; the instance document names the customer.
MANAGED_SOURCE = "managed_directory"


class DutyIdentityError(RuntimeError):
    pass


#: The only role-naming exception this repository accepts, and it is never
#: inferred: the declaration has to record it itself.
DECLARED_ROLE_GAP_KIND = "shared_bootstrap_role"


def role_naming_is_declared_gap(duty: dict) -> bool:
    """True when the declaration itself records the application-role exception.

    A duty whose application role is still its cluster bootstrap role is a
    historical fact, and the tracked declaration already describes it with
    ``custody.role_compliance = declared_gap`` plus
    ``gap_kind = shared_bootstrap_role``.  ``daily_runtime_database_duty``
    accepts exactly that pair, so the two entries cannot disagree about which
    role name is a target and which one is a recorded gap.  Nothing else is
    exempt, and no duty-name or database-name rule is relaxed.
    """
    custody = duty.get("custody")
    if not isinstance(custody, dict):
        return False
    return (
        custody.get("role_compliance") == "declared_gap"
        and custody.get("gap_kind") == DECLARED_ROLE_GAP_KIND
    )


def read_instances_file(path: str) -> str:
    """Read the managed instance document from the governed directory."""
    with open(path, encoding="utf-8") as stream:
        return stream.read()


def ssh_instances_reader(ssh_host: str):
    """Read the managed instance document through the existing governed channel.

    The reader returns the *text* so the caller can digest and validate it here
    instead of trusting the transport.  A non-zero exit or an empty document is
    a refusal: a missing managed binding must stop the entry, not fall back to
    a guessed identity.
    """

    def read(remote_path: str) -> str:
        completed = subprocess.run(
            ["ssh", ssh_host, "cat %s" % (shlex.quote(remote_path),)],
            capture_output=True,
            text=True,
        )
        if completed.returncode:
            raise DutyIdentityError(
                "managed duty instances are unreadable on %s: %s"
                % (ssh_host, (completed.stderr or "").strip()[:300] or "no diagnostic")
            )
        if not completed.stdout.strip():
            raise DutyIdentityError(
                "managed duty instances are empty on %s: %s" % (ssh_host, remote_path)
            )
        return completed.stdout

    return read


def instances_location(declaration: dict) -> str:
    """Absolute path of the managed instance document for this declaration."""
    declared = declaration.get("managed_duty_instances")
    if not isinstance(declared, dict):
        raise DutyIdentityError("declaration does not say where managed duty instances live")
    name = declared.get("file")
    if not isinstance(name, str) or not name or "/" in name or name.startswith("."):
        raise DutyIdentityError("managed duty instances file must be one plain file name")
    ops_root = str(declaration.get("ops_root") or "")
    if not ops_root.startswith("/") or ops_root.endswith("/"):
        raise DutyIdentityError("declaration ops_root must be one absolute directory path")
    return "%s/%s" % (ops_root, name)


def parse_instances(text: str, source: str) -> list[dict]:
    try:
        document = json.loads(text)
    except ValueError as error:
        raise DutyIdentityError("managed duty instances are not valid JSON (%s): %s" % (source, error))
    if not isinstance(document, dict) or document.get("schema") != INSTANCES_SCHEMA:
        raise DutyIdentityError("managed duty instances carry an unexpected schema: %s" % (source,))
    duties = document.get("duties")
    if not isinstance(duties, list) or not duties:
        raise DutyIdentityError("managed duty instances list no duty: %s" % (source,))
    for duty in duties:
        if not isinstance(duty, dict):
            raise DutyIdentityError("managed duty instances carry a non-object duty: %s" % (source,))
    return duties


def validate_instance(duty: dict, naming: dict) -> None:
    """Every reason one managed instance cannot govern a duty."""
    name = str(duty.get("duty") or "")
    if not name:
        raise DutyIdentityError("managed duty instance without a name")
    missing = [key for key in INSTANCE_KEYS if key not in duty]
    if missing:
        raise DutyIdentityError("managed duty %s lacks keys %s" % (name, ",".join(missing)))
    serialized = json.dumps(duty, ensure_ascii=False)
    leftover = sorted(set(PLACEHOLDER.findall(serialized)))
    if leftover:
        # The template may describe a shape with placeholders; a *binding* may
        # not.  Substituting one here would decide a customer identity at run
        # time from a pattern, which is exactly what this boundary forbids.
        raise DutyIdentityError(
            "managed duty %s still carries an unresolved placeholder %s"
            % (name, ",".join(leftover))
        )
    database = str(duty.get("database") or "")
    role = str(duty.get("database_role") or "")
    cluster = duty.get("cluster") or {}
    compose_project = str(cluster.get("compose_project") or "")
    patterns = [
        ("database", database, naming.get("database") or ""),
        ("database_role", role, naming.get("database_role") or ""),
        ("compose_project", compose_project, naming.get("compose_project") or ""),
    ]
    if role_naming_is_declared_gap(duty):
        patterns = [row for row in patterns if row[0] != "database_role"]
    for label, value, pattern in patterns:
        if not value or not re.fullmatch(pattern, value):
            raise DutyIdentityError(
                "managed duty %s: %s %s breaks the naming convention" % (name, label, value or "<unset>")
            )
    if str(duty.get("dbfilter") or "") != "^%s$" % (database,):
        raise DutyIdentityError("managed duty %s: dbfilter does not select exactly its database" % (name,))
    section = duty.get("section_11") or {}
    tenant_key = str(duty.get("tenant_key") or "")
    if str(section.get("TARGET_TENANT_ID") or "") != tenant_key:
        raise DutyIdentityError(
            "managed duty %s: section_11.TARGET_TENANT_ID disagrees with its tenant_key" % (name,)
        )
    if str(section.get("TARGET_ENVIRONMENT_ID") or "") != str(duty.get("environment_id") or ""):
        raise DutyIdentityError(
            "managed duty %s: section_11.TARGET_ENVIRONMENT_ID disagrees with its environment_id" % (name,)
        )


def merge_instances(declaration: dict, instances: list[dict]) -> dict:
    """Return the declaration with its managed instances resolved into duties."""
    duties = declaration.get("duties")
    if not isinstance(duties, list) or not duties:
        raise DutyIdentityError("duty declaration carries no duties")
    naming = declaration.get("naming") or {}
    names = {duty.get("duty") for duty in duties if isinstance(duty, dict)}
    for instance in instances:
        validate_instance(instance, naming)
        name = instance["duty"]
        if name in names:
            # Two documents naming the same duty is a drift, not a preference.
            raise DutyIdentityError("duty %s is declared twice" % (name,))
        names.add(name)
        duties = duties + [instance]
    merged = dict(declaration)
    merged["duties"] = duties
    return merged


def managed_instances_source(declaration, *, instances_reader=None, staging_reader=None):
    """Return ``(target, reader, source)`` for the managed instance document.

    ``SC_DAILY_RUNTIME_DUTY_INSTANCES`` is an explicit override, never a
    fallback: while it is set that path *is* the source, and while it is unset
    the governed document under ``ops_root`` is.  A workstation-side entry pairs
    an ssh reader for ``ops_root`` with the local-file reader for the override,
    so a staged revision and the already-materialised revision can never be
    mistaken for one another.
    """
    override = os.environ.get(INSTANCES_ENV, "").strip()
    if override:
        reader = staging_reader if staging_reader is not None else read_instances_file
        return override, reader, "override"
    reader = instances_reader if instances_reader is not None else read_instances_file
    return instances_location(declaration), reader, "managed"


def read_instances_document(declaration: dict, *, instances_reader=None, staging_reader=None) -> dict:
    """Read the managed document once and describe exactly what was read.

    The entry that materialises the document needs the bytes and the digest as
    well as the parsed duties, and the caller that only wants the duties must
    not read a *different* revision than the one it validated.  One reader, one
    text, one identity readback.
    """
    declared = declaration.get("managed_duty_instances") or {}
    location = instances_location(declaration)
    target, reader, source = managed_instances_source(
        declaration, instances_reader=instances_reader, staging_reader=staging_reader
    )
    try:
        text = reader(target)
    except DutyIdentityError:
        raise
    except OSError as error:
        raise DutyIdentityError(
            "managed duty instances are unreadable at %s: %s" % (target, error)
        ) from error
    return {
        "file": str(declared.get("file") or ""),
        "path": location,
        "read_from": target,
        "source": source,
        "text": text,
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "duties": parse_instances(text, target),
    }


def load_instances(declaration: dict, *, instances_reader=None, staging_reader=None) -> list[dict]:
    return read_instances_document(
        declaration, instances_reader=instances_reader, staging_reader=staging_reader
    )["duties"]


def load_declaration(path: Path | None = None, *, instances_reader=None, staging_reader=None) -> dict:
    """Read the tracked template and resolve its managed duty instances."""
    target = path or DUTY_DECLARATION
    try:
        payload = json.loads(Path(target).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DutyIdentityError("duty declaration is missing or invalid") from exc
    if not isinstance(payload, dict):
        raise DutyIdentityError("duty declaration is not an object")
    if payload.get("schema") != SCHEMA:
        raise DutyIdentityError("duty declaration schema is unexpected: %s" % (payload.get("schema"),))
    declared = payload.get("duties")
    if not isinstance(declared, list) or not declared:
        raise DutyIdentityError("duty declaration carries no duties")
    managed = payload.get("managed_duty_instances")
    if managed is None:
        # A self-contained declaration is legitimate for a synthetic fixture or
        # for a server that declares no customer duty at all.  It is not a
        # fallback: nothing is guessed, and a customer duty that nobody supplies
        # simply stays undeclared, which every entry already refuses.
        return payload
    if not isinstance(managed, dict) or managed.get("source") != MANAGED_SOURCE:
        raise DutyIdentityError(
            "duty declaration does not name the managed directory as the source of customer duties"
        )
    return merge_instances(payload, load_instances(
        payload, instances_reader=instances_reader, staging_reader=staging_reader,
    ))


def load_duties(path: Path | None = None, *, instances_reader=None, staging_reader=None) -> dict:
    """Read the single authority for which database each duty owns."""
    declared = load_declaration(
        path, instances_reader=instances_reader, staging_reader=staging_reader,
    ).get("duties")
    table: dict[str, dict] = {}
    for entry in declared:
        name = entry.get("duty") if isinstance(entry, dict) else None
        if not isinstance(name, str) or not name:
            raise DutyIdentityError("duty entry without a name")
        if name in table:
            raise DutyIdentityError(f"duplicate duty declaration: {name}")
        table[name] = entry
    return table


def duty_identity(duty: dict, naming: dict | None = None) -> dict:
    """Resolve runtime identity from the duty declaration, never from a contract.

    A contract may restate these fields for assertion, but the declaration is
    the only owner: a disagreement is a stop, not a vote.
    """

    def required(mapping: dict, key: str, source: str) -> str:
        value = mapping.get(key)
        if not isinstance(value, str) or not value:
            raise DutyIdentityError(f"duty declaration lacks {source}.{key}")
        return value

    cluster = duty.get("cluster")
    storage = duty.get("storage")
    if not isinstance(cluster, dict) or not isinstance(storage, dict):
        raise DutyIdentityError("duty declaration lacks cluster or storage")
    compose_project = required(cluster, "compose_project", "cluster")
    if not SAFE_COMPOSE_PROJECT.fullmatch(compose_project):
        raise DutyIdentityError("duty compose project is not a safe identifier")
    identity = {
        "duty": duty["duty"],
        "environment_id": required(duty, "environment_id", "duty"),
        "tenant_key": duty.get("tenant_key") or "",
        "data_purpose": required(duty, "data_purpose", "duty"),
        "database": required(duty, "database", "duty"),
        "database_role": required(duty, "database_role", "duty"),
        "dbfilter": required(duty, "dbfilter", "duty"),
        "compose_project": compose_project,
        "database_container": required(cluster, "container", "cluster"),
        "odoo_container": f"{compose_project}-odoo-1",
        "database_volume": required(cluster, "data_volume", "cluster"),
        "odoo_data_volume": required(storage, "odoo_data_volume", "storage"),
        "filestore_scope": required(storage, "filestore_scope", "storage"),
        "backup_root": required(storage, "backup_namespace", "storage"),
        "filestore_root": FILESTORE_ROOT,
    }
    for key in ("database", "database_role", "database_volume", "odoo_data_volume"):
        if not SAFE_IDENTIFIER.fullmatch(identity[key]):
            raise DutyIdentityError(f"duty declaration {key} is not a safe identifier")
    if identity["filestore_scope"] != identity["database"]:
        raise DutyIdentityError("duty filestore scope no longer matches its database")
    if identity["dbfilter"] != f"^{identity['database']}$":
        raise DutyIdentityError("duty filter no longer selects exactly its database")
    if naming:
        declared_gap = role_naming_is_declared_gap(duty)
        for label, key in (("database", "database"), ("database_role", "database_role")):
            if label == "database_role" and declared_gap:
                continue
            pattern = naming.get(label)
            if pattern and not re.fullmatch(pattern, identity[key]):
                raise DutyIdentityError(f"duty {label} breaks the naming convention")
    return identity


def resolve(duty_name: str, path: Path | None = None, *, instances_reader=None,
            staging_reader=None) -> dict:
    """Resolve one declared duty, or stop."""
    declaration = load_declaration(
        path, instances_reader=instances_reader, staging_reader=staging_reader,
    )
    duties: dict[str, dict] = {}
    for entry in declaration["duties"]:
        name = entry.get("duty")
        if name in duties:
            raise DutyIdentityError(f"duplicate duty declaration: {name}")
        duties[name] = entry
    if duty_name not in duties:
        raise DutyIdentityError(f"undeclared duty: {duty_name}")
    return duty_identity(duties[duty_name], declaration.get("naming") or {})
