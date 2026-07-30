# -*- coding: utf-8 -*-
from ..registry import SeedStep, register


def _run(env):
    """Create defaults for explicitly registered business companies only."""
    env["construction.contract"].sudo()._sc_ensure_contract_tax_seeds()


register(
    SeedStep(
        name="tax_defaults",
        description="Create missing contract tax references for registered companies.",
        run=_run,
    )
)
