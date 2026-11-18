#!/usr/bin/env python3
"""Resolve BE-CLOSE-01 acceptance identities inside the governed Odoo shell."""

from __future__ import annotations

import json
import os
from pathlib import Path


OUTPUT_PATH = Path(
    os.environ.get(
        "SC_ACCEPTANCE_BE_CLOSE01_IDS_OUTPUT",
        "/mnt/artifacts/backend/be_close_01_workflow_contract_runtime_ids_v1.json",
    )
)
ACTOR_XMLID = "smart_construction_acceptance_fixture.fe_user_config_admin"
PAYMENT_MENU = "smart_construction_core.menu_sc_user_payment_apply"
PAYMENT_ACTION = "smart_construction_core.action_payment_request_user_payment_apply"
PROJECT_MENU = "smart_construction_core.menu_sc_product_project_lifecycle_v1"
PROJECT_ACTION = "smart_construction_core.action_sc_product_project_lifecycle_v1"
PAYMENT_ACTIONABLE = "smart_construction_acceptance_fixture.fe_journey_payment_request_a"
PAYMENT_BLOCKED = "smart_construction_acceptance_fixture.fe_journey_payment_request_completed_a"
PROJECT_ACTIONABLE = "smart_construction_acceptance_fixture.fe_project_lifecycle"
PROJECT_BLOCKED_CANDIDATES = (
    "smart_construction_acceptance_fixture.fe_project_a",
    "smart_construction_acceptance_fixture.fe_project_b",
)


def _ref(xmlid):
    record = env.ref(xmlid, raise_if_not_found=False)  # noqa: F821 - Odoo shell
    if not record:
        raise RuntimeError("missing BE-CLOSE-01 fixture: %s" % xmlid)
    return record


def _entry(menu_xmlid, action_xmlid):
    menu = _ref(menu_xmlid)
    action = _ref(action_xmlid)
    if menu.action != action:
        raise RuntimeError("menu/action identity mismatch: %s" % menu_xmlid)
    return {
        "menu_xmlid": menu_xmlid,
        "menu_id": int(menu.id),
        "action_xmlid": action_xmlid,
        "action_id": int(action.id),
        "action_type": str(action.type or ""),
        "model": str(action.res_model or ""),
    }


def _record(xmlid):
    record = _ref(xmlid)
    payload = {
        "xmlid": xmlid,
        "id": int(record.id),
        "model": record._name,
        "display_name": str(record.display_name or ""),
    }
    if record._name == "payment.request":
        payload.update({
            "state": str(record.state or ""),
            "validation_status": str(record.validation_status or ""),
        })
    elif record._name == "project.project":
        payload.update({
            "lifecycle_state": str(record.lifecycle_state or ""),
            "sc_approval_state": str(record.sc_approval_state or ""),
            "validation_status": str(record.validation_status or ""),
        })
    return payload


def emit():
    actor = _ref(ACTOR_XMLID)
    salary = {
        "schema": "be_close_01.runtime_ids.v1",
        "runtime": {
            "source_revision": str(os.environ.get("SC_SOURCE_REVISION") or ""),
            "source_fingerprint": str(os.environ.get("SC_SOURCE_FINGERPRINT") or ""),
            "database": str(env.cr.dbname),  # noqa: F821 - Odoo shell
        },
        "actor": {
            "xmlid": ACTOR_XMLID,
            "id": int(actor.id),
            "login": str(actor.login or ""),
            "company_id": int(actor.company_id.id),
            "company_name": str(actor.company_id.name or ""),
        },
        "entries": {
            "payment_request": _entry(PAYMENT_MENU, PAYMENT_ACTION),
            "project_lifecycle": _entry(PROJECT_MENU, PROJECT_ACTION),
        },
        "records": {
            "payment_actionable": _record(PAYMENT_ACTIONABLE),
            "payment_blocked": _record(PAYMENT_BLOCKED),
            "project_actionable": _record(PROJECT_ACTIONABLE),
            "project_blocked_candidates": [
                _record(xmlid) for xmlid in PROJECT_BLOCKED_CANDIDATES
            ],
        },
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(salary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("BE_CLOSE_01_RUNTIME_IDS=" + json.dumps({
        "output": str(OUTPUT_PATH),
        "database": salary["runtime"]["database"],
        "actor": salary["actor"]["login"],
    }, sort_keys=True))


if "env" not in globals():
    raise SystemExit("BE-CLOSE-01 runtime IDs must run through Odoo shell")
emit()
