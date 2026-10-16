#!/usr/bin/env python3
"""Read-only ownership and visibility probe for one governed runtime database.

``smart_construction_core`` bounds row visibility through the registered data
space, so a row whose owning company is not onboarded, or whose model declares
that an owner is mandatory, is invisible to every principal. This probe answers
the questions that follow from that decision without writing anything:

* which declared models own rows whose owning company is not registered;
* how many rows carry no owner at all, and which of the models that own such
  rows are bounded by a strict ceiling (no unset-owner branch) versus a shared
  one;
* whether the *installed* rules match the semantics this checkout declares.

Provenance is recorded per section, because the two are not the same fact:

* ``live_account_query`` comes from a read-only ``odoo.shell.exec`` transaction
  on the target database;
* ``repository_source`` is read from this checkout and says nothing about what
  is deployed.

The probe never writes: ``--report`` only writes a local file. A zero exit code
is not the verdict; the ``assertions`` block is.
"""
from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
import xml.etree.ElementTree as ElementTree
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import daily_runtime_duty_identity as duty_identity  # noqa: E402
REMOTE_ROOT = "/opt/projects/repos/sce-product-odoo"
REMOTE_TMP = "/tmp/sc-daily-data-ownership-probe.py"
DEFAULT_DATABASE = ""
DECLARATIONS = ROOT / "scripts/verify/data_scope_declarations.json"
CEILING_XML = ROOT / "addons/smart_construction_core/security/sc_data_scope_ceiling_generated.xml"
HANDWRITTEN_XML = ROOT / "addons/smart_construction_core/security/sc_record_rules.xml"
MARKER = "DAILY_DATA_OWNERSHIP_PROBE="
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
SSH_HOST = re.compile(r"^[A-Za-z0-9._-]+$")
DATABASE_NAME = re.compile(r"^[A-Za-z0-9_]+$")
SHIPPING_MODULE = "smart_construction_core"


class ProbeError(RuntimeError):
    pass


