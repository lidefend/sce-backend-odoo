# P0 native action permission contract — 2026-11-28

Branch: `fix/p0-native-action-permission-contract-20261128`

Baseline: `c528f45c46bb6cc178a868cf5eb10a7c341a4f39` (`origin/main`)

## Layer declaration

| Field | Value |
| --- | --- |
| Formal Product Layer | P0 platform kernel product |
| Layer Target | generic native action contract production and frontend consumption |
| Module | `smart_core`, generic frontend contract consumer |
| Standard vs User-Specific | platform standard |
| Why Here | The parser, assembler, schema, presenter and executor must preserve one authority verdict for native actions. |
| Why Not Elsewhere | Product ACL/role changes would grant access to compensate for a lost contract verdict; frontend inference would create a second permission authority. |
| Blast Radius | Native action rule and button status rows only. ACLs, record rules, business states and action identities remain unchanged. |

## Problem

Native view buttons may carry `groups` and native modifiers but no explicit
per-user execution verdict in the final V2 action contract. Execution through
`execute_button` re-authorizes and fails closed, but the frontend can receive a
button without the `entitlementEvaluated`, `authorizationAllowed`, `allowed`,
`enabled` and `disabled` evidence required by its presenter. This creates
different outcomes across parser, assembler, schema/presenter and execution.

The fix must preserve declared runtime business-action verdicts and only seal
the missing native fallback from the same access-mode authority used by
execution.

Relation fields also require one native authority chain. The contract must use
the ORM field type/comodel, effective view field access, target-model ACL,
native `_rec_name`, and native menu/action authority. A descriptor relation that
does not match the ORM comodel, an unreadable source field, or an unreadable
target model fails closed. Record rules remain runtime ORM authority and are not
guessed during projection.

## Validation responsibility

| Gate | State | Owner target | Reason |
| --- | --- | --- | --- |
| Exact base/head identity | required | branch and full SHA preflight | always |
| Focused permission producer test | required | smart_core focused test | authority parity |
| Frontend schema/presenter parity | required | TypeScript contract tests | contract consumption |
| Affected handler/contract tests | required | smart_core targeted ORM/unit | existing action families |
| Local incremental iteration | required | `make ci.local.iteration` | exact affected set |
| Owning module baseline | deferred remote | exact-head PR CI | P0 source change |
| PR and scheduled mainline | required | exact current PR checks | protected integration |

## Implementation

- Added `smart_core.core.native_action_permission` as the shared contract
  authority for native object/action/server buttons.
- Reused the same `button_access_mode` helper from `ExecuteButtonHandler`.
- Sealed missing native action rows with explicit `entitlementEvaluated`,
  `authorizationAllowed`, `allowed`, `enabled`, `disabled` and stable denial
  reasons, including record-rule checks for persisted records.
- Preserved declared runtime business-action verdicts.
- Synchronized `actionRuleList` and `buttonStatus`.
- Added native relation authority projection: ORM field/comodel validation,
  effective field read access, target-model ACL, native `_rec_name` display
  metadata, source-authority trace and runtime record-rule policy.
- Repinned the assembled contract cache after changing producer inputs.

## Validation

- Native action permission unit tests: 6 passed.
- `TestOdooNativeAlignmentBoundaries`: 79 passed, including a real contract
  assertion for a native object button.
- Relation entry contract guard: 27 tests passed.
- Execute-button authority: 38 tests passed.
- Frontend header action/presenter: passed.
- Unified V2 action and schema guards: passed.
- Unified V2 assembler cache guard: passed.
- Final `make ci.local.iteration`: 28 affected targets exited zero.
- Test coverage registry: all declared groups gated or dispositioned.
- `make ci.delivery.freeze.prepare`: passed; generated reports refreshed.
