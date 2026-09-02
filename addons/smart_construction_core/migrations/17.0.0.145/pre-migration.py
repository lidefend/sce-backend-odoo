"""Freeze funding economic identity and add a writable reservation version."""


def migrate(cr, installed_version):
    del installed_version
    cr.execute(
        """
        ALTER TABLE project_project
          ADD COLUMN IF NOT EXISTS funding_reservation_revision integer;

        UPDATE project_project
           SET funding_reservation_revision = 0
         WHERE funding_reservation_revision IS NULL
        """
    )
    cr.execute(
        """
        UPDATE project_funding_baseline
           SET normalization_state = 'legacy_unresolved_identity',
               state = CASE
                   WHEN state = 'active' THEN 'legacy_unresolved'
                   ELSE state
               END
         WHERE normalization_state = 'normalized'
           AND (company_id IS NULL OR currency_id IS NULL)
        """
    )
    cr.execute(
        """
        UPDATE project_funding_actual_event_allocation AS allocation
           SET normalization_state = 'legacy_unresolved_relation'
          FROM project_funding_baseline_line AS line
          JOIN project_funding_baseline AS baseline
            ON baseline.id = line.baseline_id
         WHERE allocation.plan_line_id = line.id
           AND allocation.normalization_state = 'normalized'
           AND (
                allocation.baseline_id IS DISTINCT FROM baseline.id
                OR allocation.project_id IS DISTINCT FROM baseline.project_id
                OR allocation.company_id IS DISTINCT FROM baseline.company_id
                OR allocation.currency_id IS DISTINCT FROM baseline.currency_id
                OR allocation.project_id IS NULL
                OR allocation.company_id IS NULL
                OR allocation.currency_id IS NULL
           )
        """
    )
