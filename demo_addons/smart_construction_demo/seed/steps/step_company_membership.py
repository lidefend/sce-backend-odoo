# -*- coding: utf-8 -*-
"""Grant group-level demo seats access to the second operating company."""

from odoo.exceptions import UserError

from ..registry import SeedStep, register
from ...hooks import DEMO_COMPANY_SECOND_MEMBER_LOGINS


def _run(env):
    from odoo.addons.smart_core.security import data_space_provisioning as provisioning

    company = env.ref("smart_construction_demo.demo_company_second")
    Users = env["res.users"].sudo().with_context(active_test=False)
    missing = []
    for login in DEMO_COMPANY_SECOND_MEMBER_LOGINS:
        user = Users.search([("login", "=", login)], limit=1)
        if not user or not user.active or user.share:
            missing.append(login)
            continue
        if company.id not in user.company_ids.ids:
            user.write({"company_ids": [(4, company.id)]})
    if missing:
        raise UserError(
            "DEMO_COMPANY_SECOND_MEMBERS_MISSING:" + ",".join(missing)
        )
    # Adding company access enlarges the operator set of the second data space;
    # enroll those identities before the rest of the demo seed relies on them.
    provisioning.enroll_data_space_identities(env, purpose="demo")
    return company


register(
    SeedStep(
        name="demo_company_membership",
        description=(
            "Give group-level demo seats access to the second operating company "
            "and enroll them into the demo data space."
        ),
        run=_run,
    )
)
