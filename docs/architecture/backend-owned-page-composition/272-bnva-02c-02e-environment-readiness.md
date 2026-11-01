# 272 · BNVA-02C-02E-01 · 首次安装验收环境就绪检查

## 四项检查

### 1. local.clean 隔离性 — PASS

compose `sc-local-clean`、数据库 `sc_clean`、卷 `sc_local_clean_*`，与 dev / test /
production 完全分离；容器 odoo/db/redis/nginx 均 Up(healthy)。

### 2. Odoo 应用容器 — 运行但缺凭证

`sc-local-clean-odoo-1` 运行健康；但 `.env.local.clean` **缺失**，无法安全重建
clean 库（`local.clean.rebuild` / `local.clean.install` 需该凭证文件）。

### 3. 财务角色 fixture — 缺口

`fixture_role_finance` 只注册在 acceptance profile（`sc_frontend_acceptance` /
candidate），不在 `local.clean`（clean 无 demo/fixture 用户）。全新安装 + 财务角色
登录需要额外把 fixture 角色注入 clean 库，或使用专用 fresh-acceptance 环境。

### 4. 浏览器与证据采集 — 可用但不绑定 clean

acceptance profile 具备 `SC_ACCEPTANCE_FIXTURE_PASSWORD`、role_bindings、frontend
pidfile/logfile 与浏览器探针；但该环境是历史库，不是 fresh-install。

## 结论

环境未完全就绪：fresh-install（local.clean）与财务角色/浏览器验收能力分属两个
profile，且 clean 凭证缺失。02E-02 前需补齐：重建 `.env.local.clean`（或等价
凭证）+ 在 fresh 库注入 `fixture_role_finance` + 接通浏览器与证据采集。

本轮只检查，未重建数据库、未改配置。

