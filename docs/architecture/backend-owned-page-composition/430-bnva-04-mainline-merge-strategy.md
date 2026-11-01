# 430 · BNVA-04 Mainline Merge Strategy

## 提交策略

Merge Commit（不 Rebase、不 Cherry-pick），目标 GitHub main。

## 冲突文件处理

- 6 个源码冲突文件：全部取 Feature 演进版（严格演进/演进适配）。
- complexity_budget_report.md / split_plan_queue.md：合并后重新生成，不手工拼接。
- .agent/active-runs.json：三向合并，保留当前 BNVA-04 活动项，按真实状态归并 PR #790 的
  BNVA-01 / PHASE5-01 历史项。
- .agent/runs/BNVA-01/run.json：取 Feature 演进版，核对无丢失 PR #790 记录后合并。

## 合并后必须执行

- 在合并 SHA 上重跑 assembler guard、runtime guard、business_structure_integrity、
  unified_page_contract v2 相关测试。
- 定向验证技术字段排除链路。

## 结论

可以安全 Merge Commit；不采用 ours/theirs 二选一，以 Feature 演进版为基、生成报告重新生成、
治理元数据三向归并。