PROBE_TEMPLATE = '''
import json

from odoo.addons.smart_construction_core.services import business_data_ownership as own
from odoo.addons.smart_core.security import data_space_provisioning as prov

ANCHORS = __ANCHORS__
MARKER = "DAILY_DATA_OWNERSHIP_PROBE="
INTEREST = __INTEREST__


def build_sql(model_name, anchor):
    Model = env[model_name]
    parts = anchor.split(".")
    table = Model._table
    current = Model
    alias = "t0"
    joins = []
    for index, segment in enumerate(parts[:-1]):
        field = current._fields.get(segment)
        if field is None or field.type != "many2one":
            return None, "segment_not_many2one:" + segment
        related = env.get(field.comodel_name)
        if related is None:
            return None, "unknown_comodel:" + field.comodel_name
        next_alias = "t" + str(index + 1)
        joins.append(
            "LEFT JOIN " + related._table + " " + next_alias + " ON "
            + next_alias + ".id = " + alias + "." + field.name
        )
        alias = next_alias
        current = related
    last = parts[-1]
    last_field = current._fields.get(last)
    if last_field is None or last_field.type != "many2one":
        return None, "last_not_many2one:" + last
    sql = (
        "SELECT " + alias + "." + last + ", COUNT(*) FROM " + table + " t0 "
        + " ".join(joins) + " GROUP BY 1"
    )
    return sql, None


declared = own.probe_models()
registrations = prov.onboarded_registrations(env).sudo()
registered = sorted(registrations.company_id.ids)
registered_purposes = sorted({row.data_purpose for row in registrations if row.data_purpose})
registered_set = set(registered)

def measure_unset(Model, anchor):
    """Decompose the declared ownership anchor into the sets the rules bound.

    ``(anchor, '=', False)`` is *not* the unset-owner measurement when the anchor
    is a dotted path: Odoo translates that leaf into a predicate on the joined
    segment, so a row whose head relation is empty is silently excluded even
    though the installed ceiling rule carries an explicit ``(head, '=', False)``
    branch beside the joined-owner branch. Measure both parts, in the record
    rules' own universe (``active_test=False``), and keep the plain dotted
    predicate as a recorded translation fact rather than as the operative
    number. The active-universe subtotal is carried beside it so an archived row
    is never mistaken for a live visibility loss.
    """
    parts = anchor.split(".")
    head = parts[0]
    any_state = Model.sudo().with_context(active_test=False)
    live_state = Model.sudo()
    head_missing = any_state.search_count([(head, "=", False)])
    head_missing_live = live_state.search_count([(head, "=", False)])
    if len(parts) == 1:
        tail_null = 0
        tail_null_live = 0
        dotted_predicate = head_missing
    else:
        tail_null = any_state.search_count([(head, "!=", False), (anchor, "=", False)])
        tail_null_live = live_state.search_count([(head, "!=", False), (anchor, "=", False)])
        dotted_predicate = any_state.search_count([(anchor, "=", False)])
    return {
        "head_field": head,
        "dotted": len(parts) > 1,
        "head_missing_any_state": head_missing,
        "head_missing_active": head_missing_live,
        "tail_null_any_state": tail_null,
        "tail_null_active": tail_null_live,
        "dotted_predicate_any_state": dotted_predicate,
        "unset_any_state": head_missing + tail_null,
        "unset_active": head_missing_live + tail_null_live,
    }


unmapped = []
errors = {}
unset_rows_sql = {}
unset_rows = {}
unset_rows_active = {}
anchor_decomposition = {}
unregistered_rows = {}
scanned = 0

env.cr.execute("SET LOCAL statement_timeout = '25000'")
for model_name in declared:
    if model_name not in env:
        errors[model_name] = "model_absent"
        continue
    anchor = ANCHORS.get(model_name)
    if not anchor:
        unmapped.append(model_name)
        continue
    try:
        measured = measure_unset(env[model_name], anchor)
    except Exception as exc:
        errors[model_name] = "orm_count_failed:" + type(exc).__name__
        continue
    anchor_decomposition[model_name] = measured
    if measured["unset_any_state"]:
        unset_rows[model_name] = measured["unset_any_state"]
    if measured["unset_active"]:
        unset_rows_active[model_name] = measured["unset_active"]
    sql, why = build_sql(model_name, anchor)
    if sql is None:
        errors[model_name] = why
        continue
    try:
        env.cr.execute(sql)
        rows = env.cr.fetchall()
    except Exception as exc:
        env.cr.rollback()
        errors[model_name] = "query_failed:" + str(exc)[:120]
        continue
    scanned += 1
    for owner_id, count in rows:
        if not count:
            continue
        if owner_id is None or owner_id is False:
            unset_rows_sql[model_name] = unset_rows_sql.get(model_name, 0) + count
            continue
        if owner_id not in registered_set:
            entry = unregistered_rows.setdefault(str(owner_id), {})
            entry[model_name] = entry.get(model_name, 0) + count

installed_rules = {}
if INTEREST:
    rules = env["ir.rule"].sudo().search([("model_id.model", "in", INTEREST)])
    for row in rules.read(["name", "global", "domain_force", "active", "model_id"]):
        model_name = env["ir.model"].sudo().browse(row["model_id"][0]).model
        installed_rules.setdefault(model_name, []).append({
            "name": row["name"],
            "is_global": bool(row.get("global")),
            "domain": row["domain_force"],
            "active": bool(row["active"]),
        })

modules = {}
for row in env["ir.module.module"].sudo().search([("name", "=", "smart_construction_core")]).read(
    ["state", "installed_version", "latest_version"]
):
    modules["smart_construction_core"] = {
        "state": row["state"],
        "installed_version": row["installed_version"],
        "latest_version": row["latest_version"],
    }

# Declared semantics are a statement about an ordinary principal, so the verdict
# may not be inferred from rule text. Choose the most privileged *ordinary*
# internal users (largest group closure, deterministic id tie-break) and measure
# how many unset-owner rows each of them can actually read. Only counts are
# collected: no business field value, name or amount is read anywhere.
excluded = {1}
for xmlid in ("base.user_root", "base.user_admin"):
    reference = env.ref(xmlid, raise_if_not_found=False)
    if reference:
        excluded.add(reference.id)
candidates = env["res.users"].sudo().search(
    [("active", "=", True), ("share", "=", False)], limit=400
)
ranked = sorted(
    (row for row in candidates if row.id not in excluded),
    key=lambda row: (-len(row.groups_id), row.id),
)
principals = [row.id for row in ranked[:3]]
principal_groups = {str(row.id): len(row.groups_id) for row in ranked[:3]}

unset_visible = {}
for model_name in sorted(set(unset_rows) | set(unset_rows_sql)):
    if model_name not in env:
        continue
    anchor = ANCHORS.get(model_name)
    if not anchor:
        continue
    Entry = env[model_name]
    head = anchor.split(".")[0]
    dotted = "." in anchor
    visible = {}
    visible_live = {}
    principal_errors = {}
    domains = {}
    domains_errors = {}
    for uid in principals:
        # Measure the same two-part set the ceiling rule itself bounds. A single
        # ``(anchor, '=', False)`` leaf would under-count every dotted anchor and
        # turn a rule effect into an apparent exemption.
        try:
            readable = Entry.with_user(uid).with_context(active_test=False)
            total = readable.search_count([(head, "=", False)])
            if dotted:
                total += readable.search_count([(head, "!=", False), (anchor, "=", False)])
            visible[str(uid)] = total
            live = Entry.with_user(uid)
            total_live = live.search_count([(head, "=", False)])
            if dotted:
                total_live += live.search_count([(head, "!=", False), (anchor, "=", False)])
            visible_live[str(uid)] = total_live
        except Exception as exc:
            principal_errors[str(uid)] = type(exc).__name__
        try:
            domains[str(uid)] = env["ir.rule"].with_user(uid)._compute_domain(
                model_name, "read"
            )
        except Exception as exc:
            domains_errors[str(uid)] = type(exc).__name__
    unset_visible[model_name] = {
        "unset_rows": unset_rows.get(model_name, 0),
        "unset_rows_active": unset_rows_active.get(model_name, 0),
        "unset_rows_sql": unset_rows_sql.get(model_name, 0),
        "anchor_decomposition": anchor_decomposition.get(model_name) or {},
        "visible_by_principal": visible,
        "visible_by_principal_active": visible_live,
        "errors_by_principal": principal_errors,
        "effective_read_domain": domains,
        "effective_read_domain_errors": domains_errors,
    }

payload = {
    "database": env.cr.dbname,
    "declared_models": len(declared),
    "scanned_models": scanned,
    "unmapped_anchor_models": unmapped,
    "errors": errors,
    "registered_company_ids": registered,
    "registered_purposes": registered_purposes,
    "unset_owner_rows": unset_rows,
    "unset_owner_rows_active": unset_rows_active,
    "unset_owner_rows_sql": unset_rows_sql,
    "anchor_decomposition": anchor_decomposition,
    "unregistered_owner_rows": unregistered_rows,
    "installed_rules": installed_rules,
    "modules": modules,
    "principals": principals,
    "principal_group_counts": principal_groups,
    "unset_owner_visible": unset_visible,
    "writes": False,
}
print(MARKER + json.dumps(payload, ensure_ascii=False, sort_keys=True))
'''


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


