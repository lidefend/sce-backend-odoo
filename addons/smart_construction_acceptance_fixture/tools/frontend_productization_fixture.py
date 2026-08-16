# -*- coding: utf-8 -*-
"""Deterministic browser fixture for frontend productization acceptance.

This module is deliberately hosted by ``smart_construction_acceptance_fixture``.
It is an administrative data builder for a disposable acceptance database;
authorization is verified separately with fixture-owned users and without sudo.
"""

from __future__ import annotations

import os
from typing import Any, Dict


MODULE = "smart_construction_acceptance_fixture"
FRONTEND_ACCEPTANCE_DB = "sc_frontend_acceptance"


def _fixture_password():
    password = str(os.environ.get("SC_ACCEPTANCE_FIXTURE_PASSWORD") or "").strip()
    if not password:
        raise RuntimeError("frontend fixture requires SC_ACCEPTANCE_FIXTURE_PASSWORD")
    return password


def _guard_acceptance_scope(env):
    """Fail before any fixture lookup or write unless the exact scope is active."""
    if env.cr.dbname != FRONTEND_ACCEPTANCE_DB:
        raise RuntimeError(
            "frontend fixture requires database %s (got %s)"
            % (FRONTEND_ACCEPTANCE_DB, env.cr.dbname)
        )
    if os.environ.get("SC_ENVIRONMENT") != "acceptance":
        raise RuntimeError("frontend fixture requires SC_ENVIRONMENT=acceptance")
    if os.environ.get("SC_ALLOW_DEMO_DATA") != "1":
        raise RuntimeError("frontend fixture requires SC_ALLOW_DEMO_DATA=1")
    _fixture_password()


def _ref(env, xmlid):
    record = env.ref(xmlid, raise_if_not_found=False)
    if not record:
        raise RuntimeError("missing required xmlid: %s" % xmlid)
    return record


def _bind_xmlid(env, name, record):
    imd = env["ir.model.data"].sudo()
    row = imd.search([("module", "=", MODULE), ("name", "=", name)], limit=1)
    values = {"model": record._name, "res_id": record.id, "noupdate": True}
    if row:
        row.write(values)
    else:
        imd.create({"module": MODULE, "name": name, **values})


def _upsert(env, model_name, xmlid_name, domain, values):
    model = env[model_name].sudo().with_context(active_test=False, tracking_disable=True)
    record = env.ref("%s.%s" % (MODULE, xmlid_name), raise_if_not_found=False)
    if record and record._name != model_name:
        raise RuntimeError("xmlid %s points to %s" % (xmlid_name, record._name))
    if not record:
        matches = model.search(domain)
        if len(matches) > 1:
            raise RuntimeError("fixture domain is not unique: %s %s" % (model_name, domain))
        # Never adopt an unowned record that merely happens to share the
        # fixture's natural key.  Doing so could rewrite historical/demo data
        # outside this fixture's XML-ID namespace.  A clean acceptance
        # database creates the record below and binds its XML-ID; if a stale
        # same-name row exists, fail closed and require an explicit reset.
        if matches:
            raise RuntimeError(
                "fixture refuses to adopt unowned %s matching %s" % (model_name, domain)
            )
    if record:
        changed = {}
        for field_name, value in values.items():
            field = record._fields[field_name]
            current = record[field_name]
            if field.type == "many2one":
                is_equal = current.id == (value or False)
            elif field.type in ("one2many", "many2many"):
                is_equal = False
            else:
                is_equal = current == value
            if not is_equal:
                changed[field_name] = value
        if changed:
            record.write(changed)
    else:
        record = model.create(values)
    _bind_xmlid(env, xmlid_name, record)
    return record


def _company(env, suffix):
    name = "FE Company %s" % suffix
    return _upsert(
        env,
        "res.company",
        "fe_company_%s" % suffix.lower(),
        [("name", "=", name)],
        {
            "name": name,
            "currency_id": _ref(env, "base.CNY").id,
            "country_id": _ref(env, "base.cn").id,
        },
    )


def _user(env, login, name, company, companies, group_xmlids):
    groups = [_ref(env, "base.group_user")]
    groups.extend(_ref(env, xmlid) for xmlid in group_xmlids)
    return _upsert(
        env,
        "res.users",
        "fe_user_%s" % login.replace("fixture_role_", ""),
        [("login", "=", login)],
        {
            "name": name,
            "login": login,
            "email": "%s@example.invalid" % login,
            "active": True,
            "share": False,
            "lang": "zh_CN",
            "tz": "Asia/Shanghai",
            "company_id": company.id,
            "company_ids": [(6, 0, [item.id for item in companies])],
            "groups_id": [(6, 0, [group.id for group in groups])],
            "password": _fixture_password(),
        },
    )


