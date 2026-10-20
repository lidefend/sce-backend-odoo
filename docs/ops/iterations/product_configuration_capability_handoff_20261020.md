# 产品配置能力长任务交接（2026-10-20）

## 0. 身份

- Worktree：`/home/lidefend/workspace/sce-backend-odoo`
- Branch：`feature/product-configuration-capability-20261020`
- Base：`82dbd9134288576ede315370179858c5ba70ce87`（`main`）
- Batch 1 commit：`f7a53c73ad87f0c7ca505a842f581cbe97b62854`
- Batch 2 commit：`f3ab67348`
- 交接时 HEAD：本次 handoff commit（Batch 2 commit 为 `f3ab67348`，见 `git log -1`）
- 主线集成：`not_run`
- 部署：`not_run`

## 1. 已完成

### Batch 1：能力模型与 guard

- `config/product_configuration_capability_v1.json`
  - 4 类账号：业务全功能、业务配置管理员、平台管理员、支持/运维
  - 6 个登录首屏区块
  - 8 张配置卡
  - 6 类系统参数
  - 25 项能力
- `docs/product/product_configuration_capability_v1.md`
- `scripts/verify/product_configuration_capability_guard.py`
- `scripts/verify/test_product_configuration_capability_guard.py`
- `make verify.product_configuration.capability`

### Batch 2：后端能力目录契约

- `addons/smart_construction_core/services/product_configuration_capability.py`
  - `resolve_audiences(user)`
  - `build_catalog(manifest, audiences)`
- `addons/smart_construction_core/handlers/product_configuration_capability.py`
  - intent `product.configuration.capability.catalog`
- `addons/smart_construction_core/data/product_configuration_capability_v1.json`
  - runtime copy，guard 校验与产品 manifest 字节一致
- `addons/smart_construction_core/tests/test_product_configuration_capability_service.py`

验证：

```bash
make verify.product_configuration.capability
```

结果：15 tests PASS；guard PASS audiences=4 cards=8 categories=6 capabilities=25。

## 2. 未完成

| 批次 | 目标 | 状态 |
|---|---|---|
| Batch 3 | 配置工作台与登录首屏消费后端能力目录 | 未开始 |
| Batch 4 | 系统参数目录、影响预览、变更集发布/回滚 | 未开始 |
| Batch 5 | 登录首屏 6 区块与“我的能力”页面 | 未开始 |
| Batch 6 | 业务全功能账号真实浏览器验收 | 未开始 |

## 3. 下一执行器入口

从 Batch 3 开始，不要重做 Batch 1/2。

优先消费点：

- `frontend/apps/web/src/app/businessConfigBoundaries.ts`
  - 增加 `product.configuration.capability.catalog` intent 常量。
- `frontend/apps/web/src/api/businessConfig.ts`
  - 增加能力目录响应类型和加载函数。
- `frontend/apps/web/src/views/businessConfigSurface/useBusinessConfigWorkbenchBootstrap.ts`
  或 `useBusinessConfigWorkbenchMeta.ts`
  - 加载能力目录，保留后端 `available/reason/status`。
- `frontend/apps/web/src/views/businessConfigSurface/BusinessConfigStartPanel.vue`
  - 按 8 张卡渲染，显示 available/partial/planned 与不可用原因。
- `frontend/apps/web/src/views/HomeView.vue`
- `frontend/apps/web/src/components/role-home/WorkspaceHome.vue`
- `frontend/apps/web/src/composables/shared-surface/useWorkspaceHome.ts`
- `frontend/apps/web/src/stores/session.ts` 的 `WorkspaceHomeContract`
  - 消费 6 个登录首屏区块和“我的能力”。

Batch 3 验收：

- 业务全功能账号看到 6 个首屏区块；
- 业务配置管理员看到 8 张配置卡；
- planned 能力不可点击并显示原因；
- 平台/支持能力不出现在业务全功能视图；
- 前端不按菜单数量、角色名或模型前缀推导能力。

## 4. 基线风险

- 本产品分支从 `main` 建立，尚未包含 demo 分支上的两项基线修复：
  - 93 条文档缺链：demo commit `636719109`
  - 7 条 `.agent` 台账问题：demo commit `a44238ad8`
- 因此本分支直接跑 `verify.docs.all` / `verify.agent.ledger.unit` 可能仍命中这些既有缺陷。
- 不要重做；独立执行器可按需 cherry-pick 两个基线 commit，或在批次记录登记排除项。
- 不要把 demo 分支的 demo 计划提交混入产品分支。

## 5. 硬边界

- 总体目标达成前不合并 main。
- 不暴露原始 `ir.config_parameter`、密钥或部署身份。
- 配置写入必须走变更集、影响预览、审计和回滚。
- 平台管理员能力不得下放给业务全功能账号。
- 不继续在 demo 数据层补产品配置能力。

## 6. 回滚

回退 `f7a53c73a` 与 `f3ab67348` 两个 commit；不涉及数据库、服务或部署恢复。
