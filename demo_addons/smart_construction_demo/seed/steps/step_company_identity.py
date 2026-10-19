# -*- coding: utf-8 -*-
"""Author the demo company's visible identity before the showcase data."""

from ..registry import SeedStep, register
from ...hooks import apply_demo_company_identity


def _run(env):
    return apply_demo_company_identity(env)


register(
    SeedStep(
        name="demo_company_identity",
        description="Name the demo company for the showcase (四川智汇建设集团有限公司).",
        run=_run,
    )
)
