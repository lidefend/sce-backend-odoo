# -*- coding: utf-8 -*-
"""Presentation guidance only; native views/actions own initialization entries."""
from __future__ import annotations


def build(scene_key: str = "enterprise.setup", runtime: dict | None = None, context: dict | None = None) -> dict:
    runtime = runtime or {}
    return {
        "scene_key": scene_key,
        "guidance": {
            "title": "企业初始化工作空间",
            "message": "完善企业信息、组织架构、岗位、人员和业务权限，再选择启用业务场景。",
        },
        "runtime": {"role_code": runtime.get("role_code"), "company_id": runtime.get("company_id")},
    }
