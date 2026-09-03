"""Quarantine ambiguous terminal cash ownership before enforcing canonical uniqueness."""


def migrate(cr, installed_version):
    del installed_version
    # Cross-model ownership is intrinsically ambiguous. Quarantine every
    # contender instead of selecting a winner from row order or current links.
    cr.execute(
        """
        CREATE TEMP TABLE sc_p1_terminal_cash_conflicts ON COMMIT DROP AS
        SELECT DISTINCT receipt.payment_request_id
          FROM sc_receipt_income receipt
          JOIN sc_expense_claim claim
            ON claim.payment_request_id = receipt.payment_request_id
         WHERE receipt.payment_request_id IS NOT NULL
           AND receipt.finance_identity_state IN ('normalized', 'legacy_observed_identity')
           AND receipt.state IN ('received', 'legacy_confirmed')
           AND claim.finance_identity_state IN ('normalized', 'legacy_observed_identity')
           AND claim.state IN ('done', 'legacy_confirmed')
           AND claim.handling_kind IN ('deduction_paid', 'deduction_refund')
        """
    )
    cr.execute(
        """
        UPDATE sc_receipt_income receipt
           SET finance_identity_state = 'legacy_unresolved_identity'
          FROM sc_p1_terminal_cash_conflicts conflicts
         WHERE receipt.payment_request_id = conflicts.payment_request_id
           AND receipt.finance_identity_state IN ('normalized', 'legacy_observed_identity')
           AND receipt.state IN ('received', 'legacy_confirmed')
        """
    )
    cr.execute(
        """
        UPDATE sc_expense_claim claim
           SET finance_identity_state = 'legacy_unresolved_identity'
          FROM sc_p1_terminal_cash_conflicts conflicts
         WHERE claim.payment_request_id = conflicts.payment_request_id
           AND claim.finance_identity_state IN ('normalized', 'legacy_observed_identity')
           AND claim.state IN ('done', 'legacy_confirmed')
           AND claim.handling_kind IN ('deduction_paid', 'deduction_refund')
        """
    )

    # If an observed historical row competes with another canonical row in the
    # same table, only the observed evidence is quarantined. Two observed rows
    # are both quarantined; no arbitrary survivor is chosen.
    cr.execute(
        """
        WITH duplicates AS (
            SELECT payment_request_id
              FROM sc_receipt_income
             WHERE payment_request_id IS NOT NULL
               AND finance_identity_state IN ('normalized', 'legacy_observed_identity')
               AND state IN ('received', 'legacy_confirmed')
             GROUP BY payment_request_id
            HAVING COUNT(*) > 1
        )
        UPDATE sc_receipt_income receipt
           SET finance_identity_state = 'legacy_unresolved_identity'
          FROM duplicates
         WHERE receipt.payment_request_id = duplicates.payment_request_id
           AND receipt.finance_identity_state = 'legacy_observed_identity'
           AND receipt.state IN ('received', 'legacy_confirmed')
        """
    )
    cr.execute(
        """
        WITH duplicates AS (
            SELECT payment_request_id
              FROM sc_expense_claim
             WHERE payment_request_id IS NOT NULL
               AND finance_identity_state IN ('normalized', 'legacy_observed_identity')
               AND state IN ('done', 'legacy_confirmed')
               AND handling_kind IN ('deduction_paid', 'deduction_refund')
             GROUP BY payment_request_id
            HAVING COUNT(*) > 1
        )
        UPDATE sc_expense_claim claim
           SET finance_identity_state = 'legacy_unresolved_identity'
          FROM duplicates
         WHERE claim.payment_request_id = duplicates.payment_request_id
           AND claim.finance_identity_state = 'legacy_observed_identity'
           AND claim.state IN ('done', 'legacy_confirmed')
           AND claim.handling_kind IN ('deduction_paid', 'deduction_refund')
        """
    )

    # A posted inbound request ledger without a canonical terminal source is
    # traceable history, but not proved cash for canonical projections.
    cr.execute(
        """
        UPDATE sc_treasury_ledger ledger
           SET normalization_state = 'legacy_unresolved_identity'
          FROM payment_request request
         WHERE request.id = ledger.payment_request_id
           AND request.type = 'receive'
           AND ledger.state = 'posted'
           AND ledger.direction = 'in'
           AND ledger.normalization_state IN ('normalized', 'legacy_observed_identity')
           AND NOT EXISTS (
               SELECT 1
                 FROM sc_receipt_income receipt
                WHERE receipt.payment_request_id = request.id
                  AND receipt.state IN ('received', 'legacy_confirmed')
                  AND receipt.finance_identity_state IN ('normalized', 'legacy_observed_identity')
           )
           AND NOT EXISTS (
               SELECT 1
                 FROM sc_expense_claim claim
                WHERE claim.payment_request_id = request.id
                  AND claim.state IN ('done', 'legacy_confirmed')
                  AND claim.finance_identity_state IN ('normalized', 'legacy_observed_identity')
                  AND claim.handling_kind IN ('deduction_paid', 'deduction_refund')
           )
        """
    )
