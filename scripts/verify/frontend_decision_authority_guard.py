#!/usr/bin/env python3
"""Fail-closed guard for the frontend decision-authority ledger.

The guard answers one decidable question: *does every frontend decision inside
the declared scopes either come from the runtime contract, sit on the recorded
projectable-gap backlog, or belong to the declared render/interaction half?*

It fails when:

* a decision-shaped expression matches a rule but is not classified (a new
  frontend business decision, a new capability literal gate, a new action id);
* an ``invariant_zero`` rule matches anything at all;
* a ``contract-derived`` intent literal is not declared in the published intent
  catalog export;
* a ledger row cites an evidence file that no longer exists;
* the committed ledger
  (``docs/frontend_productization/decision-authority-inventory-v1.json``) is out
  of sync with the live scan in either direction.

It is read-only: it never edits product code or the ledger.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.verify.frontend_decision_authority import (  # noqa: E402
    INVENTORY_PATH,
    reconcile,
)


def main() -> int:
    result = reconcile(compare_committed=True)
    inventory = result["inventory"]
    summary = inventory["summary"]

    print("[frontend.decision_authority.guard] scopes: " + ", ".join(inventory["decisionScopes"]))
    print(
        "[frontend.decision_authority.guard] findings="
        f"{summary['totalFindings']} distinct={summary['distinctDecisions']} "
        f"contract-derived={summary['contractDerived']} "
        f"projectable-gaps={summary['contractProjectableGaps']} "
        f"frontend-logic-defects={summary['frontendLogicDefects']} "
        f"render-interaction={summary['excludedRenderInteraction']} "
        f"unclassified={summary['unclassified']}"
    )
    print(f"[frontend.decision_authority.guard] ledger: {INVENTORY_PATH}")

    for failure in result["failures"]:
        print(f"[FAIL] {failure}")

    if result["failures"]:
        print(
            f"[frontend.decision_authority.guard] FAIL ({len(result['failures'])} issue(s))"
        )
        return 1

    print("[frontend.decision_authority.guard] PASS: every scoped decision is contract-derived, a recorded projectable gap, or declared render/interaction")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
