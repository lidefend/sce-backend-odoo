# Daily Runtime Exact Bundle Sync — Batch-DRS-1

## 1. 本轮变更

- 目标：在日常服务器 GitHub smart-HTTP 不可用时，仍能把权威 `main` 精确快进到指定 SHA。
- 完成：新增增量 Git bundle、SHA-256 校验、SSH 传输、远端锁、旧/新 SHA、upstream、祖先关系与工作树双向校验的受控 Make 入口。
- 未完成：工具合并后执行真实日常同步，并继续原 action 根因修复的模块升级与发布验收。

## 2. 影响范围

- 模块：`scripts/ops/daily_runtime_bundle_sync.py`、`make/codex.mk` 和日常运行仓库规范。
- 启动链：否。
- contract/schema：否。
- 路由：否。

## 3. 风险

- P0：非快进或目标身份错误可能污染日常运行仓库；所有相关条件均在移动 HEAD 前失败关闭。
- P1：同步成功而本地 upstream 未对齐会阻断后续发布；工具将 `main` 与 `origin/main` 同步到同一 bundle 证明的 SHA，并在返回前复验。
- P2：传输中断留下临时 bundle；远端 `finally` 精确删除单个临时文件，且仓库保持原 SHA。

## 4. 验证

- PASS：`make verify.daily.runtime.main.bundle_sync`。
- PASS：从权威 `refs/remotes/origin/main` 生成 bundle，临时远端仓库正向快进
  `main`/`origin/main`，并验证文件内容更新。
- PASS：远端脏工作树负向夹具在移动 HEAD 前失败。
- PASS：`python3 scripts/verify/environment_topology_guard.py`。
- CONDITIONAL：`make verify.restricted` 的前端 lint/typecheck/build 通过；总线仍被既有第二公司快照 `1/2` 阻断。

## 5. 产物

- 真实同步证据：`.runtime/final-acceptance/daily-deployed/bundle-sync.json`。
- 单元测试：`scripts/ops/test_daily_runtime_bundle_sync.py`。

## 6. 回滚

- 工具回滚：恢复本批提交；不影响已同步的产品提交内容。
- 日常仓库回滚：必须另立受控任务，以精确旧 SHA 和可验证 bundle 执行；禁止非快进回退。

## 7. 下一批次

- 目标：同步日常服务器到正式 action 根因修复 SHA，完成配对备份、模块升级与正式发布验收。
- 前置条件：本工具当时所要求的检查已完成且精确合并完成。
- 迁移注记（2026-08-31）：当前制度应区分 `merge_policy_gate` 的合并资格
  与 `release_candidate_gate` 的发布资格。