def remote_shell(ssh_host, binding, *, stdin_path):
    """Read the carrier through the *bound duty's own* application container.

    The probe is read-only, but reading the wrong cluster is still a wrong
    answer: the deployed checkout's ``make ... DB_NAME=x odoo.shell.exec``
    resolves its target from a bare database name, and the rebuilt demo duty and
    the preserved pre-governance source both answer to ``sc_demo``.
    """
    return ssh(ssh_host, duty_identity.odoo_shell_command(binding, program_path=stdin_path))


def decode(result):
    return (result.stdout + result.stderr).decode(errors="replace").strip()


def marker_payload(text):
    for line in text.splitlines():
        if line.startswith(MARKER):
            try:
                return json.loads(line[len(MARKER):])
            except json.JSONDecodeError as error:
                raise ProbeError(f"unreadable readback payload: {error}") from error
    return None


def declarations():
    try:
        return json.loads(DECLARATIONS.read_text(encoding="utf-8"))
    except Exception as error:
        raise ProbeError(f"unreadable declaration: {error}") from error


def anchor_map(declaration):
    anchors = {}
    for entry in declaration.get("enforced") or []:
        anchors[entry["model"]] = entry["anchor"]
    for group in declaration.get("deferred") or []:
        for model in group.get("models") or []:
            anchors.setdefault(model, group["anchor"])
    for entry in declaration.get("source_bounded") or []:
        anchors.setdefault(entry["model"], entry["anchor"])
    return anchors


