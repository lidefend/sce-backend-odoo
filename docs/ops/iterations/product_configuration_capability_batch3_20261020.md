# 产品配置能力 · Batch 3 执行记录（2026-10-20）

## 0. 身份

- Worktree：`/home/lidefend/workspace/sce-backend-odoo`
- Branch：`feature/product-configuration-capability-20261020`
- Base（main）：`82dbd9134288576ede315370179858c5ba70ce87`
- 批次起点 HEAD：`2ba0ccfa801aefdffc2aac93fa08d10336247eaf`（交接提交）
- 阶段身份：HEAD + 显式 dirty 范围（日常开发，未冻结）

## 1. 决策边界

- Formal Product Layer：P1（能力模型声明已由 Batch 2 落在 `smart_construction_core`）+ P0 前端契约消费。
- Layer Target：`frontend/apps/web`（渲染器）消费 `product.configuration.capability.catalog`。
- Module：frontend / docs(contract ledger) / make / .agent。
- 目标（唯一）：前端消费后端能力目录，登录首屏与配置工作台不再自行推导能力。
- 范围：intent 常量、api 层、fail-closed 投影助手、session store、useWorkspaceHome/WorkspaceHome、
  BusinessConfigStartPanel/BusinessConfigSurfaceView（状态文案 dispatch 由 productCapabilityCatalogProjection 提供，
  不修改 useBusinessConfigWorkbenchMeta）、行为测试、make 目标、
  契约台账绑定、本批次记录与 run 台账。
- 不做：不改后端契约；不动启动链；不做 6 区块完整业务数据渲染（Batch 5）；不做系统参数目录/变更集（Batch 4）；
  不 cherry-pick demo 分支基线修复 `636719109` / `a44238ad8`（登记排除，见 §6）；不合并 main。

## 2. 实施步骤

1. `businessConfigBoundaries.ts`：新增 `PRODUCT_CAPABILITY_INTENTS.catalog`。
2. `api/productCapabilityCatalog.ts`（新）：镜像后端 `build_catalog` 投影的类型 + `fetchProductCapabilityCatalog()`。
3. `app/productCapabilityCatalogProjection.ts`（新）：fail-closed 投影
   `projectLoginHomeBlocks` / `projectConfigurationCards` / `projectCapabilities`；声明面存在但非法即
   `ContractGapError` 停机，空集合是合法投影；仅对声明枚举做展示文案 dispatch。
4. `stores/session.ts`：新增 `productCapabilityCatalog` 状态与 `loadProductCapabilityCatalog(force)`，
   并在 hydrate/clearSession/bootstrap 三处显式重置。
5. `useWorkspaceHome.ts` / `WorkspaceHome.vue`：加载能力目录，渲染登录首屏 6 区块（planned 显示原因且不可点击）。
6. `BusinessConfigSurfaceView.vue` / `BusinessConfigStartPanel.vue` / `useBusinessConfigWorkbenchMeta.ts`：
   渲染配置工作台 8 张能力卡（available/partial/planned + 原因）。
7. 行为测试 `scripts/product_capability_catalog_test.ts` + make 目标
   `verify.frontend.product_capability_catalog.unit` + 契约台账 `declarationBindings` 登记。

## 3. 验证结果（分层）

| 层 | 命令 | 状态 | 测试数 | 备注 |
|---|---|---|---|---|
| L1 | `make verify.frontend.contract_basis.unit` | passed | 15（python） | bindings=12（新增 1 条能力目录绑定） |
| L2 | `frontend/apps/web/scripts/product_capability_catalog_test.ts`（node 类型剥离直跑） | passed | 18 | 合法投影透传 / 非法声明停机 / 空集合合法 / 不按角色重过滤 |
| L2 | `make verify.product_configuration.capability` | reusable | 15 | Batch 2 已通过，声明输入未变，复用 |
| L1 | `make ci.local.iteration` | reconcile→已登记 scope | - | 首次因新文件不在 run scope 触发 reconcile，登记后重跑 |

环境修复（2026-10-20）：本机 `frontend/apps/web/node_modules` 与 `frontend/packages/ui/node_modules`
原先指向已消失的 `/tmp/sce-fix-daily-demo-env-20261019/...`。已将 21 条悬空链接重连到主仓
`frontend/node_modules/.pnpm`（同一 `pnpm-lock.yaml`），包括 `esbuild`、`typescript`、`vue-tsc`、
`vite`、`vue` 和 `@sc/ui`。

复验：

- `esbuild 0.21.5`、`tsc/vue-tsc 5.9.3`、`vite 5.4.21` 可执行；
- `scripts/dev/pnpm_exec.sh -C frontend/apps/web typecheck:strict` PASS；
- `scripts/dev/pnpm_exec.sh -C frontend/apps/web build` PASS；
- `make verify.frontend.product_capability_catalog.unit` PASS（18 cases，走原 esbuild 路径）；
- `make verify.frontend.contract_basis.unit` PASS（15 tests，bindings=12）。

node_modules 为本地环境目录，不进入 Git；远端 PR 仍需按原车道复验类型检查与构建。

## 4. 行为验收（Batch 3）

- 业务全功能账号首屏 6 区块：由 `catalog.login_home.blocks` 投影（非硬编码），planned 的
  `workspace.capability_map` 区块 `available=false`，显示「未发布」原因且不渲染可点击动作。
- 业务配置管理员 8 张配置卡：由 `catalog.configuration_cards` 投影，保留 available/partial/planned。
- 平台/支持能力不泄漏：后端投影已按受众过滤，前端 `projectCapabilities` 不做二次过滤，测试锁定透传。
- 前端不按菜单数量/角色名/模型前缀推导能力：全部消费 `capability.catalog`，测试覆盖「不按 audience 重过滤」。

## 5. 风险与回滚

- 风险：session store 持久化不含 `productCapabilityCatalog`（按需重取，避免跨登录 stale）；若远端类型检查报错，
  仅涉及前端文件，回滚本批次 diff 即可。
- 回滚：`git revert` Batch 3 提交；不涉及数据库/服务/部署。

## 6. 排除项

- demo 分支两项基线修复 `636719109`（93 条文档缺链）、`a44238ad8`（7 条 .agent 台账问题）未合入本产品分支；
  本批次不重做、不 cherry-pick；如后续交付车道命中对应 `verify.docs.all` / `verify.agent.ledger.unit`，
  按既有基线缺陷登记排除，由 demo 分支另行收口。

## 7. 下一步

- 重跑 `make ci.local.iteration` 确认 L1 收口；
- 提交 Batch 3（分层提交：前端消费 + 台账）；
- 进入 Batch 4：系统参数目录、影响预览、变更集发布/回滚。
