# -*- coding: utf-8 -*-
"""Author the demo company's visible identity before the showcase data."""

from ..registry import SeedStep, register


DEMO_COMPANY_NAME = "demo演示公司"


def _run(env):
    company = env.ref("base.main_company")
    if company.name != DEMO_COMPANY_NAME:
        company.write({"name": DEMO_COMPANY_NAME})
    partner = company.partner_id
    if partner.name != DEMO_COMPANY_NAME:
        partner.write({"name": DEMO_COMPANY_NAME})
    return company


register(
    SeedStep(
        name="demo_company_identity",
        description="Name the demo company for the showcase (demo演示公司).",
        run=_run,
    )
)
