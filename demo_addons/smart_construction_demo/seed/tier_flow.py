# -*- coding: utf-8 -*-
"""Shared helpers to drive multi-level tier validation chains in demo seeds.

Multi-level linear approval chains fire the tier server action callback
after every approved level (``action_on_tier_approved`` no-ops mid-chain),
and each level's review is scoped to its own reviewer group with
``approve_sequence`` enforcement.  A single fixed reviewer that only sits
on the last level can never satisfy the sequence guard and approves
nothing, so seeds must pick the acting reviewer per pending review.
"""

from odoo.exceptions import UserError

DEFAULT_FALLBACK_REVIEWER = "smart_construction_demo.user_sc_settlement_manager_cap"


def pick_tier_actor(record, review, fallback_xmlid=DEFAULT_FALLBACK_REVIEWER):
    """Pick a demo reviewer able to act on the given pending tier review."""
    candidates = review.sudo().reviewer_ids
    if not candidates and review.sudo().reviewer_group_id:
        candidates = review.sudo().reviewer_group_id.sudo().users
    if candidates:
        return candidates[0]
    return record.env.ref(fallback_xmlid)


def _review_signature(pending):
    return tuple(sorted((r.sequence, r.id, r.status) for r in pending))


def _describe_review(review):
    group = review.sudo().reviewer_group_id
    group_name = group.name if group else "-"
    member_count = len(review.sudo().reviewer_ids)
    return "sequence=%s group=%s members=%s" % (review.sequence, group_name, member_count)


def approve_tier_chain(record, fallback_xmlid=DEFAULT_FALLBACK_REVIEWER):
    """Approve every pending tier review with a per-review actor.

    Returns True when the record reached ``validation_status == "validated"``.
    Raises UserError when a full pass makes no progress: OCA's
    ``validate_tier`` silently no-ops for a user outside the review's
    reviewer set (e.g. an empty reviewer group falls back to a reviewer
    that cannot act), which would otherwise leave the record stuck in
    draft with no diagnostic.
    """
    record.invalidate_recordset()
    for _index in range(max(1, len(record.review_ids))):
        pending = record.review_ids.filtered(
            lambda r: r.status in ("pending", "waiting")
        )
        if not pending:
            break
        before = _review_signature(pending)
        review = min(pending, key=lambda r: (r.sequence, r.id))
        actor = pick_tier_actor(record, review, fallback_xmlid)
        record.with_user(actor).validate_tier()
        record.invalidate_recordset()
        if record.validation_status == "validated":
            break
        after_pending = record.review_ids.filtered(
            lambda r: r.status in ("pending", "waiting")
        )
        if _review_signature(after_pending) == before:
            raise UserError(
                "演示审批链推进失败：评审 %s（模型 %s，记录 %s）无人可批。"
                "请检查该级评审组的成员配置。"
                % (_describe_review(review), record._name, record.display_name)
            )
    return record.validation_status == "validated"