def _partner(env, suffix, company):
    name = "FE-%s Counterparty" % suffix
    return _upsert(
        env,
        "res.partner",
        "fe_partner_%s" % suffix.lower(),
        [("name", "=", name), ("company_id", "=", company.id)],
        {
            "name": name,
            "company_id": company.id,
            "is_company": True,
            "company_type": "company",
            "supplier_rank": 1,
            "sc_account_name": name,
            "sc_bank_name": "FE Acceptance Bank %s" % suffix,
            "sc_bank_account": "FE-ACCEPTANCE-%s-001" % suffix,
        },
    )


def _tax(env, suffix, company):
    helper = env["construction.contract"].sudo().with_company(company)
    group = helper._sc_contract_tax_group(company)
    name = helper._sc_format_contract_tax_name(13.0)
    return _upsert(
        env,
        "account.tax",
        "fe_tax_%s" % suffix.lower(),
        [
            ("company_id", "=", company.id),
            ("type_tax_use", "=", "none"),
            ("amount_type", "=", "percent"),
            ("amount", "=", 13.0),
        ],
        {
            "name": name,
            "company_id": company.id,
            "country_id": company.account_fiscal_country_id.id or _ref(env, "base.cn").id,
            "tax_group_id": group.id,
            "amount": 13.0,
            "amount_type": "percent",
            "type_tax_use": "none",
            "price_include": False,
            "active": True,
        },
    )


def _project(env, suffix, company, manager, partner):
    name = "FE Project %s" % suffix
    values = {
        "name": name,
        "code": "FE-%s" % suffix,
        "company_id": company.id,
        "partner_id": partner.id,
        "user_id": manager.id,
        "manager_id": manager.id,
        "privacy_visibility": "followers",
        "funding_enabled": True,
        "active": True,
    }
    if "project_code" in env["project.project"]._fields:
        values["project_code"] = "FE-%s" % suffix
    return _upsert(
        env,
        "project.project",
        "fe_project_%s" % suffix.lower(),
        [("name", "=", name), ("company_id", "=", company.id)],
        values,
    )


def _funding_baseline(env, suffix, project):
    return _upsert(
        env,
        "project.funding.baseline",
        "fe_funding_baseline_%s" % suffix.lower(),
        [("project_id", "=", project.id), ("state", "=", "active")],
        {
            "project_id": project.id,
            "total_amount": 5000.0,
            "state": "active",
        },
    )


def _contract(env, suffix, project, partner, tax, state, amount):
    subject = "FE-%s Contract" % suffix
    record = _upsert(
        env,
        "construction.contract",
        "fe_contract_%s" % suffix.lower(),
        [("subject", "=", subject), ("project_id", "=", project.id)],
        {
            "subject": subject,
            "type": "in",
            "project_id": project.id,
            "partner_id": partner.id,
            "company_id": project.company_id.id,
            "currency_id": project.company_id.currency_id.id,
            "tax_id": tax.id,
            "contract_payment_method_text": "按审定结算金额扣除应扣款项后支付",
            "state": state,
            "active": True,
        },
    )
    line = _upsert(
        env,
        "construction.contract.line",
        "fe_contract_line_%s" % suffix.lower(),
        [("contract_id", "=", record.id), ("note", "=", "FE-%s fixed line" % suffix)],
        {
            "contract_id": record.id,
            "qty_contract": 1.0,
            "price_contract": amount,
            "note": "FE-%s fixed line" % suffix,
        },
    )
    record.invalidate_recordset()
    return record, line


def _general_contract(env, suffix, project, partner, tax, state, amount):
    contract_name = "FE-%s General Contract" % suffix
    return _upsert(
        env,
        "sc.general.contract",
        "fe_general_contract_%s" % suffix.lower(),
        [("contract_name", "=", contract_name), ("project_id", "=", project.id)],
        {
            "contract_name": contract_name,
            "project_id": project.id,
            "company_id": project.company_id.id,
            "partner_id": partner.id,
            "contract_type": "工程服务",
            "contract_attribute": "一般合同",
            "contract_direction": "income" if suffix == "A" else "expense",
            "contract_date": "2026-07-%02d" % ({"A": 8, "B": 15, "C": 22}[suffix]),
            "amount_total": amount,
            "amount_untaxed": round(amount / 1.13, 2),
            "tax_id": tax.id,
            "tax_rate": 13.0,
            "currency_id": project.company_id.currency_id.id,
            "state": state,
            "handler_id": project.user_id.id,
            "active": True,
        },
    )


def _settlement(env, suffix, project, contract, partner, state, amount):
    name = "FE-%s-SET-001" % suffix
    record = _upsert(
        env,
        "sc.settlement.order",
        "fe_settlement_%s" % suffix.lower(),
        [("name", "=", name), ("project_id", "=", project.id)],
        {
            "name": name,
            "title": "FE-%s Settlement" % suffix,
            "project_id": project.id,
            "contract_id": contract.id,
            "partner_id": partner.id,
            "settlement_unit_id": partner.id,
            "settlement_type": "out",
            "company_id": project.company_id.id,
            "currency_id": project.company_id.currency_id.id,
            "settlement_period_start": "2026-07-01",
            "settlement_period_end": "2026-07-31",
            "submitted_amount": amount,
            "approved_amount": amount,
            "state": state,
        },
    )
    _upsert(
        env,
        "sc.settlement.order.line",
        "fe_settlement_line_%s" % suffix.lower(),
        [("settlement_id", "=", record.id), ("name", "=", "FE-%s fixed line" % suffix)],
        {
            "settlement_id": record.id,
            "contract_id": contract.id,
            "name": "FE-%s fixed line" % suffix,
            "qty": 1.0,
            "price_unit": amount,
        },
    )
    record.invalidate_recordset()
    return record


