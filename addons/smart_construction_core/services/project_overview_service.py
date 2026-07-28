# -*- coding: utf-8 -*-
from collections import defaultdict
import logging
import time

from odoo import api, models

from odoo.addons.smart_construction_core.services.project_authorization_service import (
    ProjectAuthorizationService,
)

_logger = logging.getLogger(__name__)


class ProjectOverviewService(models.AbstractModel):
    _name = "sc.project.overview.service"
    _description = "Project Overview Aggregation Service"

    def _group_count(self, row, groupby):
        if "__count" in row:
            return row.get("__count", 0)
        return row.get(f"{groupby}_count", 0)

    @api.model
    def get_overview(self, project_ids):
        normalized_ids = []
        for raw_id in project_ids or []:
            if isinstance(raw_id, bool):
                continue
            try:
                project_id = int(raw_id)
            except (TypeError, ValueError):
                continue
            if project_id > 0 and project_id not in normalized_ids:
                normalized_ids.append(project_id)
        if not normalized_ids:
            return {}
        authorization = ProjectAuthorizationService(self.env)
        ids = []
        for project_id in normalized_ids:
            resolution = authorization.resolve(project_id=project_id)
            if resolution.available:
                ids.append(int(resolution.project.id))
        data = {pid: {
            "contract": {"count": 0},
            "cost": {"count": 0},
            "payment": {"count": 0, "pending": 0},
            "task": {"count": 0, "in_progress": 0},
        } for pid in ids}
        if not ids:
            return data

        env = self.env
        can_contract = env["project.project"]._can_read_model("construction.contract")
        can_cost = env["project.project"]._can_read_model("project.cost.ledger")
        can_payment = ("payment.request" in env) and env["project.project"]._can_read_model("payment.request")
        can_task = env["project.project"]._can_read_model("project.task")

        start_ts = time.time()
        calls = 0

        if can_contract:
            calls += 1
            rows = env["construction.contract"].read_group(
                [("project_id", "in", ids)],
                ["project_id"],
                ["project_id"],
            )
            for rec in rows:
                project_id = rec["project_id"][0]
                data[project_id]["contract"]["count"] = self._group_count(rec, "project_id")

        if can_cost:
            calls += 1
            rows = env["project.cost.ledger"].read_group(
                [("project_id", "in", ids)],
                ["project_id"],
                ["project_id"],
            )
            for rec in rows:
                project_id = rec["project_id"][0]
                data[project_id]["cost"]["count"] = self._group_count(rec, "project_id")

        if can_payment:
            calls += 1
            rows = env["payment.request"].read_group(
                [("project_id", "in", ids)],
                ["project_id"],
                ["project_id"],
            )
            for rec in rows:
                project_id = rec["project_id"][0]
                data[project_id]["payment"]["count"] = self._group_count(rec, "project_id")
            calls += 1
            pending_rows = env["payment.request"].read_group(
                [
                    ("project_id", "in", ids),
                    ("state", "in", ["submit", "approve", "approved"]),
                ],
                ["project_id"],
                ["project_id"],
            )
            for rec in pending_rows:
                project_id = rec["project_id"][0]
                data[project_id]["payment"]["pending"] = self._group_count(rec, "project_id")

        if can_task:
            calls += 1
            rows = env["project.task"].read_group(
                [("project_id", "in", ids)],
                ["project_id"],
                ["project_id"],
            )
            for rec in rows:
                project_id = rec["project_id"][0]
                data[project_id]["task"]["count"] = self._group_count(rec, "project_id")
            calls += 1
            progress_rows = env["project.task"].read_group(
                [
                    ("project_id", "in", ids),
                    ("sc_state", "=", "in_progress"),
                ],
                ["project_id"],
                ["project_id"],
            )
            for rec in progress_rows:
                project_id = rec["project_id"][0]
                data[project_id]["task"]["in_progress"] = self._group_count(rec, "project_id")

        if env.context.get("sc_overview_debug"):
            elapsed = time.time() - start_ts
            _logger.info(
                "[sc_overview] project_ids=%s read_groups=%s elapsed=%.3fs",
                len(ids), calls, elapsed,
            )

        return data
