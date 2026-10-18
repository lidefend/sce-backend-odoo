# -*- coding: utf-8 -*-
"""Align the declared Demo tenant name with the product-wide company identity.

The namespace seed is ``noupdate="1"`` so an existing database keeps whatever
it was first installed with.  The Demo tenant is displayed from the platform
namespace registration, not from the tenant database's ``res.company``; the
registry name therefore has to be corrected here instead of being read across
databases at request time.
"""
from __future__ import annotations

DEMO_NAMESPACE_ID = "ns_000000000002"
DEMO_TENANT_NAME = "Demo演示公司"
LEGACY_TENANT_NAMES = ("Demo tenant", "Demo 演示租户")


def migrate(cr, version):
    del version
    cr.execute(
        """
        UPDATE sc_platform_namespace
           SET display_name = %s
         WHERE namespace_id = %s
           AND (display_name IS NULL OR display_name = ANY(%s::text[]))
        """,
        [DEMO_TENANT_NAME, DEMO_NAMESPACE_ID, list(LEGACY_TENANT_NAMES)],
    )
