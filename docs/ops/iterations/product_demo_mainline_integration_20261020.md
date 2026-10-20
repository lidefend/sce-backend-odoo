# 产品线与 demo 机制线主线集成记录（2026-10-20）

## 0. 身份

- Worktree：`/home/lidefend/workspace/sce-backend-odoo`
- 分支：`release/product-demo-integration-20261020`
- 基线：`82dbd9134288576ede315370179858c5ba70ce87`（main）
- 产品线：`feature/product-configuration-capability-20261020`，产品提交 `c8133c735`
- demo 线：`feature/demo-iteration-line-20261020`，收口提交 `bd614470a`
- 集成分支当前 HEAD：`ad552468b`

## 1. 合并顺序

1. 从 main 创建 release 分支。
2. `merge(product)`：合入产品配置能力线，无冲突。
3. `merge(demo)`：合入 demo 机制线，10 个重叠冲突：
   - `active-runs.json`：取主线后补入 demo 三条登记；
   - `make/dev_test.mk`：同时保留产品入口身份/写租约目标与 demo 场景目标；
   - 其余 8 个台账/文档/脚本冲突：main 侧为更新版本（`363eead1a`/PR #702），取 main 侧；
4. 再把 demo 最新台账收口提交并入，保证 demo 祖先关系完整。

合并结果：`ad552468b`，工作树干净。

## 2. 验证结果

| 检查 | 命令 | 结果 |
|---|---|---|
| 台账 | `make verify.agent.ledger.unit` | 18 例 PASS |
| 产品边界 | `make verify.docs.product_boundary` | 7 例 PASS |
| 产品能力 | `make verify.product_configuration.capability` | 16 例 PASS |
| 参数目录 | `make verify.product_system_parameter_catalog` | 17 例 PASS |
| 真实对象 ORM | `make verify.product.home_objects.contract` | 2 例 PASS |
| 能力目录前端 | `make verify.frontend.product_capability_catalog.unit` | 18 例 PASS |
| 契约消费 | `make verify.frontend.contract_basis.unit` | 15 例 PASS |
| 契约守卫 | `make verify.frontend.contract_basis.enforce` | bindings=13 open_defects=0 |
| 前端增量 | `make verify.frontend.dev.incremental.unit` | 32 例 PASS |
| 参数目录前端 | `make verify.frontend.product_system_parameter.unit` | 20 例 PASS |
| demo 场景步进 | `make verify.demo.scenario_step.unit` | 9 例 PASS |
| demo 重置范围 | `make verify.demo.experience_reset_scope.unit` | 4 例 PASS |
| demo 基线就绪 | `make verify.demo.baseline_readiness.unit` | 11 例 PASS |
| 类型检查 | `scripts/dev/pnpm_exec.sh -C frontend/apps/web typecheck` | PASS |
| 入口身份 | `make local.dev.entry_identity.verify` | PASS `demo -> ns_000000000002 -> sc_dev_demo` |
| demo 三角色 | `make verify.demo.role_startup.smoke` × 3 | demo_pm / demo_finance / demo_audit PASS |
| 产品浏览器 | `make verify.frontend.product_configuration_capability.browser` | 31 断言 PASS |

## 3. 并发写入处置

另一个执行器报告的 4 个“未提交前端文件”实际已经在产品线 `c8133c735` 中提交，
两个工作树当时都是干净的。没有提交任何未归属文件，也没有覆盖其他执行器的在途工作。

## 4. 未执行

- main 正式合并：未执行，需走受保护 PR / 所有者 CI 车道。
- 推送远端：未执行。
- 部署：`not_run`。
- 用户交付验收：`not_run`。

## 5. 回滚

回退 release 分支到 `82dbd913` 即可撤销整个集成候选；main 未变，无数据库或部署恢复。