def _rule_domains(path):
    if not path.is_file():
        return {}
    try:
        root = ElementTree.parse(path).getroot()
    except ElementTree.ParseError as error:
        raise ProbeError(f"unreadable rule source {path.name}: {error}") from error
    domains = {}
    for record in root.iter("record"):
        if record.get("model") != "ir.rule":
            continue
        record_id = record.get("id")
        model_ref = None
        domain = None
        for field in record.findall("field"):
            if field.get("name") == "model_id":
                model_ref = field.get("ref")
            elif field.get("name") == "domain_force":
                domain = field.text or ""
        if record_id and domain is not None:
            domains[record_id] = {"model_ref": model_ref, "domain": domain}
    return domains


def expected_semantics(declaration):
    """Declared unset-owner semantics per model, read from this checkout."""
    ceiling = _rule_domains(CEILING_XML)
    handwritten = _rule_domains(HANDWRITTEN_XML)
    expected = {}
    for entry in declaration.get("enforced") or []:
        model = entry["model"]
        strict = entry.get("unsetOwner") == "unknown"
        expected[model] = {
            "strict": strict,
            "source": CEILING_XML.name,
            "basis": "unsetOwner=" + str(entry.get("unsetOwner") or "shared"),
        }
    for group in declaration.get("deferred") or []:
        for model in group.get("models") or []:
            expected.setdefault(model, {
                "strict": group.get("unsetOwner") == "unknown",
                "source": CEILING_XML.name,
                "basis": "unsetOwner=" + str(group.get("unsetOwner") or "shared"),
            })
    for entry in declaration.get("source_bounded") or []:
        model = entry["model"]
        rule_id = entry.get("rule")
        record = handwritten.get(rule_id) if rule_id else None
        if record is None:
            expected[model] = {
                "strict": None, "source": HANDWRITTEN_XML.name,
                "basis": f"named rule {rule_id!r} not found",
            }
            continue
        expected[model] = {
            "strict": "False" not in record["domain"],
            "source": HANDWRITTEN_XML.name,
            "basis": f"named rule {rule_id} domain",
        }
    return expected


def probe(expected_sha, binding, ssh_host):
    database = str(binding["database"])
    if not FULL_SHA.fullmatch(expected_sha or ""):
        raise ProbeError("expected SHA must be a full lowercase commit identity")
    if not DATABASE_NAME.fullmatch(database or ""):
        raise ProbeError("database must be a plain database name")
    if not SSH_HOST.fullmatch(ssh_host or ""):
        raise ProbeError("SSH host must be a configured host alias")
    if not (ROOT / ".git").exists():
        raise ProbeError("must run from the governed repository")

    declaration = declarations()
    anchors = anchor_map(declaration)
    expected = expected_semantics(declaration)

    head = ssh(ssh_host, f"cd {shlex.quote(REMOTE_ROOT)} && git rev-parse HEAD")
    if head.returncode:
        raise ProbeError(f"remote revision read failed: {decode(head)[:400]}")
    remote_head = head.stdout.decode().strip()
    if remote_head != expected_sha:
        raise ProbeError(f"remote HEAD {remote_head or '<unknown>'} != expected {expected_sha}")

    interest = sorted(expected)
    program = (
        PROBE_TEMPLATE
        .replace("__ANCHORS__", json.dumps(anchors, ensure_ascii=False, sort_keys=True))
        .replace("__INTEREST__", json.dumps(interest, ensure_ascii=False))
    ).encode("utf-8")

    upload = ssh(ssh_host, f"cat > {shlex.quote(REMOTE_TMP)}", input_bytes=program)
    if upload.returncode:
        raise ProbeError(f"remote program upload failed: {decode(upload)[:400]}")
    executed = remote_shell(ssh_host, binding, stdin_path=REMOTE_TMP)
    ssh(ssh_host, f"rm -f {shlex.quote(REMOTE_TMP)}")
    output = decode(executed)
    payload = marker_payload(output)
    if payload is None:
        raise ProbeError(f"no readback payload in the odoo-shell output: {output[-800:]}")
    landed = str(payload.get("database") or "")
    if landed != database:
        raise ProbeError(
            f"the probe ran in database {landed or '<unknown>'}, not the bound {database}"
        )
    return expected, payload, remote_head


