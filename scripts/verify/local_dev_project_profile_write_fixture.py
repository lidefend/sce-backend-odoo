# -*- coding: utf-8 -*-
"""Governed, disposable project-profile write fixture for local.dev.

This is a P4 verification carrier, not product data and not an acceptance
fixture.  It is intentionally strict about database identity, batch ownership
and cleanup scope.
"""

from __future__ import annotations

import json
import os
import re
from typing import Dict, Iterable, List


EXPECTED_DB = "sc_dev_demo"
EXPECTED_ENV = "dev"
MODULE = "codex_p4_project_profile_write"
def _text(value: object) -> str:
    return str(value or "").strip()


def _batch() -> str:
    value = _text(os.environ.get("P4_PROJECT_PROFILE_BATCH"))
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,31}", value):
        raise RuntimeError("P4_PROJECT_PROFILE_BATCH must be 3-32 lowercase alnum/dash characters")
    return value


def _guard(env):
    if env.cr.dbname != EXPECTED_DB:
        raise RuntimeError("project profile fixture requires database sc_dev_demo")
    if _text(os.environ.get("SC_ENVIRONMENT")) != EXPECTED_ENV:
        raise RuntimeError("project profile fixture requires SC_ENVIRONMENT=dev")
    if _text(os.environ.get("ODOO_DBFILTER")) != "^sc_dev_demo$":
        raise RuntimeError("project profile fixture requires exact sc_dev_demo dbfilter")
    sha = _text(os.environ.get("CANDIDATE_GIT_HEAD"))
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise RuntimeError("CANDIDATE_GIT_HEAD must be a full 40-character SHA")
    if _text(os.environ.get("P4_PROJECT_PROFILE_CONFIRM")) not in {"INSPECT", "PREPARE", "DRY_RUN", "CLEANUP"}:
        raise RuntimeError("P4_PROJECT_PROFILE_CONFIRM must be INSPECT, DRY_RUN, PREPARE or CLEANUP")
    return sha, _batch()


def _xmlid(env, name):
    return env.ref("%s.%s" % (MODULE, name), raise_if_not_found=False)


def _bind(env, name, record):
    model = env["ir.model.data"].sudo()
    row = model.search([("module", "=", MODULE), ("name", "=", name)], limit=1)
    values = {"model": record._name, "res_id": record.id, "noupdate": True}
    if row:
        if row.model != record._name or row.res_id != record.id:
            raise RuntimeError("fixture XMLID ownership conflict: %s.%s" % (MODULE, name))
        return
    model.create({"module": MODULE, "name": name, **values})


def _role_candidates(env):
    User = env["res.users"].sudo().with_context(active_test=True)
    groups = {
        "project_manager": "smart_construction_core.group_sc_role_project_manager",
        "project_user": "smart_construction_core.group_sc_cap_business_initiator",
        "project_read_only": "smart_construction_core.group_sc_cap_project_read",
    }
    out = {}
    for role, xmlid in groups.items():
        group = env.ref(xmlid, raise_if_not_found=False)
        if not group:
            out[role] = []
            continue
        rows = User.search([("share", "=", False)], order="id")
        selected = [
            {
                "id": user.id,
                "login": user.login,
                "name": user.name,
                "company_id": user.company_id.id,
                "company": user.company_id.name,
            }
            for user in rows
            if group in user.groups_id
        ]
        if role == "project_read_only":
            manager_group = env.ref(groups["project_manager"], raise_if_not_found=False)
            initiator_group = env.ref(groups["project_user"], raise_if_not_found=False)
            selected = [
                row for row in selected
                if not any(
                    user.id == row["id"]
                    and ((manager_group and manager_group in user.groups_id)
                         or (initiator_group and initiator_group in user.groups_id))
                    for user in rows
                )
            ]
        out[role] = selected
    return out


def _project_identity(batch):
    suffix = batch.replace("-", "_")
    return {
        "xmlid": "project_%s" % suffix,
        "responsibility_xmlids": ["responsibility_%s_manager" % suffix, "responsibility_%s_cost" % suffix],
        "name": "Codex P4 项目资料写入验收 %s" % batch,
        "code": "CODEX-P4-%s" % batch.upper(),
    }


def _owned_project(env, identity):
    project = _xmlid(env, identity["xmlid"])
    if not project:
        return None
    if project._name != "project.project":
        raise RuntimeError("fixture project XMLID is not owned by this batch")
    marker = getattr(project, "project_code", False)
    if project.code != identity["code"] and marker != identity["code"] and project.name != identity["name"]:
        raise RuntimeError("fixture project XMLID is not owned by this batch")
    return project.sudo()


def _external_references(env, project_id) -> List[Dict[str, object]]:
    refs = []
    fields = env["ir.model.fields"].sudo().search([
        ("ttype", "=", "many2one"), ("relation", "=", "project.project"),
    ])
    for field in fields:
        if field.model == "project.responsibility":
            continue
        try:
            model = env[field.model]
        except KeyError:
            model = None
        if not model or field.name not in model._fields:
            continue
        count = model.sudo().search_count([(field.name, "=", project_id)])
        if count:
            refs.append({"model": field.model, "field": field.name, "count": count})
    return refs


