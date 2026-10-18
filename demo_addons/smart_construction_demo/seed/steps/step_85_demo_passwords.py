# -*- coding: utf-8 -*-
"""Reapply the published showcase password after every demo identity exists."""

from ..registry import SeedStep, register
from ...hooks import apply_demo_user_passwords


def run(env):
    apply_demo_user_passwords(env)


register(
    SeedStep(
        name="demo_85_passwords",
        description="Reapply the fixed 123456 showcase password to every demo identity.",
        run=run,
    )
)
