# -*- coding: utf-8 -*-
from odoo import fields

from ..registry import SeedStep, register
from .step_20_projects_demo import STAGE_PROJECTS, declared_stage


PROJECT_TENDER_CODE = "DEMO-PJ-TENDER"
STAGE_PROJECT_CODES = [row[0] for row in STAGE_PROJECTS]


def _get_project(env, code):
    return env["project.project"].sudo().search([("project_code", "=", code)], limit=1)


def _get_or_create_partner(env, name):
    Partner = env["res.partner"].sudo()
    partner = Partner.search([("name", "=", name)], limit=1)
    if partner:
        if partner.company_type != "company":
            partner.company_type = "company"
        return partner
    return Partner.create({"name": name, "company_type": "company"})


def _advance_bid(bid, target):
    """Record an explicit demo opening, then let the product confirm its fact."""
    if target not in {"prepare", "submitted", "waiting", "won", "lost"}:
        raise ValueError("Undeclared demo tender target: %s" % target)
    if bid.state == target:
        if target == "won" and not bid.award_confirmed_at:
            raise ValueError("Legacy won demo bid has no authoritative award snapshot")
        return
    forward = {
        "prepare": {"submitted", "waiting", "won", "lost"},
        "submitted": {"waiting", "won", "lost"},
        "waiting": {"won", "lost"},
    }
    if target not in forward.get(bid.state, set()) or bid.award_confirmed_at:
        raise ValueError("Demo bid replay would change an existing business outcome")
    if bid.state == "prepare":
        bid.action_to_submitted()
    if target == "waiting":
        bid.action_to_waiting()
    elif target == "lost":
        bid.action_mark_lost()
    elif target == "won":
        reference = "DEMO-AWARD-" + bid.name
        openings = bid.env["tender.opening"].search([
            ("bid_id", "=", bid.id), ("remark", "=", reference),
        ])
        if not openings:
            openings = bid.env["tender.opening"].create({
                "bid_id": bid.id, "open_time": bid.open_date,
                "result": "won", "win_price": bid.bid_amount,
                "remark": reference,
            })
        if len(openings) != 1 or openings.result != "won" or openings.win_price != bid.bid_amount:
            raise ValueError("Demo award source conflicts with declared opening")
        bid.write({"award_opening_id": openings.id,
                   "award_source_kind": "award_notice",
                   "award_source_reference": reference})
        bid.action_mark_won()
    if bid.state != target or (target == "won" and not bid.award_confirmed_at):
        raise ValueError("Demo tender action did not produce its declared outcome")


def run(env):
    projects = [
        _get_project(env, PROJECT_TENDER_CODE),
    ]
    for code in STAGE_PROJECT_CODES:
        projects.append(_get_project(env, code))
    projects = [p for p in projects if p]

    owner = _get_or_create_partner(env, "德阳市城市建设投资集团有限公司")
    uom_unit = env.ref("uom.product_uom_unit", raise_if_not_found=False)
    if not uom_unit:
        uom_unit = env["uom.uom"].sudo().search([], limit=1)

    from ...tools.scenario_loader import _demo_action_record, _demo_project_members
    actor = env.ref("smart_construction_demo.user_sc_project_user")
    for project in projects:
        _demo_project_members(env, project, ("smart_construction_demo.user_sc_project_user",))
    Tender = _demo_action_record(env, env["tender.bid"], "action_to_submitted")
    TenderLine = env["tender.bid.line"].with_user(actor).sudo(False)
    now = fields.Datetime.now()
    bid_year = fields.Date.context_today(env.user).year
    state_map = {
        "draft": "prepare",
        "in_progress": "submitted",
        "paused": "waiting",
        "closing": "won",
        "done": "won",
        "warranty": "won",
        "closed": "lost",
    }

    for project in projects:
        state = state_map[declared_stage(project)]
        bids = [
            {
                "name": f"TB-{bid_year}-{project.id:03d}-01",
                "tender_name": f"{project.name} 投标",
                "project_id": project.id,
                "tender_round": 1,
                "owner_id": owner.id,
                "bid_amount": 880000.0,
                "deadline": now,
                "open_date": now,
            },
        ]
        if project.project_code == PROJECT_TENDER_CODE:
            bids.append(
                {
                    "name": f"TB-{bid_year}-{project.id:03d}-02",
                    "tender_name": f"{project.name} 投标（二次）",
                    "project_id": project.id,
                    "tender_round": 2,
                    "owner_id": owner.id,
                    "bid_amount": 930000.0,
                    "deadline": now,
                    "open_date": now,
                }
            )

        for bid_vals in bids:
            bid = Tender.search(
                [("project_id", "=", project.id), ("name", "=", bid_vals["name"])], limit=1
            )
            if bid:
                if bid.state == "prepare":
                    bid.write(bid_vals)
            else:
                bid = Tender.create(bid_vals)

            line_vals = [
                {
                    "bid_id": bid.id,
                    "sequence": 10,
                    "code": f"{project.project_code}-BID-01",
                    "name": "路基填筑",
                    "uom_id": uom_unit.id if uom_unit else False,
                    "quantity": 120,
                    "price": 820,
                },
                {
                    "bid_id": bid.id,
                    "sequence": 20,
                    "code": f"{project.project_code}-BID-02",
                    "name": "桥梁下部结构",
                    "uom_id": uom_unit.id if uom_unit else False,
                    "quantity": 60,
                    "price": 1500,
                },
            ]
            for vals in line_vals:
                existing = TenderLine.search(
                    [("bid_id", "=", bid.id), ("code", "=", vals["code"])], limit=1
                )
                if bid.state == "prepare":
                    if existing:
                        existing.write(vals)
                    else:
                        TenderLine.create(vals)
                elif not existing:
                    raise ValueError("Completed demo bid is missing declared lines")

            _advance_bid(bid, state)


register(
    SeedStep(
        name="demo_30_tenders",
        description="Seed tender records for demo project.",
        run=run,
    )
)
