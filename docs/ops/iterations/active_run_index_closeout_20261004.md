# 活动 run 索引收口（P4 运维治理）

- 批次：`ACTIVE-RUN-INDEX-CLOSEOUT`
- 基线：`main` = `bcd6c47ee727aa957285204df986e9f3f1f4a01e`（PR #557 合并后）
- 责任层：P4 ops/交付治理；仅 `.agent` 元数据。

## 背景

`REMOTE-BRANCH-CARRIER-RETIREMENT`（PR #557）在冻结候选里把
`.agent/active-runs.json` 绑到自身分支，这是记录离线检查回执所必需的。
该候选合并、分支退役后，索引里会留下一条指向已退役分支的悬挂映射。
既有收口先例（`WORKSPACE-FINAL-CLOSEOUT`）要求收口后
`.agent/active-runs.json` 回到 `{"schema_version":1,"branches":{}}`，
本批只做这一件事，不改任何 run/goal/manifest，也不删除任何远端引用。

## 顺序

工作期索引仍绑定本批分支以记录回执；**最终提交**把 `branches` 清空，
随后在该冻结 HEAD 上跑一次 `ci.local.quick`（Quick 不依赖 run 绑定），
再经普通 PR 车道合并。冻结后 `make ci.local.iteration` 会报 `unregistered`，
与既有 closeout 先例一致。

## 证据

- 回执：`.runtime/agent-runs/ACTIVE-RUN-INDEX-CLOSEOUT/agent_resume.json`
- 最终状态：`.agent/active-runs.json` 的 `branches` 为空对象