def evaluate(expected, payload):
    installed = payload.get("installed_rules") or {}
    unset_rows = payload.get("unset_owner_rows") or {}
    assertions = []

    scanned = payload.get("scanned_models")
    declared = payload.get("declared_models")
    assertions.append({
        "id": "scan_covers_every_declared_model",
        "passed": bool(declared) and scanned == declared,
        "detail": f"scanned={scanned} declared={declared}",
    })
    assertions.append({
        "id": "every_declared_model_has_an_anchor",
        "passed": not payload.get("unmapped_anchor_models"),
        "detail": f"unmapped={payload.get('unmapped_anchor_models')}",
    })
    assertions.append({
        "id": "no_scan_query_failed",
        "passed": not payload.get("errors"),
        "detail": f"errors={payload.get('errors')}",
    })
    assertions.append({
        "id": "registered_data_space_present",
        "passed": bool(payload.get("registered_company_ids")),
        "detail": f"registered={payload.get('registered_company_ids')}",
    })
    assertions.append({
        "id": "no_unregistered_company_owns_rows",
        "passed": not payload.get("unregistered_owner_rows"),
        "detail": f"unregistered_owners={sorted((payload.get('unregistered_owner_rows') or {}).keys())}",
    })

    missing = []
    for model in sorted(unset_rows):
        if not [row for row in installed.get(model) or [] if row.get("active")]:
            missing.append(model)
    assertions.append({
        "id": "every_unset_owner_model_has_an_active_rule",
        "passed": not missing,
        "detail": missing,
    })

    # Rule text is not the verdict: the same model can carry a global rule that
    # ANDs an owner requirement with group rules that OR a group scope. Measure
    # what the most privileged ordinary internal users can actually read.
    measured = payload.get("unset_owner_visible") or {}
    mismatched = []
    for model in sorted(unset_rows):
        want = expected.get(model)
        if want is None or want.get("strict") is None:
            continue
        observed = measured.get(model) or {}
        counts = list((observed.get("visible_by_principal") or {}).values())
        if not counts:
            mismatched.append({
                "model": model, "declared": want,
                "effective": "not_measured",
                "errors": observed.get("errors_by_principal"),
            })
            continue
        peak = max(counts)
        if (peak == 0) != bool(want["strict"]):
            mismatched.append({
                "model": model, "declared": want, "effective_visible_rows": peak,
                "unset_rows": unset_rows[model],
            })
    assertions.append({
        "id": "effective_visibility_matches_declared_semantics",
        "passed": not mismatched,
        "detail": mismatched,
    })

    # The decomposition and the raw join must describe the same rows. A
    # difference means the declared anchor does not actually identify the
    # attribution the probe scans (a dangling relation, a fan-out join, or a
    # segment that is not a many2one), so the count may not be read as a rule
    # effect.
    decomposition = payload.get("anchor_decomposition") or {}
    sql_rows = payload.get("unset_owner_rows_sql") or {}
    unreconciled = []
    for model in sorted(set(decomposition) | set(sql_rows)):
        counted = (decomposition.get(model) or {}).get("unset_any_state", 0)
        if counted != sql_rows.get(model, 0):
            unreconciled.append({
                "model": model, "anchor_decomposition": counted,
                "raw_join": sql_rows.get(model, 0),
            })
    assertions.append({
        "id": "anchor_decomposition_reconciles_with_the_raw_scan",
        "passed": not unreconciled,
        "detail": unreconciled,
    })

    # Odoo translates ``(dotted_anchor, '=', False)`` into a predicate on the
    # joined segment, so the plain dotted leaf can never be the operative
    # unset-owner measurement. Record that translation as a checked fact instead
    # of leaving it implicit: if a future engine or field change makes the two
    # agree, the probe must say so rather than silently changing the口径.
    translation = []
    for model in sorted(decomposition):
        entry = decomposition[model]
        expected_leaf = (
            entry.get("tail_null_any_state") if entry.get("dotted")
            else entry.get("head_missing_any_state")
        )
        if entry.get("dotted_predicate_any_state") != expected_leaf:
            translation.append({
                "model": model,
                "dotted_predicate_any_state": entry.get("dotted_predicate_any_state"),
                "expected_leaf_translation": expected_leaf,
            })
    assertions.append({
        "id": "declared_anchor_translation_recorded",
        "passed": not translation,
        "detail": translation,
    })

    modules = payload.get("modules") or {}
    shipping = modules.get(SHIPPING_MODULE) or {}
    aligned = bool(shipping) and (
        shipping.get("state") == "installed"
        and shipping.get("installed_version") == shipping.get("latest_version")
    )
    assertions.append({
        "id": "shipping_module_version_aligned",
        "passed": aligned,
        "detail": shipping or "module record not found",
    })

    visibility_loss = {}
    shared_visible = {}
    unmeasured = {}
    archived_hidden = {}
    for model, count in sorted(unset_rows.items()):
        want = expected.get(model) or {}
        counts = list(((measured.get(model) or {}).get("visible_by_principal") or {}).values())
        if counts:
            hidden = max(counts) == 0
        elif want.get("strict") is None:
            # No declaration and no measurement: report the rows as unresolved
            # rather than silently labelling them hidden or shared.
            hidden = True
            unmeasured[model] = count
        else:
            hidden = bool(want["strict"])
            unmeasured[model] = count
        target = visibility_loss if hidden else shared_visible
        target[model] = count
        live = (payload.get("unset_owner_rows_active") or {}).get(model, 0)
        if hidden and count and not live:
            archived_hidden[model] = count
    return {
        "assertions": assertions,
        "passed": all(row["passed"] for row in assertions),
        "unset_owner_total": sum(unset_rows.values()),
        "unset_owner_total_active_universe": sum(
            (payload.get("unset_owner_rows_active") or {}).values()
        ),
        "visibility_loss_rows": {"total": sum(visibility_loss.values()), "by_model": visibility_loss},
        "shared_visible_rows": {"total": sum(shared_visible.values()), "by_model": shared_visible},
        "rows_not_measured_against_a_principal": {
            "total": sum(unmeasured.values()), "by_model": unmeasured,
        },
        "visibility_loss_that_is_archived_only": {
            "total": sum(archived_hidden.values()), "by_model": archived_hidden,
        },
    }




