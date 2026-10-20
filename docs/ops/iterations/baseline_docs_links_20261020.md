# 基线文档缺链独立收口（2026-10-20）

## 0. 身份与边界

- 分支：`fix/baseline-docs-links-20261020`
- 基线：`13b0395db4da63147b3f9c311a4bb5d060dc6a4e`
- Formal Product Layer：P4（docs link integrity）
- 范围：24 个历史文档的链接目标、3 个代码示例误识别、批次记录与 run 元数据
- 不做：产品代码、契约、前端、数据库、服务、部署、demo 场景语义

## 1. 问题与分类

`verify.docs.all` 原先在 `verify.docs.links` 失败：

- `missing_count=93`
- 本批 demo 文档贡献 0/93
- 典型来源：`/mnt/e/...`、`/mnt/wsl/...`、`/home/lidefend/sce-product-odoo/...`
  历史绝对路径，以及 `…`、`':none'` 等代码示例被 Markdown 链接正则误识别

分类：`baseline_evidence_defect`，属于 demo 迭代线范围外的既有文档缺陷。

## 2. 处理

- 88 条目标仍存在的历史绝对路径改为仓内相对链接，并保留 `#L<line>` 锚点；
- 7 条目标已不存在的历史链接降为普通文本，不伪造目标；
- 9 + 3 条代码示例用 HTML 实体括号转义，避免被当作 Markdown 链接；
- 合计 93 条全部收口。

## 3. 验证

```bash
PYTHONDONTWRITEBYTECODE=1 make verify.docs.all
```

结果：

- `verify.docs.inventory`：PASS，`docs_markdown_count=1897`
- `verify.docs.links`：PASS，`missing_count=0`
- `verify.docs.temp_guard`：PASS
- `verify.docs.contract_sync`：PASS
- `verify.docs.product_boundary`：PASS，7 tests，13 addon modules / 5 product layers
- `git diff --check`：PASS
- `ci.local.iteration`：PASS（L1，dirty；`unmappedPathCount=0`）

### 3.1 台账基线排除项（BASELINE-AGENT-LEDGER-7）

`verify.agent.ledger.unit` 运行 18 tests，其中 1 个仓库台账测试失败，列出 7 条历史
`.agent` 台账问题：

- `PRODUCT-MENU-CONFIG-ENTRY-20261019.yaml` 不是机器可读 YAML；
- `DAILY-RUNTIME-BATCH-20261019` 的 goal 不可解析；
- `DEMO-ORG-MASTER-20261019` 的 run completed 但 goal 仍 active；
- `DEMO-ORG-MASTER-MERGE-RECORD-20261019` 的 run completed 但 goal 仍 active；
- `DEMO-R1-F02-F03-CONTRACT-LABEL-20261019` 的 run completed 但 goal 仍 active；
- `active-runs.json` 仍登记已完成的 `codex/demo-integration-record-20261019`；
- `active-runs.json` 仍登记已完成的 `feature/demo-r1-realistic-data-20261019`。

这些记录属于其他执行器已完成批次，本批不修改其运行状态或索引；登记为
`BASELINE-AGENT-LEDGER-7`，后续独立 P4 台账收口处理。本批的 docs links 结论不受影响。

## 4. 风险与回滚

- 风险：历史链接降为文本后，读者需按文本中的旧路径自行检索；不制造假链接是有意选择。
- 回滚：回退本批 commit，恢复原始历史链接；不涉及数据库或服务恢复。

## 5. 后续

- 将本分支 commit cherry-pick 到 demo 迭代分支，解除 demo 文档门禁的基线阻塞。
- 然后从 demo 迭代线 Batch 1 开始实施基线 readiness manifest/verifier。
