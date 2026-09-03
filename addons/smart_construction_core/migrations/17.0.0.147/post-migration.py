"""Enforce one normalized terminal cash source per payment request."""


def migrate(cr, installed_version):
    del installed_version
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
