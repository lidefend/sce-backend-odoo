"""Explicit demo authors; product ACLs and record rules still decide access."""

MODEL_SEATS = {
    "account.analytic.plan": "user_sc_accounting_manager_demo",
    'hr.job': 'user_sc_business_config_demo',
    'account.analytic.account': 'user_sc_accounting_manager_demo',
    'account.analytic.distribution.model': 'user_sc_accounting_manager_demo',
    'sc.office.asset': 'user_sc_business_config_demo',
    'sc.site.variation': 'user_sc_project_manager_cap',
    'sc.contract.change': 'user_sc_contract_manager_cap',
    'sc.labor.worker': 'user_sc_project_manager_cap',
    'sc.labor.deduction': 'user_sc_project_manager_cap',
    'sc.quality.acceptance': 'user_sc_project_manager_cap',
    'sc.material.supplier.return': 'user_sc_material_mgr_01',
    'sc.hr.salary.payment': 'user_sc_project_manager_cap',
    'tender.opportunity': 'user_sc_project_manager_cap',
    'tender.document': 'user_sc_project_manager_cap',
    'sc.tax.certificate.registration': 'user_sc_fin_mgr_01',
    'sc.tax.filing': 'user_sc_fin_mgr_01',

    "project.project": "user_sc_project_manager_cap",
    "project.task": "user_sc_project_manager_cap",
    "construction.work.breakdown": "user_sc_project_manager_cap",
    "project.progress.entry": "user_sc_cost_manager_cap",
    "project.boq.analysis": "user_sc_cost_manager_cap",
    "project.boq.version": "user_sc_cost_manager_cap",
    "project.boq.line": "user_sc_cost_manager_cap",
    "project.budget": "user_sc_cost_manager_cap",
    "project.budget.boq.line": "user_sc_cost_manager_cap",
    "project.cost.ledger": "user_sc_cost_manager_cap",
    "project.cost.plan": "user_sc_cost_manager_cap",
    "project.cost.plan.line": "user_sc_cost_manager_cap",
    "construction.location.breakdown": "user_sc_cost_manager_cap",
    "construction.contract.section": "user_sc_cost_manager_cap",
    "construction.execution.scope": "user_sc_cost_manager_cap",
    "project.boq.allocation": "user_sc_cost_manager_cap",
    "construction.contract": "user_sc_contract_manager_cap",
    "sc.settlement.order": "user_sc_settlement_user_cap",
    "sc.settlement.order.line": "user_sc_settlement_user_cap",
    "payment.request": "user_demo_role_project_a_member",
}


def business_model(env, model):
    from ..tools.scenario_loader import _demo_action_record

    seat = MODEL_SEATS[model]  # Missing declaration is an error, never sudo.
    return _demo_action_record(env, env[model], "create", "smart_construction_demo." + seat)


def project_actor(project):
    return business_model(project.env, "project.project").browse(project.ids)


def prepare_project(env, project):
    """Prepare declared organization facts before any business operation."""
    from ..tools.scenario_loader import _demo_project_members, _DEMO_PAYMENT_SCOPED_SEATS, _DEMO_APPROVAL_ACTORS

    if project.company_id != env.ref("base.main_company"):
        raise ValueError("Demo project must belong to its explicitly declared company")
    seats = tuple(sorted(
        {"smart_construction_demo." + name for name in MODEL_SEATS.values()}
        | set(_DEMO_APPROVAL_ACTORS.values())
    ))
    _demo_project_members(env, project, seats + _DEMO_PAYMENT_SCOPED_SEATS + (
        "smart_construction_demo.user_sc_cost_01",
        "smart_construction_demo.user_sc_purchase_manager_cap",
    ))


def ensure_manual_boq_analysis(env, line, unit_price):
    """Author the declared single-material example before publishing its BOQ.

    This is native draft analysis input, not an imported snapshot: no import
    batch, source sheet, digest or successful-import status is fabricated.
    """
    analyses = line.analysis_id
    if analyses:
        if len(analyses) != 1 or analyses.source_unit_price != unit_price:
            raise ValueError("Demo BOQ analysis conflicts with its declared source")
        return analyses
    if line.version_id.state != "draft":
        raise ValueError("Published demo BOQ lacks declared analysis; rebuild rather than backfill")
    return business_model(env, "project.boq.analysis").create({
        "name": "手工录入单项材料分析", "boq_line_id": line.id,
        "source_quantity": line.quantity, "source_unit_price": unit_price,
        "uom_raw": line.uom_id.name,
        "norm_line_ids": [(0, 0, {"norm_code": "DEMO-MANUAL-MATERIAL",
            "name": "C30 混凝土材料组成", "budget_consumption": 1.0,
            "unit_material": unit_price, "amount_material": unit_price})],
        "resource_line_ids": [(0, 0, {"name": "C30 混凝土材料来源",
            "resource_type": "material", "unit_raw": line.uom_id.name,
            "budget_consumption": 1.0, "budget_unit_price": unit_price,
            "budget_unit_amount": unit_price})],
    })


def write_if_changed(record, values):
    """Avoid treating an unchanged replay as an edit of a published object."""
    changes = {}
    for field, value in values.items():
        current = record[field]
        if record._fields[field].type == "many2one":
            current = current.id or False
        if current != value:
            changes[field] = value
    if changes:
        record.write(changes)
    return record
