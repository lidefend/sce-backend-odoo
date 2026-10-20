# -*- coding: utf-8 -*-
"""Governed shell entrypoint: compute the scoped experience-reset scope (no delete)."""
import json

result = env["demo.scenario.tick"].plan_experience_reset()  # noqa: F821
print(json.dumps(result, ensure_ascii=False, default=str))
