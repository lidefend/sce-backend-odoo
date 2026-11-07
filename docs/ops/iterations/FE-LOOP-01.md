# FE-LOOP-01 前端增量质量反馈闭环

## 身份与边界

- 基线：`3e5b9f144cf6b3e7c29a695b2e8db3eed09a01ec`
- 分支：`codex/fe-loop-01-quality-closure`
- Formal Product Layer：P4
- Layer Target：前端增量验证规划、执行、运行登记
- Module：前端质量反馈闭环

本批只修交付工具链，不修改前端产品行为、Renderer 架构、金额表达、业务契约或冻结基线。
不创建候选构建、浏览器验收、发布、PR 或合并结果。

## 第一阶段：只读审计

现状审计结论：

| 变更类型 | 当前计划结果 | 缺口 |
| --- | --- | --- |
| 未命中专项规则的 Vue/TS | `verify.frontend.typecheck.strict` | 缺少 `verify.frontend.lint.src` |
| 命中专项规则的 Vue/TS | 仅专项 Make 目标 | 专项规则覆盖基础 lint/typecheck |
| Renderer 注册表及测试 | 未命中规则，回退 typecheck | 缺少 Registry 单测 |
| `ci.local.iteration` | `frontend_dev_incremental.py --plan-worktree` | 只规划、不执行 |
| run.json 检查登记 | 目标存在、输入路径存在 | 不校验当前差异推导出的必需目标是否已登记 |
| 规划器 `--path` | 可真实调用 Make 目标 | 未接入内循环，且回执不逐目标区分状态 |

## 第二阶段：增量规则

已实现：

- `frontend/apps/web/src` 与 `frontend/packages/ui/src` 下的 `.ts/.tsx/.vue` 始终追加
  `verify.frontend.lint.src` 和 `verify.frontend.typecheck.strict`。
- 专项规则只追加目标，基础 lint/typecheck 不再被专项规则覆盖。
- Renderer 注册表、生成 carrier、行业扩展入口、Registry 测试和守卫统一路由到
  `verify.frontend.professional_component_registry.unit` 与 `verify.semantic.registry.lint`。
- FormSection 路由到字段映射、契约 V2 occurrence、Primitive、页面模式、样式和基础检查。
- 规划器自身、`agent_run_context.py`、执行策略守卫均有独立路由。
- 每个推荐目标都必须能在 Make 面中找到可执行 recipe，或经由非空依赖链到达可执行 recipe。

`verify.frontend.contract_v2_occurrence_authority.unit` 原登记为“无门禁消费”的零引用面；
本次成为 FormSection 行为锁后，通过审计器的 reasoned unregister 移除过期分类，没有放宽基线。

## 第三阶段：执行闭环

已实现：

- `make verify.frontend.dev.incremental.plan`：只读规划，`testsRun=false`。
- `make verify.frontend.dev.incremental.execute`：执行当前 run 的完整必需目标集。
- `make ci.local.iteration` 直接调用真实执行入口，不再只打印建议。
- 每个目标独立执行，记录目标、命令、状态、退出码、耗时、原始日志与日志 SHA-256。
- 状态区分 `passed`、`failed`、`blocked`、`not_run`、`interrupted`；未执行目标另列在
  `notRunTargets`。
- 已知前端工具链缺失在执行前进入 `BLOCKED`，不会伪装成产品失败或验证通过。
- `run.json` 缺少当前差异推导出的目标时，执行器在执行任何目标前 fail-closed。
- 无相关 L2 时只输出 `NOT_RUN`，`verificationPassed=false`。

## 第四阶段：场景验证

- 单 TS：`frontend/apps/web/src/main.ts` → lint + strict typecheck，2 个目标 PASS。
- 单 Vue：`FormSection.vue` → 8 个基础/专项目标 PASS。
- Renderer 注册表及测试 → 4 个基础/专项目标 PASS；Registry 测试 137 例，守卫 147 例。
- 前后端混合 → workflow contract + lint + strict typecheck，3 个目标 PASS。
- 调度器与守卫自身 → run context 56 例、执行策略 19 例、规划器 56 例、
  verification-lane coverage 73 例，全部 PASS。
- 缺少前端依赖时先产生 `BLOCKED` 回执，执行目标数为 0；用
  `make fe.install.cached` 恢复后，相同单 TS 场景 2 个目标 PASS。最初的依赖错误原始
  `FAILED` 日志保留，未覆盖或改写。
- 完整 `make ci.local.iteration` PASS，增量执行器实际执行 4 个目标，未执行目标为 0。

## 第五阶段：交付复核

本地候选已完成定向测试、Ledger/diff/范围复核并形成本地提交。未有推送、PR、合并、部署、
浏览器验收或候选构建。

## 后续治理

- `FE-RENDERER-02`：绑定 `rendererVersion` 与契约版本；只在出现真实运行时消费方后建立
  capabilities 声明和验证。当前空 `requiredCapabilities` 不作为能力治理已交付的证据。
- `FE-EXPR-02`：继续收敛金额、日期、状态、空值、关系、权限、校验、操作和行业组件表达。
