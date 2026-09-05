# -*- coding: utf-8 -*-
"""Model import order guard for init() cross-table SQL.

Fresh database installs create module tables in model import order.
``payment_ledger_allocation.init()`` backfills from the ``payment_ledger``
table, so ``payment_ledger`` must be imported (and therefore created)
first. Existing databases never hit this because upgrade paths find the
table already present; fresh demo tenant installs (the physically
isolated public demo lifecycle) install into an empty database and fail
with ``UndefinedTable`` when the order regresses.
"""

from pathlib import Path

import unittest

_CORE_INIT = (
    Path(__file__).resolve().parents[1]
    / "models"
    / "core"
    / "__init__.py"
).read_text(encoding="utf-8")


class ModelInitImportOrderTest(unittest.TestCase):
    def test_payment_ledger_imported_before_allocation(self):
        self.assertIn("from . import payment_ledger\n", _CORE_INIT)
        self.assertIn("from . import payment_ledger_allocation\n", _CORE_INIT)
        self.assertLess(
            _CORE_INIT.index("from . import payment_ledger\n"),
            _CORE_INIT.index("from . import payment_ledger_allocation\n"),
            "payment_ledger must be imported before payment_ledger_allocation: "
            "allocation.init() backfills FROM payment_ledger, so a fresh "
            "database install requires the ledger table to exist first",
        )


if __name__ == "__main__":
    unittest.main()
