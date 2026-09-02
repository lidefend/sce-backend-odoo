"""Backfill the payment-request terminal cash-source authority claim."""


def migrate(cr, installed_version):
    del installed_version
    cr.execute(
        "LOCK TABLE payment_request, sc_receipt_income, sc_expense_claim "
        "IN SHARE ROW EXCLUSIVE MODE"
    )
    cr.execute(
        """
        UPDATE payment_request request
           SET terminal_cash_source_model = 'sc.receipt.income',
               terminal_cash_source_res_id = receipt.id
          FROM sc_receipt_income receipt
         WHERE request.id = receipt.payment_request_id
           AND receipt.finance_identity_state IN (
               'normalized', 'legacy_observed_identity'
           )
           AND receipt.state IN ('received', 'legacy_confirmed')
           AND receipt.active IS TRUE
           AND request.type = 'receive'
           AND receipt.project_id = request.project_id
           AND receipt.company_id = request.company_id
           AND receipt.currency_id = request.currency_id
           AND receipt.partner_id IS NOT NULL
           AND receipt.partner_id = request.partner_id
           AND receipt.contract_id IS NOT NULL
           AND receipt.contract_id = request.contract_id
           AND request.terminal_cash_source_model IS NULL
        """
    )
    cr.execute(
        """
        UPDATE payment_request request
           SET terminal_cash_source_model = 'sc.expense.claim',
               terminal_cash_source_res_id = claim.id
          FROM sc_expense_claim claim
         WHERE request.id = claim.payment_request_id
           AND claim.finance_identity_state IN (
               'normalized', 'legacy_observed_identity'
           )
           AND claim.state IN ('done', 'legacy_confirmed')
           AND claim.financial_flow IN ('cash_in', 'cash_out')
           AND claim.active IS TRUE
           AND claim.project_id = request.project_id
           AND claim.company_id = request.company_id
           AND claim.currency_id = request.currency_id
           AND claim.partner_id IS NOT NULL
           AND claim.partner_id = request.partner_id
           AND request.type = CASE
                   WHEN claim.financial_flow = 'cash_in' THEN 'receive'
                   WHEN claim.financial_flow = 'cash_out' THEN 'pay'
               END
           AND request.terminal_cash_source_model IS NULL
        """
    )
