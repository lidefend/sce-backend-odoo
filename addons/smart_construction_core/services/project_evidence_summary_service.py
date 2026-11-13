# -*- coding: utf-8 -*-
from __future__ import annotations

from odoo import api, models
from odoo.exceptions import AccessError


class ProjectEvidenceSummaryService(models.AbstractModel):
    """Caller-scoped project evidence totals for the formal dashboard."""

    _name = "sc.evidence.summary.service"
    _description = "Project Evidence Summary Service"

    PAYMENT_REQUEST_STATES = ("approved", "approve", "done")
    PAYMENT_LEDGER_NORMALIZATION_STATES = (
        "normalized",
        "legacy_observed_identity",
    )
    SETTLEMENT_STATES = ("approve", "done")
    COST_TREATMENTS = ("financial_actual", "manual_actual")
    REFERENCE_LIMIT = 10

    @api.model
    def summary_for_project(self, project):
        project = self._visible_project(project)
        currency = project.company_id.currency_id
        summary = self._empty_summary(project, currency)
        if not currency:
            summary["source_status"] = {
                model_name: "company_currency_unavailable"
                for model_name in self._source_models()
            }
            return summary

        project_domain = [("project_id", "=", project.id)]
        currency_domain = [("currency_id", "=", currency.id)]
        sources = {
            "payment.request": (
                project_domain
                + currency_domain
                + [
                    ("type", "=", "pay"),
                    ("state", "in", list(self.PAYMENT_REQUEST_STATES)),
                ],
                "amount",
            ),
            "payment.ledger": (
                project_domain
                + currency_domain
                + [
                    ("state", "=", "posted"),
                    (
                        "normalization_state",
                        "in",
                        list(self.PAYMENT_LEDGER_NORMALIZATION_STATES),
                    ),
                ],
                "amount",
            ),
            "project.cost.ledger": (
                project_domain
                + currency_domain
                + [
                    ("recognition_state", "=", "active"),
                    ("reporting_treatment", "in", list(self.COST_TREATMENTS)),
                ],
                "amount",
            ),
            "sc.settlement.order": (
                project_domain
                + currency_domain
                + [("state", "in", list(self.SETTLEMENT_STATES))],
                "amount_total",
            ),
        }
        totals = {}
        for model_name, (domain, sum_field) in sources.items():
            total, count, status = self._aggregate(model_name, domain, sum_field)
            totals[model_name] = {"total": total, "count": count}
            summary["source_status"][model_name] = status

        payment_request = totals["payment.request"]
        payment_ledger = totals["payment.ledger"]
        cost_ledger = totals["project.cost.ledger"]
        settlement = totals["sc.settlement.order"]
        summary.update(
            {
                "pay_total": payment_ledger["total"],
                "payment_request_total": payment_request["total"],
                "payment_request_count": payment_request["count"],
                "pay_done_total": payment_ledger["total"],
                "pay_done_count": payment_ledger["count"],
                "payment_count": payment_ledger["count"],
                "cost_total": cost_ledger["total"],
                "cost_count": cost_ledger["count"],
                "settlement_total": settlement["total"],
                "settlement_count": settlement["count"],
                "evidence_count": (
                    payment_ledger["count"]
                    + cost_ledger["count"]
                    + settlement["count"]
                ),
            }
        )

        reference_domains = {
            model_name: domain
            for model_name, (domain, _sum_field) in sources.items()
        }
        source_refs = {}
        evidence_refs = []
        for model_name, domain in reference_domains.items():
            refs = self._source_refs(model_name, domain)
            source_refs[model_name] = refs
            evidence_refs.extend(refs)
        summary["source_refs"] = source_refs
        summary["evidence_refs"] = evidence_refs
        return summary

    @api.model
    def _visible_project(self, project):
        project_id = int(getattr(project, "id", 0) or 0)
        visible = self.env["project.project"].search(
            [("id", "=", project_id)],
            limit=1,
        )
        if not visible:
            raise AccessError("项目不存在或当前用户无权访问。")
        return visible

    def _empty_summary(self, project, currency):
        return {
            "available": True,
            "project_id": int(getattr(project, "id", 0) or 0),
            "company_id": int(getattr(project.company_id, "id", 0) or 0),
            "currency_id": int(getattr(currency, "id", 0) or 0),
            "currency_name": str(getattr(currency, "name", "") or ""),
            "pay_total": 0.0,
            "payment_request_total": 0.0,
            "pay_done_total": 0.0,
            "pay_done_count": 0,
            "payment_count": 0,
            "payment_request_count": 0,
            "cost_total": 0.0,
            "cost_count": 0,
            "settlement_total": 0.0,
            "settlement_count": 0,
            "evidence_count": 0,
            "source_status": {},
            "source_refs": {},
            "evidence_refs": [],
        }

    @staticmethod
    def _source_models():
        return (
            "payment.request",
            "payment.ledger",
            "project.cost.ledger",
            "sc.settlement.order",
        )

    def _model(self, model_name):
        try:
            return self.env[model_name]
        except (KeyError, TypeError):
            return None

    def _can_read(self, model_name):
        model = self._model(model_name)
        if model is None:
            return None, "unavailable"
        if not model.check_access_rights("read", raise_exception=False):
            return model, "forbidden"
        try:
            model.check_access_rule("read")
        except AccessError:
            return model, "forbidden"
        return model, "ready"

    def _aggregate(self, model_name, domain, sum_field):
        model, status = self._can_read(model_name)
        if status != "ready":
            return 0.0, 0, status
        if sum_field not in model._fields:
            return 0.0, 0, "contract_gap"
        try:
            rows = model.read_group(domain, [sum_field], [], lazy=False)
        except AccessError:
            return 0.0, 0, "forbidden"
        except (KeyError, TypeError, ValueError):
            return 0.0, 0, "query_failed"
        if not rows:
            return 0.0, 0, "ready"
        row = rows[0]
        total = float(row.get(sum_field + "_sum", row.get(sum_field, 0.0)) or 0.0)
        count = row.get("__count")
        if type(count) is not int:
            try:
                count = int(model.search_count(domain))
            except (AccessError, KeyError, TypeError, ValueError):
                return 0.0, 0, "query_failed"
        return round(total, 2), max(count, 0), "ready"

    def _source_refs(self, model_name, domain):
        model, status = self._can_read(model_name)
        if status != "ready":
            return []
        try:
            ids = model.search(domain, order="id desc", limit=self.REFERENCE_LIMIT).ids
        except (AccessError, KeyError, TypeError, ValueError):
            return []
        return ["%s#%s" % (model_name, record_id) for record_id in ids]
