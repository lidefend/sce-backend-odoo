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

## 日常候选部署与真实页面回读（2026-10-19）

候选 `8a4767b8ab25a4ff71085f6a25b91385a05d352e` 已经受管 bundle sync、frontend build、platform_control/demo refresh 部署；entry.verify 全部通过。旧源码与前端恢复材料保留，未执行 seed、模块升级或用户模块服务刷新，未主线合并。

页面验收未通过：已发布项目台账卡片状态显示“草稿”，经营方式仍为 `direct`；实际 kanban 契约字段描述出现字典字符串化且缺少选择项载体。项目看板观察到加载后失败，错误响应待定向取证，不认定为本候选引入。当前账号为既有验收声明的 fixture_role_config_admin / FE Company A，不能据此声称业务全能角色完成验收。

原始契约、DOM 文本、截图与部署结果：`.runtime/final-acceptance/daily-deployed/label-20261019/`。下一步回到 P0 kanban 投影及看板错误响应诊断，仅重验受影响页面。

## 根因续修

P0 / smart_core / 通用契约装配：kanban.fields 的对象被 _text 转成字典字符串；另一个事实来源 list_profile.columns 的字段描述未投影，故消费方取不到 selection。按字段身份解析对象，并把已发布列对应的已授权源描述投影，缺描述拒绝；不新增行业映射，不读 registry 绕过权限。装配缓存版本与输入摘要同步更新。

通用前端 renderer：groupCollectionRecords 泳道标题原本直接 stringify 原始分组值，绕开卡片标签消费；现由 KanbanPage 注入相同 semanticCell 格式化，组身份保持原值。

复查修正：看板等待真实请求完成后加载成功，未复现此前快速切页后的失败；能够确认的是原泳道 draft 英文。不把瞬态观察写成已确认后端故障。

本轮局部验证：130 compact（含真实装配入口投影断言）、27 label 断言、36 collection tests、11 card、15 basis、strict typecheck、assembler guard、ci.local.iteration 均通过。缓存版本变更是必要依赖，旧契约证据不可复用；未变 seed/生命周期测试复用。L3 模块升级跳过：无模型/schema/XML/安装依赖改动；L4 仅定向两个项目入口；L5 主线发布不在本次部署结论内。

日常更新恢复点：`.runtime/final-acceptance/daily-deployed/label-root-20261019-before`（服务器），旧候选 8a4767b8，前端归档摘要 2e633ab4f3a094cf59c03bc913fbb99499699b0c8402ed2573f8a79670989e43。

### 157bf676 实际回读后的顺序缺口

新候选看板正常且泳道为“草稿”；两页面 kanban widget 已具有有效字段身份和 lifecycle_state / operation_strategy selection。但卡片消费以描述发现顺序作为展示顺序，使经营方式被原有显示数量截断，中文虽已传到前端却未展示，验收判 FAIL。补充通用消费修复：现有字段身份按已发布 listProfile.columns 顺序排列，追加未列入的原生字段；不制造缺失 widget，不改变业务选择项。新增 normalized store 两个反例覆盖顺序及无描述字段不得加入，36 tests 与 typecheck PASS。旧后台投影测试输入未变，复用130 tests及缓存守卫。
