# -*- coding: utf-8 -*-
"""项目概况受限富文本读投影块（G7.4-B 前端切片）。

块数据一次性携带 canonical 内容 + 摘要基线 + 能力投影（can_edit），
编辑面板无需二次 fetch intent：

- content/overview_digest：restricted_html canonical 内容与服务端摘要
  （sha256 前 16 位）。digest 是编辑会话的 expected 基线，提交时透传
  服务端比对（BASELINE_MISMATCH 并发防护，契约 decision_semantics）。
- can_edit：kill switch flag + 专用组双闸投影，仅控制前端编辑入口
  显隐；写路径权威校验仍在 intent handler（纵深防御，非唯一防线）。
- max_length：契约上限（ADR-006 决策 4）随块下发供前端预校验。

本块为读投影，不携带写事实；写入仅走
``project.overview.rich_text.patch`` intent（claim 幂等 + nh3 净化）。
"""
from __future__ import annotations

from ..overview_rich_text_patch_service import (
    FLAG_KEY,
    MAX_LENGTH,
    flag_enabled,
    overview_digest,
)
from .base import BaseProjectBlockBuilder

RICH_TEXT_PATCH_INTENT = "project.overview.rich_text.patch"
RICH_TEXT_EDITOR_GROUP = "smart_construction_core.group_sc_cap_rich_text_editor"


class ProjectOverviewBuilder(BaseProjectBlockBuilder):
    block_key = "block.project.overview"
    block_type = "rich_text_overview"
    title = "项目概况"
    required_groups = ()

    def build(self, project=None, context=None):
        visibility = self._visibility()
        if not visibility.get("allowed"):
            return self._envelope(
                state="forbidden",
                visibility=visibility,
                data=self._projection_data(None),
            )
        if not project:
            return self._envelope(
                state="empty",
                visibility=visibility,
                data=self._projection_data(None),
            )
        content = getattr(project, "overview_html", None) or ""
        state = "ready" if content else "empty"
        return self._envelope(
            state=state,
            visibility=visibility,
            data=self._projection_data(project, content=content),
        )

    def _can_edit(self):
        """编辑入口能力投影：flag 开 + 专用组（fail-closed）。

        与 handler 同口径：ir.config_parameter 读取 + flag_enabled 解析
        （仅认显式真值），异常与缺席一律视为关。
        """
        try:
            Parameters = self.env.get("ir.config_parameter")
            if Parameters is None:
                return False
            raw = Parameters.sudo().get_param(FLAG_KEY)
            if not flag_enabled(raw):
                return False
            return bool(self.env.user.has_group(RICH_TEXT_EDITOR_GROUP))
        except Exception:
            return False

    def _projection_data(self, project, content=""):
        content = str(content or "")
        data = {
            "field": "overview_html",
            "content": content,
            "overview_digest": overview_digest(content),
            "content_length": len(content),
            "max_length": int(MAX_LENGTH),
            "patch_intent": RICH_TEXT_PATCH_INTENT,
            "can_edit": bool(project is not None and self._can_edit()),
            "empty_message": "项目概况尚未填写。",
        }
        if project is not None:
            data["project_id"] = int(project.id)
        return data
