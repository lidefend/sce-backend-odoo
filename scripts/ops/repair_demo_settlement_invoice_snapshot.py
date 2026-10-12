#!/usr/bin/env python3
"""Report / apply the demo settlement invoice-snapshot repair.

The demo seed (``demo_40_contracts``) records an invoice snapshot
``invoice_amount = round(amount_total * ratio(lifecycle_state), 2)`` for the
settlements it owns while they are still drafts, then approves them. When the
project stage is promoted afterwards (``project_stage_sync``), an approved
settlement keeps the snapshot of the earlier lifecycle stage; because approved
settlement facts are immutable, the seed's reconciliation can only report that
drift, never converge it.

This entry repairs exactly that drift: it re-derives the sample snapshot for the
projects the seed owns and fills ``invoice_amount`` only where it is still NULL.
Any other value (a real business fact) is left untouched and is reported as a
hard mismatch instead of being rewritten.

Run through the governed ``odoo.shell.exec`` entry so the target database is
bound by ``DB_NAME`` and the registered compose project, never by hand.

    DEMO_SETTLEMENT_SNAPSHOT_ACTION=report make local.dev.demo.settlement_snapshot.repair
    DEMO_SETTLEMENT_SNAPSHOT_CONFIRM=1 \
      DEMO_SETTLEMENT_SNAPSHOT_ACTION=apply make local.dev.demo.settlement_snapshot.repair

``report`` is the default. The repair only touches synthetic demo data: it
refuses to run when the demo module is not installed, and ``apply`` requires an
explicit confirmation. The previous value of every repaired row is printed so
the write is reversible.
"""

from __future__ import annotations

import json
import os

from odoo.addons.smart_construction_demo.seed.steps.step_40_contracts_demo import (
    DEMO_INVOICE_RATIO_BY_STATE,
    DEMO_INVOICE_WARN_RATIO_BY_STATE,
    DEMO_WARN_PROJECT_CODES,
    PROJECT_EXEC_CODE,
    STAGE_PROJECT_CODES,
    _get_project,
    _get_showroom_projects,
)

ACTION = os.getenv("DEMO_SETTLEMENT_SNAPSHOT_ACTION", "report").strip().lower()
if ACTION not in {"report", "apply"}:
    raise SystemExit("DEMO_SETTLEMENT_SNAPSHOT_ACTION must be report or apply")
CONFIRM = os.getenv("DEMO_SETTLEMENT_SNAPSHOT_CONFIRM", "").strip() == "1"

demo_installed = env["ir.module.module"].sudo().search_count(  # noqa: F821
    [("name", "=", "smart_construction_demo"), ("state", "=", "installed")]
)
if not demo_installed:
    raise SystemExit("demo settlement snapshot repair requires the demo module; refusing to run")


def _owned_projects(env):
    projects = [_get_project(env, PROJECT_EXEC_CODE)]
    projects.extend(_get_project(env, code) for code in STAGE_PROJECT_CODES)
    projects.extend(_get_showroom_projects(env))
    return list({project.id: project for project in projects if project}.values())


def expected_snapshot(project, settlement):
    ratio_by_state = (
        DEMO_INVOICE_WARN_RATIO_BY_STATE
        if project.project_code in DEMO_WARN_PROJECT_CODES
        else DEMO_INVOICE_RATIO_BY_STATE
    )
    ratio = ratio_by_state.get(project.lifecycle_state, 1.0)
    return round((settlement.amount_total or 0.0) * ratio, 2)


candidates = []
hard_mismatch = []
Settlement = env["sc.settlement.order"].sudo()  # noqa: F821
for project in _owned_projects(env):
    # ``_ensure_settlement`` owns exactly one settlement per project, named
    # after the project code; other settlements of the same project belong to
    # different scenarios and are never validated by the seed.
    settlement = Settlement.search(
        [
            ("project_id", "=", project.id),
            ("name", "=", "SET-%s-01" % project.project_code),
            ("state", "in", ("approve", "done")),
        ],
        order="id",
        limit=1,
    )
    if settlement:
        expected = expected_snapshot(project, settlement)
        if expected <= 0:
            # A zero sample snapshot and an unset (NULL) snapshot are equivalent.
            continue
        # Odoo maps a NULL monetary column to 0.0 in the cache, so both are
        # "no snapshot recorded" for a non-zero settlement.
        actual = settlement.invoice_amount or 0.0
        if not actual:
            candidates.append(
                {
                    "id": settlement.id,
                    "name": settlement.name,
                    "project_code": project.project_code,
                    "lifecycle_state": project.lifecycle_state,
                    "amount_total": settlement.amount_total,
                    "invoice_amount": None,
                    "expected": expected,
                }
            )
        elif abs(actual - expected) > 0.005:
            hard_mismatch.append(
                {
                    "id": settlement.id,
                    "name": settlement.name,
                    "project_code": project.project_code,
                    "invoice_amount": actual,
                    "expected": expected,
                }
            )

applied = []
if ACTION == "apply":
    if not CONFIRM:
        raise SystemExit("DEMO_SETTLEMENT_SNAPSHOT_CONFIRM=1 is required to apply the repair")
    for row in candidates:
        env.cr.execute(  # noqa: F821
            "UPDATE sc_settlement_order SET invoice_amount = %s "
            "WHERE id = %s AND (invoice_amount IS NULL OR invoice_amount = 0)",
            (row["expected"], row["id"]),
        )
        applied.append(row)
    env.invalidate_all()  # noqa: F821
    env.cr.commit()  # noqa: F821

readback = []
for row in applied:
    settlement = Settlement.browse(row["id"])
    readback.append(
        {
            "id": row["id"],
            "name": row["name"],
            "previous_invoice_amount": None,
            "invoice_amount": settlement.invoice_amount,
        }
    )

print(
    "DEMO_SETTLEMENT_SNAPSHOT_REPAIR "
    + json.dumps(
        {
            "action": ACTION,
            "db": env.cr.dbname,  # noqa: F821
            "candidates": candidates,
            "hard_mismatch": hard_mismatch,
            "repaired": len(applied),
            "readback": readback,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
)
