"""Keep unresolved historical ownership evidence outside every company scope."""


def migrate(cr, installed_version):
    del installed_version
    cr.execute(
        """
        UPDATE project_cost_ledger AS ledger
           SET company_id = NULL
         WHERE ledger.normalization_state = 'legacy_unresolved_owner'
           AND ledger.company_id IS NOT NULL
           AND (
                ledger.project_id IS NULL
                OR NOT EXISTS (
                    SELECT 1
                      FROM project_project AS project
                     WHERE project.id = ledger.project_id
                       AND project.company_id IS NOT NULL
                )
           )
        """
    )
