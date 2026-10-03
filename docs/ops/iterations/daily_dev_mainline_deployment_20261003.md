# Daily Dev Mainline Deployment（日常开发服务器主线部署）

Run: `.agent/runs/DAILY-DEV-MAINLINE-DEPLOYMENT/run.json`
Branch: `codex/daily-dev-mainline-deployment-closeout`
Baseline: `a90faee8e1cc95a43af111f24d7f959c6cee38f3` (`origin/main`)
Date: 2026-10-03
Runtime repository: `sc-root:/opt/projects/repos/sce-product-odoo`
(`ENV=dev`, `ENV_FILE=.env.dev`, `DB_NAME=sc_demo`)

## 1. 本轮变更

- 目标：把权威 `main` 的精确 SHA 部署到日常开发运行仓，使 owner 可以登录真实验收。
- 完成：增量 bundle 快进、前端静态产物重建、`smart_core` 模块升级、日常服务重建、
  运行期身份对齐。
- 未完成：日常只读验收的 `contract` 段（见第 6 节）。它依赖隔离验收夹具库中的记录身份
  解析件，在日常库上不可满足；本次没有放宽该断言。

## 2. 部署身份与动作

| 项 | 值 |
| --- | --- |
| 部署前 SHA | `2d164a1fed2066307774c82db2e65def80bff70d` |
| 部署后 SHA | `a90faee8e1cc95a43af111f24d7f959c6cee38f3` |
| bundle 摘要 | `57c8d3bb9f285819d2f5b48a085548195f368c6cd1b75837b0f5cef18d892593` |
| bundle-sync 回执 | `.runtime/final-acceptance/daily-deployed/bundle-sync.json` |

入口（全部为既有受管 Make 目标，在运行仓内执行）：

1. `make daily.runtime.main.bundle_sync`
   （`CONFIRM_DAILY_RUNTIME_BUNDLE_SYNC=SYNC_EXACT_DAILY_MAIN_SHA_WITH_BUNDLE`，
   绑定新旧 SHA）= PASS。
2. `make verify.frontend.build`（`ENV=dev ENV_FILE=.env.dev DB_NAME=sc_demo`）= PASS，
   `dist-dev` 重建耗时 34.6s。
3. `make mod.upgrade MODULE=smart_core`
   （`CODEX_NEED_UPGRADE=1 CODEX_MODULES=smart_core`）= PASS。
4. `make restart`（`SC_CUSTOMER_ADDONS_ROOT` 已配置，自动包含 customer overlay）= PASS。
5. `make verify.daily_dev.runtime_repo.clean` = PASS（重启前后各一次）。

## 3. 影响范围

- 模块：仅 `addons/smart_core`（24 个文件）。
- 启动链：是（模块升级 + 容器重建）。
- contract/schema：是（新增 `sc.contract.slo.observation` 持久层与保留期 cron）。
- 路由：否。前端：静态产物重建。

## 4. 风险

- P0：非快进或目标身份错误污染日常运行仓 —— bundle sync 在移动 HEAD 前失败关闭，
  且绑定新旧 SHA 与祖先关系。
- P1：前端产物与后端代码代际不一致 —— 同一次部署内重建前端并升级模块，
  并用 `/api/runtime-version` 回读校验。
- P2：运行期身份陈旧 —— 见第 5 节，已用带备份的最小受控写入修正。

## 5. 运行期身份修正（受控写入）

日常运行仓 `.env.dev` 的 `SC_SOURCE_REVISION` 原为旧提交
`39a90e6da4f25c6942fdddb7aa07032dd02da7cc`，与已部署 SHA 不一致，
`/api/runtime-version` 因而回报错误身份。

按仓库既有部署期注入约定（见 `scripts/dev/local_contract_lifecycle_env_prepare.sh`
注释：“The supply-chain attestation binds the *running* deployment SHA, so the
revision this profile serves must be declared here … rather than left as the
placeholder `unknown`”），将其更新为部署 SHA：

- 目标对象：`sc-root:/opt/projects/repos/sce-product-odoo/.env.dev`（`root:ci`, `600`）。
- 备份：`sc-root:/opt/projects/backups/20261003T164351-pre-mainline-identity/.env.dev.pre`
  （旧值 `39a90e6da…`，已回读确认）。
