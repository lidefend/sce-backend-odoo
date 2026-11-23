# -*- coding: utf-8 -*-
from __future__ import annotations


class ProjectTaskStateSupport:
    BUSINESS_STATES = ("draft", "ready", "in_progress", "done", "cancelled")
    OPEN_STATES = ("draft", "ready", "in_progress")
    ACTIVE_STATES = ("ready", "in_progress")
    CLOSED_STATES = ("done", "cancelled")
    NATIVE_DONE_STATE = "1_done"
    NATIVE_CANCELED_STATE = "1_canceled"
    NATIVE_WAITING_STATE = "04_waiting_normal"
    NATIVE_IN_PROGRESS_STATE = "01_in_progress"
    NATIVE_OPEN_FALLBACK_STATES = (
        "01_in_progress",
        "02_changes_requested",
        "03_approved",
        "04_waiting_normal",
    )

    @classmethod
    def normalize(cls, raw) -> str:
        state = str(raw or "").strip().lower()
        return state if state in cls.BUSINESS_STATES else "draft"

    @classmethod
    def is_open(cls, raw) -> bool:
        return cls.normalize(raw) in cls.OPEN_STATES

    @classmethod
    def is_active(cls, raw) -> bool:
        return cls.normalize(raw) in cls.ACTIVE_STATES

    @classmethod
    def is_done(cls, raw) -> bool:
        return cls.normalize(raw) == "done"

    @classmethod
    def open_domain(cls):
        return [("sc_state", "not in", list(cls.CLOSED_STATES))]

    @classmethod
    def active_domain(cls):
        return [("sc_state", "in", list(cls.ACTIVE_STATES))]

    @classmethod
    def done_domain(cls):
        return [("sc_state", "=", "done")]

    @classmethod
    def native_open_states(cls, task_model) -> tuple[str, ...]:
        declared = tuple(getattr(task_model, "OPEN_STATES", ()) or ())
        return declared or cls.NATIVE_OPEN_FALLBACK_STATES

    @classmethod
    def native_open_domain(cls, task_model):
        return [("state", "in", list(cls.native_open_states(task_model)))]

    @classmethod
    def native_done_domain(cls):
        return [("state", "=", cls.NATIVE_DONE_STATE)]

    @classmethod
    def native_waiting_domain(cls):
        return [("state", "=", cls.NATIVE_WAITING_STATE)]

    @classmethod
    def native_in_progress_domain(cls):
        return [("state", "=", cls.NATIVE_IN_PROGRESS_STATE)]

    @classmethod
    def native_metrics(cls, tasks, task_model=None) -> dict:
        rows = list(tasks or [])
        open_states = set(
            cls.native_open_states(task_model)
            if task_model is not None
            else cls.NATIVE_OPEN_FALLBACK_STATES
        )
        done = len([task for task in rows if str(getattr(task, "state", "") or "") == cls.NATIVE_DONE_STATE])
        canceled = len([task for task in rows if str(getattr(task, "state", "") or "") == cls.NATIVE_CANCELED_STATE])
        open_count = len([
            task for task in rows
            if str(getattr(task, "state", "") or "") in open_states
        ])
        waiting = len([task for task in rows if str(getattr(task, "state", "") or "") == cls.NATIVE_WAITING_STATE])
        in_progress = len([task for task in rows if str(getattr(task, "state", "") or "") == cls.NATIVE_IN_PROGRESS_STATE])
        denominator = max(len(rows) - canceled, 0)
        return {
            "task_total": len(rows),
            "task_open_count": open_count,
            "task_waiting_count": waiting,
            "task_in_progress_count": in_progress,
            "task_done_count": done,
            "task_cancelled_count": canceled,
            "task_completion_percent": round(done * 100.0 / denominator, 2) if denominator else 0.0,
        }

    @classmethod
    def sync_kanban_state(cls, task) -> None:
        if "kanban_state" not in getattr(task, "_fields", {}):
            return
        task_state = cls.normalize(getattr(task, "sc_state", "draft"))
        kanban_state = "done" if task_state == "done" else "normal"
        task.sudo().write({"kanban_state": kanban_state})
