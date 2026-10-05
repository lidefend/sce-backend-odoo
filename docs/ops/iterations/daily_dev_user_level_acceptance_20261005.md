# Daily Dev User-Level Acceptance（日常开发服务器用户级交付验收，2026-10-05）

Run: `.agent/runs/DAILY-DEV-USER-LEVEL-ACCEPTANCE/run.json`
Branch: `codex/daily-dev-user-acceptance-20261005`
Baseline: `4ba044e037a7bf2c3d737eaec94ea891fc602581` (`main`，PR #572 后)
Date: 2026-10-05
Runtime repository: `sc-root:/opt/projects/repos/sce-product-odoo`
(`ENV=dev`, `ENV_FILE=.env.dev`, `DB_NAME=sc_demo`)
Owner acceptance entry: `http://1.95.85.92:18081/`（自定义前端），口令 `wutao/123456`

## 1. 目标与责任层

- **Formal Product Layer**：P4（ops delivery / 运行态验收工具）。
- **Layer Target**：日常开发运行态（sc-root）主线提升 + 用户视角产品交付验收。
- **Module**：`.agent`、`docs/ops/iterations`、`scripts/ops`（只读探测）。
- **Standard vs User-Specific**：运维交付；无产品语义、无客户基线、无平台机制变更。
- **Why Here**：把权威 `main` 精确 SHA 提升到日常运行态并以真实用户验证，属交付验收层。
- **Why Not Elsewhere**：不改 P0 平台/前端契约、P1 行业语义、P2 客户偏好/数据基线、P3 运行配置，
  不做 schema/迁移/生产变更。
- **Blast Radius**：sc-root 日常运行仓、其前端静态产物与 dev compose profile、`sc_demo`
  的 wutao 验收口令；不改隔离验收库、`sc-local-*`、生产租户、通用登录默认。

## 2. 状态（占位，执行中）

- 部署前 served SHA：`8a77c237`（PR #550）。
- 目标 served SHA：`4ba044e0`（PR #572）。

## 3. 执行记录（占位）

（受管入口回执与浏览器验收结果回填）

## 4. 四层状态（占位）

- 批次验收：
- 主线集成：
- 版本发布：未主张。
- 产品交付：
