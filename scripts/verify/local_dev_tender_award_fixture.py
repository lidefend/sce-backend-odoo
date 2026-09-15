# -*- coding: utf-8 -*-
"""Governed, disposable tender-award write fixture for local.dev.

This P4 carrier owns only one tender bid, one BOQ line and one opening record.
It reuses existing demo master data and never creates users, companies,
projects, partners, databases or runtime profiles.
"""

from __future__ import annotations

import json
import os
import re


EXPECTED_DB = "sc_dev_demo"
EXPECTED_ENV = "dev"
EXPECTED_DBFILTER = "^sc_dev_demo$"
MODULE = "codex_p4_tender_award"
WRITER_LOGIN = "demo_role_project_manager"
EXPECTED = {
    "bid_amount": 1200.0,
    "line_total": 1000.0,
    "award_amount": 900.0,
    "tax_basis": "unknown",
    "source_kind": "final_quote",
    "source_reference": "最终报价文件-CODEX-P4-001",
}


def _text(value):
    return str(value or "").strip()


def _batch():
    value = _text(os.environ.get("P4_TENDER_AWARD_BATCH"))
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,31}", value):
        raise RuntimeError(
            "P4_TENDER_AWARD_BATCH must be 3-32 lowercase alnum/dash characters"
        )
    return value


def _guard(env):
    if env.cr.dbname != EXPECTED_DB:
        raise RuntimeError("tender award fixture requires database sc_dev_demo")
    if _text(os.environ.get("SC_ENVIRONMENT")) != EXPECTED_ENV:
        raise RuntimeError("tender award fixture requires SC_ENVIRONMENT=dev")
    if _text(os.environ.get("ODOO_DBFILTER")) != EXPECTED_DBFILTER:
        raise RuntimeError("tender award fixture requires exact sc_dev_demo dbfilter")
    sha = _text(os.environ.get("CANDIDATE_GIT_HEAD"))
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise RuntimeError("CANDIDATE_GIT_HEAD must be a full 40-character SHA")
    if _text(os.environ.get("P4_TENDER_AWARD_CONFIRM")) not in {
        "INSPECT",
        "DRY_RUN",
        "PREPARE",
        "CLEANUP",
    }:
        raise RuntimeError(
            "P4_TENDER_AWARD_CONFIRM must be INSPECT, DRY_RUN, PREPARE or CLEANUP"
        )
    return sha, _batch()


def _suffix(batch):
    return batch.replace("-", "_")


def _names(batch):
    suffix = _suffix(batch)
    return {
        "bid": "bid_%s" % suffix,
        "line": "line_%s" % suffix,
        "opening": "opening_%s" % suffix,
        "marker": "CODEX-P4-AWARD-%s" % batch.upper(),
    }


def _xmlid(env, name):
    return env.ref("%s.%s" % (MODULE, name), raise_if_not_found=False)


def _bind(env, name, record):
    ModelData = env["ir.model.data"].sudo()
    row = ModelData.search([("module", "=", MODULE), ("name", "=", name)], limit=1)
    values = {"model": record._name, "res_id": record.id, "noupdate": True}
    if row:
        if row.model != record._name or row.res_id != record.id:
            raise RuntimeError("fixture XMLID ownership conflict: %s.%s" % (MODULE, name))
        return
    ModelData.create({"module": MODULE, "name": name, **values})


def _writer(env):
    user = env["res.users"].sudo().search(
        [("login", "=", WRITER_LOGIN), ("active", "=", True)], limit=1
    )
    if not user:
        raise RuntimeError("existing governed project-manager demo user is missing")
    group = env.ref(
        "smart_construction_core.group_sc_cap_project_manager",
        raise_if_not_found=False,
    )
    if not group or group not in user.groups_id:
        raise RuntimeError("governed writer is not a project manager")
    return user


def _master_data(env, user):
    scoped = env(user=user, context={**env.context, "allowed_company_ids": [user.company_id.id]})
    Project = scoped["project.project"]
    projects = Project.search([("company_id", "=", user.company_id.id)], order="id")
    project = next(
        (
            row
            for row in projects
            if row.check_access_rights("read", raise_exception=False)
            and row.check_access_rights("write", raise_exception=False)
        ),
        None,
    )
    if not project:
        raise RuntimeError("governed writer has no existing project in the active company")
    partner = project.owner_id or env["res.partner"].sudo().search(
        [("company_type", "=", "company")], order="id", limit=1
    )
    if not partner:
        raise RuntimeError("existing demo owner/counterparty is missing")
    return project.sudo(), partner.sudo()


