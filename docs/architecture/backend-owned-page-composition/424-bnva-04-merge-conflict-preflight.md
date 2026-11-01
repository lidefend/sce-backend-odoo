# 424 · BNVA-04 Merge Conflict Preflight

## 方法

`git merge-tree --write-tree HEAD origin/main`（只读，未执行 merge）。

## 结果

- 10 个文件内容冲突。
- 生成报告类（complexity_budget_report.md / split_plan_queue.md）可在合并后重新生成。
- 架构资产冲突集中在 native_view_projection / assembler / ui_contract_v2 / assembler_guard。

## 架构决策核对

- ARCH-DECISION-004：两分支均存在，自动合并（PR790 未改）。
- ARCH-DECISION-005 / 006：仅本分支存在，自动合并保留。
- BNVA-02 发布门禁、BNVA-03 导航治理、BNVA-04 页面产品化：均为本分支增量，不与 PR790 冲突。

## 兼容性

PR #790 与本分支同时改动了 Contract V2 装配、Native View Projection 与相关 guard 的源码；
因此不能假设契约/装配行为一致，合并后必须重跑 assembler guard、runtime guard、
business_structure_integrity 与相关 V2 测试，并以合并 SHA 为准，不沿用任一侧历史回执。
