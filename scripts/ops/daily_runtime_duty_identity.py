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

#: A *protected historic source* is a database carrier the governed runtime must
#: never write to and must never mistake for a duty.  Before the 2026-10-16 demo
#: rebuild the only carrier named ``sc_demo`` was a duty; afterwards a rebuilt
#: duty and the preserved pre-governance cluster both carry that name.  A bare
#: database name therefore stops identifying a target, and the declaration has to
#: say so itself.
PROTECTED_SOURCES_KEY = "protected_historic_sources"
PROTECTED_HISTORIC_SOURCE_KEYS = (
    "source_id", "database", "cluster", "visibility", "authority", "reason",
)
PROTECTED_VISIBILITIES = ("read_only_historic",)
CARRIER_DUTY = "duty"
CARRIER_PROTECTED_SOURCE = "protected_historic_source"


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


def protected_historic_sources(declaration: dict) -> list[dict]:
    """The declared read-only historic carriers, or an empty list.

    An absent section means "this declaration names no historic source", which is
    a legitimate shape for a synthetic fixture.  A present but malformed section
    is a stop, because the only reason the section exists is to make a bare
    database name ambiguous on purpose -- a half-written one would reintroduce
    exactly the guess it is there to forbid.
    """
    sources = declaration.get(PROTECTED_SOURCES_KEY)
    if sources is None:
        return []
    if not isinstance(sources, list) or not sources:
        raise DutyIdentityError(
            "%s must be a non-empty list when declared" % (PROTECTED_SOURCES_KEY,)
        )
    return sources


def validate_protected_historic_sources(declaration: dict) -> None:
    """Every reason a declared historic source cannot be a faithful record."""
    duties = [
        entry for entry in declaration.get("duties") or [] if isinstance(entry, dict)
    ]
    seen_ids = set()
    for source in protected_historic_sources(declaration):
        if not isinstance(source, dict):
            raise DutyIdentityError("%s entries must be objects" % (PROTECTED_SOURCES_KEY,))
        missing = [key for key in PROTECTED_HISTORIC_SOURCE_KEYS if key not in source]
        if missing:
            raise DutyIdentityError(
                "protected historic source lacks keys %s" % (",".join(missing),)
            )
        source_id = str(source["source_id"])
        if not SAFE_IDENTIFIER.fullmatch(source_id):
            raise DutyIdentityError(
                "protected historic source id %s is not a safe identifier"
                % (source_id or "<unset>",)
            )
        if source_id in seen_ids:
            raise DutyIdentityError("duplicate protected historic source id: %s" % (source_id,))
        seen_ids.add(source_id)
        database = str(source["database"])
        # A preserved carrier is named by history, not by the current duty
        # convention: the pre-governance databases predate it.  What has to hold
        # is only that the name is a plain database identifier a governed entry
        # can safely interpolate, never that it fits a convention it was
        # invented without.
        if not SAFE_IDENTIFIER.fullmatch(database):
            raise DutyIdentityError(
                "protected historic source %s: database %s is not a plain database name"
                % (source_id, database or "<unset>")
            )
        if str(source["visibility"]) not in PROTECTED_VISIBILITIES:
            raise DutyIdentityError(
                "protected historic source %s: visibility must be one of %s"
                % (source_id, ",".join(PROTECTED_VISIBILITIES))
            )
        for field in ("authority", "reason"):
            if not str(source[field] or "").strip():
                raise DutyIdentityError(
                    "protected historic source %s needs %s" % (source_id, field)
                )
        cluster = source["cluster"]
        if not isinstance(cluster, dict):
            raise DutyIdentityError(
                "protected historic source %s: cluster must be an object" % (source_id,)
            )
        for key in ("container", "compose_project", "data_volume"):
            value = str(cluster.get(key) or "")
            if not (SAFE_IDENTIFIER.fullmatch(value) or SAFE_COMPOSE_PROJECT.fullmatch(value)):
                raise DutyIdentityError(
                    "protected historic source %s: cluster.%s %s is not a safe identifier"
                    % (source_id, key, value or "<unset>")
                )
        for duty in duties:
            duty_cluster = duty.get("cluster") or {}
            same_container = str(duty_cluster.get("container") or "") == str(cluster["container"])
            same_volume = str(duty_cluster.get("data_volume") or "") == str(cluster["data_volume"])
            if same_container or same_volume:
                raise DutyIdentityError(
                    "protected historic source %s shares a cluster container or data volume with "
                    "duty %s; a preserved source must be a different carrier, not the duty itself"
                    % (source_id, duty.get("duty"))
                )


