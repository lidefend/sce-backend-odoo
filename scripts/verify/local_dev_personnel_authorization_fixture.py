# -*- coding: utf-8 -*-
"""Governed personnel-authorization write fixture for local.dev.

The fixture owns one non-login test person and one test project.  Cleanup is an
auditable retirement: assignments, the person and the project are deactivated.
No protected authorization history is physically deleted.
"""

from __future__ import annotations

import json
import os
import re
import secrets


EXPECTED_DB = "sc_dev_demo"
EXPECTED_ENV = "dev"
EXPECTED_DBFILTER = "^sc_dev_demo$"
MODULE = "codex_p4_personnel_authorization"
OPERATOR_XMLID = "smart_construction_demo.sc_demo_user_test_admin"
PERSONNEL_MENU_XMLID = "smart_construction_core.menu_sc_runtime_user_management"
PERSONNEL_ACTION_XMLID = "smart_construction_core.action_sc_runtime_user_management"
PERMISSION_MENU_XMLID = "smart_construction_core.menu_sc_product_data_permission_v1"
PERMISSION_ACTION_XMLID = "smart_construction_core.action_sc_product_data_permission_v1"


def _text(value):
    return str(value or "").strip()


def _batch():
    value = _text(os.environ.get("P4_PERSONNEL_AUTH_BATCH"))
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,31}", value):
        raise RuntimeError("P4_PERSONNEL_AUTH_BATCH must be 3-32 lowercase alnum/dash characters")
    return value


def _guard(env):
    if env.cr.dbname != EXPECTED_DB:
        raise RuntimeError("personnel authorization fixture requires database sc_dev_demo")
    if _text(os.environ.get("SC_ENVIRONMENT")) != EXPECTED_ENV:
        raise RuntimeError("personnel authorization fixture requires SC_ENVIRONMENT=dev")
    if _text(os.environ.get("ODOO_DBFILTER")) != EXPECTED_DBFILTER:
        raise RuntimeError("personnel authorization fixture requires exact sc_dev_demo dbfilter")
    sha = _text(os.environ.get("CANDIDATE_GIT_HEAD"))
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise RuntimeError("CANDIDATE_GIT_HEAD must be a full 40-character SHA")
    if _text(os.environ.get("P4_PERSONNEL_AUTH_CONFIRM")) not in {
        "INSPECT", "DRY_RUN", "PREPARE", "RETIRE",
    }:
        raise RuntimeError("P4_PERSONNEL_AUTH_CONFIRM must be INSPECT, DRY_RUN, PREPARE or RETIRE")
    return sha, _batch()


def _identity(batch):
    suffix = batch.replace("-", "_")
    return {
        "person_xmlid": "person_%s" % suffix,
        "project_xmlid": "project_%s" % suffix,
        "assignment_xmlid": "assignment_%s" % suffix,
        "login": "codex_p4_person_%s" % suffix,
        "person_name": "Codex P4 人员授权验收 %s" % batch,
        "project_name": "Codex P4 人员授权项目 %s" % batch,
        "project_code": "CODEX-P4-PA-%s" % batch.upper(),
    }


def _xmlid(env, name):
    return env.ref("%s.%s" % (MODULE, name), raise_if_not_found=False)


def _bind(env, name, record):
    ModelData = env["ir.model.data"].sudo()
    row = ModelData.search([("module", "=", MODULE), ("name", "=", name)], limit=1)
    if row:
        if row.model != record._name or row.res_id != record.id:
            raise RuntimeError("fixture XMLID ownership conflict: %s.%s" % (MODULE, name))
        return
    ModelData.create({
        "module": MODULE,
        "name": name,
        "model": record._name,
        "res_id": record.id,
        "noupdate": True,
    })


def _operator(env):
    operator = env.ref(OPERATOR_XMLID, raise_if_not_found=False)
    if not operator or operator._name != "res.users" or not operator.active:
        raise RuntimeError("governed personnel authorization operator is missing or inactive")
    platform_admin = env.ref("smart_core.group_smart_core_admin", raise_if_not_found=False)
    industry_admin = env.ref("smart_construction_core.group_sc_super_admin", raise_if_not_found=False)
    if not platform_admin or not industry_admin:
        raise RuntimeError("governed personnel authorization operator groups are unavailable")
    if platform_admin not in operator.groups_id or industry_admin not in operator.groups_id:
        raise RuntimeError("governed personnel authorization operator no longer has the registered authority")
    return operator


