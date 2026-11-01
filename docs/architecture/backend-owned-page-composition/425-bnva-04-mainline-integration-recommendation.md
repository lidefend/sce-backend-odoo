# 425 · BNVA-04 Mainline Integration Recommendation

## 提交策略

推荐 **Merge Commit**，理由：

- BNVA-01～04 是连续治理历史，不应改写。
- PR #790 已进入 GitHub main，必须作为历史事实纳入。
- 冲突集中在少量架构文件，可通过一次受控合并提交解决。

不推荐 Rebase（会改写 122 提交历史）；不推荐 Cherry-pick（会割裂 BNVA 治理链）。

## 合并顺序

1. 以 GitHub main 为唯一目标。
2. 本地创建合并提交：`git merge origin/main`，逐文件裁定冲突：
   - 架构源码（native_view_projection / assembler / ui_contract_v2 / guard）：以本分支演进版本为基，
     逐项核对 PR790 是否含本分支缺失的独立增量后合并，禁止 ours/theirs 二选一。
   - 测试：统一为演进后的断言，补 PR790 独有覆盖。
   - .agent 元数据：三向合并 active-runs 与 BNVA-01 run。
   - 生成报告：合并后重新生成。
3. 精确 HEAD 跑 `ci.local.quick`（clean 冻结候选）。
4. 受保护 PR → GitHub CI → 合并 main。

## 前置裁决

合并前必须先人工/独立复核 native_view_projection 与 assembler 的两份实现差异，确认本分支是
PR790 的严格演进且无丢失增量。未确认前不执行 merge。
