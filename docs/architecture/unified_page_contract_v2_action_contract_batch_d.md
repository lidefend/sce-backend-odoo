# Unified Page Contract v2+ ActionContract Batch-D

Date: 2026-05-01
Status: Batch-D implementation note

## Layer Target

Contract Governance / ActionContract Consolidation

## Module

- `addons/smart_core/core/unified_page_contract_v2_action.py`
- `docs/architecture/unified_page_contract_v2/fixtures/action_contract_source.json`
- `docs/architecture/unified_page_contract_v2/fixtures/action_patch_source.json`
- `docs/architecture/unified_page_contract_v2/snapshots/action_contract_snapshot_v2.json`
- `scripts/verify/unified_page_contract_v2_action_guard.py`
- `Makefile`

## Reason

Existing interaction semantics are spread across onchange, page action schema, action policies, form save/validate/delete, and patch responses. v2+ requires these sources to be normalized into `ActionContract` so frontend runtimes dispatch stable `actionId` values and never implement business linkage logic.

## Source Mapping

| Source | v2+ output |
| --- | --- |
| `onchange_fields` / `changed_fields` | `triggerType=change`, `dispatchMode=serverDebounced` or `server`, `targetScope=widget`. |
| `action_schema.actions` | click action rules with server dispatch and target scope derived from intent category. |
| `action_policies` | button action rules using backend-governed availability as input, without executing business logic. |
| `form_actions.save` | `action.form.save` with `triggerType=submit` and `dispatchMode=serverBlocking`. |
| `form_actions.validate` | `action.form.validate` with `triggerType=confirm` and no refresh by default. |
| `delete_policy.allowed` | `action.record.delete` with `triggerType=delete` and server blocking dispatch. |
| `chain_actions` | dependency graph edges between action IDs, not executable client logic. |
| action result patch | `UnifiedPagePatch v2+` partial envelope with `layoutPatch/statusPatch/dataPatch/runtimePatch/meta`. |

## Anti-DSL Boundary

The normalizer does not emit:

- scripts
- expressions
- JSON logic
- BPMN
- workflow VM instructions
- frontend executable code

`ActionContract` remains a dispatch declaration. Semantic evaluation remains backend-owned.

## Upgrade Assessment

No Odoo model field, view, security, data XML, cron, or manifest dependency is added.

Result:

- `-u smart_core`: not required for this batch.
- service restart: not required for static validation; required only if a live Odoo worker must import the new module without process reload.

## Verification

Primary restricted target:

```bash
make verify.unified_page_contract.v2
```

Action-only target:

```bash
make verify.unified_page_contract.v2.action
```

## Rollback

Revert:

- `addons/smart_core/core/unified_page_contract_v2_action.py`
- `scripts/verify/unified_page_contract_v2_action_guard.py`
- `docs/architecture/unified_page_contract_v2/fixtures/action_contract_source.json`
- `docs/architecture/unified_page_contract_v2/fixtures/action_patch_source.json`
- `docs/architecture/unified_page_contract_v2/snapshots/action_contract_snapshot_v2.json`
- `Makefile` action target changes

No database rollback is required.

### Action-bound advisory confirmation (2026-10-13)

`actionRule.presentation` is the existing declared presentation carrier.
`requires_confirmation: true` together with a non-empty `warning_message` declares
a non-blocking advisory shown only when that exact action is invoked. It does not
change allowed/enabled/disabled, risk classification, or field visibility. The
backend binds runtime advisories by the same record model/id and object method;
final hydration preserves the declaration. Missing or empty content for this
confirmation is a contract defect, never permission to execute silently or invent
a default message. Existing native safety confirmations and reason-entry flows
retain their independent requirements. Cancel stops execution; continue still
uses the original authorized action executor.

付款申请的往来单位复核提醒属于提交动作：blocked 沿既有业务校验原文禁止提交；
review_required 仅在提交交互时提醒并允许取消/继续，不变成禁止态。页面正文不再
声明同一指导 alert 或旧 task/risk 指导锚点；业务状态事实与其他入口职责保留。
