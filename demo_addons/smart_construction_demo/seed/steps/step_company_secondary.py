# -*- coding: utf-8 -*-
"""Author the demo tenant's second operating company.

The demo is a group: the environment main company is the group head office and
``demo_company_second`` is its second engineering subsidiary.  Both live in the
same tenant database, so this is an internal company, not a second tenant and
not another platform control identity.
"""

from ..registry import SeedStep, register
from ...hooks import (
    apply_demo_company_secondary,
    guard_demo_data_space,
    register_demo_company_secondary,
)


def _run(env):
    # The main company must already be an onboarded demo data space before the
    # subsidiary is registered under the same tenant key.
    guard_demo_data_space(env)
    company = apply_demo_company_secondary(env)
    register_demo_company_secondary(env, company)
    return company


register(
    SeedStep(
        name="demo_company_secondary",
        description=(
            "Create or converge the demo group's second operating company and "
            "register it as a demo data space."
        ),
        run=_run,
    )
)
