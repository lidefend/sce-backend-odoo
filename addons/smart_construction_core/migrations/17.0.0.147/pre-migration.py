"""Quarantine identities previously inferred from mutable current relations."""


def migrate(cr, installed_version):
    del installed_version
    for table in (
        "sc_expense_claim",
        "sc_tax_deduction_registration",
        "sc_self_funding_registration",
        "sc_receipt_income",
    ):
        cr.execute(
            f"""
            UPDATE {table}
               SET finance_identity_state = 'legacy_unresolved_identity'
             WHERE finance_identity_state IS NULL
                OR finance_identity_state = 'legacy_observed_identity'
            """
        )
    cr.execute(
        """
        UPDATE sc_treasury_ledger
           SET normalization_state = 'legacy_unresolved_identity'
         WHERE normalization_state IS NULL
            OR normalization_state = 'legacy_observed_identity'
        """
    )
    cr.execute(
        """
        UPDATE tender_guarantee
           SET finance_identity_state = 'legacy_unresolved_identity'
         WHERE finance_identity_state IS NULL
            OR finance_identity_state = 'legacy_observed_identity'
        """
    )
