# 冻结头 Quick 证据分片组合（2026-10-08）

## 1. 责任层声明

- `Formal Product Layer`: **P4**（运维/交付工具）。
- `Layer Target`: `scripts/ops/local_quick_evidence.py`（回执生产者/验证器）、`make/ci.mk` 入口、
  单测 `scripts/verify/test_local_quick_evidence.py`。
- `Standard vs User-Specific`: 平台/交付证据机制本身，不含行业或客户语义。
- `Why Here`: 回执生产者与其消费者（`pr.merge.local_quick_gate` → `verify`）都在这一层；
  「必需目标清单」就是紧邻的 `ci.local.quick.run` 前置列表。
- `Why Not Elsewhere`: 不改产品模块、不动前端渲染、不放宽任何断言/ACL/字段权限/负例，
  不跨 head/tree 组合，也不从清单里删任何必需目标。
- `Blast Radius`: 只新增 `shard`/`compose` 入口与 `make/ci.mk` 两个目标；`run`/`verify` 的既有语义不变。

## 2. 问题

`ci.local.quick` 是**全有或全无**：生产者 `run` 只签一份绑定 head+tree+扫描 coverage 的整体回执，
验证器只认这一种形状。于是冻结头只能由「一次完整运行」证明：

- 运行被中断或中途失败 → 证据为零，必须整列重跑；
- 无法把若干次有界调用（分片、不同执行器/会话）的通过结果组合成同一 head 的证据；
- `ci.local.quick.run` 是一整列 `.PHONY` 前置，Make 层没有逐目标回执。

## 3. 设计

1. **声明式必需目标清单**：从 `make/ci.mk` 的 `ci.local.quick.run:` 前置行机械解析（`required_targets`），
   不手工维护。fail-closed 条件：该行恰好出现一次、不得续行、首 token 必须是 `guard.prod.forbid`、
   token 必须是字面目标名（不含 `$`/`%`/`:`）且不重复。
2. **分片回执（part）**：`make ci.local.quick.shard QUICK_SHARDS=N QUICK_SHARD=i` 执行 `manifest[i::N]`，
   在 `<git-dir>/codex/evidence/ci.local.quick/<head>/parts/shard-i-of-N.json` 写 part 回执，绑定
   head、tree、coverage、`shards`/`index` 与该分片目标列表；要求 clean **主工作树**（linked worktree 拒绝），
   运行失败时不落 part。
3. **组合（compose）**：`make ci.local.quick.compose QUICK_SHARDS=N [EXPECTED_HEAD=<sha>]` 校验
   - 每个分片都在场、`status=passed`、`shards/index` 一致；
   - 每个分片的 `targets` 精确等于 `manifest[i::N]`（顺序由此绑定）；
   - 并集（忽略顺序）必须精确覆盖 manifest：缺、多、重复均拒绝；
   - 所有分片绑定**同一 head 与同一 tree**；分片记录的 coverage 必须等于组合时的当前快照；
   - 重新校验扫描 proof：`proof` 必须等于「由当前快照该 kind 行构造的期望 dict」全等
     （protocol/kind/head/tree/coverage/mode/base，与整体 `run` 同一形状），`base` 必须是 head 的祖先。
4. 组合成功后签发**与整体运行完全同形**的 schema-3 回执，因此现有验证器与合并前置无需改动即可消费；
   组合来源与各分片哈希另存 `<head>/composition.json` 供审计。

组合**不跨 head/tree**：identity 相同才允许拼接。跨 head 复用需要逐目标输入映射，属后续独立专题。

## 4. 验证

阶段身份：候选提交前 `HEAD=579b2e16…`（= origin/main），dirty（本专题 workspace 改动未提交）。

| 层 | 入口 | 结果 | 非零测试数 |
| --- | --- | --- | --- |
| L1 | `python3 scripts/verify/test_local_quick_evidence.py` | passed | 29 |
| L1 | `python3 scripts/verify/test_branch_governance_consistency_guard.py` | passed | 21 |
| L2 | `ENV=dev make verify.branch.governance.consistency` | passed | 50 |
| L1 | `ENV=dev make ci.local.iteration` | passed | — |

run 记录：`.agent/runs/QUICK-EVIDENCE-SHARD-COMPOSITION/run.json` 的
`local_quick_evidence_composition_unit`，日志
`.agent/runs/QUICK-EVIDENCE-SHARD-COMPOSITION/evidence/verify.branch.governance.consistency.log`。

覆盖到的机械不变量（锁定「声明消费」与「实际行为」，不以字符串出现为证）：

