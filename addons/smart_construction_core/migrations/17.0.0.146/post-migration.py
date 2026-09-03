"""Add selective lookup indexes for canonical finance projection joins."""


def migrate(cr, installed_version):
    del installed_version
    cr.execute(
        """
        CREATE INDEX IF NOT EXISTS sc_treasury_ledger_posted_source_identity_idx
            ON sc_treasury_ledger
               (source_model, source_res_id, source_kind, project_id, company_id, currency_id, direction)
         WHERE state = 'posted'
        """
    )
    cr.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS sc_receipt_income_one_normalized_terminal_per_request_idx
            ON sc_receipt_income(payment_request_id)
         WHERE payment_request_id IS NOT NULL
           AND finance_identity_state = 'normalized'
           AND state = 'received'
        """
    )
    cr.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS sc_expense_claim_one_normalized_terminal_per_request_idx
            ON sc_expense_claim(payment_request_id)
         WHERE payment_request_id IS NOT NULL
           AND finance_identity_state = 'normalized'
           AND state = 'done'
           AND financial_flow IN ('cash_in', 'cash_out')
        """
    )
    cr.execute(
        """
        CREATE INDEX IF NOT EXISTS sc_treasury_ledger_posted_payment_identity_idx
            ON sc_treasury_ledger
               (payment_request_id, project_id, company_id, currency_id, direction)
         WHERE state = 'posted' AND payment_request_id IS NOT NULL
        """
    )
