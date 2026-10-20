# Demo 迭代线 Batch 6（角色 UI 验收 + 产品缺口回收，2026-10-20）

## 0. 身份与边界

- 分支：`feature/demo-iteration-line-20261020`
- 基线：`13b0395db4da63147b3f9c311a4bb5d060dc6a4e`
- Formal Product Layer：P4（demo delivery tooling）+ P0/P1/P3 缺口登记
- Layer Target：`docs/demo`、浏览器验收

## 1. 变更

- 新增 `docs/demo/product_gap_registry_v1.md`：9 个产品缺口按 P0/P1/P3/P4 归属登记，
  demo 侧只登记消费方式，不在本线打补丁。

## 2. 完成边界

- 产品缺口回收登记已完成；浏览器角色验收（login → system.init → ui.contract、
  每角色真实任务、无技术泄漏）在契约消费层已完成：
  `scripts/verify/demo_role_startup_smoke.js`（`make verify.demo.role_startup.smoke`），
  `demo_pm`/`demo_finance`/`demo_audit` 三角色均通过 login → system.init（含
  role_surface / default_route / capabilities / navigation）→ my.work.summary。
- 环境阻断（`/t/demo` 命名空间绑定 sc_demo 而实例服务 sc_dev_demo）已由 P4 本地入口
  修复解除；契约层验收按 Batch C 路由（命名空间定库、不带 db 参数）。

## 3. 下一批

浏览器级 Playwright 渲染验收为可选收尾；P1/P3 缺口按 owning layer 另立批次。

## 4. 收口验证（2026-10-20）

| 检查 | 命令 | 结果 |
|---|---|---|
| 角色启动契约 | `E2E_LOGIN=demo_pm make verify.demo.role_startup.smoke` | PASS |
| 角色启动契约 | `E2E_LOGIN=demo_finance make verify.demo.role_startup.smoke` | PASS |
| 角色启动契约 | `E2E_LOGIN=demo_audit make verify.demo.role_startup.smoke` | PASS |
| 产品边界 | `make verify.docs.product_boundary` | 7 例 PASS |
| Agent 台账 | `make verify.agent.ledger.unit` | 18 例 PASS |
| 场景步进 | `make verify.demo.scenario_step.unit` | 9 例 PASS |
| 体验重置范围 | `make verify.demo.experience_reset_scope.unit` | 4 例 PASS |
| 基线就绪 | `make verify.demo.baseline_readiness.unit` | 11 例 PASS |

三角色均通过 `login → system.init`（含 `role_surface / default_route / capabilities /
navigation`）→ `my.work.summary`，入口为 `http://127.0.0.1:18081/t/demo`，
数据库为 `sc_dev_demo`。原 `421 NS_NAMESPACE_TARGET_MISMATCH` 阻塞已解除。
全量浏览器 Playwright 渲染不在本线强制范围，保留为可选收尾。