def _owned(env, batch):
    names = _names(batch)
    bid = _xmlid(env, names["bid"])
    if not bid:
        return None, None, None
    if bid._name != "tender.bid" or bid.name != names["marker"]:
        raise RuntimeError("fixture bid XMLID is outside the owned batch")
    line = _xmlid(env, names["line"])
    opening = _xmlid(env, names["opening"])
    if not line or line._name != "tender.bid.line" or line.bid_id != bid:
        raise RuntimeError("fixture line XMLID is missing or outside the owned bid")
    if not opening or opening._name != "tender.opening" or opening.bid_id != bid:
        raise RuntimeError("fixture opening XMLID is missing or outside the owned bid")
    if set(bid.line_ids.ids) != {line.id}:
        raise RuntimeError("fixture bid contains BOQ rows outside the batch-owned scope")
    if set(bid.opening_ids.ids) != {opening.id}:
        raise RuntimeError("fixture bid contains opening rows outside the batch-owned scope")
    return bid.sudo(), line.sudo(), opening.sudo()


def _m2o_id(value):
    return value.id if value else None


def _summary(env, sha, batch, mode, bid=None, line=None, opening=None):
    names = _names(batch)
    writer = _writer(env)
    action = env.ref("smart_construction_core.action_tender_bid")
    menu = env.ref("smart_construction_core.menu_sc_project_tender")
    values = {
        "mode": mode,
        "database": env.cr.dbname,
        "environment": _text(os.environ.get("SC_ENVIRONMENT")),
        "dbfilter": _text(os.environ.get("ODOO_DBFILTER")),
        "candidate_sha": sha,
        "batch": batch,
        "namespace": MODULE,
        "existing_batch": bool(bid),
        "formal_entry": {
            "menu_xmlid": "smart_construction_core.menu_sc_project_tender",
            "menu_id": menu.id,
            "action_xmlid": "smart_construction_core.action_tender_bid",
            "action_id": action.id,
            "model": action.res_model,
        },
        "writer": {
            "id": writer.id,
            "login": writer.login,
            "company_id": writer.company_id.id,
        },
        "expected": EXPECTED,
        "recovery": (
            "cleanup validates XMLID/name ownership and no contract handoff, then unlinks "
            "only the batch-owned tender; its owned line/opening cascade with the tender"
        ),
    }
    if not bid:
        values["fixture"] = {
            "bid_xmlid": "%s.%s" % (MODULE, names["bid"]),
            "marker": names["marker"],
        }
        return values
    scoped_bid = bid.with_user(writer).with_context(
        allowed_company_ids=[writer.company_id.id]
    )
    read_allowed = write_allowed = False
    try:
        scoped_bid.check_access_rights("read")
        scoped_bid.check_access_rule("read")
        read_allowed = True
    except Exception:
        pass
    try:
        scoped_bid.check_access_rights("write")
        scoped_bid.check_access_rule("write")
        write_allowed = True
    except Exception:
        pass
    values["fixture"] = {
        "bid_xmlid": "%s.%s" % (MODULE, names["bid"]),
        "bid_id": bid.id,
        "line_id": line.id,
        "opening_id": opening.id,
        "marker": bid.name,
        "project_id": bid.project_id.id,
        "owner_id": bid.owner_id.id,
        "state": bid.state,
        "bid_amount": bid.bid_amount,
        "line_total": bid.amount_total,
        "line_count": len(bid.line_ids),
        "opening_count": len(bid.opening_ids),
        "opening_result": opening.result,
        "opening_amount": opening.win_price,
        "award_opening_id": _m2o_id(bid.award_opening_id),
        "award_source_kind": bid.award_source_kind or None,
        "award_source_reference": bid.award_source_reference or None,
        "award_tax_basis": bid.award_tax_basis or None,
        "award_amount": bid.award_amount,
        "award_currency_id": _m2o_id(bid.award_currency_id),
        "award_confirmed_by_id": _m2o_id(bid.award_confirmed_by_id),
        "award_confirmed_at": str(bid.award_confirmed_at or "") or None,
        "award_confirmation_state": bid.award_confirmation_state,
        "award_contract_handoff_message": bid.award_contract_handoff_message or None,
        "contract_id": _m2o_id(bid.contract_id),
        "writer_read_allowed": read_allowed,
        "writer_write_allowed": write_allowed,
    }
    return values