def _summary(env, sha, batch, mode, project=None):
    identity = _project_identity(batch)
    candidates = _role_candidates(env)
    return {
        "mode": mode,
        "database": env.cr.dbname,
        "environment": os.environ.get("SC_ENVIRONMENT"),
        "dbfilter": os.environ.get("ODOO_DBFILTER"),
        "candidate_sha": sha,
        "batch": batch,
        "namespace": MODULE,
        "project": {
            "xmlid": "%s.%s" % (MODULE, identity["xmlid"]),
            "id": project.id if project else None,
            "name": project.name if project else identity["name"],
            "code": project.code if project else identity["code"],
            "responsibility_ids": project.responsibility_ids.ids if project else [],
        },
        "role_candidates": candidates,
        "write_scope": ["name", "date_start", "date", "description", "responsibility_ids"],
        "recovery": "cleanup verifies XMLID/code ownership, scans external many2one references, removes only this project and its responsibility rows",
    }


def inspect(env, sha, batch, mode):
    identity = _project_identity(batch)
    project = _owned_project(env, identity)
    summary = _summary(env, sha, batch, mode, project)
    summary["existing_batch"] = bool(project)
    if project:
        summary["external_references"] = _external_references(env, project.id)
    return summary


def prepare(env, sha, batch, mode):
    identity = _project_identity(batch)
    existing = _owned_project(env, identity)
    if existing:
        raise RuntimeError("batch already exists; inspect or cleanup it before prepare")
    candidates = _role_candidates(env)
    pm = candidates["project_manager"][0] if candidates["project_manager"] else None
    user = candidates["project_user"][0] if candidates["project_user"] else None
    if not pm or not user:
        raise RuntimeError("prepare requires existing project_manager and project_user candidates; no users are created")
    Project = env["project.project"].sudo()
    project = Project.create({
        "name": identity["name"],
        "code": identity["code"],
        "company_id": pm["company_id"],
        "user_id": user["id"],
        "manager_id": pm["id"],
        "privacy_visibility": "followers",
        "active": True,
    })
    # Odoo may replace the native sequence ``code`` during create.  Preserve a
    # deterministic batch marker in the optional product field when available;
    # XMLID ownership remains the primary cleanup boundary.
    if "project_code" in Project._fields and project.project_code != identity["code"]:
        project.write({"project_code": identity["code"]})
    if project.code != identity["code"] and "project_code" not in Project._fields:
        project.write({"code": identity["code"]})
    _bind(env, identity["xmlid"], project)
    Responsibility = env["project.responsibility"].sudo()
    for xmlid, role_key, user_id, note in [
        (identity["responsibility_xmlids"][0], "manager", pm["id"], "P4 batch baseline"),
        (identity["responsibility_xmlids"][1], "cost", user["id"], "P4 batch baseline"),
    ]:
        row = Responsibility.create({"project_id": project.id, "role_key": role_key, "user_id": user_id, "note": note})
        _bind(env, xmlid, row)
    project.message_subscribe(partner_ids=[env["res.users"].sudo().browse(user["id"]).partner_id.id])
    project.message_subscribe(partner_ids=[env["res.users"].sudo().browse(pm["id"]).partner_id.id])
    env.cr.commit()
    return _summary(env, sha, batch, mode, project)


def cleanup(env, sha, batch, mode):
    identity = _project_identity(batch)
    project = _owned_project(env, identity)
    if not project:
        return {"mode": mode, "database": env.cr.dbname, "candidate_sha": sha, "batch": batch, "clean": True, "deleted": False}
    refs = _external_references(env, project.id)
    if refs:
        raise RuntimeError("cleanup stopped: external project references exist: %s" % json.dumps(refs, ensure_ascii=False))
    responsibility_ids = set(project.responsibility_ids.ids)
    env["project.responsibility"].sudo().browse(list(responsibility_ids)).unlink()
    project.sudo().unlink()
    leftovers = _owned_project(env, identity)
    if leftovers:
        raise RuntimeError("cleanup failed: owned project still exists")
    env.cr.commit()
    return {"mode": mode, "database": env.cr.dbname, "candidate_sha": sha, "batch": batch, "clean": True, "deleted": True, "deleted_responsibility_ids": sorted(responsibility_ids)}


sha, batch = _guard(env)
mode = _text(os.environ.get("P4_PROJECT_PROFILE_MODE"))
if mode == "inspect":
    result = inspect(env, sha, batch, mode)
elif mode == "dry-run":
    result = inspect(env, sha, batch, mode)
    result["would_prepare"] = not result.get("existing_batch")
    result["would_cleanup"] = bool(result.get("existing_batch"))
elif mode == "prepare":
    result = prepare(env, sha, batch, mode)
elif mode == "cleanup":
    result = cleanup(env, sha, batch, mode)
else:
    raise RuntimeError("P4_PROJECT_PROFILE_MODE must be inspect, dry-run, prepare or cleanup")
print("LOCAL_DEV_PROJECT_PROFILE_WRITE_FIXTURE_JSON=" + json.dumps(result, ensure_ascii=False, sort_keys=True))
