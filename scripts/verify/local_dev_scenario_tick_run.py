# -*- coding: utf-8 -*-
"""Governed shell entrypoint: advance the demo scenario by one business day."""
import json

result = env["demo.scenario.tick"].run_tick()  # noqa: F821
print(json.dumps(result, ensure_ascii=False, default=str))