def _owned_person(env, identity):
    person = _xmlid(env, identity["person_xmlid"])
    if not person:
        return None
    if person._name != "res.users" or person.login != identity["login"]:
        raise RuntimeError("fixture person XMLID is not owned by this batch")
    if not person.sc_runtime_user_managed or person.share:
        raise RuntimeError("fixture person is outside the managed internal-user boundary")
    return person.sudo().with_context(active_test=False)


def _owned_project(env, identity):
    project = _xmlid(env, identity["project_xmlid"])
    if not project:
        return None
    marker = getattr(project, "project_code", False) or project.code
    if project._name != "project.project" or marker != identity["project_code"]:
        raise RuntimeError("fixture project XMLID is not owned by this batch")
    return project.sudo().with_context(active_test=False)


def _assignments(env, identity, person, project):
    Assignment = env["sc.project.member.assignment"].sudo().with_context(active_test=False)
    if not person or not project:
        return Assignment.browse()
    owned = Assignment.search([("user_id", "=", person.id), ("project_id", "=", project.id)])
    outside = Assignment.search([("user_id", "=", person.id), ("project_id", "!=", project.id)])
    if outside:
        raise RuntimeError("fixture person has project assignments outside the owned batch")
    if len(owned) > 1:
        raise RuntimeError("fixture batch has duplicate project assignments")
    bound = _xmlid(env, identity["assignment_xmlid"])
    if bound and (bound._name != "sc.project.member.assignment" or bound not in owned):
        raise RuntimeError("fixture assignment XMLID is not owned by this batch")
    return owned


def _entry(env, menu_xmlid, action_xmlid):
    menu = env.ref(menu_xmlid, raise_if_not_found=False)
    action = env.ref(action_xmlid, raise_if_not_found=False)
    if not menu or not action:
        raise RuntimeError("personnel authorization formal entry is missing")
    return {
        "menu_id": menu.id,
        "menu_xmlid": menu_xmlid,
        "menu_name": menu.name,
        "action_id": action.id,
        "action_xmlid": action_xmlid,
        "action_name": action.name,
    }


def _summary(env, sha, batch, mode, person=None, project=None):
    identity = _identity(batch)
    operator = _operator(env)
    assignments = _assignments(env, identity, person, project)
    assignment = assignments[:1]
    if person and project and person.company_id != project.company_id:
        raise RuntimeError("fixture person and project company identity mismatch")
    dangerous_groups = env["res.groups"].browse()
    for xmlid in (
        "base.group_system",
        "smart_core.group_smart_core_admin",
        "smart_construction_core.group_sc_super_admin",
    ):
        group = env.ref(xmlid, raise_if_not_found=False)
        if group:
            dangerous_groups |= group
    if person and dangerous_groups & person.groups_id:
        raise RuntimeError("fixture person unexpectedly has administrator authority")
    return {
        "mode": mode,
        "database": env.cr.dbname,
        "environment": _text(os.environ.get("SC_ENVIRONMENT")),
        "dbfilter": _text(os.environ.get("ODOO_DBFILTER")),
        "candidate_sha": sha,
        "batch": batch,
        "namespace": MODULE,
        "existing_batch": bool(person or project),
        "complete_batch": bool(person and project),
        "operator": {
            "xmlid": OPERATOR_XMLID,
            "id": operator.id,
            "login": operator.login,
            "company_id": operator.company_id.id,
        },
        "person": {
            "xmlid": "%s.%s" % (MODULE, identity["person_xmlid"]),
            "id": person.id if person else None,
            "login": person.login if person else identity["login"],
            "name": person.name if person else identity["person_name"],
            "company_id": person.company_id.id if person else None,
            "active": bool(person.active) if person else None,
            "share": bool(person.share) if person else None,
            "managed": bool(person.sc_runtime_user_managed) if person else None,
            "administrator_group_ids": sorted((dangerous_groups & person.groups_id).ids) if person else [],
        },
        "project": {
            "xmlid": "%s.%s" % (MODULE, identity["project_xmlid"]),
            "id": project.id if project else None,
            "name": project.name if project else identity["project_name"],
            "code": (getattr(project, "project_code", False) or project.code) if project else identity["project_code"],
            "company_id": project.company_id.id if project else None,
            "active": bool(project.active) if project else None,
        },
        "assignment": {
            "xmlid": "%s.%s" % (MODULE, identity["assignment_xmlid"]),
            "id": assignment.id if assignment else None,
            "user_id": assignment.user_id.id if assignment else None,
            "project_id": assignment.project_id.id if assignment else None,
            "company_id": assignment.company_id.id if assignment else None,
            "source": assignment.source if assignment else None,
            "note": assignment.note if assignment else None,
            "active": bool(assignment.active) if assignment else None,
            "follower_owned": bool(assignment.sc_follower_owned) if assignment else None,
            "person_is_follower": bool(assignment and assignment.user_id.partner_id in project.message_partner_ids),
        },
        "entries": {
            "personnel": _entry(env, PERSONNEL_MENU_XMLID, PERSONNEL_ACTION_XMLID),
            "data_permission": _entry(env, PERMISSION_MENU_XMLID, PERMISSION_ACTION_XMLID),
        },
        "write_scope": ["sc_project_member_assignment_ids.project_id", "active", "note"],
        "retirement_policy": "retain XMLIDs and audit rows; deactivate assignment, person and project; never unlink assignment history",
    }


