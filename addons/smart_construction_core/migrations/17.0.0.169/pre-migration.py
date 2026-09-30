"""Classify pre-allocation payment history before ORM defaults are applied."""

from pathlib import Path
import runpy


def migrate(cr, installed_version):
    del installed_version
    # The ledger predates its allocation table.  Do not gate parent-history
    # classification on the existence of that newer child table (153-155).
    cr.execute("SELECT to_regclass('public.payment_ledger')")
    if cr.fetchone()[0] is None:
        return
    cr.execute("LOCK TABLE payment_ledger IN SHARE ROW EXCLUSIVE MODE")
    cr.execute(
        "ALTER TABLE payment_ledger ADD COLUMN IF NOT EXISTS normalization_state varchar"
    )
    # Preserve both established classifications and original identity/amounts.
    # Missing provenance must never acquire the ORM default 'normalized'.
    cr.execute(
        """
        UPDATE payment_ledger
           SET normalization_state = 'legacy_unresolved_identity'
         WHERE normalization_state IS NULL
        """
    )
    # 156 ran before this parent classification. Replay its idempotent child
    # quarantine/recomputation so a formerly NULL parent cannot retain canonical
    # funding allocations. Reuse the established migration authority verbatim.
    funding_migration = Path(__file__).resolve().parents[1] / "17.0.0.156/pre-migration.py"
    runpy.run_path(str(funding_migration))["migrate"](cr, None)
