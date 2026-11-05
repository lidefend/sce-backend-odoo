# Guard registry 治理收口（2026-11-06）

基线为干净最新 main `f79d29f55a22d6dbaec778237fbf710a12b6f4b3`。`make verify.guard.registry` 的 24 项单测通过，随后复现 32 项登记/接线失败。范围仅 P4 工程治理，不改前端产品或后端业务。未运行或批量采纳 `guard.registry.seed`。

| 脚本 | 处置 | 真实消费/执行依据 |
|---|---|---|
| `capability_asset_evidence_verification.py` | file-consumed | `scripts/verify/test_capability_asset_evidence_verification.py` |
| `capability_asset_gap_classification.py` | file-consumed | `scripts/verify/test_capability_asset_gap_classification.py` |
| `capability_asset_reconciliation.py` | file-consumed | `scripts/verify/test_capability_asset_reconciliation.py` |
| `capability_candidate_catalog_check.py` | file-consumed | `scripts/verify/capability_maturity_bundle_build.py` |
| `capability_composite_and_decision.py` | file-consumed | `scripts/verify/test_capability_composite_and_decision.py` |
| `capability_contract_mapper.py` | file-consumed | `scripts/verify/capability_maturity_bundle_build.py`、`scripts/verify/test_capability_contract_mapper.py` |
| `capability_impact_propagation.py` | file-consumed | `scripts/verify/module_change_impact_report.py`、`scripts/verify/test_capability_impact_propagation.py` |
| `capability_maturity_bundle_build.py` | file-consumed | `scripts/verify/test_capability_contract_mapper.py` |
| `capability_provider_reconciliation.py` | file-consumed | `scripts/verify/test_capability_provider_reconciliation.py` |
| `capability_unresolved_execution_chain.py` | file-consumed | `scripts/verify/test_capability_unresolved_execution_chain.py` |
| `module_capability_index.py` | file-consumed | `scripts/verify/capability_asset_reconciliation.py`、`scripts/verify/capability_impact_propagation.py`、`scripts/verify/test_module_capability_index.py` |
| `module_change_impact_report.py` | file-consumed | `scripts/verify/test_module_change_impact_report.py` |
| `module_change_observation.py` | file-consumed | `scripts/verify/module_upgrade_observation.py`、`scripts/verify/test_module_change_observation.py` |
| `module_snapshot_diff.py` | file-consumed | `scripts/verify/test_module_snapshot_diff.py` |
| `module_upgrade_observation.py` | file-consumed | `scripts/verify/test_module_upgrade_observation.py` |
| `odoo_runtime_facts.py` | file-consumed | `scripts/verify/module_upgrade_observation.py` |
| `test_capability_asset_evidence_verification.py` | wired-test | `verify.capability.module_tooling.unit`；挂入 local Quick 与专业后端根，加入 gate_required 防止空接线 |
| `test_capability_asset_gap_classification.py` | wired-test | `verify.capability.module_tooling.unit`；挂入 local Quick 与专业后端根，加入 gate_required 防止空接线 |
| `test_capability_asset_reconciliation.py` | wired-test | `verify.capability.module_tooling.unit`；挂入 local Quick 与专业后端根，加入 gate_required 防止空接线 |
| `test_capability_composite_and_decision.py` | wired-test | `verify.capability.module_tooling.unit`；挂入 local Quick 与专业后端根，加入 gate_required 防止空接线 |
| `test_capability_contract_mapper.py` | wired-test | `verify.capability.module_tooling.unit`；挂入 local Quick 与专业后端根，加入 gate_required 防止空接线 |
| `test_capability_impact_propagation.py` | wired-test | `verify.capability.module_tooling.unit`；挂入 local Quick 与专业后端根，加入 gate_required 防止空接线 |
| `test_capability_provider_reconciliation.py` | wired-test | `verify.capability.module_tooling.unit`；挂入 local Quick 与专业后端根，加入 gate_required 防止空接线 |
| `test_capability_unresolved_execution_chain.py` | wired-test | `verify.capability.module_tooling.unit`；挂入 local Quick 与专业后端根，加入 gate_required 防止空接线 |
| `test_construction_diary_list_contract.py` | wired-test | `verify.construction.diary.list_contract.unit`；挂入 local Quick 与专业后端根，加入 gate_required 防止空接线 |
| `test_module_capability_index.py` | wired-test | `verify.capability.module_tooling.unit`；挂入 local Quick 与专业后端根，加入 gate_required 防止空接线 |
| `test_module_change_impact_report.py` | wired-test | `verify.capability.module_tooling.unit`；挂入 local Quick 与专业后端根，加入 gate_required 防止空接线 |
| `test_module_change_observation.py` | wired-test | `verify.capability.module_tooling.unit`；挂入 local Quick 与专业后端根，加入 gate_required 防止空接线 |
| `test_module_snapshot_diff.py` | wired-test | `verify.capability.module_tooling.unit`；挂入 local Quick 与专业后端根，加入 gate_required 防止空接线 |
| `test_module_upgrade_observation.py` | wired-test | `verify.capability.module_tooling.unit`；挂入 local Quick 与专业后端根，加入 gate_required 防止空接线 |
| `capability_d03_conclusion.py` | 按现有 guard.retire 退役 | 一次性 D03 历史报告写入器，没有 Make/CI/脚本消费者；历史输出不删除，源码移入 retired |
| `test_pr_publish_preflight.py` | 纠正 stale orphan 为 active | 已被 verify.pr.push.unit / verify.ci.workflow.contract 执行，无需重复新建入口 |

能力与模块工具的测试只执行纯逻辑/临时文件/模拟子进程，不运行观察脚本的真实模块升级、数据库或发布写操作。file-consumed 登记只说明模块有真实消费者，不能用作其真实运行验收。

同步工具边界：当前 frontend 候选只有两条责任提交，普通 sync 不要求 Quick，但生成冲突会中止；extended 要求当前 HEAD Quick 且通常至少 13 提交，并只复位登记生成文件，不自动运行生成器。若治理修复引入遇到这条循环，需通过独立受管 bootstrap 修复，不能临时跳钩或把旧回执改绑新 HEAD。

原始日志及逐项 JSON 位于当前 run 索引所指的 `.runtime/guard-registry-governance/`。

## Frozen-plan worker authentication follow-up

The failed PR #815 backend worker called `validate_execution_plan` →
`isolated_plan_reuse` → `isolated_history` → `gh api` from **Resolve module list**.
That step lacked `GH_TOKEN`, although planning and final coverage authentication
already supply it. The independent follow-up commit adds the existing GitHub job
token to that step; receipt identity, success, digest and historical authority
checks remain unchanged. No token is persisted in evidence.

The regression parses the actual workflow and runs its frozen-plan shell with
external executors stubbed. It verifies token inheritance and the frozen-plan,
digest and shard arguments; missing authentication still fails before module
selection is delivered. `make verify.ci.workflow.contract` passes, including the
existing real planner reuse/rejection regression suite. This is offline wiring
validation; authoritative remote checks remain required.
