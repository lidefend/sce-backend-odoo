"""Normalize deterministic history and quarantine ambiguous cost evidence."""


def migrate(cr, installed_version):
    del installed_version
    cr.execute(
        """
        UPDATE project_cost_ledger AS ledger
           SET company_id = project.company_id,
               source_currency_id = CASE
                                        WHEN ledger.normalization_state = 'legacy_unresolved_currency'
                                        THEN ledger.source_currency_id
                                        ELSE COALESCE(ledger.source_currency_id, ledger.currency_id)
                                    END,
               source_amount = CASE
                                   WHEN ledger.normalization_state = 'legacy_unresolved_currency'
                                   THEN ledger.source_amount
                                   ELSE COALESCE(ledger.source_amount, ledger.amount)
                               END,
               amount = CASE
                            WHEN ledger.normalization_state = 'legacy_unresolved_currency'
                              OR ledger.currency_id IS DISTINCT FROM company.currency_id THEN 0
                            ELSE ledger.amount
                        END,
               currency_id = company.currency_id,
               normalization_state = CASE
                                         WHEN ledger.normalization_state = 'legacy_unresolved_currency'
                                           OR ledger.currency_id IS DISTINCT FROM company.currency_id
                                         THEN 'legacy_unresolved_currency'
                                         ELSE 'normalized'
                                     END,
               recognition_stage = CASE
                                       WHEN ledger.normalization_state = 'legacy_unresolved_currency'
                                         OR ledger.currency_id IS DISTINCT FROM company.currency_id
                                       THEN 'legacy_unresolved'
                                       ELSE ledger.recognition_stage
                                   END,
               reporting_treatment = CASE
                                         WHEN ledger.normalization_state = 'legacy_unresolved_currency'
                                           OR ledger.currency_id IS DISTINCT FROM company.currency_id
                                         THEN 'memorandum'
                                         ELSE ledger.reporting_treatment
                                     END
          FROM project_project AS project
          JOIN res_company AS company ON company.id = project.company_id
         WHERE project.id = ledger.project_id
           AND (
                ledger.company_id IS DISTINCT FROM project.company_id
             OR ledger.currency_id IS DISTINCT FROM company.currency_id
             OR ledger.source_currency_id IS DISTINCT FROM CASE
                    WHEN ledger.normalization_state = 'legacy_unresolved_currency'
                    THEN ledger.source_currency_id
                    ELSE COALESCE(ledger.source_currency_id, ledger.currency_id)
                END
             OR ledger.source_amount IS DISTINCT FROM CASE
                    WHEN ledger.normalization_state = 'legacy_unresolved_currency'
                    THEN ledger.source_amount
                    ELSE COALESCE(ledger.source_amount, ledger.amount)
                END
             OR ledger.normalization_state IS DISTINCT FROM CASE
                    WHEN ledger.normalization_state = 'legacy_unresolved_currency'
                      OR ledger.currency_id IS DISTINCT FROM company.currency_id
                    THEN 'legacy_unresolved_currency'
                    ELSE 'normalized'
                END
           )
        """
    )
    cr.execute(
        """
        UPDATE project_cost_ledger AS ledger
           SET company_id = NULL,
               source_currency_id = COALESCE(ledger.source_currency_id, ledger.currency_id),
               source_amount = COALESCE(ledger.source_amount, ledger.amount),
               normalization_state = 'legacy_unresolved_owner',
               recognition_stage = 'legacy_unresolved',
               reporting_treatment = 'memorandum'
         WHERE (
                   ledger.project_id IS NULL
                OR NOT EXISTS (
                    SELECT 1
                      FROM project_project AS project
                     WHERE project.id = ledger.project_id
                       AND project.company_id IS NOT NULL
                )
               )
           AND (
                ledger.company_id IS NOT NULL
             OR ledger.normalization_state IS DISTINCT FROM 'legacy_unresolved_owner'
             OR ledger.recognition_stage IS DISTINCT FROM 'legacy_unresolved'
             OR ledger.reporting_treatment IS DISTINCT FROM 'memorandum'
             OR ledger.source_currency_id IS DISTINCT FROM
                    COALESCE(ledger.source_currency_id, ledger.currency_id)
             OR ledger.source_amount IS DISTINCT FROM
                    COALESCE(ledger.source_amount, ledger.amount)
           )
        """
    )
    cr.execute(
        """
        WITH candidate_origins AS (
            SELECT id
              FROM sc_material_outbound_line
             WHERE returned_qty IS DISTINCT FROM 0
            UNION
            SELECT line.origin_issue_line_id
              FROM sc_material_outbound_line AS line
              JOIN sc_material_outbound AS outbound ON outbound.id = line.outbound_id
             WHERE line.origin_issue_line_id IS NOT NULL
               AND outbound.outbound_type = 'return'
               AND outbound.state = 'issued'
        ),
        returned AS (
            SELECT line.origin_issue_line_id AS origin_id, SUM(line.qty) AS qty
              FROM sc_material_outbound_line AS line
              JOIN sc_material_outbound AS outbound ON outbound.id = line.outbound_id
             WHERE line.origin_issue_line_id IS NOT NULL
               AND outbound.outbound_type = 'return'
               AND outbound.state = 'issued'
             GROUP BY line.origin_issue_line_id
        ),
        desired AS (
            SELECT candidate.id, COALESCE(returned.qty, 0) AS returned_qty
              FROM candidate_origins AS candidate
              LEFT JOIN returned ON returned.origin_id = candidate.id
        )
        UPDATE sc_material_outbound_line AS origin
           SET returned_qty = desired.returned_qty
          FROM desired
         WHERE origin.id = desired.id
           AND origin.returned_qty IS DISTINCT FROM desired.returned_qty
        """
    )
