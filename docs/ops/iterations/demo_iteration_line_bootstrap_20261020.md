# Demo 迭代线 Bootstrap（2026-10-20）

## 0. 身份与边界

- 分支：`feature/demo-iteration-line-20261020`
- Worktree：`/home/lidefend/workspace/sce-backend-odoo-local-env`（专用 demo 树）
- 基线：`13b0395db4da63147b3f9c311a4bb5d060dc6a4e`（`feature/daily-batch-demo-multicompany-20261019` HEAD）
- Formal Product Layer：P4（demo delivery tooling）
- Supporting Layers：P0/P1/P3（仅登记产品缺口，不在本批修改）
- Module：`smart_construction_demo`、`scripts/verify`、`deploy/demo-tenant`、`docs/demo`
- 本批性质：文档、基线排查、总体计划、run 登记；不落库、不改产品代码、不改服务。

## 1. 预检

- `pwd` / `git rev-parse --show-toplevel`：`/home/lidefend/workspace/sce-backend-odoo`
- 起始分支：`main`，工作树干净
- 当前分支：`feature/demo-iteration-line-20261020`
- 起始 HEAD：`13b0395db4da63147b3f9c311a4bb5d060dc6a4e`
- 已登记 worktree：主仓 + `sce-backend-odoo-local-env`；本批只写专用 demo 树
- Docker/D B 只读回读：`not_run`（当前沙箱无法访问 Docker socket，未执行数据库查询）

迁移说明：Batch 0 最初误落在主仓工作树；已按所有者口径迁移到专用 demo 树，
主仓已恢复 `main` 干净状态。后续 demo 迭代只在专用 demo 树进行。

## 2. 本批变更

- 新增 `docs/demo/demo_baseline_readiness_v1.md`：G0–G6 基线就绪矩阵、硬前置、
  派生/配置分类、业务动作依赖、当前缺口。
- 新增 `docs/demo/demo_iteration_line_v1.md`：demo 迭代线总体计划、批次拆分、
  日运行架构、体验重置边界、10 日业务线、产品缺口归属。
- 更新 `docs/demo/system_demo_v1.md`：增加总体计划入口。
- 新增 `.agent/goals/DEMO-ITERATION-LINE-20261020.yaml` 与 run 记录。
- 更新 `.agent/active-runs.json`：登记当前分支。

## 3. 排查结论

1. **基线顺序**：租户/公司 → 组织/身份 → 业务主数据 → 治理配置 → 项目基线 →
   交易事实 → 证据投影。G0–G4 未就绪时，不应进入合同/结算/付款补数。
2. **作用域问题**：正式入口验收表 90 行中 65 行记录空态/0 渲染，27 行明确是
   “数据归属公司 1、受测公司作用域排除”。先修公司/角色/数据作用域。
3. **真实性问题**：showroom 种子仍有 `100.0` 结算单价、`50.0` 付款金额；
   部分场景固定 2025 年日期，与当前 2026 年业务日历不一致。
4. **验证口径**：`demo.verify` 主要是 SQL 存在性，不足以证明审批链、角色可见性、
   跨记录金额/日期自洽和用户下一步。
5. **审批提示**：`payment.request.available_actions` 的 approve/reject 岗位提示固定为
   executive，而默认付款审批是四级；实际 `allowed` 仍按 `can_review`，但交接提示会误导。
6. **组织与审批**：组织 `manager_id` 只用于展示/分组，不构成审批路由；若产品期望
   “部门负责人审批”，属于 P1 机制缺口。
7. **体验重置边界**：当前 `scems-demo-tenant.timer` 04:00/16:00 调用
   `make demo.tenant.reset`，后者是全库重建 + release seed；按最新口径，体验重置只能清理
   体验用户产生的增量，不能重置 demo 基线。Batch 5 必须先核对 timer 指向的租户身份，
   再决定是保留全库重建（仅隔离体验租户）还是新增 scoped experience reset。

## 4. 验证

待执行：