- 分片组合成功 → 签发可被 `verify` 消费的同形回执；
- 缺分片 / 分片多目标或乱序 / 分片绑定其它 head、tree / 分片未 passed / `shards` 不一致 → 全部拒绝；
- 扫描 proof 缺失或与当前快照不一致 → 拒绝且不签发回执；
- 分片在 linked worktree、脏工作树、非法 `--shards/--shard` 下拒绝；分片失败不落 part；
- 清单消费：真实 `make/ci.mk` 的 manifest 非空、首 token 为 `guard.prod.forbid`、字面且不重复；
  合成 makefile 的重复 / 续行 / 变量 / 模式 / 带冒号 / 首 token 错误 / 重复行 / 缺失 → 全部 fail-closed；
- 搭车不变量：本专题候选（`.agent/`+`docs/`+`make/`+`scripts/`）不会被 `pr.merge.local_quick_gate`
  判为 bookkeeping-only，必走 fail-closed 全量路径。

未做（按设计排除）：跨 head/tree 组合、并行分片执行、真实产品部署。

## 5. 边界

本条只主张批次验收与主线集成；版本发布、产品交付均未主张。

候选冻结后，本专题的精确 head 回执由 `make ci.local.quick.shard QUICK_SHARDS=N QUICK_SHARD=i`（逐片）
加 `make ci.local.quick.compose QUICK_SHARDS=N EXPECTED_HEAD=<sha>` 产出，或由一次整体
`make ci.local.quick` 产出；两种来源对验证器与合并前置完全等价。本专题改动 `make/`+`scripts/`，
属非记账类候选，`pr.merge.local_quick_gate` 必走 fail-closed 全量路径，不会被记账短路跳过。

## 6. 收口

- 候选 `e6e434c14efed0406e64da767e86c1fb41b81d31`（tree `50e6ca28deee54dc5dbd2ae1dd63a9fe37ae5f25`），
  分支 `codex/quick-evidence-shard-composition-20261008`，基线 `579b2e16…`。
- 精确 head 回执**由分片 + 组合路径产出**：`QUICK_SHARDS=2 QUICK_SHARD=0/1 make ci.local.quick.shard`
  → `QUICK_SHARDS=2 EXPECTED_HEAD=<sha> make ci.local.quick.compose`，`verify` 通过，回执
  `.git/codex/evidence/ci.local.quick/e6e434c1….json`，组合审计 `<head>/composition.json`。
- PR #618 四项必需检查（`public_guard`、`merge_policy_gate`、`professional_quality_gate`、
  `frontend_release_gate`）在精确 head 全 success；`ENV=dev make pr.merge PR=618 EXPECTED_HEAD=e6e434c1…`
  经受保护 PR 流程 squash 合并为 `429a7f78f5f606dde6188148b463e0e35e35326a`；
  合并前置 `pr.merge.local_quick_gate` 走 `REUSE`（复用组合回执，未重跑）。
- 本专题 run/goal 已标记完成；`.agent/active-runs.json` 回到空终态。
- 合并后 `origin/main` = `429a7f78`。

**状态边界**：批次验收完成 + 主线集成完成；**版本发布未主张，产品交付未主张**。

### 6.1 收口期暴露并修复的两处潜在缺陷（同一收口候选内）

终端退役会让 `pr.merge` 走 fail-closed 全量回退（记账类候选没有精确 head 回执），
正是在这条真实路径上，套件抓到两处既有潜在缺陷：

1. **门禁测试 harness 不密闭**（PR #617 引入的真实缺陷）：
   `scripts/verify/test_branch_governance_consistency_guard.py` 的 `HARNESS_CONTROLLED_VARS`
   只剥离了 `EXPECTED_HEAD/PR/PR_MERGE_*/MAKEFLAGS/...`，未剥离新增的
   `PR_MERGE_BOOKKEEPING_TERMINAL_RETIRE` / `PR_MERGE_BOOKKEEPING_BASE_REF` /
   `PR_MERGE_LOCAL_QUICK_GATE_SKIP`。当套件被终端退役路径带着这些环境变量运行时，
   `test_bookkeeping_only_candidate_is_denied_before_running_quick` 会误取
   「已确认/已跳过」分支并返回 0，导致**终端退役本身无法合并**。修复：把三个控制变量加入剥离列表，
   并新增 `test_ambient_bookkeeping_controls_cannot_unblock_a_bookkeeping_candidate` 锁住该行为
   （负例已验证：移除剥离项后该测试失败）。
2. **shard/compose 的 stdout 标签误报**：`main()` 对非 `run` 模式统一打印 `VERIFIED`，
   而 `shard`/`compose` 实际是**记录**证据。修复：`result_label(mode)` —— 只有 `verify` 打印
   `VERIFIED`，`run`/`shard`/`compose` 打印 `RECORDED`；新增单测锁定映射。

两处修复均不改变回执/part 内容与门禁强度，未放宽任何断言、ACL、字段权限、负例或必需目标。
