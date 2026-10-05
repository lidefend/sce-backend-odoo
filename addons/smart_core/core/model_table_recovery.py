# -*- coding: utf-8 -*-
"""Recover the backing table of models that override ``init()``.

Odoo recreates a missing model table by calling only ``model.init()``
(``Registry.check_tables_exist``, reached from ``init_models`` and from the
module-loading recovery path).  It does not call ``_auto_init()`` there, so a
model whose ``init()`` only adds extra indexes never creates its own columns on
that path, and every database that lacks the table fails the module upgrade
with ``UndefinedTable``.

``ensure_table_on_init`` runs the ordinary table-creation path -- ``_auto_init``
plus the deferred foreign keys and the field indexes -- but only when the
backing table is actually missing, so the normal install/upgrade cycle is left
untouched.
"""
from __future__ import annotations

from collections import deque

from odoo.tools import table_exists

_MISSING = object()
_REGISTRY_ATTRS = ("_post_init_queue", "_foreign_keys", "_is_install")


def ensure_table_on_init(model):
    """Create ``model``'s table when only ``init()`` is called for it.

    Returns ``True`` when the table had to be recreated, ``False`` when it was
    already there or when the model is not backed by an ordinary ``_auto``
    table.  Convention: a smart_core model that overrides ``init()`` must call
    this helper from the first line of that override, otherwise the recovery
    entry silently regresses to "indexes only, no table" (see
    ``tests/test_smart_core_model_init_table_recovery.py``).
    """
    cr = model.env.cr
    if table_exists(cr, model._table):
        return False
    if not model._auto:
        # A model that manages its own backing object (``_auto = False``) has
        # nothing for ``_auto_init`` to create; leave it to the model.
        return False

    pool = model.pool
    queue = deque()
    foreign_keys = {}
    saved = {attr: getattr(pool, attr, _MISSING) for attr in _REGISTRY_ATTRS}

    # ``_auto_init`` defers column work -- foreign keys in particular -- through
    # the registry post-init queue, and records the expected keys in
    # ``_foreign_keys``.  On the recovery path those structures are either
    # already drained (``init_models``) or absent (module loading), so this
    # helper owns a private queue/dict and flushes them itself.
    pool._post_init_queue = queue
    pool._foreign_keys = foreign_keys
    if saved["_is_install"] is _MISSING:
        # ``post_constraint`` reads it when a constraint cannot be applied
        # eagerly; queue the failure for the cycle's later finalize step.
        pool._is_install = False
    # ``is_an_ordinary_table`` answers from a cached snapshot of ``pg_class``.
    # This model's table is missing, so any snapshot is older than it -- and may
    # also predate other tables recovered later in the same pass, which would
    # silently skip their foreign keys.  Force a fresh snapshot while the table
    # exists, and drop it again on the way out so the next model recomputes too.
    pool._ordinary_tables = None
    try:
        model._auto_init()
        while queue:
            queue.popleft()()
        pool.check_indexes(cr, [model._name])
        pool.check_foreign_keys(cr)
    finally:
        pool._ordinary_tables = None
        for attr, value in saved.items():
            if value is _MISSING:
                delattr(pool, attr)
            else:
                setattr(pool, attr, value)
    return True
