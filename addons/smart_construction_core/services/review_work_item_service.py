"""Project actual assigned reviews into the existing current-user workspace."""
from urllib.parse import urlencode

from odoo.exceptions import AccessError
from odoo.addons.smart_core.core.project_context import record_in_business_scope
from .payment_request_work_item_service import PaymentRequestWorkItemService


def authorize_review_origin(env, origin, *, model, record_id, method_name=None):
    if origin.get("source") != "tier.review":
        return None
    if method_name not in (None, "validate_tier", "reject_tier"):
        return False
    review = env["tier.review"].sudo().browse(origin["id"]).exists()
    if not review or review.model != model or review.res_id != record_id:
        return False
    if review.status not in ("waiting", "pending") or env.uid not in review.reviewer_ids.ids:
        return False
    if model not in env:
        return False
    record = env[model].browse(record_id).exists()
    if not record:
        return False
    record.check_access_rights("read")
    record.check_access_rule("read")
    if "review_ids" not in record._fields or review.id not in record.review_ids.ids or not record.can_review:
        return False
    company = record.company_id if "company_id" in record._fields else record.project_id.company_id if "project_id" in record._fields else env.company
    return bool(company == env.company and record_in_business_scope(env[model], record_id, {}, env.context)[0])


class CurrentWorkItemService:
    def __init__(self, env, *, params=None, context=None):
        self.env, self.params, self.context = env, params or {}, context or {}

    def build(self):
        workspace = PaymentRequestWorkItemService(self.env, params=self.params, context=self.context).build()
        todo = next(section for section in workspace["sections"] if section["key"] == "todo")
        existing = {(item["target"]["model"], item["target"]["record_id"]) for item in todo["items"]}
        company_id = workspace["query_scope"]["company_ids"][0]
        if company_id not in self.env.companies.ids:
            return workspace
        review_env = self.env(context={**self.env.context, "allowed_company_ids": [company_id]})
        reviews = review_env["tier.review"].sudo().search([
            ("reviewer_ids", "in", self.env.uid), ("status", "in", ["waiting", "pending"]),
        ], order="id desc", limit=80)
        for review in reviews:
            identity = (review.model, review.res_id)
            origin = {"source": "tier.review", "id": review.id}
            try:
                if identity in existing or not authorize_review_origin(review_env, origin, model=review.model, record_id=review.res_id):
                    continue
                record = review_env[review.model].browse(review.res_id)
                if not record_in_business_scope(review_env[review.model], record.id, self.params, self.context)[0]:
                    continue
                label, business_type = str(record.display_name), str(record._description)
                target = {"model": review.model, "record_id": record.id, "work_item_origin": origin,
                          "route": "/r/%s/%s?%s" % (review.model, record.id, urlencode({"work_item_source": origin["source"], "work_item_id": origin["id"]}))}
                todo["items"].append({
                    "key": "%s:%s" % identity, "section": "todo", "business_type": business_type,
                    "record": {"label": label}, "state": {"key": "pending", "label": "待我审批"},
                    "facts": [], "search_text": "%s %s" % (label, business_type),
                    "sort_values": {"updated_desc": str(record.write_date or "")},
                    "actions": [], "target": target,
                    "source_authority": "assigned tier.review + current record ACL/rules/can_review",
                })
                existing.add(identity)
            except AccessError:
                continue
        todo["count"] = len(todo["items"])
        workspace["counts"] = {section["key"]: section["count"] for section in workspace["sections"]}
        workspace["total"] = sum(workspace["counts"].values())
        workspace["version"] = "current-user-workspace-v2"
        workspace["source_authority"] = "current-user payment action contract + assigned review authority"
        return workspace