- `make verify.docs.all`
- `make verify.docs.product_boundary`
- `make verify.agent.ledger.unit`
- `make ci.local.iteration`

当前状态：`verify.docs.all` 在 `verify.docs.links` 处失败（基线遗留 93 条缺链），
本批文档贡献为 0；`temp_guard`、`contract_sync`、`product_boundary` 未由聚合入口执行。

已完成的轻量校验：

- metadata JSON/YAML 解析：PASS
- `git diff --check`：PASS
- `make agent.run.resume`：`status=resolved`，`run_status=verification_pending`，
  `outside_scope=[]`
- 主仓工作树：已恢复 `main`，无本批残留

### 4.1 基线遗留链接排除项（BASELINE-DOCS-LINKS-93）

复跑命令：

```bash
PYTHONDONTWRITEBYTECODE=1 make verify.docs.all
```

执行顺序与结果：

1. `verify.docs.inventory`：PASS，`docs_markdown_count=1899`；
2. `verify.docs.links`：FAIL，`missing_count=93 > max_missing_allowed=0`；
3. `verify.docs.temp_guard`：未执行；
4. `verify.docs.contract_sync`：未执行；
5. `verify.docs.product_boundary`：未执行。

缺链归属核对：

- 报告：`artifacts/docs/docs_links_report.json` / `.md`
- 缺失链接总数：93
- 本批三份文档贡献：0/93
- 本批文档内部链接：3 个文件、7 条内部链接、0 条缺失
- 典型基线来源：`/mnt/e/...`、`/mnt/wsl/...`、`/home/lidefend/sce-product-odoo/...`
  等历史绝对路径，以及 `…`、`':none'` 等历史记录格式残留；均不属于本批文档

处理结论：

- 分类：`baseline_evidence_defect`（范围外既有缺陷）
- 本批处理：登记为排除项，不修改 93 条无关链接
- 影响：`verify.docs.all` 不能视为 PASS；Batch 0 只保留元数据解析、
  `git diff --check`、本批内部链接 7/7 和 run 解析证据
- 后续归属：独立的 P4 docs baseline cleanup 批次；不并入 demo 迭代线 Batch 1

## 5. 未运行

- 数据库/模块/种子/浏览器/部署：`not_run`
- 体验重置实际执行：`not_run`
- 日推进 timer 修改：`not_run`

## 6. 风险与回滚

- 风险：若把 `demo.tenant.reset` 误当体验清理入口，会删除 demo 基线并破坏连续性。
- 风险：基线就绪契约若由前端推导，会违反契约驱动边界。
- 回滚：回退本批文档、goal/run 与 active-runs 登记；不改数据库、服务或产品代码，
  回滚不涉及环境恢复。

## 7. 下一批

Batch 1：实现只读 `baseline.readiness` manifest/verifier（P4），离线证明 G0–G6 的
`ready/partial/blocked` 判定，再接入 demo 种子与体验重置门禁。

## 8. 暂停与交接

- 所有者要求：计划完成后先暂停，不进入 Batch 1。
- 当前 run 状态：`verification_pending`（文档计划已完成，门禁尚未执行）。
- 恢复工作树：`/home/lidefend/workspace/sce-backend-odoo-local-env`
- 恢复分支：`feature/demo-iteration-line-20261020`
- 恢复命令：

  ```bash
  cd /home/lidefend/workspace/sce-backend-odoo-local-env
  make agent.run.resume
  make verify.docs.all
  make verify.docs.product_boundary
  make verify.agent.ledger.unit
  make ci.local.iteration
  ```

- 门禁通过后：`make agent.run.record AGENT_CHECK=docs_product_boundary ...` 与
  `make agent.run.record AGENT_CHECK=agent_ledger ...`，再把 run 状态收口。
- 未完成事项：Batch 1 基线 readiness manifest/verifier 尚未开始。
- 环境限制：本次未执行数据库、种子、浏览器、部署或体验重置；Docker socket 不可用。
