#!/usr/bin/env python3
"""Pure, read-only demo scenario step scheduling (P4 delivery tooling).

Implements the step contract and idempotent tick planning described in
``docs/demo/demo_iteration_line_v1.md`` section 6.2 without touching a database.
It never executes a business action: it only classifies and schedules steps.
"""
from __future__ import annotations

from dataclasses import dataclass


ACTOR_MODES = ("system_fact", "role_draft", "role_decision", "showcase_history")
STEP_FIELDS = (
    "scenario_id",
    "business_date",
    "day_index",
    "step_key",
    "sequence",
    "actor_mode",
    "intent_or_action",
    "params",
    "precondition",
    "expected_state",
    "idempotency_key",
)


class StepError(ValueError):
    pass


@dataclass(frozen=True)
class Step:
    scenario_id: str
    business_date: str
    day_index: int
    step_key: str
    sequence: int
    actor_mode: str
    intent_or_action: str
    params: dict
    precondition: str
    expected_state: str
    idempotency_key: str


def idempotency_key(scenario_id: str, business_date: str, step_key: str) -> str:
    if not scenario_id or not business_date or not step_key:
        raise StepError("idempotency key requires scenario_id, business_date and step_key")
    return f"{scenario_id}::{business_date}::{step_key}"


def coerce_step(raw: dict) -> Step:
    missing = [field for field in STEP_FIELDS if field not in raw]
    if missing:
        raise StepError(f"step missing fields: {missing}")
    if raw["actor_mode"] not in ACTOR_MODES:
        raise StepError(f"invalid actor_mode: {raw['actor_mode']!r}")
    if not isinstance(raw["day_index"], int) or raw["day_index"] < 0:
        raise StepError("day_index must be a non-negative int")
    if not isinstance(raw["sequence"], int) or raw["sequence"] < 0:
        raise StepError("sequence must be a non-negative int")
    if not isinstance(raw["params"], dict):
        raise StepError("params must be an object")
    if not isinstance(raw["idempotency_key"], str) or not raw["idempotency_key"]:
        raise StepError("idempotency_key must be a non-empty string")
    expected = idempotency_key(raw["scenario_id"], raw["business_date"], raw["step_key"])
    if raw["idempotency_key"] != expected:
        raise StepError(
            f"idempotency_key mismatch: {raw['idempotency_key']!r} != {expected!r}"
        )
    return Step(
        scenario_id=raw["scenario_id"],
        business_date=raw["business_date"],
        day_index=raw["day_index"],
        step_key=raw["step_key"],
        sequence=raw["sequence"],
        actor_mode=raw["actor_mode"],
        intent_or_action=raw["intent_or_action"],
        params=raw["params"],
        precondition=raw["precondition"],
        expected_state=raw["expected_state"],
        idempotency_key=raw["idempotency_key"],
    )


def validate_manifest(steps: list[dict]) -> list[Step]:
    coerced = [coerce_step(raw) for raw in steps]
    seen: set[str] = set()
    for step in coerced:
        if step.idempotency_key in seen:
            raise StepError(f"duplicate idempotency key: {step.idempotency_key}")
        seen.add(step.idempotency_key)
    return coerced


def plan_tick(
    manifest: list[Step],
    executed_keys: set[str],
    business_date: str | None = None,
) -> list[Step]:
    """Return the not-yet-executed steps for the next tick, idempotently.

    ``business_date`` selects one calendar day; when omitted, the earliest
    business date with pending steps is advanced. ``role_decision`` steps are
    returned as todo-only; nothing in this engine ever approves or completes a
    decision.
    """
    pending = [step for step in manifest if step.idempotency_key not in executed_keys]
    if not pending:
        return []
    if business_date is None:
        business_date = min(step.business_date for step in pending)
    selected = [step for step in pending if step.business_date == business_date]
    selected.sort(key=lambda step: (step.day_index, step.sequence))
    return selected


def todo_only(steps: list[Step]) -> list[Step]:
    """Project role_decision steps into todos; never an auto-approval action."""
    return [
        step
        for step in steps
        if step.actor_mode == "role_decision"
        or step.actor_mode == "role_draft"
    ]


def auto_advance(steps: list[Step]) -> list[Step]:
    """The only steps the system may run without a human decision."""
    return [step for step in steps if step.actor_mode == "system_fact"]
