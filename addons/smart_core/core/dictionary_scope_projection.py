# -*- coding: utf-8 -*-
"""The one scope vocabulary for ``sc.dictionary`` startup projection.

``sc.dictionary.scope_type`` is ``global`` / ``company`` / ``role``. Only two of
those have a delivery meaning in the startup contract today:

* ``global`` publishes the row under the ``__global__`` role bucket;
* ``role`` publishes the row under its own role code.

``company`` has no delivery meaning yet, and it is *not* global. Mapping it into
the global bucket (the previous behaviour) promoted a company-scoped
configuration row into every principal's contract, so an unknown scope is
dropped and counted instead of being made public. Adding real company delivery
means teaching this module the company bucket and its consumer in the same
change, never widening ``global`` by accident.
"""
from __future__ import annotations

from typing import Optional

GLOBAL_SCOPE = "global"
ROLE_SCOPE = "role"
GLOBAL_BUCKET = "__global__"
DELIVERED_SCOPES = (GLOBAL_SCOPE, ROLE_SCOPE)


def projection_bucket(scope_type: str, scope_ref: str) -> Optional[str]:
    """Return the delivery bucket for a row, or ``None`` when undeliverable."""
    scope = (scope_type or "").strip()
    ref = (scope_ref or "").strip()
    if scope == GLOBAL_SCOPE:
        return GLOBAL_BUCKET
    if scope == ROLE_SCOPE:
        return ref or None
    return None
