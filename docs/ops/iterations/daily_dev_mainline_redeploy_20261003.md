# Daily Dev Mainline Redeploy（日常开发服务器主线刷新）

Run: `.agent/runs/DAILY-DEV-MAINLINE-REDEPLOY/run.json`
Branch: `codex/daily-dev-mainline-redeploy-20261003`
Baseline: `64efb6bf61ba1b7364d03c25fe0a2e1ae8849d75` (`origin/main`)
Date: 2026-10-03
Runtime repository: `sc-root:/opt/projects/repos/sce-product-odoo`
(`ENV=dev`, `ENV_FILE=.env.dev`, `DB_NAME=sc_demo`)

## Objective

Refresh the daily development runtime from `a90faee8e1cc95a43af111f24d7f959c6cee38f3`
to the current mainline `64efb6bf61ba1b7364d03c25fe0a2e1ae8849d75` through the existing
governed entries, then align the served runtime identity so the owner can log in.

## 1. 部署身份

| 项 | 值 |
| --- | --- |
| 部署前 SHA | `a90faee8e1cc95a43af111f24d7f959c6cee38f3` |
| 部署后 SHA | `64efb6bf61ba1b7364d03c25fe0a2e1ae8849d75` |
| bundle 摘要 | `7831855cfa1377c1af3d0ac951addfa5a65478a4fe85c10619c5746c0f13389f` |
| bundle-sync 回执 | `.runtime/final-acceptance/daily-deployed/bundle-sync.json` |
| 远端仓库状态 | `branch=main`、`upstream=origin/main`、工作区干净 |

## 2. 受管入口与结果

在 `sc-root:/opt/projects/repos/sce-product-odoo` 内按既有受管 Make 目标顺序执行：

1. `make daily.runtime.main.bundle_sync`
   （`CONFIRM_DAILY_RUNTIME_BUNDLE_SYNC=SYNC_EXACT_DAILY_MAIN_SHA_WITH_BUNDLE`，
   `DAILY_RUNTIME_EXPECTED_SHA=64efb6bf…`，`DAILY_RUNTIME_EXPECTED_OLD_SHA=a90faee8…`）
   = PASS；回执 `status=PASS`、`changed=true`、`old_sha=a90faee8…`、
   `source_sha=64efb6bf…`、`upstream=origin/main`。该入口要求从 `main` 的精确干净 SHA 执行，
   因此不在本记录的元数据提交上运行。
2. `make verify.frontend.build`（`ENV=dev ENV_FILE=.env.dev DB_NAME=sc_demo`）= PASS
   （36.31s），入口 `assets/index-DGsa_kfq.js`（853556 bytes）在 nginx 容器内存在。
3. `make mod.upgrade MODULE=smart_core`
   （`CODEX_NEED_UPGRADE=1 CODEX_MODULES=smart_core`）= PASS。
4. `make restart` = PASS（odoo 容器 Recreate/Started）。
5. `make verify.daily_dev.runtime_repo.clean` = PASS。
6. `make verify.daily_dev.acceptance.readonly.probe` = 分段结果见第 5 节（`contract` 段 FAIL）。

## 3. 模块与契约层回读

- `ir_module_module`：`smart_core=17.0.1.1.14 installed`、
  `smart_construction_core=17.0.0.169 installed`、
  `smart_construction_custom=17.0.2.0.0 installed`。
- 契约遥测持久层：表 `sc_contract_slo_observation` 存在，
  `sc.contract.slo.observation` ACL 2 条，cron `SC Contract SLO Observation Prune active=true`。

## 4. 运行期身份修正（受控写入）

- 目标对象：`sc-root:/opt/projects/repos/sce-product-odoo/.env.dev`（`root:ci`, `600`）。
- 备份：`sc-root:/opt/projects/backups/20261003T150227-pre-mainline-identity/.env.dev.pre`
  （旧值 `a90faee8e1cc95a43af111f24d7f959c6cee38f3`，已回读；`diff` 仅第 46 行不同）。
- 写入：`SC_SOURCE_REVISION=64efb6bf61ba1b7364d03c25fe0a2e1ae8849d75`（第 46 行，回读确认）。
- 生效：`make restart`；容器内 `printenv SC_SOURCE_REVISION` 与
  `GET /api/runtime-version` 均回报 `64efb6bf…`。
