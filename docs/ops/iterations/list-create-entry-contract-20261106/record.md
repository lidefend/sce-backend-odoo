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
- L3（candidate 环境）：四场景浏览器全通过。台账正例最终表单
  `action_id=795/menu_id=379/profile=create`；普通列表正例 `action_id=800/menu_id=426/profile=create`。

## 状态

- 批次：L2/L3 通过；L4 冻结与完整发布门禁未跑。