def _request(env, suffix, sequence, project, contract, settlement, partner, state, amount):
    name = "FE-%s-PR-%03d" % (suffix, sequence)
    xmlid_name = "fe_request_%s_%03d" % (suffix.lower(), sequence)
    category = _ref(env, "smart_construction_core.business_category_finance_payment_apply_pay")
    validation_status = "validated" if state in ("approved", "done") else "no"
    existing = env.ref(
        "%s.%s" % (MODULE, xmlid_name), raise_if_not_found=False
    )
    if existing:
        # A completed browser journey can leave this fixture-owned request in
        # done/approved with OCA reviews. Restore only the disposable row to an
        # ORM-editable phase, reconcile its facts through _upsert, then freeze
        # the requested workflow state below. Product state guards stay intact.
        existing.sudo().review_ids.unlink()
        env["mail.activity"].sudo().search(
            [("res_model", "=", "payment.request"), ("res_id", "=", existing.id)]
        ).unlink()
        env.cr.execute(
            "UPDATE payment_request "
            "SET state='draft', validation_status='no', reject_reason=NULL "
            "WHERE id=%s",
            (existing.id,),
        )
        existing.invalidate_recordset(
            ["state", "validation_status", "reject_reason"]
        )
    record = _upsert(
        env,
        "payment.request",
        xmlid_name,
        [("name", "=", name), ("project_id", "=", project.id)],
        {
            "name": name,
            "type": "pay",
            "business_category_id": category.id,
            "project_id": project.id,
            "contract_id": contract.id,
            "settlement_id": settlement.id,
            "partner_id": partner.id,
            "currency_id": project.company_id.currency_id.id,
            "amount": amount,
            # A payment request owns an immutable account snapshot.  Keeping
            # only the partner default would make the form look incomplete
            # even though the execution guard can resolve a fallback.
            "actual_payee_unit": partner.name,
            "payment_account_name": partner.sc_account_name,
            "payment_bank_name": partner.sc_bank_name,
            "payment_account_no": partner.sc_bank_account,
            "note": "FE-%s deterministic payment request" % suffix,
        },
    )
    # Business state and tier-validation state are one workflow fact. Freeze
    # them together after all editable facts have been reconciled.
    env.cr.execute(
        "UPDATE payment_request SET state=%s, validation_status=%s WHERE id=%s",
        (state, validation_status, record.id),
    )
    record.invalidate_recordset(["state", "validation_status"])
    return record


def _execution(env, suffix, project, contract, request, partner, finance, state, amount):
    name = "FE-%s-PE-001" % suffix
    return _upsert(
        env(user=finance.id),
        "sc.payment.execution",
        "fe_execution_%s" % suffix.lower(),
        [("name", "=", name), ("project_id", "=", project.id)],
        {
            "name": name,
            "project_id": project.id,
            "contract_id": contract.id,
            "payment_request_id": request.id,
            "partner_id": partner.id,
            "currency_id": project.company_id.currency_id.id,
            "planned_amount": amount,
            "paid_amount": amount if state == "paid" else 0.0,
            "state": state,
            "document_no": name,
            "note": "FE-%s deterministic payment execution" % suffix,
            "active": True,
        },
    )
def _reconcile_payment_facts(env, requests, finance):
    """Return fixture requests to a reusable state without deleting finance facts."""
    requests = requests.exists()
    if not requests:
        return
    executions = env["sc.payment.execution"].sudo().search([
        ("payment_request_id", "in", requests.ids),
        ("active", "=", True),
        ("state", "!=", "cancel"),
    ])
    for execution in executions:
        actor_execution = execution.with_user(finance)
        if execution.state == "paid":
            actor_execution.write({
                "reversal_reason": "验收夹具复原：保留原付款事实并执行受控冲销",
            })
        actor_execution.action_cancel()
    posted_ledgers = env["payment.ledger"].sudo().search([
        ("payment_request_id", "in", requests.ids),
        ("state", "=", "posted"),
    ])
    if posted_ledgers:
        raise RuntimeError(
            "fixture found posted payment ledgers without a reversible active execution: %s"
            % posted_ledgers.ids
        )


