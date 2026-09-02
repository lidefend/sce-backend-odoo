"""Converge terminal cash uniqueness indexes after the model init path."""


def migrate(cr, installed_version):
    del installed_version
    cr.execute(
        "LOCK TABLE payment_request, sc_receipt_income, sc_expense_claim "
        "IN SHARE ROW EXCLUSIVE MODE"
    )
    cr.execute("DROP INDEX IF EXISTS sc_receipt_income_one_normalized_terminal_per_request_idx")
    cr.execute("DROP INDEX IF EXISTS sc_expense_claim_one_normalized_terminal_per_request_idx")
    cr.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS sc_receipt_income_one_canonical_terminal_per_request_idx
            ON sc_receipt_income(payment_request_id)
         WHERE payment_request_id IS NOT NULL
           AND finance_identity_state IN ('normalized', 'legacy_observed_identity')
           AND state IN ('received', 'legacy_confirmed')
        """
    )
    cr.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS sc_expense_claim_one_canonical_terminal_per_request_idx
            ON sc_expense_claim(payment_request_id)
         WHERE payment_request_id IS NOT NULL
           AND finance_identity_state IN ('normalized', 'legacy_observed_identity')
           AND state IN ('done', 'legacy_confirmed')
           AND financial_flow IN ('cash_in', 'cash_out')
        """
    )
