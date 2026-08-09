"""Narrow legacy adjustment roles to reconciliation and negative analysis rows."""


def migrate(cr, installed_version):
    cr.execute(
        """
        UPDATE project_cost_plan_line
           SET line_role = CASE
               WHEN analysis_id IS NOT NULL
                AND source_resource_line_id IS NULL
                AND calculation_mode = 'amount'
                AND (cost_type = 'material' OR budget_unit_price < 0)
                   THEN 'adjustment'
               WHEN budget_unit_consumption < 0
                 OR budget_unit_price < 0
                 OR budget_rate < 0
                   THEN 'deduction'
               ELSE 'cost'
           END
        """
    )