- 回滚：恢复备份文件并 `make restart`。

## 5. 只读验收探针分段结果

`make verify.daily_dev.acceptance.readonly.probe`（`ACCEPTANCE_TARGET_SHA=64efb6bf…`），
回执 `sc-root:artifacts/backend/daily_dev_acceptance_probe.json`：

- `runtime_identity` PASS：`served_sha == expected_sha == 64efb6bf…`、`served_database=sc_demo`。
- `frontend` PASS：root 200、`/assets/index-DGsa_kfq.js` 200、`intent` GET 405 / OPTIONS 204，
  db/app_env 令牌符合日常期望。
- `login` PASS：`auth_uid=16`（吴涛）、`role_code=business_config_admin`、
  `nav_action_count=89`、`nav_forbidden_label_hits=[]`、`nav_required_path_misses=[]`、
  `system_init_ok=true`。
- `contract` FAIL（未放宽）：`errors=["record_resolution_missing"]`，11 项 required checks
  全部 `not_run`。该段要求受管记录身份解析件，解析器
  `scripts/verify/frontend_delivery_hardening_runtime_ids.py` 依赖 xmlid
  `smart_construction_acceptance_fixture.fe_project_a`，而
  `smart_construction_acceptance_fixture` 在日常库 `sc_demo` 为 `uninstalled`（上一轮已回读）。
  与 `docs/ops/iterations/daily_dev_mainline_deployment_20261003.md` 第 6 节同一根因；
  本次没有关闭该段、改写断言或向日常库注入夹具。
- 探针整体 `status=FAIL` 仅由 `contract` 段导致，未把它当作通过。

## 6. 探针凭据确认（如实记录）

日常探针拒绝已知默认口令，除非调用方提供身份绑定的确认信封。本轮由执行器在远端自建了一次
`daily-readonly-credential-confirmation.v1`（绑定 tool/baseUrl/apiUrl/database/login/
expectedSha/runId，5 分钟过期），仅用于让既有受管探针运行；日常登录口令本身未做任何修改。

## 7. 影响范围

- 仅 `sc-root:/opt/projects/repos/sce-product-odoo`（`ENV=dev`、`.env.dev`、`sc_demo`）、
  其前端静态产物、`smart_core` 模块与该 profile 的容器。
- 未改动：产品语义、数据库 schema（仅模块升级）、其他运行 profile、验收夹具环境、
  Gitee 镜像、生产租户、凭据权威。

## 8. 风险

- P0：非快进或目标身份错误污染日常运行仓 —— bundle sync 在移动 HEAD 前失败关闭，
  且同时绑定新旧 SHA 与祖先关系。
- P1：前端产物与后端代码代际不一致 —— 同一次部署内重建前端并升级模块，
  再用 `/api/runtime-version` 回读校验。
- P2：运行期身份陈旧 —— 见第 4 节，带备份的最小受控写入修正。

## 9. 回滚

- 身份：恢复 `.env.dev.pre` 并 `make restart`（旧值已回读）。
- 代码：日常运行仓是 git 仓库；回退必须另立受控任务，以精确旧 SHA `a90faee8…` 和可验证
  bundle 执行，禁止非快进回退。
- 前端：恢复上一代产物需要对应 commit 的受控重建。

## 10. 四层状态

- 批次验收完成：本轮为 P4 运维部署，不产生产品批次。
- 主线集成完成：本次部署使用的 `64efb6bf…` 已是 `main`/`origin/main`/Gitee 镜像的同一 SHA；
  本记录的元数据经独立 PR 合入 `main`。
- 版本发布完成：否（正式发布仍由 owner hold）。
- 产品交付完成：否。日常开发服务器已刷新到最新主线，owner 可登录验收。

## 11. 遗留

- 日常库 `contract` 段前置：是否让日常库承载隔离验收夹具，待 owner 判断；在此之前该段保持 FAIL。
- 日常运行仓的 `SC_SOURCE_REVISION` 目前没有随 bundle-sync 自动同步的受管入口，本轮仍为受控
  手工写入；建议后续单独授权 P4 变更补齐。
