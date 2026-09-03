# -*- coding: utf-8 -*-
from __future__ import annotations

from .base import BaseProjectBlockBuilder

BOQ_PREVIEW_FETCH_INTENT = "project.boq.import.preview.fetch"
BOQ_BATCH_MODEL = "project.boq.import.batch"


class ProjectBoqPreviewBuilder(BaseProjectBlockBuilder):
    """清单导入预检快照块（G3.3 组件挂接）。

    只读投影块：本块不携带业务事实，仅声明受权数据引用
    （fetch intent + project_id）。快照事实源仍由
    ``project.boq.import.preview.fetch`` intent 权威输出，
    与 contracts/domain/boq.yaml v1 的 safe_degradation 语义一致。
    """

    block_key = "block.project.boq_preview"
    block_type = "boq_import_preview"
    title = "清单导入预览"
    required_groups = ()

    def build(self, project=None, context=None):
        visibility = self._visibility()
        if not visibility.get("allowed"):
            return self._envelope(
                state="forbidden",
                visibility=visibility,
                data=self._projection_data(0, 0),
            )
        if not project:
            return self._envelope(
                state="empty",
                visibility=visibility,
                data=self._projection_data(0, 0),
            )

        project_id = int(getattr(project, "id", 0) or 0)
        batch_count = self._safe_count(
            BOQ_BATCH_MODEL,
            [("project_id", "=", project_id)],
        )
        state = "ready" if batch_count > 0 else "empty"
        return self._envelope(
            state=state,
            visibility=visibility,
            data=self._projection_data(project_id, batch_count),
        )

    @staticmethod
    def _projection_data(project_id, batch_count):
        return {
            "project_id": int(project_id or 0),
            "batch_count": int(batch_count or 0),
            "fetch_intent": BOQ_PREVIEW_FETCH_INTENT,
            "fetch_params": {"project_id": int(project_id or 0)},
            "readonly": True,
        }
