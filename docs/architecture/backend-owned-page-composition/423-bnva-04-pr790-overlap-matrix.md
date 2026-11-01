# 423 · BNVA-04 PR #790 Overlap Matrix

## 冲突文件（10）

| 文件 | 冲突类型 | 分叉量（origin/main ↔ HEAD） | 备注 |
| --- | --- | --- | --- |
| addons/smart_core/core/native_view_projection.py | add/add | 419 ↔ 536 行 | 两份不同实现，需逐行裁定 |
| addons/smart_core/core/unified_page_contract_v2_assembler.py | content | HEAD 少约 720 行 | 本分支大规模重构 vs PR790 小幅改动 |
| addons/smart_core/handlers/ui_contract_v2.py | content | +46/-13 | 架构治理资产 |
| addons/smart_core/handlers/ui_contract_v2_form_structure.py | content | 小 | 需核对 |
| scripts/verify/unified_page_contract_v2_assembler_guard.py | content | +4/-2 | 需核对 |
| addons/smart_core/tests/test_native_view_projection.py | add/add | — | 两份测试，需统一 |
| .agent/active-runs.json | content | — | 分支索引需三向合并 |
| .agent/runs/BNVA-01/run.json | add/add | — | 需合并 run 记录 |
| docs/engineering_convergence/complexity_budget_report.md | content | 生成报告 | 可重新生成 |
| docs/engineering_convergence/split_plan_queue.md | content | 生成报告 | 可重新生成 |

## 自动可合并

其余文件自动合并，含 `.agent/decisions/ARCH-DECISION-004/005/006.yaml`、
`ui_business_config_contract.py`、`backend_contract_boundaries.py`、
`core_extension_policy_maps.py`、`page_composition_integrity_guard.py`——这些未被 PR #790 改动，
本分支版本直接保留。

## 需要人工裁定的文件

native_view_projection.py、unified_page_contract_v2_assembler.py、ui_contract_v2.py 及其
测试与 guard，必须核对本分支是否为 PR #790 版本的严格演进，还是含独立增量；不可 ours/theirs 二选一。
