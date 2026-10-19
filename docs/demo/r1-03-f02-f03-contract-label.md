# Demo R1 F02/F03 契约标签最小修复批次记录

## 目标

项目看板状态、项目台账卡片「经营方式/状态」按真实中文契约显示。状态代码保持不变，仅标签消费声明。

## 缺陷证据（反例）

1. `addons/smart_construction_core/services/project_state_explain_service.py`
   `LIFECYCLE_STATE_LABELS` 是私有英文 key→中文映射，与声明
   `ScStateMachine.PROJECT_STATES`（`models/support/state_machine.py`）不一致：

   | code | 声明 | 私有映射 |
   | --- | --- | --- |
   | draft | 草稿 | 筹备中 |
   | paused | 停工 | 暂停 |
   | done | 竣工 | 完工 |
   | closing | 结算中 | 收口 |
   | warranty | 保修期 | 质保 |

2. `frontend/apps/web/src/pages/KanbanPage.vue` `semanticCell` 对非状态字段调用
   `semanticValueByField`，不消费 `props.fieldSelections`；P0 投影
   `unified_page_contract_v2_assembler._field_widget` 已把 selection 写入
   `componentConfig.selection`，因此「经营方式」显示英文 key `direct`/`joint`
   而非「公司直营/联营项目」。

## 修复

- `project_state_explain_service.py`：`lifecycle_state_label` 改为从记录
  `_fields["lifecycle_state"]._description_selection(record.env)` 消费声明；`ProjectStateExplainService.build`
  与 `project_context_contract.build_project_context` 改传记录而非裸字符串。
- `frontend/apps/web/src/app/presentation/collectionStatusPresentation.ts`：
  新增纯函数 `resolveSelectionLabel`，`resolveCollectionStatusPresentation` 复用它。
- `frontend/apps/web/src/pages/KanbanPage.vue`：`semanticCell` 对非状态字段优先
  消费已声明 `fieldSelections`。

## 验证

- 后端：`python3 addons/smart_construction_core/tests/test_project_semantic_carriers.py`（离线，反例断言）。
- 前端：`frontend/apps/web/scripts/collection_kanban_selection_label_test.ts`（esbuild+node，反例断言）。
- `make verify.frontend.collection_kanban_record_card.unit`（卡片结构门禁）。
- `make ci.local.iteration`（L1 静态，dirty）。
- `git diff --check`。

运行态 L3 与浏览器回读不落库、不部署、不伪造；需真实服务器复现的项如实 pending。

## 总调度接管修复

原执行器已停止。本轮P1标签使用Odoo正式翻译接口，异常不回退原始声明，空标签报错；卡片状态/普通selection共享resolveCollectionCell。ActionView经collectColumnSelections保留空数组，未知非空值/空标签显式ContractGap；合法空值与普通非selection字段保留原行为。状态代码不改，无模型特判或新增中文映射。

6项后端测试、25条前端实际消费断言、11项卡片门禁已通过。新增断言覆盖上游空selection传递、状态绕过、翻译env身份/异常、空标签、合法false空值及普通字段。最终typecheck/L1与独立复核见run；尚未提交/集成/部署/浏览器验收，Demo种子原始dirty保留。

最终严格类型检查PASS、L1 iteration PASS、diff检查PASS；独立代码复核通过（复跑25条前端断言）。当前仅F02/F03本地代码修复完成，日常服务器页面验收与部署仍pending。
