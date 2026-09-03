"""Prepare immutable funding authority columns before the 17.0.0.143 registry."""


def migrate(cr, installed_version):
    del installed_version
    cr.execute(
        """
        ALTER TABLE project_funding_baseline
          ADD COLUMN IF NOT EXISTS version_no integer,
          ADD COLUMN IF NOT EXISTS version_key varchar,
          ADD COLUMN IF NOT EXISTS period_start date,
          ADD COLUMN IF NOT EXISTS period_end date,
          ADD COLUMN IF NOT EXISTS supersedes_id integer,
          ADD COLUMN IF NOT EXISTS superseded_by_id integer,
          ADD COLUMN IF NOT EXISTS revision_reason text,
          ADD COLUMN IF NOT EXISTS normalization_state varchar,
          ADD COLUMN IF NOT EXISTS activated_at timestamp,
          ADD COLUMN IF NOT EXISTS activated_by_id integer,
          ADD COLUMN IF NOT EXISTS ended_at timestamp,
          ADD COLUMN IF NOT EXISTS ended_by_id integer,
          ADD COLUMN IF NOT EXISTS end_reason text;

        ALTER TABLE project_funding_baseline_line
          ADD COLUMN IF NOT EXISTS line_key varchar;

        ALTER TABLE payment_request
          ADD COLUMN IF NOT EXISTS funding_baseline_id integer;

        ALTER TABLE project_funding_actual_event_allocation
          ADD COLUMN IF NOT EXISTS baseline_id integer,
          ADD COLUMN IF NOT EXISTS operation_key varchar,
          ADD COLUMN IF NOT EXISTS allocation_key varchar,
          ADD COLUMN IF NOT EXISTS entry_type varchar,
          ADD COLUMN IF NOT EXISTS effective_amount numeric,
          ADD COLUMN IF NOT EXISTS reverses_id integer,
          ADD COLUMN IF NOT EXISTS reversed_by_id integer,
          ADD COLUMN IF NOT EXISTS effective_at timestamp,
          ADD COLUMN IF NOT EXISTS effective_date date,
          ADD COLUMN IF NOT EXISTS normalization_state varchar,
          ADD COLUMN IF NOT EXISTS reason text
        """
    )
    cr.execute(
        """
        WITH duplicate_active AS (
            SELECT project_id
              FROM project_funding_baseline
             WHERE state = 'active'
             GROUP BY project_id
            HAVING COUNT(*) > 1
        )
        UPDATE project_funding_baseline AS baseline
           SET version_key = COALESCE(baseline.version_key, 'legacy:' || baseline.id::text),
               version_no = NULL,
               normalization_state = CASE
                   WHEN baseline.total_amount <= 0
                     THEN 'legacy_unresolved_amount'
                   WHEN duplicate_active.project_id IS NOT NULL AND baseline.state = 'active'
                     THEN 'legacy_unresolved_authority'
                   ELSE 'legacy_unresolved_period'
               END,
               state = CASE
                   WHEN baseline.total_amount <= 0
                     OR (duplicate_active.project_id IS NOT NULL AND baseline.state = 'active')
                     THEN 'legacy_unresolved'
                   ELSE baseline.state
               END
          FROM (SELECT id, project_id FROM project_funding_baseline) AS source
          LEFT JOIN duplicate_active ON duplicate_active.project_id = source.project_id
         WHERE baseline.id = source.id
           AND baseline.normalization_state IS NULL
        """
    )
    cr.execute(
        """
        UPDATE project_funding_baseline_line
           SET line_key = 'legacy:' || id::text
         WHERE line_key IS NULL
        """
    )
    cr.execute(
        """
        UPDATE project_funding_actual_event_allocation AS allocation
           SET baseline_id = line.baseline_id,
               operation_key = COALESCE(allocation.operation_key, 'legacy:' || allocation.id::text),
               allocation_key = COALESCE(allocation.allocation_key, 'legacy:' || allocation.id::text),
               entry_type = COALESCE(allocation.entry_type, 'allocation'),
               effective_amount = COALESCE(allocation.effective_amount, allocation.allocated_amount),
               effective_at = COALESCE(allocation.effective_at, ledger.paid_at),
               effective_date = COALESCE(allocation.effective_date, ledger.paid_at::date),
               normalization_state = CASE
                   WHEN ledger.id IS NULL OR line.id IS NULL
                     OR ledger.project_id IS DISTINCT FROM line.project_id
                     OR ledger.currency_id IS DISTINCT FROM line.currency_id
                     OR ledger.state != 'posted'
                     THEN 'legacy_unresolved_relation'
                   ELSE 'legacy_unresolved_period'
               END
          FROM project_funding_baseline_line AS line
          JOIN payment_ledger AS ledger ON TRUE
         WHERE line.id = allocation.plan_line_id
           AND ledger.id = allocation.actual_event_id
           AND (
                allocation.baseline_id IS NULL
                OR allocation.operation_key IS NULL
                OR allocation.allocation_key IS NULL
                OR allocation.entry_type IS NULL
                OR allocation.effective_amount IS NULL
                OR allocation.normalization_state IS NULL
           )
        """
    )
    cr.execute(
        """
        UPDATE project_funding_actual_event_allocation AS allocation
           SET operation_key = COALESCE(allocation.operation_key, 'legacy:' || allocation.id::text),
               allocation_key = COALESCE(allocation.allocation_key, 'legacy:' || allocation.id::text),
               entry_type = COALESCE(allocation.entry_type, 'allocation'),
               effective_amount = COALESCE(allocation.effective_amount, allocation.allocated_amount),
               normalization_state = 'legacy_unresolved_relation'
         WHERE (
                allocation.baseline_id IS NULL
                OR allocation.operation_key IS NULL
                OR allocation.allocation_key IS NULL
                OR allocation.entry_type IS NULL
                OR allocation.effective_amount IS NULL
                OR allocation.normalization_state IS NULL
           )
           AND (
                allocation.operation_key IS NULL
                OR allocation.allocation_key IS NULL
                OR allocation.entry_type IS NULL
                OR allocation.effective_amount IS NULL
                OR allocation.normalization_state IS DISTINCT FROM 'legacy_unresolved_relation'
           )
        """
    )
    cr.execute(
        """
        WITH invalid_lines AS (
            SELECT allocation.plan_line_id
              FROM project_funding_actual_event_allocation AS allocation
              JOIN project_funding_baseline_line AS line ON line.id = allocation.plan_line_id
             GROUP BY allocation.plan_line_id, line.planned_amount
            HAVING SUM(allocation.effective_amount) > line.planned_amount
        ), invalid_events AS (
            SELECT allocation.actual_event_id
              FROM project_funding_actual_event_allocation AS allocation
              JOIN payment_ledger AS ledger ON ledger.id = allocation.actual_event_id
             GROUP BY allocation.actual_event_id, ledger.amount, ledger.state
            HAVING SUM(allocation.effective_amount) > ledger.amount OR ledger.state = 'reversed'
        ), invalid_baselines AS (
            SELECT allocation.baseline_id
              FROM project_funding_actual_event_allocation AS allocation
              JOIN project_funding_baseline AS baseline ON baseline.id = allocation.baseline_id
             GROUP BY allocation.baseline_id, baseline.total_amount
            HAVING SUM(allocation.effective_amount) > baseline.total_amount
        )
        UPDATE project_funding_actual_event_allocation AS allocation
           SET normalization_state = 'legacy_unresolved_conservation'
         WHERE allocation.normalization_state NOT IN (
                   'legacy_unresolved_relation', 'legacy_unresolved_conservation'
               )
           AND (
                allocation.plan_line_id IN (SELECT plan_line_id FROM invalid_lines)
                OR allocation.actual_event_id IN (SELECT actual_event_id FROM invalid_events)
                OR allocation.baseline_id IN (SELECT baseline_id FROM invalid_baselines)
           )
        """
    )
