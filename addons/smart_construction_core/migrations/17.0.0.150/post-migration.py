"""Quarantine guessed claims and rebuild only exact terminal cash ownership."""


def _ensure_index_shape(cr, name, columns, unique, predicate_terms, predicate_and_count, create_sql):
    cr.execute(
        """
        SELECT index.indisunique,
               ARRAY(
                   SELECT attribute.attname
                     FROM unnest(index.indkey) WITH ORDINALITY AS key(attnum, position)
                     JOIN pg_attribute attribute
                       ON attribute.attrelid = index.indrelid
                      AND attribute.attnum = key.attnum
                    ORDER BY key.position
               ),
               pg_get_expr(index.indpred, index.indrelid)
          FROM pg_class index_class
          JOIN pg_index index ON index.indexrelid = index_class.oid
         WHERE index_class.relname = %s
        """,
        [name],
    )
    row = cr.fetchone()
    predicate = "".join(
        character
        for character in str(row[2] if row else "").lower()
        if not character.isspace() and character not in '()"'
    )
    terms = [
        "".join(
            character
            for character in term.lower()
            if not character.isspace() and character not in '()"'
        )
        for term in predicate_terms
    ]
    shape_matches = bool(
        row
        and row[0] is unique
        and list(row[1] or []) == columns
        and all(term in predicate for term in terms)
        and predicate.count("and") == predicate_and_count
    )
    if shape_matches:
        return
    if row:
        cr.execute('DROP INDEX "%s"' % name.replace('"', '""'))
    cr.execute(create_sql)


