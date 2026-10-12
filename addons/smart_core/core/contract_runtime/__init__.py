# -*- coding: utf-8 -*-
"""Contract-runtime support that consumes the contract declaration layer.

Kept free of Odoo imports so the resolution semantics stay offline-verifiable.
"""
from __future__ import annotations

from . import semantic_resolver

__all__ = ["semantic_resolver"]
