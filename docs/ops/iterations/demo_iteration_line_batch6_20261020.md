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
