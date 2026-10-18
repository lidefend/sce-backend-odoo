# -*- coding: utf-8 -*-
"""Normalize the platform namespace's operator-facing name.

The namespace seed is ``noupdate="1"``, so an existing database keeps the
English name it was first installed with.  The platform administrator works
with the logical namespace identity, and the label must therefore be the
product-facing Chinese name rather than the legacy seed value.
"""
from __future__ import annotations

PLATFORM_NAMESPACE_ID = "ns_000000000001"
PLATFORM_NAMESPACE_NAME = "平台控制台"
LEGACY_PLATFORM_NAMES = ("Platform administration", "Platform Administration", "Platform Admin")


def migrate(cr, version):
    del version
    cr.execute(
        """
        UPDATE sc_platform_namespace
           SET display_name = %s
         WHERE namespace_id = %s
           AND (display_name IS NULL OR display_name = ANY(%s::text[]))
        """,
        [PLATFORM_NAMESPACE_NAME, PLATFORM_NAMESPACE_ID, list(LEGACY_PLATFORM_NAMES)],
    )
