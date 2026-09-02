"""Freeze observable finance identities without asserting unproved normalization."""


def _add_identity_state(cr, table):
    cr.execute(
        f"""
        ALTER TABLE {table}
          ADD COLUMN IF NOT EXISTS finance_identity_state varchar
        """
    )


def _quarantine_existing_source(cr, table):
    cr.execute(
        f"""
        UPDATE {table}
           SET finance_identity_state = 'legacy_unresolved_identity'
         WHERE finance_identity_state IS NULL
        """
    )


def migrate(cr, installed_version):
    del installed_version
    for table in (
        "sc_expense_claim",
        "sc_tax_deduction_registration",
        "sc_self_funding_registration",
        "sc_receipt_income",
    ):
        _add_identity_state(cr, table)
        _quarantine_existing_source(cr, table)

    cr.execute(
        """
        ALTER TABLE sc_treasury_ledger
          ADD COLUMN IF NOT EXISTS company_id integer,
          ADD COLUMN IF NOT EXISTS normalization_state varchar
        """
    )
    cr.execute(
        """
        UPDATE sc_treasury_ledger
           SET normalization_state = 'legacy_unresolved_identity'
         WHERE normalization_state IS NULL
        """
    )

    cr.execute(
        """
        ALTER TABLE tender_guarantee
          ADD COLUMN IF NOT EXISTS company_id integer,
          ADD COLUMN IF NOT EXISTS partner_id integer,
          ADD COLUMN IF NOT EXISTS treasury_ledger_id integer,
          ADD COLUMN IF NOT EXISTS finance_identity_state varchar
        """
    )
    cr.execute(
        """
        UPDATE tender_guarantee
           SET finance_identity_state = 'legacy_unresolved_identity'
         WHERE finance_identity_state IS NULL
        """
    )