def bind_target(options, *, instances_reader=None) -> dict:
    """Bind the target duty, its cluster, its database and its storage, or stop.

    Ownership is a property of one carrier's rows; probing another carrier's database would answer a different question.
    """
    try:
        reader = instances_reader
        if reader is None:
            reader = duty_identity.ssh_instances_reader(options.ssh_host)
        return duty_identity.bind_duty_database(
            getattr(options, "duty", ""), options.database, instances_reader=reader,
        )
    except duty_identity.DutyIdentityError as error:
        raise ProbeError(str(error))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--database", default=DEFAULT_DATABASE)
    parser.add_argument("--duty", default="", help="the declared duty this entry binds; a database name alone is not a target identity")
    parser.add_argument("--ssh-host", required=True)
    parser.add_argument("--report", required=True)
    options = parser.parse_args()

    try:
        binding = bind_target(options)
        expected, payload, remote_head = probe(
            options.expected_sha, binding, options.ssh_host,
        )
        verdict = evaluate(expected, payload)
    except ProbeError as error:
        print(f"[daily.runtime.data_ownership.probe] BLOCKED {error}", file=sys.stderr)
        return 2

    report = {
        "schema": "daily.runtime.data_ownership.probe.v1",
        "expected_sha": options.expected_sha,
        "remote_head": remote_head,
        "database": binding["database"],
        "ssh_host": options.ssh_host,
        "database_binding": binding,
        "writes": False,
        "provenance": {
            "live_account_query": [
                "registered_company_ids", "registered_purposes", "installed_rules",
                "modules", "unset_owner_rows", "unregistered_owner_rows",
                "scanned_models", "errors", "principals",
                "principal_group_counts", "unset_owner_visible",
            ],
            "repository_source": [
                "declared_models", "declared_anchors", "declared_unset_semantics",
            ],
            "read_scope": "aggregate counts and rule metadata only; no business field value, name or amount is read",
        },
        "declared_unset_semantics": {
            model: expected[model] for model in sorted(expected)
        },
        "observation": payload,
        "verdict": verdict,
        "status": "PASS" if verdict["passed"] else "FAIL",
    }
    report_path = Path(options.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "schema": report["schema"], "status": report["status"],
        "expected_sha": report["expected_sha"], "remote_head": report["remote_head"],
        "database": report["database"], "report": str(report_path),
        "unset_owner_total": verdict["unset_owner_total"],
        "visibility_loss_rows": verdict["visibility_loss_rows"],
        "shared_visible_rows": verdict["shared_visible_rows"],
        "rows_not_measured_against_a_principal": verdict["rows_not_measured_against_a_principal"],
        "principals": payload.get("principals"),
        "failed_assertions": [r["id"] for r in verdict["assertions"] if not r["passed"]],
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if verdict["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