def inspect(env, sha, batch, mode):
    bid, line, opening = _owned(env, batch)
    return _summary(env, sha, batch, mode, bid, line, opening)


def prepare(env, sha, batch, mode):
    bid, _line, _opening = _owned(env, batch)
    if bid:
        raise RuntimeError("batch already exists; inspect or cleanup it before prepare")
    writer = _writer(env)
    project, partner = _master_data(env, writer)
    names = _names(batch)
    Bid = env["tender.bid"].sudo().with_context(tracking_disable=True)
    bid = Bid.create(
        {
            "name": names["marker"],
            "tender_name": "Codex P4 中标事实确认 %s" % batch,
            "project_id": project.id,
            "owner_id": partner.id,
            "bid_amount": EXPECTED["bid_amount"],
            "state": "waiting",
            "award_tax_basis": EXPECTED["tax_basis"],
        }
    )
    _bind(env, names["bid"], bid)
    line = env["tender.bid.line"].sudo().create(
        {
            "bid_id": bid.id,
            "sequence": 10,
            "code": "%s-LINE" % names["marker"],
            "name": "受管清单合计",
            "quantity": 1.0,
            "price": EXPECTED["line_total"],
        }
    )
    _bind(env, names["line"], line)
    opening = env["tender.opening"].sudo().create(
        {
            "bid_id": bid.id,
            "result": "won",
            "win_price": EXPECTED["award_amount"],
            "remark": "Codex P4 受管中标开标记录 %s" % batch,
        }
    )
    _bind(env, names["opening"], opening)
    bid.invalidate_recordset()
    summary = _summary(env, sha, batch, mode, bid, line, opening)
    fixture = summary["fixture"]
    if not (
        fixture["writer_read_allowed"]
        and fixture["writer_write_allowed"]
        and fixture["bid_amount"] == EXPECTED["bid_amount"]
        and fixture["line_total"] == EXPECTED["line_total"]
        and fixture["opening_amount"] == EXPECTED["award_amount"]
        and fixture["state"] == "waiting"
    ):
        raise RuntimeError("prepared tender award fixture failed its authority checks")
    env.cr.commit()
    return summary


def cleanup(env, sha, batch, mode):
    bid, line, opening = _owned(env, batch)
    if not bid:
        return {
            "mode": mode,
            "database": env.cr.dbname,
            "candidate_sha": sha,
            "batch": batch,
            "namespace": MODULE,
            "clean": True,
            "deleted": False,
        }
    if bid.contract_id:
        raise RuntimeError("cleanup stopped: batch-owned tender has a contract handoff")
    ids = {"bid_id": bid.id, "line_id": line.id, "opening_id": opening.id}
    bid.sudo().unlink()
    names = _names(batch)
    env["ir.model.data"].sudo().search(
        [
            ("module", "=", MODULE),
            ("name", "in", [names["bid"], names["line"], names["opening"]]),
        ]
    ).unlink()
    if env["tender.bid"].sudo().browse(ids["bid_id"]).exists():
        raise RuntimeError("cleanup failed: batch-owned tender still exists")
    if env["tender.bid.line"].sudo().browse(ids["line_id"]).exists():
        raise RuntimeError("cleanup failed: batch-owned tender line still exists")
    if env["tender.opening"].sudo().browse(ids["opening_id"]).exists():
        raise RuntimeError("cleanup failed: batch-owned opening still exists")
    env.cr.commit()
    return {
        "mode": mode,
        "database": env.cr.dbname,
        "candidate_sha": sha,
        "batch": batch,
        "namespace": MODULE,
        "clean": True,
        "deleted": True,
        **ids,
    }


sha, batch = _guard(env)
mode = _text(os.environ.get("P4_TENDER_AWARD_MODE"))
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
    raise RuntimeError(
        "P4_TENDER_AWARD_MODE must be inspect, dry-run, prepare or cleanup"
    )
print(
    "LOCAL_DEV_TENDER_AWARD_FIXTURE_JSON="
    + json.dumps(result, ensure_ascii=False, sort_keys=True)
)
