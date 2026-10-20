# -*- coding: utf-8 -*-
"""Read-only U1/U2 master-data presence + date-classification acceptance (F3)."""
from __future__ import annotations

import json

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "-standard", "demo_usage_foundation_master_data")
class TestDemoUsageFoundationMasterData(TransactionCase):
    def test_master_data_presence_and_date_classification(self):
        models = (
            "res.partner",
            "res.partner.bank",
            "account.tax",
            "uom.uom",
            "sc.dictionary",
            "project.cost.code",
            "sc.material.catalog",
            "sc.material.price",
            "project.project",
            "project.task",
        )
        minimums = {
            "res.partner": 1,
            "res.partner.bank": 9,
            "account.tax": 1,
            "uom.uom": 1,
            "sc.dictionary": 1,
            "project.cost.code": 1,
            "sc.material.catalog": 1,
            "sc.material.price": 1,
            "project.project": 1,
            "project.task": 1,
        }
        report = {"counts": {}, "date_2025": {}, "errors": []}
        for model in models:
            try:
                count = self.env[model].search_count([])
                report["counts"][model] = count
                self.assertGreaterEqual(
                    count, minimums[model], f"{model} below minimum {minimums[model]}"
                )
            except Exception as exc:  # noqa: BLE001 - audit must not die on one model
                report["counts"][model] = None
                report["errors"].append(f"{model}: {type(exc).__name__}")

        for model, field in (
            ("project.project", "start_date"),
            ("project.task", "date_deadline"),
        ):
            key = f"{model}.{field}"
            try:
                records = self.env[model].search([])
                report["date_2025"][key] = sum(
                    1 for rec in records if rec[field] and getattr(rec[field], "year", None) == 2025
                )
            except Exception as exc:  # noqa: BLE001
                report["date_2025"][key] = f"ERR {type(exc).__name__}"

        print("DEMO_MASTER_DATA_REPORT " + json.dumps(report, ensure_ascii=False))
        self.assertEqual(report["errors"], [])