def _payment_journey(env, project, contract, partner, finance):
    """Reconcile the isolated FE-B04/B05 mutation journeys to deterministic starts."""
    settlement = _upsert(
        env,
        "sc.settlement.order",
        "fe_journey_settlement_a",
        [("name", "=", "FE-JOURNEY-SETTLEMENT-001"), ("project_id", "=", project.id)],
        {
            "name": "FE-JOURNEY-SETTLEMENT-001",
            "title": "FE Journey Settlement",
            "project_id": project.id,
            "contract_id": contract.id,
            "partner_id": partner.id,
            "settlement_unit_id": partner.id,
            "settlement_type": "out",
            "company_id": project.company_id.id,
            "currency_id": project.company_id.currency_id.id,
            "settlement_period_start": "2026-07-01",
            "settlement_period_end": "2026-07-31",
            "submitted_amount": 200.0,
            "approved_amount": 200.0,
            "state": "approve",
        },
    )
    _upsert(
        env,
        "sc.settlement.order.line",
        "fe_journey_settlement_line_a",
        [("settlement_id", "=", settlement.id), ("name", "=", "FE Journey payable line")],
        {
            "settlement_id": settlement.id,
            "contract_id": contract.id,
            "name": "FE Journey payable line",
            "qty": 1.0,
            "price_unit": 100.0,
        },
    )
    # J06 mutates its request.  Keep it on a dedicated settlement so the
    # following J07 My Work journey still sees its own request in draft.
    j06_settlement = _upsert(
        env,
        "sc.settlement.order",
        "fe_j06_settlement_a",
        [("name", "=", "FE-J06-SETTLEMENT-001"), ("project_id", "=", project.id)],
        {
            "name": "FE-J06-SETTLEMENT-001",
            "title": "FE J06 Financial Workspace Settlement",
            "project_id": project.id,
            "contract_id": contract.id,
            "partner_id": partner.id,
            "settlement_unit_id": partner.id,
            "settlement_type": "out",
            "company_id": project.company_id.id,
            "currency_id": project.company_id.currency_id.id,
            "settlement_period_start": "2026-07-01",
            "settlement_period_end": "2026-07-31",
            "submitted_amount": 200.0,
            "approved_amount": 200.0,
            "state": "approve",
        },
    )
    _upsert(
        env,
        "sc.settlement.order.line",
        "fe_j06_settlement_line_a",
        [("settlement_id", "=", j06_settlement.id), ("name", "=", "FE J06 payable line")],
        {
            "settlement_id": j06_settlement.id,
            "contract_id": contract.id,
            "name": "FE J06 payable line",
            "qty": 1.0,
            "price_unit": 100.0,
        },
    )
    # FE-B05 approval probes use an isolated settlement so their reserved
    # amounts cannot change the FE-B04 journey's fixed 100.00 balance.
    work_settlement = _upsert(
        env,
        "sc.settlement.order",
        "fe_b05_work_settlement_a",
        [("name", "=", "FE-B05-WORK-SETTLEMENT-001"), ("project_id", "=", project.id)],
        {
            "name": "FE-B05-WORK-SETTLEMENT-001",
            "title": "FE B05 Work Settlement",
            "project_id": project.id,
            "contract_id": contract.id,
            "partner_id": partner.id,
            "settlement_unit_id": partner.id,
            "settlement_type": "out",
            "company_id": project.company_id.id,
            "currency_id": project.company_id.currency_id.id,
            "settlement_period_start": "2026-07-01",
            "settlement_period_end": "2026-07-31",
            "submitted_amount": 200.0,
            "approved_amount": 200.0,
            "state": "approve",
        },
    )
    _upsert(
        env,
        "sc.settlement.order.line",
        "fe_b05_work_settlement_line_a",
        [("settlement_id", "=", work_settlement.id), ("name", "=", "FE B05 work payable line")],
        {
            "settlement_id": work_settlement.id,
            "contract_id": contract.id,
            "name": "FE B05 work payable line",
            "qty": 1.0,
            "price_unit": 200.0,
        },
    )
    # Browser-created FE-B05 requests are real intent mutations and therefore
    # receive sequence numbers rather than stable XML IDs.  Acceptance reset
    # removes only rows created from this isolated settlement by the finance
    # fixture actor, keeping repeat runs and work-item counts deterministic.
    transient_requests = env["payment.request"].sudo().search([
        ("settlement_id", "=", work_settlement.id),
        ("create_uid", "=", finance.id),
        ("name", "not in", [
            "FE-JOURNEY-APPROVAL-001",
            "FE-JOURNEY-REJECT-001",
            "FE-JOURNEY-COMPLETED-001",
        ]),
    ])
    if transient_requests:
        _reconcile_payment_facts(env, transient_requests, finance)
        historical_requests = transient_requests.filtered(
            lambda row: bool(env["payment.ledger"].sudo().search_count([
                ("payment_request_id", "=", row.id),
            ]))
        )
        transient_requests = transient_requests - historical_requests
        transient_requests.sudo().review_ids.unlink()
        env["mail.activity"].sudo().search([
            ("res_model", "=", "payment.request"),
            ("res_id", "in", transient_requests.ids),
        ]).unlink()
        env["ir.attachment"].sudo().search([
            ("res_model", "=", "payment.request"),
            ("res_id", "in", transient_requests.ids),
        ]).unlink()
        env.cr.execute(
            "UPDATE payment_request SET state='draft', validation_status='no' WHERE id = ANY(%s)",
            (transient_requests.ids,),
        )
        transient_requests.invalidate_recordset(["state", "validation_status"])
        transient_requests.sudo().unlink()
    category = _ref(env, "smart_construction_core.business_category_finance_payment_apply_pay")
    existing_j06_request = env.ref(
        "%s.fe_j06_payment_request_a" % MODULE,
        raise_if_not_found=False,
    )
    if existing_j06_request:
        _reconcile_payment_facts(env, existing_j06_request, finance)
        existing_j06_request.sudo().review_ids.unlink()
        env["mail.activity"].sudo().search([
            ("res_model", "=", "payment.request"),
            ("res_id", "=", existing_j06_request.id),
        ]).unlink()
        env.cr.execute(
            "UPDATE payment_request SET state=%s, validation_status=%s WHERE id=%s",
            ("draft", "no", existing_j06_request.id),
        )
        existing_j06_request.invalidate_recordset(["state", "validation_status"])
    j06_request = _upsert(
        env,
        "payment.request",
        "fe_j06_payment_request_a",
        [("name", "=", "FE-J06-PAYMENT-001"), ("project_id", "=", project.id)],
        {
            "name": "FE-J06-PAYMENT-001",
            "type": "pay",
            "business_category_id": category.id,
            "project_id": project.id,
            "contract_id": contract.id,
            "settlement_id": j06_settlement.id,
            "partner_id": partner.id,
            "currency_id": project.company_id.currency_id.id,
            "amount": 100.0,
            "state": "draft",
            "note": "FE-B04 isolated financial workspace mutation",
        },
    )
    env.cr.execute(
        "UPDATE payment_request SET create_uid=%s WHERE id=%s",
        (finance.id, j06_request.id),
    )
    j06_request.invalidate_recordset(["create_uid"])
    existing_request = env.ref(
        "%s.fe_journey_payment_request_a" % MODULE,
        raise_if_not_found=False,
    )
    if existing_request:
        _reconcile_payment_facts(env, existing_request, finance)
        existing_request.sudo().message_ids.unlink()
        existing_request.sudo().review_ids.unlink()
        env["mail.activity"].sudo().search([
            ("res_model", "=", "payment.request"),
            ("res_id", "=", existing_request.id),
        ]).unlink()
        # Acceptance reset is deliberately out-of-band: the journey itself must
        # exercise the guarded intent, while setup must be able to restore the
        # same pre-transition row after a previous successful browser run.
        env.cr.execute(
            "UPDATE payment_request SET state=%s, validation_status=%s WHERE id=%s",
            ("draft", "no", existing_request.id),
        )
        existing_request.invalidate_recordset(["state", "validation_status"])
    request = _upsert(
        env,
        "payment.request",
        "fe_journey_payment_request_a",
        [("name", "=", "FE-JOURNEY-PAYMENT-001"), ("project_id", "=", project.id)],
        {
            "name": "FE-JOURNEY-PAYMENT-001",
            "type": "pay",
            "business_category_id": category.id,
            "project_id": project.id,
            "contract_id": contract.id,
            "settlement_id": settlement.id,
            "partner_id": partner.id,
            "currency_id": project.company_id.currency_id.id,
            "amount": 100.0,
            "state": "draft",
            "note": "FE-B04 isolated permitted action journey",
        },
    )
    env.cr.execute(
        "UPDATE payment_request SET create_uid=%s WHERE id=%s",
        (finance.id, request.id),
    )
    request.invalidate_recordset(["create_uid"])
    attachment = _upsert(
        env,
        "ir.attachment",
        "fe_journey_payment_request_attachment_a",
        [("name", "=", "FE-JOURNEY-PAYMENT-001.txt"), ("res_model", "=", "payment.request"), ("res_id", "=", request.id)],
        {
            "name": "FE-JOURNEY-PAYMENT-001.txt",
            "type": "binary",
            "datas": "RkUtQjA1IGF1dGhvcml0YXRpdmUgam91cm5leSBhdHRhY2htZW50",
            "res_model": "payment.request",
            "res_id": request.id,
            "mimetype": "text/plain",
        },
    )
    request.sudo().write({"attachment_ids": [(6, 0, [attachment.id])]})

    def _approval_request(xmlid_name, name, state):
        existing = env.ref(
            "%s.%s" % (MODULE, xmlid_name),
            raise_if_not_found=False,
        )
        if existing:
            # Browser journeys legitimately leave these fixture-owned rows in
            # submitted/approved states.  Restore the disposable row to the
            # only ORM-editable phase before _upsert aligns its business facts;
            # never weaken payment.request.write() for fixture administration.
            env.cr.execute(
                "UPDATE payment_request "
                "SET state='draft', validation_status='no', reject_reason=NULL "
                "WHERE id=%s",
                (existing.id,),
            )
            existing.invalidate_recordset(
                ["state", "validation_status", "reject_reason"]
            )
        row = _upsert(
            env,
            "payment.request",
            xmlid_name,
            [("name", "=", name), ("project_id", "=", project.id)],
            {
                "name": name,
                "type": "pay",
                "business_category_id": category.id,
                "project_id": project.id,
                "contract_id": contract.id,
                "settlement_id": work_settlement.id,
                "partner_id": partner.id,
                "currency_id": project.company_id.currency_id.id,
                "amount": 20.0,
                "note": "FE-B05 isolated approval journey",
            },
        )
        row.sudo().review_ids.unlink()
        env["mail.activity"].sudo().search([
            ("res_model", "=", "payment.request"),
            ("res_id", "=", row.id),
        ]).unlink()
        env.cr.execute(
            "UPDATE payment_request SET state=%s, validation_status=%s, create_uid=%s WHERE id=%s",
            (
                state,
                "validated" if state in ("approved", "done") else "no",
                finance.id,
                row.id,
            ),
        )
        row.invalidate_recordset(["state", "validation_status", "create_uid"])
        return row

    approval_request = _approval_request(
        "fe_journey_payment_request_approval_a",
        "FE-JOURNEY-APPROVAL-001",
        "submit",
    )
    reject_request = _approval_request(
        "fe_journey_payment_request_reject_a",
        "FE-JOURNEY-REJECT-001",
        "submit",
    )
    completed_request = _approval_request(
        "fe_journey_payment_request_completed_a",
        "FE-JOURNEY-COMPLETED-001",
        "approved",
    )
    hardening_request = _approval_request(
        "fe_delivery_hardening_payment_request_a",
        "FE-DELIVERY-HARDENING-001",
        "draft",
    )
    core_form_request = _approval_request(
        "fe_core_form_payment_request_a",
        "FE-CORE-FORM-CONFLICT-001",
        "draft",
    )
    _reconcile_payment_facts(env, request, finance)
    request.invalidate_recordset()
    settlement.invalidate_recordset()
    j06_request.invalidate_recordset()
    j06_settlement.invalidate_recordset()
    return (
        settlement,
        request,
        j06_settlement,
        j06_request,
        approval_request,
        reject_request,
        completed_request,
        hardening_request,
        core_form_request,
    )


