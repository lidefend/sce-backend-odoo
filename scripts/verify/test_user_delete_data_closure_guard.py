#!/usr/bin/env python3
"""Self-test for scripts/verify/user_delete_data_closure_guard.py.

The guard is a text probe over the frontend write path, so it is exactly the
kind of gate that can quietly stop proving anything.  That already happened
once: the batch delete flow moved out of ``ActionView.vue`` into the
selection-action runtime, the probe kept looking at the page, and the gate
reported a location drift as a product failure for as long as nobody read it.

This test binds the guard to the shipped sources and then proves that the
guard is still falsifiable: deleting the dry-run preflight, deleting the
destructive write, reordering them, hiding them behind an error handler, or
dropping the contract surface-policy fallback must each be rejected.
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GUARD_PATH = Path(__file__).resolve().with_name("user_delete_data_closure_guard.py")
_spec = importlib.util.spec_from_file_location("user_delete_data_closure_guard", GUARD_PATH)
assert _spec and _spec.loader
guard = importlib.util.module_from_spec(_spec)
sys.modules["user_delete_data_closure_guard"] = guard
_spec.loader.exec_module(guard)

RUNTIME_PATH = "frontend/apps/web/src/app/action_runtime/useActionViewSelectionActionRuntime.ts"
ACTION_VIEW_PATH = "frontend/apps/web/src/views/ActionView.vue"

# Minimal stand-in for the owner module: it carries only the sequence the guard
# asserts on, so each mutation below changes exactly one of them.
RUNTIME_TEMPLATE = """\
async function runBatchPolicyAction(action) {
  const seed = resolveBatchDeleteExecutionSeed({ selectedIds: selected });
  options.batchBusy.value = true;
  try {
    await unlinkActionViewRecord({
      model: targetModel,
      ids: selected,
      idempotencyKey: seed.dryRunIdempotencyKey,
      dryRun: true,
    });
    const result = await unlinkActionViewRecord({
      model: targetModel,
      ids: selected,
      idempotencyKey: seed.idempotencyKey,
    });
  } catch (err) {
    options.batchMessage.value = resolveBatchDeleteFailureMessage(err, options.text);
  } finally {
    options.batchBusy.value = false;
  }
}
"""


def _shipped(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def _reader(overrides: dict[str, str]):
    def read(rel_path: str) -> str:
        return overrides.get(rel_path, _shipped(rel_path))

    return read


def _frontend_probe(overrides: dict[str, str]) -> list[str]:
    errors: list[str] = []
    guard._probe_frontend_delete_flow(errors, read=_reader(overrides))
    return errors


class UserDeleteDataClosureGuardSelfTest(unittest.TestCase):
    def test_shipped_sources_satisfy_the_delete_flow_probe(self):
        # The binding test: the guard must hold against the code that actually
        # ships.  A guard that no longer matches reality is not a gate.
        self.assertEqual(_frontend_probe({RUNTIME_PATH: RUNTIME_TEMPLATE}), [])

    def test_removing_the_dry_run_preflight_is_rejected(self):
        mutated = RUNTIME_TEMPLATE.replace("      dryRun: true,\n", "")
        self.assertIn(
            "batch delete must issue a dry-run preflight before writing",
            _frontend_probe({RUNTIME_PATH: mutated}),
        )

    def test_removing_the_destructive_write_is_rejected(self):
        mutated = RUNTIME_TEMPLATE.replace(
            "const result = await unlinkActionViewRecord", "await somethingUnrelated"
        )
        self.assertIn(
            "batch delete must still execute the real unlink after the preflight",
            _frontend_probe({RUNTIME_PATH: mutated}),
        )

    def test_reordering_the_preflight_after_the_write_is_rejected(self):
        mutated = RUNTIME_TEMPLATE.replace(
            """      idempotencyKey: seed.dryRunIdempotencyKey,
      dryRun: true,
    });
    const result = await unlinkActionViewRecord({
      model: targetModel,
      ids: selected,
      idempotencyKey: seed.idempotencyKey,
    });
""",
            """      idempotencyKey: seed.idempotencyKey,
    });
    const result = await unlinkActionViewRecord({
      model: targetModel,
      ids: selected,
      idempotencyKey: seed.dryRunIdempotencyKey,
      dryRun: true,
    });
""",
        )
        # Both anchors survive the swap, so only the ordering rule can reject it.
        self.assertIn("dryRun: true", mutated)
        self.assertIn("const result = await unlinkActionViewRecord", mutated)
        self.assertIn(
            "the dry-run preflight must be awaited before the real unlink, not after it",
            _frontend_probe({RUNTIME_PATH: mutated}),
        )

    def test_an_error_handler_between_preflight_and_write_is_rejected(self):
        mutated = RUNTIME_TEMPLATE.replace(
            "    });\n    const result = await unlinkActionViewRecord",
            "    });\n    // catch\n    const result = await unlinkActionViewRecord",
        )
        self.assertNotEqual(mutated, RUNTIME_TEMPLATE)
        self.assertIn(
            "no error handler may sit between the dry-run preflight and the destructive write",
            _frontend_probe({RUNTIME_PATH: mutated}),
        )

    def test_sharing_one_idempotency_key_between_preflight_and_write_is_rejected(self):
        mutated = RUNTIME_TEMPLATE.replace(
            "idempotencyKey: seed.dryRunIdempotencyKey", "idempotencyKey: seed.idempotencyKey"
        )
        self.assertIn(
            "the dry-run preflight and the destructive write must carry distinct idempotency keys",
            _frontend_probe({RUNTIME_PATH: mutated}),
        )

    def test_dropping_the_contract_surface_policy_fallback_is_rejected(self):
        action_view = _shipped(ACTION_VIEW_PATH)
        mutated = action_view.replace(
            "resolveContractV2SurfacePolicies(actionContract.value)", "listProfile.value?.batch_policy"
        )
        self.assertNotEqual(mutated, action_view)
        self.assertIn(
            "ActionView batch policy must prefer the list_profile declaration and fall back to the contract surface policy",
            _frontend_probe({RUNTIME_PATH: RUNTIME_TEMPLATE, ACTION_VIEW_PATH: mutated}),
        )

    def test_a_second_delete_path_in_the_page_is_rejected(self):
        mutated = _shipped(ACTION_VIEW_PATH) + "\nawait unlinkActionViewRecord({ model, ids });\n"
        self.assertIn(
            "ActionView must delegate the batch delete flow to the selection runtime instead of owning a second delete path",
            _frontend_probe({RUNTIME_PATH: RUNTIME_TEMPLATE, ACTION_VIEW_PATH: mutated}),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
