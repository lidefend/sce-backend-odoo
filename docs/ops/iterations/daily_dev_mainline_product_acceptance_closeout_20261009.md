# Daily Dev Mainline Product Acceptance Closeout（最新主线产品验收收口，2026-10-09）

Run: `.agent/runs/DAILY-DEV-MAINLINE-PRODUCT-ACCEPTANCE-CLOSEOUT/run.json`
Branch: `audit/daily-dev-mainline-product-acceptance-closeout-20261009`
Baseline: `aea2c19bbe4edb2a13fbf908255e918e18f3a299`（`main`，PR #630 退役后）

## 1. 目标与责任层

- **Formal Product Layer**：P4（ops delivery / 运行态验收收口）。
- **Layer Target**：日常开发运行态（`sc-root:/opt/projects/repos/sce-product-odoo`，`ENV=dev`，
  `DB_NAME=sc_demo`，入口 `http://1.95.85.92:18081/`）主线身份对齐 + 用户视角验收边界收口。
- **Standard vs User-Specific**：运维交付与验收，无行业/客户语义。
- **Why Here**：验收入口必须服务最新主线，属交付验收层。
- **Why Not Elsewhere**：不改 P0-P3 产品语义，不放宽 ACL/字段权限/断言，不新增环境/凭据。
- **Blast Radius**：日常运行仓的 git 树与 served 身份；`sc_demo` 只读验收面。

## 2. 复用裁定（为什么不是重跑矩阵）

- `git diff --stat bfb38367 aea2c19b -- addons/ frontend/` **为空**：最新主线相对已验收态
  （served `bfb38367`，`bfb38367` 是 `aea2c19b` 的祖先）**产品代码零变化**。
- 该区间唯一的验收工具变化是 PR #626（`b28d4499`）对 `dailyHomeSummaryMatches` 的收紧断言
  与路由规则；其受影响断言已在 `docs/ops/iterations/hierarchical_worksheet_usable_ready_20261008.md`
  §13 重跑并通过（served `bfb38367`：`router-workspace-home` 明暗各 `summaryResponses=1`、`officialCards=3`）。
- 既有验收的唯一未决产品策略项（`项目台账` `/f/` ↔ `readonly`）已于 2026-10-09 由同记录 §14 收口。
- 前端产物只依赖前端源（未变）→ 已验收产物 `b0311c6f` 仍为当前产物。
- 结论：**不重跑验收矩阵**（`.agent/decisions/evidence-reuse-identity.yaml` OPS-DECISION-002）。

## 3. 状态

- 批次验收：进行中（本文件随执行更新）。
- 主线集成：本轮为运行态对齐 + 收口，不做产品代码候选。
- 版本发布：未主张。
- 产品交付：待所有者登录核对后判定。
