#!/usr/bin/env python3
"""Single authority for the line budget of every size-monitored source file.

Why this module exists
----------------------
Every ``*_split_guard.py`` used to freeze its own numeric limit at the size the
file happened to have when that guard was written.  Because the same file was
watched by a dozen independent guards, one file carried a dozen drifting limits
at once -- ``addons/smart_construction_core/core_extension.py`` was guarded at
1787, 1809, 1820, 1830, 1858, 2065, 2120, 2243, 3145, 3763, 4180 and 4241 all
simultaneously.  Adding a small feature therefore meant hand-editing several
guards, which is mechanical, hides the real signal, and trains people to bump
numbers instead of noticing that the shell is growing.

The rule is now a single one:

    guidance budget = registered baseline (size at the last review) + uniform headroom

and the budget is **advisory**: it points at files that are drifting toward
another extraction, it never blocks a functional iteration.  Guards keep their
real, blocking assertions -- module ownership, split tokens, forbidden
dependencies -- and only the raw line count is demoted to a printed hint.

* One file, one baseline, one headroom.  Reviewing a budget is one edit here.
* The headroom is deliberately uniform: no per-file exception to negotiate.
* An unregistered file fails closed, so a new size-monitored file must be
  registered here instead of silently inheriting a stale limit.
* Structural growth belongs in a split module, not in a raised baseline.

``scripts/verify/file_line_budget_uniform_guard.py`` keeps this real: no guard
may hardcode a numeric line budget again.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# One uniform headroom for every monitored file.  This is the only tunable
# number in the policy; changing it changes every budget at once, on purpose.
HEADROOM_LINES = 60

# Frozen baseline = the file size at the last line-budget review.
BASELINES: dict[str, int] = {
    # --- smart_construction_core extension shell and its split modules ---
    "addons/smart_construction_core/core_extension.py": 1830,
    "addons/smart_construction_core/core_extension_actor_roles.py": 31,
    "addons/smart_construction_core/core_extension_contract_normalizers.py": 399,
    "addons/smart_construction_core/core_extension_intent_handlers.py": 248,
    "addons/smart_construction_core/core_extension_service_builders.py": 110,
    # --- smart_core contract governance shell and page-contract handler ---
    "addons/smart_core/utils/contract_governance.py": 1432,
    "addons/smart_core/handlers/ui_contract_v2.py": 4138,
    # --- web application shells, page patterns and record runtimes ---
    "frontend/apps/web/src/views/ActionView.vue": 3665,
    "frontend/apps/web/src/layouts/AppShell.vue": 1597,
    "frontend/apps/web/src/pages/ListPage.vue": 2155,
    "frontend/apps/web/src/pages/ContractFormPage.vue": 1894,
    "frontend/apps/web/src/pages/ContractFormRoute.vue": 7,
    "frontend/apps/web/src/views/BusinessConfigSurfaceView.vue": 554,
    "frontend/apps/web/src/pages/contractForm/useRecordFormActions.ts": 599,
    "frontend/apps/web/src/pages/contractForm/useRecordFormDesignerPersistence.ts": 686,
    "frontend/apps/web/src/pages/contractForm/useRecordPageLifecycle.ts": 533,
    "frontend/apps/web/src/pages/contractForm/useRecordRelationships.ts": 639,
}


class LineBudgetNotRegistered(KeyError):
    """Raised when a guard asks for a file that has no registered baseline."""


def normalize(rel_path: str | Path) -> str:
    text = str(rel_path).replace("\\", "/")
    while text.startswith("./"):
        text = text[2:]
    return text


def baseline_for(rel_path: str | Path) -> int:
    key = normalize(rel_path)
    try:
        return BASELINES[key]
    except KeyError:
        raise LineBudgetNotRegistered(
            "no line budget registered for "
            + key
            + "; register it in scripts/verify/line_budgets.py"
        ) from None


def budget_for(rel_path: str | Path) -> int:
    """Budget for a registered file.  Unknown files fail closed."""
    return baseline_for(rel_path) + HEADROOM_LINES


def budget_or_default(rel_path: str | Path, default: int) -> int:
    """Budget for a registered file, or ``default`` for a deliberately unlisted one."""
    key = normalize(rel_path)
    if key in BASELINES:
        return BASELINES[key] + HEADROOM_LINES
    return default


ADVISORY_PREFIX = "[size-advisory]"


def advisory(rel_path: str | Path, lines: int, budget: int, *, label: str = "") -> bool:
    """Print a non-blocking size hint against an explicit budget."""
    if lines <= budget:
        return False
    print(
        f"{ADVISORY_PREFIX} {label or normalize(rel_path)} is {lines} lines, "
        f"{lines - budget} over the {budget}-line guidance budget; "
        "consider splitting before the next structural change"
    )
    return True


def advise_size(rel_path: str | Path, lines: int, *, label: str = "") -> bool:
    """Print a non-blocking size hint; return True when the file is over budget.

    Line count is a *direction* for code optimization, not a gate.  Nothing here
    changes a guard's exit status: an over-budget file still passes, it just
    says which file is next in line for a split and by how much it drifted.
    """
    key = normalize(rel_path)
    baseline = BASELINES.get(key)
    if baseline is None:
        return False
    budget = baseline + HEADROOM_LINES
    if lines <= budget:
        return False
    print(
        f"{ADVISORY_PREFIX} {label or key} is {lines} lines, "
        f"{lines - budget} over the {budget}-line guidance budget "
        f"(baseline {baseline}); consider splitting before the next structural change"
    )
    return True


def registered() -> dict[str, int]:
    return dict(BASELINES)
