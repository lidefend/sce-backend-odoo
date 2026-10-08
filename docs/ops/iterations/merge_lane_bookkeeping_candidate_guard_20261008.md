# 合并门禁：记账类候选短路（2026-10-08）

## 1. 责任层声明

- `Formal Product Layer`: **P4**（运维/交付工具）。
- `Layer Target`: `make/codex.mk` 的 `pr.merge.local_quick_gate`（合并前置门禁）+ 其单元测试
  `scripts/verify/test_branch_governance_consistency_guard.py` + 规则文本
  `docs/ops/codex_workspace_execution_rules.md`。
- `Standard vs User-Specific`: 平台/交付机制本身，不含行业或客户语义。
- `Why Here`: 门禁与规则文本就是该约束的机械载点；`ci.local.quick` 的生产者
  (`scripts/ops/local_quick_evidence.py`) 与合并前置都在这一层。
- `Why Not Elsewhere`: 不改产品模块、不动前端渲染、不放宽任何断言/ACL/字段权限/负例，
  不取消四项必需远端检查，也未经由 `PR_MERGE_LOCAL_QUICK_GATE_SKIP`（该变量仅服务单元测试 harness）。
- `Blast Radius`: 只影响“精确 head 无回执且差异全部落在 `.agent/`+`docs/`”的合并前置判定；
  其余候选路径不变。

## 2. 缺陷事实

`make ci.local.quick` 是**精确候选生产者**：每个冻结 commit 只签发一份回执，无自复用分支。
合并门禁 `pr.merge.local_quick_gate` 历史上只有两条路径——复用同 head 回执，或全量跑一次。
策略层面“按输入复用”“能复用必须先复用”已写死在 `AGENTS.md` 与
`docs/ops/codex_workspace_execution_rules.md`，但**机械层面缺少记账类短路**，于是
“只改台账再冻结一次候选”既拿不到新增覆盖，又必然多付一次全量套件。

已发生的实例：PR #613（纯 `chore(agent)` 退役提交 `2ff12544`）照付了一次全量 Quick
（回执 `.git/codex/evidence/ci.local.quick/2ff12544….json`）。本轮同一 P1 专题也因此出现 3 个
冻结候选（`a9ce7528` / `ae0c5ba6` / `f833b860`）→ 3 次全量 Quick，其中 `ae0c5ba6` 为纯簿记。

## 3. 修复

`pr.merge.local_quick_gate` 增加记账类短路，判定顺序为：

1. `harness skip`（既有，仅单元测试使用）。
2. **精确 head 回执复用（既有，零成本）** —— 记账类候选只要已有回执仍走 `REUSE`，不被拦。
3. 记账类判定：取 `git merge-base HEAD ${PR_MERGE_BOOKKEEPING_BASE_REF:-origin/main}`；若差异非空且
   **全部**落在 `.agent/` 与 `docs/`，输出 `DENY: bookkeeping-only candidate`、逐条打印改动路径并
   `exit 13`，**不启动全量套件**，同时提示该台账改动应搭相邻产品候选。
4. 终端退役豁免：`PR_MERGE_BOOKKEEPING_TERMINAL_RETIRE=<reason>` 显式声明后走常规
   “复用 / fail-closed 回退”路径，仍在日志留痕。
5. fail-closed 方向：基线不可解析、差异为空、或出现任一非 `.agent/`/`docs/` 路径 → 一律按非记账类处理。

该门禁**只增加检查**：不放宽断言、ACL、字段权限、负例，也不取消 `public_guard`、
`merge_policy_gate`、`professional_quality_gate`、`frontend_release_gate` 四项必需检查。

## 4. 验证（离线、非零）

- `python3 scripts/verify/test_branch_governance_consistency_guard.py` → `Ran 20 tests … OK`。
  新增 4 项：
  - 记账类候选（无回执）被拒绝且不出现 `running make ci.local.quick`，回执探测只发生 1 次；
  - 含产品路径（`make/codex.mk`）仍走 fail-closed 全量回退；
  - `PR_MERGE_BOOKKEEPING_TERMINAL_RETIRE` 显式声明走常规路径；
  - 基线引用不可解析时不产生任何跳过。

## 5. 边界

本条只主张批次验收与主线集成；版本发布、产品交付均未主张。本候选自身包含
`make/`+`scripts/` 改动，因此按非记账类正常支付一次精确 head Quick，不适用本次新增的短路。
