# -*- coding: utf-8 -*-
from __future__ import annotations

from .base import BaseProjectBlockBuilder


class ProjectNextActionsBuilder(BaseProjectBlockBuilder):
    """推荐「下一步动作」块：从决策引擎的 actions 投影可点击动作列表。

    G3.3-B capture 实跑发现 RUNTIME_BLOCK_MAP 存在 next_actions 映射但
    缺 builder，导致驾驶舱出现 1 处 zone 级「当前内容暂不可用」兜底。
    本 builder 以决策引擎推荐动作（含 intent 路由）填充，block_type 采用
    前端已注册的 todo_list 词表，消除未注册 fallback。

    决策引擎经 env 模型获取（sc.evidence.action.engine），无模型时走
    空动作兜底，保持与 ProjectDecisionEngineService 同构的分层。
    """

    ACTION_ENGINE_MODEL = "sc.evidence.action.engine"
    block_key = "block.project.next_actions"
    block_type = "todo_list"
    title = "下一步动作"
    required_groups = ()
    MAX_ITEMS = 6

    def _decide(self, project):
        engine = self._model(self.ACTION_ENGINE_MODEL)
        if engine is None:
            return {}
        try:
            return engine.decide(project) or {}
        except Exception:
            return {}

    def build(self, project=None, context=None):
        visibility = self._visibility()
        if not visibility.get("allowed"):
            return self._envelope(
                state="forbidden",
                visibility=visibility,
                data=self._projection_data([]),
            )
        if not project:
            return self._envelope(
                state="empty",
                visibility=visibility,
                data=self._projection_data([]),
            )

        items = []
        for action in self._decide(project).get("actions") or []:
            action_key = str(action.get("action_key") or "").strip()
            if not action_key:
                continue
            items.append(
                {
                    "id": action_key,
                    "title": str(action.get("label") or action_key),
                    "description": str(action.get("reason") or ""),
                    "count": 1,
                    "status": "pending",
                    "source": "decision_engine",
                    "source_label": "推荐动作",
                    "tone": "info",
                    "action_label": "进入处理",
                    "action_key": action_key,
                    "target": {"type": "intent", "intent": str(action.get("intent") or "")},
                }
            )

        if not items:
            items.append(
                {
                    "id": "no_next_action",
                    "title": "暂无推荐下一步",
                    "description": "当前项目无紧急推进事项，请按阶段目标推进。",
                    "count": 0,
                    "status": "completed",
                    "source": "capability_fallback",
                    "source_label": "状态",
                    "tone": "neutral",
                    "action_label": "返回驾驶舱",
                    "action_key": "open_dashboard",
                }
            )

        return self._envelope(
            state="ready",
            visibility=visibility,
            data=self._projection_data(
                [row for row in items[: self.MAX_ITEMS] if isinstance(row, dict)]
            ),
        )

    @classmethod
    def _projection_data(cls, items):
        # base._envelope 契约要求数据为 dict；条目列表收纳在 "items" 键下，
        # 前端 BlockTodoList 以 dataset.items 双形态兼容消费（同 progress 块）。
        return {
            "items": [dict(row) for row in (items or []) if isinstance(row, dict)],
            "count": len([row for row in (items or []) if isinstance(row, dict)]),
            "max_items": cls.MAX_ITEMS,
        }