def migrate(cr, installed_version):
    del installed_version
    cr.execute(
        "LOCK TABLE payment_request, sc_receipt_income, sc_expense_claim "
        "IN SHARE ROW EXCLUSIVE MODE"
    )
    cr.execute(
        """
        UPDATE sc_receipt_income receipt
           SET finance_identity_state = 'legacy_unresolved_identity'
          FROM payment_request request
         WHERE request.id = receipt.payment_request_id
           AND receipt.state IN ('received', 'legacy_confirmed')
           AND receipt.finance_identity_state IN ('normalized', 'legacy_observed_identity')
           AND NOT (
                receipt.active IS TRUE
            AND request.type = 'receive'
            AND receipt.project_id = request.project_id
            AND receipt.company_id = request.company_id
            AND receipt.currency_id = request.currency_id
            AND receipt.partner_id IS NOT NULL
            AND receipt.partner_id = request.partner_id
            AND receipt.contract_id IS NOT NULL
            AND receipt.contract_id = request.contract_id
           )
        """
    )
    cr.execute(
        """
        UPDATE sc_expense_claim claim
           SET finance_identity_state = 'legacy_unresolved_identity'
          FROM payment_request request
         WHERE request.id = claim.payment_request_id
           AND claim.state IN ('done', 'legacy_confirmed')
           AND claim.finance_identity_state IN ('normalized', 'legacy_observed_identity')
           AND NOT (
                claim.active IS TRUE
            AND claim.financial_flow IN ('cash_in', 'cash_out')
            AND claim.project_id = request.project_id
            AND claim.company_id = request.company_id
            AND claim.currency_id = request.currency_id
            AND claim.partner_id IS NOT NULL
            AND claim.partner_id = request.partner_id
            AND request.type = CASE
                    WHEN claim.financial_flow = 'cash_in' THEN 'receive'
                    WHEN claim.financial_flow = 'cash_out' THEN 'pay'
                END
           )
        """
    )
    cr.execute(
        """
        UPDATE payment_request request
           SET terminal_cash_source_model = NULL,
               terminal_cash_source_res_id = 0
         WHERE terminal_cash_source_model IS NOT NULL
           AND NOT (
                (
                    terminal_cash_source_model = 'sc.receipt.income'
                    AND EXISTS (
                        SELECT 1
                          FROM sc_receipt_income receipt
                         WHERE receipt.id = request.terminal_cash_source_res_id
                           AND receipt.payment_request_id = request.id
                           AND receipt.active IS TRUE
                           AND receipt.state IN ('received', 'legacy_confirmed')
                           AND receipt.finance_identity_state IN ('normalized', 'legacy_observed_identity')
                           AND request.type = 'receive'
                           AND receipt.project_id = request.project_id
                           AND receipt.company_id = request.company_id
                           AND receipt.currency_id = request.currency_id
                           AND receipt.partner_id IS NOT NULL
                           AND receipt.partner_id = request.partner_id
                           AND receipt.contract_id IS NOT NULL
                           AND receipt.contract_id = request.contract_id
                    )
                )
                OR
                (
                    terminal_cash_source_model = 'sc.expense.claim'
                    AND EXISTS (
                        SELECT 1
                          FROM sc_expense_claim claim
                         WHERE claim.id = request.terminal_cash_source_res_id
                           AND claim.payment_request_id = request.id
                           AND claim.active IS TRUE
                           AND claim.state IN ('done', 'legacy_confirmed')
                           AND claim.finance_identity_state IN ('normalized', 'legacy_observed_identity')
                           AND claim.financial_flow IN ('cash_in', 'cash_out')
                           AND claim.project_id = request.project_id
                           AND claim.company_id = request.company_id
                           AND claim.currency_id = request.currency_id
                           AND claim.partner_id IS NOT NULL
                           AND claim.partner_id = request.partner_id
                           AND request.type = CASE
                                   WHEN claim.financial_flow = 'cash_in' THEN 'receive'
                                   WHEN claim.financial_flow = 'cash_out' THEN 'pay'
                               END
                    )
                )
           )
        """
    )
    cr.execute(
        """
        UPDATE payment_request request
           SET terminal_cash_source_model = 'sc.receipt.income',
               terminal_cash_source_res_id = receipt.id
          FROM sc_receipt_income receipt
         WHERE request.id = receipt.payment_request_id
           AND receipt.active IS TRUE
           AND receipt.state IN ('received', 'legacy_confirmed')
           AND receipt.finance_identity_state IN ('normalized', 'legacy_observed_identity')
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
           AND claim.active IS TRUE
           AND claim.state IN ('done', 'legacy_confirmed')
           AND claim.finance_identity_state IN ('normalized', 'legacy_observed_identity')
           AND claim.financial_flow IN ('cash_in', 'cash_out')
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
    _ensure_index_shape(
        cr,
        "sc_treasury_ledger_posted_payment_identity_idx",
        [
            "payment_request_id", "project_id", "company_id", "currency_id",
            "partner_id", "direction", "source_model", "source_res_id",
        ],
        False,
        ["state", "'posted'", "payment_request_id", "is not null"],
        1,
        """
        CREATE INDEX sc_treasury_ledger_posted_payment_identity_idx
            ON sc_treasury_ledger
               (payment_request_id, project_id, company_id, currency_id, partner_id, direction,
                source_model, source_res_id)
         WHERE state = 'posted' AND payment_request_id IS NOT NULL
        """,
    )
    _ensure_index_shape(
        cr,
        "sc_expense_claim_one_canonical_terminal_per_request_idx",
        ["payment_request_id"],
        True,
        [
            "payment_request_id", "is not null", "finance_identity_state",
            "'normalized'", "'legacy_observed_identity'", "state", "'done'",
            "'legacy_confirmed'", "financial_flow", "'cash_in'", "'cash_out'",
        ],
        3,
        """
        CREATE UNIQUE INDEX sc_expense_claim_one_canonical_terminal_per_request_idx
            ON sc_expense_claim(payment_request_id)
         WHERE payment_request_id IS NOT NULL
           AND finance_identity_state IN ('normalized', 'legacy_observed_identity')
           AND state IN ('done', 'legacy_confirmed')
           AND financial_flow IN ('cash_in', 'cash_out')
        """,
    )
    cr.execute(
        """
        CREATE INDEX IF NOT EXISTS payment_ledger_allocation_contract_identity_idx
            ON payment_ledger_allocation
               (contract_id, project_id, company_id, currency_id, allocation_state, ledger_id)
         WHERE allocation_state = 'allocated' AND contract_id IS NOT NULL
        """
    )
