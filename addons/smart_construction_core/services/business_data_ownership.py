# -*- coding: utf-8 -*-
"""Industry-side probe list for the business-data ownership readiness check.

The construction industry owns the answer to "which of my models carry
company-owned business rows", so the model list lives here and never in
``smart_core``. It is generated from
``scripts/verify/data_scope_declarations.json`` by
``scripts/verify/sc_data_scope_ceiling_generate.py``, so the probe list and the
company ceilings that make those models depend on a registered data space stay
one fact.

Only the platform decides what an unregistered owner means; this module hands
it the industry's model set and nothing else.
"""

import json
from pathlib import Path

from odoo.addons.smart_core.security import data_space_provisioning as provisioning

MODULE_ROOT = Path(__file__).resolve().parents[1]
PROBE_MODELS_PATH = "data/tenant/scoped_business_models.v1.json"
MODELS_KEY = "models"


def probe_models(path=None):
    """The declared business models whose visibility is bounded by a data space."""
    target = Path(path) if path else MODULE_ROOT / PROBE_MODELS_PATH
    if not target.is_file():
        raise ValueError("DATA_SPACE_SCOPED_MODEL_DECLARATION_MISSING:%s" % (PROBE_MODELS_PATH,))
    try:
        document = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError("DATA_SPACE_SCOPED_MODEL_DECLARATION_INVALID:%s" % (error,))
    models = document.get(MODELS_KEY)
    if not isinstance(models, list) or not models:
        raise ValueError("DATA_SPACE_SCOPED_MODEL_DECLARATION_INVALID:models")
    return [str(model) for model in models]


def assert_existing_business_data_ownership(env):
    """Fail closed unless every company already owning industry rows is onboarded.

    Called by the governed read-only readiness entry. Historical development
    migrations are retired; this service does not install an upgrade hook.
    """
    return provisioning.assert_business_data_ownership_registered(env, probe_models())


def ownership_readiness(env):
    """Read-only readback of the same decision, for diagnostics and acceptance."""
    models = probe_models()
    owners = provisioning.business_data_company_ids(env, models)
    unregistered = provisioning.unregistered_business_companies(env, owners)
    return {
        "probe_model_count": len(models),
        "business_data_company_ids": owners,
        "unregistered_business_data_company_ids": unregistered,
        "registered_company_ids": sorted(
            provisioning.onboarded_registrations(env).company_id.ids
        ),
        "environment_role": provisioning.environment_role(env),
        "passed": not unregistered,
    }
