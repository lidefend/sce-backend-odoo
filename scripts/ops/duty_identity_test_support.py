#!/usr/bin/env python3
"""Shared support for the governed duty-identity unit tests.

The concrete binding of a customer duty lives outside the git checkout, so a unit
test that resolves the *tracked* declaration has to name a fixture through the one
explicit override the resolver supports.  It is the same code path the entry uses
for a first materialisation, which keeps the tests on the real resolver instead of
a stand-in: the parser, the naming checks, the placeholder refusal and the merge
are all exercised, only the identity is synthetic.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
#: The synthetic binding every ops unit test resolves the tracked template against.
SYNTHETIC_INSTANCES = ROOT / "scripts" / "ops" / "synthetic_duty_instances.sample.json"
SYNTHETIC_DUTY = "customer_tenant_dev"
SYNTHETIC_TENANT_KEY = "sample"
SYNTHETIC_CUSTOMER_MODULE = "sce_customer_sample"
SYNTHETIC_DATABASE = "sc_tenant_sample_dev"
SYNTHETIC_DATABASE_ROLE = "sc_tenant_sample_dev_app"
SYNTHETIC_COMPOSE_PROJECT = "sc-tenant-sample-dev"


def synthetic_instances_override():
    """Point the explicit instance override at the synthetic fixture."""
    return mock.patch.dict(
        os.environ, {"SC_DAILY_RUNTIME_DUTY_INSTANCES": str(SYNTHETIC_INSTANCES)}
    )
