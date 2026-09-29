# -*- coding: utf-8 -*-
"""The single authority for the declared action-semantics vocabulary.

The platform only *carries* a business owner's declaration; it never derives a
purpose from a method name, a label or a button position.  What a valid
declaration is must therefore be defined exactly once - here.  Every other
appearance of this vocabulary is a checked projection:

- the published schema
  ``docs/architecture/unified_page_contract_v2/unified_page_contract_v2.schema.json``
- the contract assembler :mod:`unified_page_contract_v2_assembler`
- the terminal consumer ``frontend/packages/schema/src/actionSemantics.ts``

Editing a projection does not publish a new meaning; it only makes a guard
fail.  That is the mechanism that keeps a missing declaration visible instead of
letting one layer quietly fill the gap for the others.

The unit of the vocabulary is a ``(kind, executor)`` pair.  Validating the three
sets independently would accept ``business`` + ``return`` + ``client.back`` -
a combination every consumer drops - so the producer would publish a
declaration no terminal can read.  The pairing is part of the vocabulary.
"""
from __future__ import annotations

DECLARATIONS = {
    "persistence": {
        "record.save": frozenset({"save_draft"}),
    },
    "business": {
        "contract.action": frozenset(
            {
                "submit",
                "approve",
                "reject",
                "cancel_record",
                "start_execution",
                "complete",
                "reopen",
            }
        ),
    },
    "interaction": {
        "client.back": frozenset({"return"}),
        "client.discard": frozenset({"discard_changes"}),
    },
}

KINDS = frozenset(DECLARATIONS)
EXECUTORS = frozenset(
    executor for kind_map in DECLARATIONS.values() for executor in kind_map
)
PURPOSES = frozenset(
    purpose
    for kind_map in DECLARATIONS.values()
    for purposes in kind_map.values()
    for purpose in purposes
)
OPERATIONS = frozenset({"create", "write"})

# Purposes a business owner may declare, and the remainder owned by platform
# persistence and the shared client commands.  Both are derived, never listed
# twice, so a new business purpose cannot silently belong to the wrong group.
BUSINESS_PURPOSES = DECLARATIONS["business"]["contract.action"]
NON_BUSINESS_PURPOSES = PURPOSES - BUSINESS_PURPOSES


def purposes_for(kind, executor):
    """Return the purposes a ``(kind, executor)`` pair may declare."""
    kind_map = DECLARATIONS.get(str(kind or "").strip().lower()) or {}
    return kind_map.get(str(executor or "").strip().lower()) or frozenset()


def is_declared(kind, purpose, executor) -> bool:
    """Whether the three parts form one declaration from this vocabulary."""
    return str(purpose or "").strip().lower() in purposes_for(kind, executor)
