# 94 · Session Closeout Status

## 状态总览

Backend-Owned Page Composition 的结构侧已闭环，迁移与证据侧待独立批次。

## 已完成

- fieldOwnership 生产者：`build_form_structure_contract` 从 field_roles 派生，
  33 条唯一主归属，590/1776 assembler 判 formal。
- 原生组身份保留：`_normalize_native_layout_nodes` 从 attributes.name 读 group，
  11 个 sc_project_information_* 组进入 containerId。
- 权限边界：原生 group 是权限载体，groups 属性只在 _runtime_filter 投影；
  fieldOwnership 不读取权限。
- role 降级为业务语义：identity 由 group:identity 表达，不承载权限。
- Guard 对齐运行时约定：PC-001/002/003/004/006 PASS。

## 测试

- 3 项生产者单测、62 项 view_orchestrator、53 项 Guard/evidence 全绿。
- Odoo determinism 多次 PASS。

## 文件

后端 P0/P1：unified_page_contract_v2_assembler.py、form_structure_authority.py、
view_orchestrator.py、ui_contract_v2.py、ui_contract_v2_form_structure.py、
view_orchestration_form_section_contract_data.xml。

Guard/证据：page_composition_integrity_guard.py、evidence contract/collector、
测试文件。

文档：01～93（含 87/88/89/90 设计、91/92/93 收口）。

## 待办（独立批次）

1. Phase 5-01 前端 shadow 收缩：`useNativeFormTree` 渲染门控，渲染与诊断分离。
2. Phase 4 证据闭环：PC-005/008/009/010/011 证据采集。
3. 79 个 overlap 字段清单（从 View 1776 正式入口枚举）。

## 工作树

全部未提交改动保留，未清理、未 reset、未迁移、未删 Legacy fallback。
