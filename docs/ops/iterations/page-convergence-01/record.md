# PAGE-CONVERGENCE-01 · 批次记录

状态：active（批次进行中；主线/部署/用户验收均未发生）

## 阶段身份

- 分支：`feature/page-convergence-01`
- 基线：`1640a7e1b19349be6490f6055c26955b4a468853`
- 本轮工作树：分析文档 + 受管 `.agent` 运行元数据；产品代码尚未修改。

## 已完成

- TASK-01 真实基线核对：远程日常服务器身份、页面身份、4 视口截图与 DOM 证据。
- 契约缺口与「合同」卡片缺失的定位；TASK-06 根因定位。
- 目标设计与实施计划定稿（本目录）。

## 未完成 / 下一步

1. ~~修 `dependency.lifecycle_state` 契约缺口~~（已完成代码修复，待运行时验证）。
2. 概览四卡统一（含合同卡片空态）。
3. 基本信息/计划责任六组拆分。
4. 页头层级与操作分组。
5. TASK-06 只读化。
6. local.dev 定向验证 + 远程浏览器验收 + 独立 PR。

## 证据

- 运行身份：`docs/ops/iterations/page-convergence-01/baseline.json`
- 截图：`.runtime/page-convergence-01/baseline/screenshots/`

## TASK-05.1 已实施

- 根因：`hydrate_final_modifier_dependencies` 批量 `record.read(missing)` 中，
  `sc_stage_required_done/total` 计算链触及 pm1 无权限的 `project.funding.baseline`，抛
  AccessError 被整体吞掉，导致 `lifecycle_state` 等所有可读依赖字段一起缺失。
- 修复：改为逐字段读取并单独容错；单个被拒字段 fail-closed，其余可读依赖字段继续水合。
- 载体：`addons/smart_core/core/unified_page_contract_v2_modifier_dependencies.py`
  （P0/P1 通用契约水合层，不写死页面语义）。
- 回归测试：`addons/smart_core/tests/test_ui_contract_v2_boundaries.py`
  `PYTHONDONTWRITEBYTECODE=1 python3 .../test_ui_contract_v2_boundaries.py` → 159 tests OK。
- 待运行时验证：local.dev 升级 smart_core + 候选前端，确认阶段状态与合同卡片恢复。

## TASK-05.1 运行时验证（通过）

- 候选前端 127.0.0.1:5176 绑定提交 `397a3b4da`；本地后端已加载修复。
- 探针（pm1，project 21）结果：`status=200`、`tokenKey=true`、`hasLifecycle=true`、
  `lifecycleValue=in_progress`；`mainData` 从 0 个关键依赖字段恢复，`start_date`、
  `manager_id`、`user_id`、`project_type_id` 均已水合。
- 遗留（进入 TASK-05.2 处理）：`owner_id`（仅存在于概览身份头块，不在标准布局水合闭包）、
  `sc_overview_contract_count`、`sc_project_contract_entry_available` 对 pm1 仍缺失，
  需在四卡收敛时按其权限与空态一并处理。

## 职责边界纠偏（2026-10-30）

- 保留：TASK-05.1、`f334f112` 合同卡片权限隔离、`79fd6010e` 隐藏 fact 字段有界水合。
- 暂停：通用条件子树保留策略与组装器修改。
- 独立诊断：`docs/ops/iterations/page-convergence-01/contract-field-fact-diagnosis.md`。
- 恢复配置驱动收敛：四卡视觉、六组基本信息、计划责任、责任协作、四视口；配置不生成业务事实。
