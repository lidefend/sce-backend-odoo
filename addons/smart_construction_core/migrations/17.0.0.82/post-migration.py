"""Retire unresolved customer handoff UI metadata without touching fact data."""

import json

from odoo import SUPERUSER_ID, api
from psycopg2 import sql


SNAPSHOT_KEY = "smart_construction_core.17.0.0.82.orphan_handoff_ui_snapshot"
ORPHAN_MODELS = (
    "sc.invoice.analysis.summary",
    "sc.invoice.cost.progress.summary",
    "sc.tender.guarantee.summary",
)
SUMMARY_VIEWS = (
    "sc_invoice_analysis_summary",
    "sc_invoice_cost_progress_summary",
    "sc_tender_guarantee_summary",
)
FACT_TABLES = (
    "sc_legacy_invoice_analysis_report_fact",
    "sc_legacy_invoice_cost_progress_report_fact",
    "sc_legacy_tender_guarantee_report_fact",
)


def _table_count(cr, table_name):
    cr.execute("SELECT to_regclass(%s)", [table_name])
    if not cr.fetchone()[0]:
        return None
    cr.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(table_name)))
    return int(cr.fetchone()[0])


def _xmlid(record):
    return record.get_external_id().get(record.id, "")


def migrate(cr, installed_version):
    del installed_version
    env = api.Environment(cr, SUPERUSER_ID, {})
    Action = env["ir.actions.act_window"].sudo()
    View = env["ir.ui.view"].sudo()
    Menu = env["ir.ui.menu"].sudo()
    actions = Action.search([("res_model", "in", ORPHAN_MODELS)])
    views = View.search([("model", "in", ORPHAN_MODELS)])
    action_refs = ["ir.actions.act_window,%s" % action_id for action_id in actions.ids]
    menus = Menu.search([("action", "in", action_refs)]) if action_refs else Menu.browse()
    target_recordsets = (menus, actions, views)
    target_ids = {records._name: list(records.ids) for records in target_recordsets}
    external_id_ids = []
    ModelData = env["ir.model.data"].sudo()
    for records in target_recordsets:
        if records:
            external_id_ids.extend(
                ModelData.search(
                    [
                        ("module", "=", "external_customer_legacy_handoff"),
                        ("model", "=", records._name),
                        ("res_id", "in", records.ids),
                    ]
                ).ids
            )
    snapshot = {
        "schema_version": "smart_construction_core.orphan_handoff_ui_snapshot.v1",
        "orphan_models": list(ORPHAN_MODELS),
        "summary_view_counts": {name: _table_count(cr, name) for name in SUMMARY_VIEWS},
        "fact_table_counts": {name: _table_count(cr, name) for name in FACT_TABLES},
        "menus": [
            {"id": row.id, "xmlid": _xmlid(row), "name": row.complete_name, "active": row.active, "action": row.action._name + "," + str(row.action.id)}
            for row in menus
        ],
        "actions": [
            {"id": row.id, "xmlid": _xmlid(row), "name": row.name, "res_model": row.res_model, "view_mode": row.view_mode}
            for row in actions
        ],
        "views": [
            {"id": row.id, "xmlid": _xmlid(row), "name": row.name, "model": row.model, "type": row.type, "arch_db": row.arch_db}
            for row in views
        ],
    }
    Parameters = env["ir.config_parameter"].sudo()
    if not Parameters.get_param(SNAPSHOT_KEY):
        Parameters.set_param(SNAPSHOT_KEY, json.dumps(snapshot, ensure_ascii=False, default=str))
    menus.write({"active": False})
    menus.unlink()
    actions.unlink()
    views.unlink()
    for model_name, record_ids in target_ids.items():
        external_id_ids.extend(
            ModelData.search(
                [
                    ("module", "=", "external_customer_legacy_handoff"),
                    ("model", "=", model_name),
                    ("res_id", "in", record_ids),
                ]
            ).ids
        )
    ModelData.browse(sorted(set(external_id_ids))).exists().unlink()