def ensure_fixture(env) -> Dict[str, Any]:
    _guard_acceptance_scope(env)
    """Create or reconcile the fixed dataset and return a secret-free summary."""
    module = env["ir.module.module"].sudo().search([("name", "=", MODULE)], limit=1)
    if not module or module.state != "installed":
        raise RuntimeError("smart_construction_acceptance_fixture must be installed before fixture initialization")

    company_a = _company(env, "A")
    company_b = _company(env, "B")

    finance = _user(
        env,
        "fixture_role_finance",
        "Acceptance Fixture Finance",
        company_a,
        [company_a, company_b],
        ["smart_construction_core.group_sc_role_finance_manager"],
    )
    finance_user = _user(
        env,
        "fixture_role_pfl035_finance_user",
        "PFL-035 Finance User",
        company_a,
        [company_a],
        ["smart_construction_core.group_sc_role_finance_user"],
    )
    empty_finance = _user(
        env,
        "fixture_role_pfl035_empty_finance",
        "PFL-035 Empty Finance User",
        company_a,
        [company_a],
        ["smart_construction_core.group_sc_role_finance_user"],
    )

    # PFL-035 must exercise the real base_tier_validation runtime.  The
    # company-specific policy wins over generic templates and is owned by the
    # disposable acceptance fixture, so repeated resets remain deterministic.
    finance_manager_group = _ref(
        env, "smart_construction_core.group_sc_cap_finance_manager"
    )
    pfl035_execution_policy = _upsert(
        env,
        "sc.approval.policy",
        "fe_pfl035_payment_execution_approval_policy",
        [
            ("target_model", "=", "sc.payment.execution"),
            ("company_id", "=", company_a.id),
        ],
        {
            "name": "PFL-035 付款执行审批",
            "code": "fe_pfl035_payment_execution_approval",
            "active": True,
            "sequence": 10,
            "company_id": company_a.id,
            "target_model": "sc.payment.execution",
            "approval_required": True,
            "trigger": "submit",
            "mode": "single",
            "runtime_state": "tier_validation",
            "manager_scope_key": "finance_manager",
            "manager_group_id": finance_manager_group.id,
            "note": "PFL-035 acceptance: finance user submits and finance manager reviews through OCA tier validation.",
        },
    )
    pfl035_execution_step = _upsert(
        env,
        "sc.approval.step",
        "fe_pfl035_payment_execution_approval_step",
        [
            ("policy_id", "=", pfl035_execution_policy.id),
            ("name", "=", "财务经理审批"),
        ],
        {
            "policy_id": pfl035_execution_policy.id,
            "active": True,
            "sequence": 10,
            "name": "财务经理审批",
            "approval_scope_key": "finance_manager",
            "approve_group_id": finance_manager_group.id,
            "condition_note": "全部 PFL-035 付款执行由财务经理审批",
        },
    )
    pfl035_execution_policy.sync_tier_definitions()
    project_member = _user(
        env,
        "fixture_role_project_a_member",
        "Acceptance Fixture Project A Member",
        company_a,
        [company_a],
        [
            "smart_construction_core.group_sc_cap_project_read",
            "smart_construction_core.group_sc_cap_business_initiator",
        ],
    )
    pm = _user(
        env,
        "fixture_role_pm",
        "Acceptance Fixture PM",
        company_a,
        [company_a],
        ["smart_construction_core.group_sc_role_project_manager"],
    )
    contract_operator = _user(
        env,
        "fixture_role_contract_operator",
        "Acceptance Fixture Contract Operator",
        company_a,
        [company_a],
        ["smart_construction_core.group_sc_role_operation_user"],
    )
    config_admin = _user(
        env,
        "fixture_role_config_admin",
        "Acceptance Fixture Business Config Admin",
        company_a,
        [company_a],
        ["smart_construction_core.group_sc_role_business_admin"],
    )
    config_admin_peer = _user(
        env,
        "fixture_role_config_admin_peer",
        "Acceptance Fixture Business Config Admin Peer",
        company_a,
        [company_a],
        ["smart_construction_core.group_sc_role_business_admin"],
    )
    owner = _user(
        env,
        "fixture_role_owner",
        "Acceptance Fixture Owner",
        company_a,
        [company_a],
        ["smart_construction_core.group_sc_role_owner"],
    )
    executive = _user(
        env,
        "fixture_role_executive",
        "Acceptance Fixture Executive",
        company_a,
        [company_a],
        ["smart_construction_core.group_sc_role_executive"],
    )

    partner_a = _partner(env, "A", company_a)
    partner_b = _partner(env, "B", company_a)
    partner_c = _partner(env, "C", company_b)
    tax_a = _tax(env, "A", company_a)
    tax_b = _tax(env, "B", company_b)
    project_a = _project(env, "A", company_a, pm, partner_a)
    project_b = _project(env, "B", company_a, pm, partner_b)
    project_c = _project(env, "C", company_b, finance, partner_c)

    # Reconcile only follower rows attached to projects owned by this fixture.
    follower_model = env["mail.followers"].sudo()
    fixture_partners = [project_member.partner_id.id, pm.partner_id.id]
    follower_model.search(
        [
            ("res_model", "=", "project.project"),
            ("res_id", "in", [project_a.id, project_b.id, project_c.id]),
            ("partner_id", "in", fixture_partners),
        ]
    ).unlink()
    project_a.message_subscribe(partner_ids=[project_member.partner_id.id, pm.partner_id.id])
    project_b.message_subscribe(partner_ids=[pm.partner_id.id])
    project_a.message_subscribe(partner_ids=[finance_user.partner_id.id])

    _funding_baseline(env, "A", project_a)
    _funding_baseline(env, "B", project_b)
    _funding_baseline(env, "C", project_c)

    contract_a, _ = _contract(env, "A", project_a, partner_a, tax_a, "confirmed", 1000.0)
    contract_b, _ = _contract(env, "B", project_b, partner_b, tax_a, "draft", 1000.0)
    contract_c, _ = _contract(env, "C", project_c, partner_c, tax_b, "confirmed", 1000.0)
    _general_contract(env, "A", project_a, partner_a, tax_a, "signed", 2680000.0)
    _general_contract(env, "B", project_b, partner_b, tax_a, "confirmed", 985000.0)
    _general_contract(env, "C", project_c, partner_c, tax_b, "draft", 460000.0)
    settlement_a = _settlement(env, "A", project_a, contract_a, partner_a, "approve", 1000.0)
    settlement_b = _settlement(env, "B", project_b, contract_b, partner_b, "draft", 1000.0)
    settlement_c = _settlement(env, "C", project_c, contract_c, partner_c, "approve", 1000.0)
    request_a = _request(env, "A", 1, project_a, contract_a, settlement_a, partner_a, "approved", 1000.0)
    _request(env, "A", 2, project_a, contract_a, settlement_a, partner_a, "draft", 250.0)
    request_b = _request(env, "B", 1, project_b, contract_b, settlement_b, partner_b, "draft", 1000.0)
    request_c = _request(env, "C", 1, project_c, contract_c, settlement_c, partner_c, "approved", 1000.0)
    env.cr.execute(
        "UPDATE payment_request SET validation_status=%s, create_uid=%s WHERE id=%s",
        ("validated", finance.id, request_c.id),
    )
    request_c.invalidate_recordset(["validation_status", "create_uid"])
    _execution(env, "A", project_a, contract_a, request_a, partner_a, finance, "paid", 1000.0)
    _execution(env, "C", project_c, contract_c, request_c, partner_c, finance, "confirmed", 1000.0)

    # PFL-035 owns isolated records for authoritative positive and rejection
    # paths.  They must not reuse records that already have an execution.
    pfl035_settlement = _settlement(
        env, "PFL035", project_a, contract_a, partner_a, "approve", 1000.0
    )
    pfl035_approved = _request(
        env, "PFL035", 1, project_a, contract_a, pfl035_settlement, partner_a, "approved", 80.0
    )
    _reconcile_payment_facts(env, pfl035_approved, finance)
    pfl035_draft = _request(
        env, "PFL035", 2, project_a, contract_a, pfl035_settlement, partner_a, "draft", 40.0
    )

    income_contract = _upsert(
        env,
        "construction.contract",
        "fe_pfl035_income_contract",
        [("subject", "=", "PFL-035 Income Contract"), ("project_id", "=", project_a.id)],
        {
            "subject": "PFL-035 Income Contract",
            "type": "out",
            "project_id": project_a.id,
            "partner_id": partner_a.id,
            "company_id": company_a.id,
            "currency_id": company_a.currency_id.id,
            "tax_id": tax_a.id,
        },
    )
    pfl035_receive = _upsert(
        env,
        "payment.request",
        "fe_pfl035_receive_request",
        [("name", "=", "FE-PFL035-RECEIVE-001"), ("project_id", "=", project_a.id)],
        {
            "name": "FE-PFL035-RECEIVE-001",
            "type": "receive",
            "business_category_id": _ref(
                env, "smart_construction_core.business_category_finance_payment_apply_receive"
            ).id,
            "project_id": project_a.id,
            "contract_id": income_contract.id,
            "partner_id": partner_a.id,
            "company_id": company_a.id,
            "currency_id": company_a.currency_id.id,
            "amount": 30.0,
            "state": "approved",
        },
    )
    incomplete_partner = _upsert(
        env,
        "res.partner",
        "fe_pfl035_incomplete_partner",
        [("name", "=", "PFL-035 Incomplete Payee"), ("company_id", "=", company_a.id)],
        {
            "name": "PFL-035 Incomplete Payee",
            "company_id": company_a.id,
            "is_company": True,
            "supplier_rank": 1,
            "sc_account_name": False,
            "sc_bank_name": False,
            "sc_bank_account": False,
        },
    )
    incomplete_contract = _upsert(
        env,
        "construction.contract",
        "fe_pfl035_incomplete_contract",
        [("subject", "=", "PFL-035 Incomplete Account Contract"), ("project_id", "=", project_a.id)],
        {
            "subject": "PFL-035 Incomplete Account Contract",
            "type": "in",
            "project_id": project_a.id,
            "partner_id": incomplete_partner.id,
            "company_id": company_a.id,
            "currency_id": company_a.currency_id.id,
            "tax_id": tax_a.id,
        },
    )
    pfl035_incomplete = _upsert(
        env,
        "payment.request",
        "fe_pfl035_incomplete_request",
        [("name", "=", "FE-PFL035-INCOMPLETE-001"), ("project_id", "=", project_a.id)],
        {
            "name": "FE-PFL035-INCOMPLETE-001",
            "type": "pay",
            "business_category_id": _ref(
                env, "smart_construction_core.business_category_finance_payment_apply_pay"
            ).id,
            "project_id": project_a.id,
            "contract_id": incomplete_contract.id,
            "partner_id": incomplete_partner.id,
            "company_id": company_a.id,
            "currency_id": company_a.currency_id.id,
            "amount": 20.0,
            "state": "approved",
            "payment_account_name": False,
            "payment_bank_name": False,
            "payment_account_no": False,
        },
    )
    (
        journey_settlement,
        journey_request,
        j06_settlement,
        j06_request,
        approval_request,
        reject_request,
        completed_request,
        hardening_request,
        core_form_request,
    ) = _payment_journey(
        env,
        project_a,
        contract_a,
        partner_a,
        finance,
    )

    return {
        "db": env.cr.dbname,
        "users": [
            finance.login,
            finance_user.login,
            empty_finance.login,
            project_member.login,
            pm.login,
            contract_operator.login,
            config_admin.login,
            config_admin_peer.login,
            owner.login,
            executive.login,
        ],
        "companies": [company_a.name, company_b.name],
        "projects": [project_a.name, project_b.name, project_c.name],
        "records": {
            "contracts": 3,
            "general_contracts": 3,
            "settlements": 3,
            "payment_requests": 4,
            "payment_executions": 2,
        },
        "journey": {
            "settlement": journey_settlement.name,
            "payment_request": journey_request.name,
            "state": journey_request.state,
            "ledger_count": len(journey_request.ledger_line_ids),
            "j06_settlement": j06_settlement.name,
            "j06_payment_request": j06_request.name,
            "j06_state": j06_request.state,
            "j06_ledger_count": len(j06_request.ledger_line_ids),
            "approval_request": approval_request.name,
            "reject_request": reject_request.name,
            "completed_request": completed_request.name,
            "hardening_request": hardening_request.name,
            "core_form_request": core_form_request.name,
        },
        "pfl035": {
            "approved": pfl035_approved.name,
            "draft": pfl035_draft.name,
            "receive": pfl035_receive.name,
            "incomplete": pfl035_incomplete.name,
            "execution_approval_policy": pfl035_execution_policy.code,
            "execution_approval_step": pfl035_execution_step.name,
            "oca_tier_definition": pfl035_execution_step.tier_definition_id.name,
        },
    }