def database_carriers(declaration: dict) -> dict[str, list[dict]]:
    """Every declared carrier of each database name, keyed by that name."""
    carriers: dict[str, list[dict]] = {}

    def add(name: str, row: dict) -> None:
        if name:
            carriers.setdefault(name, []).append(row)

    for entry in declaration.get("duties") or []:
        if not isinstance(entry, dict):
            continue
        cluster = entry.get("cluster") or {}
        add(str(entry.get("database") or ""), {
            "kind": CARRIER_DUTY,
            "id": str(entry.get("duty") or ""),
            "database": str(entry.get("database") or ""),
            "database_role": str(entry.get("database_role") or ""),
            "dbfilter": str(entry.get("dbfilter") or ""),
            "data_purpose": str(entry.get("data_purpose") or ""),
            "compose_project": str(cluster.get("compose_project") or ""),
            "database_container": str(cluster.get("container") or ""),
            "database_volume": str(cluster.get("data_volume") or ""),
            "writable": True,
        })
    for source in protected_historic_sources(declaration):
        cluster = source.get("cluster") or {}
        name = str(source.get("database") or "")
        add(name, {
            "kind": CARRIER_PROTECTED_SOURCE,
            "id": str(source.get("source_id") or ""),
            "database": name,
            "database_role": "",
            "dbfilter": "^%s$" % (name,),
            "data_purpose": str(source.get("visibility") or ""),
            "compose_project": str(cluster.get("compose_project") or ""),
            "database_container": str(cluster.get("container") or ""),
            "database_volume": str(cluster.get("data_volume") or ""),
            "writable": False,
        })
    return carriers


def resolve_duty_carrier(database: str, path: Path | None = None, *, instances_reader=None,
                         staging_reader=None) -> dict:
    """Resolve one database *name* to exactly one declared *duty* carrier, or stop.

    A database name is not a target identity.  Once two declared carriers can
    both answer to ``sc_demo`` -- the rebuilt duty and the preserved historic
    source -- an entry that receives only a name cannot tell which one the
    operator meant, and picking either is a guess about which data is about to be
    written or read.  The refusal lists every carrier so the operator can bind
    the duty, the cluster, the database and the storage explicitly instead.

    The returned carrier is always a duty.  A *protected historic source* is a
    carrier by name only: it exists so that the name stops resolving silently,
    never so that a duty entry may adopt it as a write or acceptance target.
    """
    wanted = str(database or "").strip()
    if not wanted:
        raise DutyIdentityError("DUTY_IDENTITY_DATABASE_UNNAMED")
    declaration = load_declaration(
        path, instances_reader=instances_reader, staging_reader=staging_reader,
    )
    matches = database_carriers(declaration).get(wanted) or []
    if not matches:
        raise DutyIdentityError("DUTY_IDENTITY_DATABASE_UNDECLARED:%s" % (wanted,))
    if len(matches) > 1:
        raise DutyIdentityError(
            "DUTY_IDENTITY_DATABASE_AMBIGUOUS:%s:%s"
            % (wanted, ",".join(
                "%s=%s=%s" % (row["kind"], row["id"], row["database_container"])
                for row in matches
            ))
        )
    carrier = matches[0]
    if carrier["kind"] != CARRIER_DUTY:
        raise DutyIdentityError(
            "DUTY_IDENTITY_DATABASE_HISTORIC_SOURCE:%s:%s" % (wanted, carrier["id"])
        )
    return carrier


def carrier_binding(carrier: dict, *, bound_by: str) -> dict:
    """One normalized binding of a duty, its cluster, its database and its storage.

    Every entry that targets a deployed face needs the same five facts, and the
    owner ruling of 2026-10-16 makes them one identity: a database name alone
    stopped being a target.  Returning one shape from here is what keeps the
    entries from each assembling their own variation of it.
    """
    return {
        "bound_by": bound_by,
        "duty": carrier["id"],
        "database": carrier["database"],
        "database_role": carrier["database_role"],
        "dbfilter": carrier["dbfilter"],
        "data_purpose": carrier["data_purpose"],
        "compose_project": carrier["compose_project"],
        "database_container": carrier["database_container"],
        "database_volume": carrier["database_volume"],
        "odoo_container": odoo_container_of(carrier["compose_project"]),
    }