def inspect(env, sha, batch, mode):
    identity = _identity(batch)
    person = _owned_person(env, identity)
    project = _owned_project(env, identity)
    if bool(person) != bool(project):
        raise RuntimeError("fixture batch is incomplete: person/project ownership mismatch")
    return _summary(env, sha, batch, mode, person, project)


def prepare(env, sha, batch, mode):
    identity = _identity(batch)
    if _owned_person(env, identity) or _owned_project(env, identity):
        raise RuntimeError("batch already exists; inspect or retire it before using another batch")
    operator = _operator(env)
    company = operator.company_id
    internal_group = env.ref("base.group_user")
    person = env["res.users"].sudo().with_context(no_reset_password=True).create({
        "login": identity["login"],
        "name": identity["person_name"],
        "password": secrets.token_urlsafe(32),
        "company_id": company.id,
        "company_ids": [(6, 0, company.ids)],
        "groups_id": [(6, 0, internal_group.ids)],
        "share": False,
        "active": True,
        "sc_runtime_user_managed": True,
    })
    project = env["project.project"].sudo().create({
        "name": identity["project_name"],
        "code": identity["project_code"],
        "company_id": company.id,
        "active": True,
        "privacy_visibility": "followers",
    })
    if "project_code" in project._fields and project.project_code != identity["project_code"]:
        project.write({"project_code": identity["project_code"]})
    if project.code != identity["project_code"] and "project_code" not in project._fields:
        project.write({"code": identity["project_code"]})
    _bind(env, identity["person_xmlid"], person)
    _bind(env, identity["project_xmlid"], project)
    if _assignments(env, identity, person, project):
        raise RuntimeError("prepare created an unexpected authorization assignment")
    env.cr.commit()
    return _summary(env, sha, batch, mode, person, project)


def retire(env, sha, batch, mode):
    identity = _identity(batch)
    person = _owned_person(env, identity)
    project = _owned_project(env, identity)
    if not person or not project:
        raise RuntimeError("retire requires a complete owned batch")
    assignments = _assignments(env, identity, person, project)
    if assignments:
        _bind(env, identity["assignment_xmlid"], assignments)
        assignments.with_user(_operator(env)).write({"active": False})
    project.with_user(_operator(env)).write({"active": False})
    person.with_user(_operator(env)).with_context(sc_runtime_user_management=True).write({"active": False})
    env.cr.commit()
    result = _summary(env, sha, batch, mode, person, project)
    assignment = result["assignment"]
    if result["person"]["active"] or result["project"]["active"]:
        raise RuntimeError("retire failed to deactivate the owned person/project")
    if assignment["id"] and (assignment["active"] or assignment["person_is_follower"]):
        raise RuntimeError("retire failed to deactivate authorization or release its owned follower")
    result["retired"] = True
    result["physical_delete_count"] = 0
    return result


sha, batch = _guard(env)
mode = _text(os.environ.get("P4_PERSONNEL_AUTH_MODE"))
if mode == "inspect":
    result = inspect(env, sha, batch, mode)
elif mode == "dry-run":
    result = inspect(env, sha, batch, mode)
    result["would_prepare"] = not result["existing_batch"]
    result["would_retire"] = bool(result["complete_batch"])
elif mode == "prepare":
    result = prepare(env, sha, batch, mode)
elif mode == "retire":
    result = retire(env, sha, batch, mode)
else:
    raise RuntimeError("P4_PERSONNEL_AUTH_MODE must be inspect, dry-run, prepare or retire")
print("LOCAL_DEV_PERSONNEL_AUTH_FIXTURE_JSON=" + json.dumps(result, ensure_ascii=False, sort_keys=True))
