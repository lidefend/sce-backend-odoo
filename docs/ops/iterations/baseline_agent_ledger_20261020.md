# 基线 Agent 台账独立收口（2026-10-20）

## 0. 身份与边界

- 分支：`fix/baseline-agent-ledger-20261020`
- 基线：`3e1ceb34ac54b364c701d54666e8e7bf8665fdd3`
- Formal Product Layer：P4
- 范围：`.agent` 目标/运行/索引元数据与批次记录
- 不做：产品代码、契约、数据库、服务、部署、历史完成结果改写

## 1. 当前完整 7 条

复核命令：`python3 scripts/verify/agent_ledger_consistency_guard.py`

1. `.agent/goals/PRODUCT-MENU-CONFIG-ENTRY-20261019.yaml` 不是机器可读 YAML；
2. `.agent/runs/DAILY-RUNTIME-BATCH-20261019/run.json` 的 goal 指向字符串；
3. `DEMO-ORG-MASTER-20261019` 的 run completed 但 goal 仍 active；
4. `DEMO-ORG-MASTER-MERGE-RECORD-20261019` 的 run completed 但 goal 仍 active；
5. `DEMO-R1-F02-F03-CONTRACT-LABEL-20261019` 的 run completed 但 goal 仍 active；
6. `active-runs.json` 仍登记已完成的 `codex/demo-integration-record-20261019`；
7. `active-runs.json` 仍登记已完成的 `feature/demo-r1-realistic-data-20261019`。

与上一轮清单逐条一致，无新增、无漂移。

## 2. 处理

- `PRODUCT-MENU-CONFIG-ENTRY-20261019.yaml` 补齐 `schema_version` 与 `goal` 映射；
- 新增 `DAILY-RUNTIME-BATCH-20261019.yaml`，run 的 goal 改为该文件；
- `DEMO-ORG-MASTER-20261019` 与 `DEMO-R1-F02-F03-CONTRACT-LABEL-20261019` 的 goal 关闭为
  `completed`，保留原 run 的完成证据与下一步边界；
- 从 `active-runs.json` 移除两条已完成 run 的索引；
- 保留所有历史 run 的 `status=completed`、`completion`、`verification_results` 和合并记录，
  不复活、不重跑、不改写完成事实。

## 3. 验证

结果：

- `make verify.agent.ledger.unit`：PASS，18 tests；
  `PASS goals=130 runs=117 pinned_residuals=2 open_run_allowlist=2`
- `make ci.local.iteration`：PASS，L1，`unmappedPathCount=0`
- `PYTHONDONTWRITEBYTECODE=1 make verify.docs.all`：PASS，`missing_count=0`
- `git diff --check`：PASS
- metadata JSON/YAML 解析：PASS

## 4. 回滚

回退本批 commit，恢复 7 条原始元数据；不涉及数据库、服务或产品代码恢复。
