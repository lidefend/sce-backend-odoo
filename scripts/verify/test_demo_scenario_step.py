import unittest

from scripts.verify.demo_scenario_step import (
    StepError,
    auto_advance,
    coerce_step,
    plan_tick,
    todo_only,
    validate_manifest,
)


def _step(scenario_id="s-golden", date="2026-10-20", day=1, key="fact_arrival", seq=1, mode="system_fact"):
    return {
        "scenario_id": scenario_id,
        "business_date": date,
        "day_index": day,
        "step_key": key,
        "sequence": seq,
        "actor_mode": mode,
        "intent_or_action": "demo.scenario.advance" if mode == "system_fact" else "wait",
        "params": {},
        "precondition": "",
        "expected_state": "recorded",
        "idempotency_key": f"{scenario_id}::{date}::{key}",
    }


class DemoScenarioStepTest(unittest.TestCase):
    def test_valid_manifest_accepts_step(self):
        manifest = validate_manifest([_step()])
        self.assertEqual(len(manifest), 1)
        self.assertEqual(manifest[0].actor_mode, "system_fact")

    def test_duplicate_idempotency_key_rejected(self):
        with self.assertRaises(StepError):
            validate_manifest([_step(), _step(seq=2)])

    def test_idempotency_key_mismatch_rejected(self):
        raw = _step()
        raw["idempotency_key"] = "wrong"
        with self.assertRaises(StepError):
            coerce_step(raw)

    def test_invalid_actor_mode_rejected(self):
        with self.assertRaises(StepError):
            coerce_step(_step(mode="auto_approve"))

    def test_tick_plans_only_unexecuted_steps(self):
        manifest = validate_manifest([_step(), _step(day=2, key="fact_invoice", seq=2)])
        executed = {f"s-golden::2026-10-20::fact_arrival"}
        planned = plan_tick(manifest, executed, "2026-10-20")
        self.assertEqual([step.step_key for step in planned], ["fact_invoice"])

    def test_tick_is_idempotent_after_execution(self):
        manifest = validate_manifest([_step()])
        executed = {f"s-golden::2026-10-20::fact_arrival"}
        self.assertEqual(plan_tick(manifest, executed, "2026-10-20"), [])

    def test_role_decision_is_todo_only_never_auto_advance(self):
        manifest = validate_manifest(
            [
                _step(key="fact_arrival"),
                _step(key="decision_approve", seq=2, mode="role_decision"),
                _step(key="draft_submit", seq=3, mode="role_draft"),
            ]
        )
        self.assertEqual(
            [step.step_key for step in todo_only(manifest)],
            ["decision_approve", "draft_submit"],
        )
        self.assertEqual([step.step_key for step in auto_advance(manifest)], ["fact_arrival"])


if __name__ == "__main__":
    unittest.main()
