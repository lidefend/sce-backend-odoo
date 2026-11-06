# 列表新建契约（list create entry）批次记录

- 候选：`codex/list-create-entry-contract-20261106`
- 产品 SHA：`e76d150c30099bb4082717d6cdab6c714b327d12`
- 基线：`5b842bdde0d483413bde708b32aa3523992c6e77`（PR #826 后主线）

## 目标

列表“新建”由布尔能力改为带 target 与当前用户授权的 `action.list.create` 契约动作。
普通列表默认 `record_create` 直建当前入口标准创建表单；项目台账 590 委托到标准项目立项
（`action_project_initiation` / `menu_sc_project_initiation`）。

## 变更范围

- P0：`unified_page_contract_v2_assembler.py` 投影 `action.list.create`；`ui_contract_v2.py`
  生产者解析目标并对委托目标做模型 ACL × action groups × published route 授权。
- P1：`project_list_actions.xml` 在台账 590 context 声明 `sc_create_entry_action_xmlid`。
- 前端：`ActionView.vue` 以同一契约动作决定显隐与去向。
- P4：`frontend_list_surface_structure_browser.mjs` 改读 `action.list.create.target`。

## 验证

- L1：`verify.unified_page_contract.v2.runtime`（137 条装配器测试，含新增默认/委托断言）。
- L1：前端 `vue-tsc --noEmit` 0 错误。
- L2：CI 回执链路本地单测（`test_backend_changed_test_coverage`、
  `test_backend_test_receipt`、`test_backend_suite_plan`）149 条通过，含同模块一次 ORM +
  两个 Python 文件按 `(module, kind, execution)` 去重、`__main__` 身份拒绝、非对象路由
  context 拒绝等新增回归。
- L2：`run_mixed_python_tests.py` 单文件独立进程跑
  `test_ui_contract_v2_boundaries.py`（163）与
  `test_unified_page_contract_v2_mobile_compact.py`（137），身份为
  `<filename>.Class.method`，与核验器一致。

## 本轮（CI 回执链路 + 两个产品边界，2026-11-06）

- 同模块（smart_core）一次 ORM + 两个 Python 文件的端到端回执链路：执行改为
  `run_mixed_python_tests.py` 单文件独立进程；`backend_test_receipt.py` 的
  `record`/`archive-attempt` 增加 `--execution` 命名空间；`backend_suite_plan.py` 的
  `verify_execution_coverage` 按 `(module, kind, execution)` 去重，`scope-plan.json`
  改为沿祖先定位。断言 162/137（本轮边界文件新增一例后为 163/137）两组方法可逐项核验。
- 产品边界：`_merge_route_default_context` 对 `[]`/`1` 等非对象路由字面量返回原
  context 而非 `.items()` 抛错；`ActionView.vue` 的委托 target 要求 `action_id` 与
  `menu_id` 同时存在才显隐/导航。

## 状态

- 批次：L1/L2 通过；L3 四场景浏览器与 L4 冻结、完整发布门禁仍待实测（真实账号回执）。
- 远端 `professional_quality_gate` 在旧 HEAD `7330ecbd3` 因回执撞名/汇总路径/身份三段失败；
  本轮修复待推送后由同一候选远端复跑。
