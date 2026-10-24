# Quick 输入范围复用（设计，planned）

责任层：P4 交付工具。目标：让 `ci.local.quick` 不再为「只改一个 target 输入」的提交
全量重跑 129 个 target，而是只重跑受影响 target、复用未变 target 的回执。

## 现状与根因

- `local_quick_evidence.py verify` 的 carry-forward 只接受 `bookkeeping_only_delta`
  （docs/.agent/.codex/.devcontainer/*.md），且该判定与 `runtime_tree_digest`
  （非记账整树摘要）等价——所以任何代码文件（含 `scripts/ci/*`、`scripts/ops/*`）改动
  都使摘要变化 → 全量重跑 ~7 分钟。
- 三个可信扫描已在 `trusted_scan_scope.py` 内做增量（scan-authority 不变就复用祖先回执），
  但 Quick 整体不按 target 粒度复用。

## 设计方向

1. 给 `ci.local.quick.run` 的每个 target 登记输入指纹（复用 `evidence_scope` 的
   units/ledger 机制，check 为 `ci.local.quick.target`）。
2. 一次提交后：计算 delta → 逐个 target 判定 affected/reusable；只执行 affected。
3. 只有「affected=0」才签发整 Quick 回执；部分执行保留分片回执，不冒充全绿。
4. 三个扫描的 authority 判定继续由 `trusted_scan_scope.py` 持有，不重复实现。

## 边界

- 不动任何门禁断言、不改 Quick 覆盖集合；只改「何时重跑」。
- 冻结交付（clean head + 全指纹）仍全量执行一次 Quick，不被输入范围复用绕过。

## 第一增量（已落地并测试）

`scripts/ops/quick_input_scope.py`：
- `quick_targets()`：`ci.local.quick.run` 传递闭包实测 128 target。
- `target_inputs()`：target → 引用脚本 + recipe 显式文件路径；98 个 target 有声明输入，
  30 个无声明输入（fail-closed RUN）。
- `target_fingerprint()`：recipe + 输入文件 blob 的内容寻址指纹。
- `affected_targets()`：两个精确提交之间逐 target 判 RUN/REUSE。

`verify.quick.input_scope.unit` 已接入 `ci.local.quick.run`（本地 Quick）与
`ci.professional.backend.shard-verify`（远端专业门禁），3 项单测 PASS。

下一步：把 `affected_targets` 接进 `local_quick_evidence.py`，让 Quick 实际跳过可复用 target、
只执行 affected target；保留冻结交付全量执行。