def odoo_container_of(compose_project: str) -> str:
    """The application container of one compose project, by the same rule the compiler uses.

    A duty's application is addressed through its *own* compose project, never
    through a remembered container name: the pre-governance cluster and the
    rebuilt demo carrier are two projects, and a name remembered from one would
    silently reach into the other.
    """
    return "%s-odoo-1" % (compose_project,)


#: The application container's own Odoo configuration and the flags a
#: non-serving shell needs.  A duty-scoped write runs inside the *bound duty's
#: own* application container, because a database name is not a target: the
#: rebuilt demo carrier and the preserved historic source both answer to
#: ``sc_demo``, and a command that named only the database would run in
#: whichever cluster happened to serve that name -- for the demo that is the
#: preserved pre-governance cluster, which the owner ruling protects from every
#: governed write.
ODOO_CONF_PATH = "/var/lib/odoo/odoo.conf"
ODOO_SHELL_FLAGS = ("--no-http", "--workers=0", "--max-cron-threads=0")


def odoo_shell_command(binding: dict, *, program_path: str = "",
                       odoo_conf: str = ODOO_CONF_PATH,
                       env: dict | None = None) -> str:
    """The shell command that runs an Odoo shell inside the bound duty's container.

    Nothing here comes from a working directory, an environment file or a
    remembered container name: the target is the bound duty's own application,
    named by the declaration's compose project.  ``env`` passes the few inputs a
    program reads from the process environment without touching anything the
    container already declares, and ``program_path`` feeds the program on stdin
    so the entry does not depend on which shell the remote host happens to
    start.
    """
    parts = ["docker", "exec", "-i"]
    for key, value in sorted((env or {}).items()):
        parts += ["-e", "%s=%s" % (key, value)]
    parts += [
        binding["odoo_container"],
        "odoo", "shell", "-c", odoo_conf, "-d", binding["database"],
    ] + list(ODOO_SHELL_FLAGS)
    command = " ".join(shlex.quote(part) for part in parts)
    if program_path:
        command = "%s < %s" % (command, shlex.quote(program_path))
    return command


def bind_duty_database(duty_name, database, path: Path | None = None, *, instances_reader=None,
                       staging_reader=None) -> dict:
    """Bind a target to one declared duty, or stop with the reason it cannot.

    Two shapes are legitimate and they are not interchangeable.  Naming the
    *duty* is the strong form: the duty declares its database, its cluster, its
    storage and its purpose, so the binding is complete by construction.  Naming
    only the *database* is the weak form and is accepted only while exactly one
    declared duty carries that name; the moment a preserved second carrier
    exists -- which is the whole point of ``protected_historic_sources`` -- the
    weak form stops resolving and the caller has to say which duty it means.
    """
    kwargs = {"instances_reader": instances_reader, "staging_reader": staging_reader}
    wanted = str(duty_name or "").strip()
    if wanted:
        declared = resolve(wanted, path, **kwargs)
        resolved_database = str(declared.get("database") or "")
        asked = str(database or "").strip()
        if asked and asked != resolved_database:
            # A caller that named both and they disagree is not choosing; it is
            # stating one identity and asking for another.  Refusing is the only
            # answer that cannot silently target the wrong database.
            raise DutyIdentityError(
                "DUTY_IDENTITY_DATABASE_DISAGREES_WITH_DUTY:%s:%s:%s"
                % (wanted, asked, resolved_database)
            )
        # ``resolve`` already flattened and validated the duty: the container,
        # the volumes and the filestore scope it returns are the ones the
        # declaration names, so this binding is complete without re-reading it.
        return carrier_binding({
            key: str(declared.get(key) or "")
            for key in ("database", "database_role", "dbfilter", "data_purpose",
                        "compose_project", "database_container", "database_volume")
        } | {"id": str(declared.get("duty") or wanted)}, bound_by="duty")
    return carrier_binding(resolve_duty_carrier(database, path, **kwargs), bound_by="database")


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
    # Validated before the managed instances are merged, because the historic
    # source section describes carriers the merged document cannot extend: its
    # whole purpose is to keep a preserved carrier distinguishable from a duty.
    validate_protected_historic_sources(payload)
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