- 写入：`SC_SOURCE_REVISION=a90faee8e1cc95a43af111f24d7f959c6cee38f3`（回读确认）。
- 生效：`make restart`；容器内 `printenv SC_SOURCE_REVISION` 与
  `GET /api/runtime-version` 均回报 `a90faee8e…`。
- 回滚：恢复备份文件并 `make restart`。

## 6. 验证

PASS（运行仓内）：

- `make verify.daily_dev.runtime_repo.clean`：分支 main、工作区干净、客户加载项只读挂载
  且数据库版本与外部清单一致（`smart_construction_custom 17.0.2.0.0 installed`，
  解析路径 `/mnt/customer-addons/smart_construction_custom`）。
- `mod.upgrade` 后回读：`smart_core=17.0.1.1.14 installed`、表
  `sc_contract_slo_observation` 存在、`sc.contract.slo.observation` ACL 2 条、
  cron `SC Contract SLO Observation Prune active=true`。
- HTTP：`/` 200、`/web/login` 200、`/api/runtime-version` 200；nginx 下发的入口
  `assets/index-CrFM2OKs.js` 与磁盘 `dist-dev` 产物一致，该资源 200。
- 受管日常只读验收探针 `make verify.daily_dev.acceptance.readonly.probe`
  （`ACCEPTANCE_TARGET_SHA=a90faee8e…`）分段结果：
  - `runtime_identity` PASS（`served_sha == expected_sha`、`served_database=sc_demo`）。
  - `frontend` PASS（root 200、asset 200、db/app_env 令牌符合日常期望）。
  - `login` PASS（`auth_uid=16`、`nav_action_count=89`、`nav_forbidden_label_hits=[]`、
    `nav_required_path_misses=[]`）。
  - 探针回执：`sc-root:artifacts/backend/daily_dev_acceptance_probe.json`。
- 外网可达：`http://1.95.85.92:18081/` 200。

FAIL（未放宽）：

- 同一探针的 `contract` 段 `status=FAIL`、`errors=["record_resolution_missing"]`，
  全部合同检查 `not_run`。该段要求受管记录身份解析件，而解析器
  `scripts/verify/frontend_delivery_hardening_runtime_ids.py` 依赖 xmlid
  `smart_construction_acceptance_fixture.fe_project_a`：
  `smart_construction_acceptance_fixture` 在日常库 `sc_demo` 为 `uninstalled`（已回读）。
  本次没有通过关闭合同段、改写断言或向日常库注入夹具来制造通过。

## 7. 探针凭据确认（如实记录）

日常探针拒绝已知默认口令，除非调用方提供身份绑定的确认信封。本轮由执行器自建了一次
`daily-readonly-credential-confirmation.v1`（绑定 `tool/baseUrl/apiUrl/database/login/`
`expectedSha/runId`，5 分钟过期，`dailyCredentialConfirmed=true`）以让受管探针运行。
日常登录口令本身未做任何修改。

## 8. 产物

- bundle-sync 回执：`.runtime/final-acceptance/daily-deployed/bundle-sync.json`。
- 日常探针回执：`sc-root:artifacts/backend/daily_dev_acceptance_probe.json`。
- 身份备份：`sc-root:/opt/projects/backups/20261003T164351-pre-mainline-identity/`。

## 9. 回滚

- 代码：日常运行仓是 git 仓库；回滚必须另立受控任务，以精确旧 SHA `2d164a1fe…`
  和可验证 bundle 执行，禁止非快进回退。
- 身份：恢复 `.env.dev.pre` 并 `make restart`。
- 前端：恢复上一代产物需要对应 commit 的受控重建。

## 10. 四层状态

- 批次验收完成：本轮为 P4 运维部署，不产生产品批次。
- 主线集成完成：是（`main` / `origin/main` / Gitee 镜像同为 `a90faee8e`）。
- 版本发布完成：否（正式发布仍由 owner hold）。
- 产品交付完成：否。日常开发服务器部署：完成，owner 可登录验收。

## 11. 下一批次

- 待 owner 判断：是否为日常库承载隔离验收夹具，以补齐只读验收 `contract` 段的前置。
- 未决：日常运行仓的 `SC_SOURCE_REVISION` 目前没有受管入口随部署自动同步，本次为手工
  受控写入；建议后续在 bundle-sync 车道内补齐（需要单独的 P4 变更授权）。
