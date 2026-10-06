#!/usr/bin/env python3
"""Report / apply the unified project-ledger field-overlay repair.

Run through the governed ``odoo.shell.exec`` entry so the target database is
bound by ``DB_NAME`` and the registered compose project, never by hand.

    PROJECT_LEDGER_OVERLAY_ACTION=report make project.ledger.field_overlay.repair
    PROJECT_LEDGER_OVERLAY_ACTION=apply  make project.ledger.field_overlay.repair

``report`` is the default; ``apply`` retires only the stale legacy
``ui.form.field.policy`` rows on the ledger action that suppress a field the
unified surface's authoritative native form declares.
"""

from __future__ import annotations

import json
import os

from odoo.addons.smart_construction_core.services.project_ledger_field_overlay_repair import (
    retire_stale_ledger_field_overlay,
)


ACTION = os.getenv("PROJECT_LEDGER_OVERLAY_ACTION", "report").strip().lower()
if ACTION not in {"report", "apply"}:
    raise SystemExit("PROJECT_LEDGER_OVERLAY_ACTION must be report or apply")

report = retire_stale_ledger_field_overlay(env, dry_run=ACTION != "apply")  # noqa: F821
print("PROJECT_LEDGER_FIELD_OVERLAY_REPAIR " + json.dumps(report, ensure_ascii=False, sort_keys=True))
