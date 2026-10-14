"""Refuse a data-carrying upgrade whose business rows have no onboarded owner.

The company ceilings this module ships resolve row visibility through the
registered data space (``user._sc_data_company_ids()``).  An environment whose
business rows predate the data-space declaration therefore upgraded into a
state where every ownership decision resolved against an empty registration
set: the product silently served an empty surface for every principal,
including the platform administrator, and nothing failed loudly enough to say
why.

Industry initialization owns the question "which of my models carry
company-owned rows", so the probe list is the module's own generated
declaration.  The platform owns the meaning of an unregistered owner.  A
database that fails here is repaired by the governed onboarding entry, never by
widening a scope in a migration.

The gate runs before any schema change, so a refusal leaves the module exactly
as it was.
"""

from odoo import SUPERUSER_ID, api

from odoo.addons.smart_construction_core.services.business_data_ownership import (
    assert_existing_business_data_ownership,
)


def migrate(cr, installed_version):
    if not installed_version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    assert_existing_business_data_ownership(env)
