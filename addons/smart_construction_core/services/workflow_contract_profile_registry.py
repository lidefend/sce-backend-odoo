# -*- coding: utf-8 -*-
"""Service-layer seam onto the P0 workflow-contract-profile registry.

`smart_construction_core` owns the construction-industry projection only.  A
model owned by a user or product module publishes its own workflow profile
through the P0 registry, and the industry workflow service merges it at read
time instead of declaring rules for a model it does not own.

The registry read lives here, in the services layer, because this module's ORM
model layer must not depend on the P0 contract-governance mechanism, which
`scripts/verify/model_ui_dependency_guard.py` enforces.  This module is the
single seam through which the workflow service consumes that registry.
"""
from __future__ import annotations

from typing import Any

from odoo.addons.smart_core.utils.contract_governance import workflow_contract_profiles


def external_workflow_contract_profiles() -> dict[str, dict[str, Any]]:
    """Return the profiles other modules published to the P0 registry."""
    return workflow_contract_profiles()
