# Contract Runtime 状态归属边界 v1

- 阶段：FE-CONTRACT-RUNTIME-01-E
- 定位：冻结"什么状态由谁定"的归属，**不建状态机 DSL**、不新增运行时能力
- 上位权威：[`contract_authority_hierarchy_v1.md`](architecture/contract_authority_hierarchy_v1.md)
  已确定的权威链；本文只补充"状态与动作"这一层的归属细则

## 决策

运行时有四类"状态/可用性"，它们的事实源不同，**不得互为回退真相**：

| 内容 | 唯一事实源 | 运行时载体 | 消费方 |
| --- | --- | --- | --- |
| 业务状态与状态可用的业务动作 | Odoo ORM 记录字段 + P1 行业档案 `sc.workflow.contract.service`（`state_field` / `state_phase` / `state_actions` / `method_by_action`） | `workflowContract`（由 `smart_construction_core/core_extension.py` 注入，`describe_record(record)` 按记录现算） | 前端按契约给出的动作集渲染与派发 |
| 记录数据事实 | 记录/列表/关联 payload（`unified_page_contract_v2_data.py`，其 `SOURCE_AUTHORITIES` 只有 payload 与 data-source schema） | `dataContract` | 字段值渲染 |
| UI 展示状态（可见 / 禁用 / 原因码） | `permission_surface` / `access_policy` / `field_modifiers` / `button_status`（`unified_page_contract_v2_status.py`） | `statusContract`（`globalStatus` / `widgetStatus` / `containerStatus` / `buttonStatus`） | 可见性与禁用态渲染 |
| 按钮可用性与动作规则 | `ui_action_contract` / `button_contract` / `action_rule_schema`（`unified_page_contract_v2_action.py`），最终结论落在 `statusContract.buttonStatus` | `actionContract` + `statusContract.buttonStatus` | 动作区渲染与派发 |
| 权限与策略判定 | 后端 group、access rule、record rule；Scene/action 绑定校验（`handlers/ui_contract_v2.py::_validate_scene_action_binding`） | `statusContract.globalStatus` 的 `pageVisible` / `pageAuth` / `reasonCode`（如 `REASON_ACTION_GROUP_ACCESS_DENIED`、`REASON_SCENE_ACTION_BINDING_INVALID`） | 前端只显示结论 |
| 字段语义（用什么组件渲染） | 模型元数据 + 视图 arch 的治理解析产物，经 `contracts/registry/semantic.yaml` 推导 | `domain_field_semantics_generated.py` -> `semantic -> componentKey` | 组件选择 |

### 归属判定依据

- `statusContract`、`actionContract`、`dataContract` 的生产模块都自带
  `NO_BUSINESS_FACT_AUTHORITY = True`：它们是**投影**，不持有业务事实。把业务规则
  写进这三者，等于让投影变成第二个事实源。
- `workflowContract` 不是声明表：它由记录现算（`describe_record(record)`），
  所以业务状态永远以 ORM 记录为准，行业模块只提供"状态->动作"的档案。
- `contracts/domain/*.yaml` 的 `states` / `transitions` 是**领域声明**（对账与
  生成用），运行时业务状态仍取自记录字段值，避免"声明状态"与"记录状态"两套。

## 禁止事项

- 前端不得用 `state`/`status` 字符串自行判断按钮显隐、流程分支或权限；缺声明时
  按契约缺陷处理（向上要契约），不得本地兜底。
- 前端不得用用户组名复现授权判定；`statusContract.buttonStatus` 是唯一结论。
- 除 `semantic.yaml` 推导链外，任何模块不得新增第二份"语义 -> 组件键"映射。
- 投影层（status/action/data/runtime）不得承载业务事实。

## 验证入口（本归属的机器可读约束）

- `make verify.contract.authority_hierarchy.guard`
- `make verify.frontend.auth_surface.guard`
- `make verify.semantic.registry.lint`

## 已知边界（不在本轮完成）

- 尚未建状态机 DSL：`state_actions` 目前是"状态 -> 动作名"的档案，转移的合法性
  仍由 ORM 方法自身守卫；把它编译成 DSL 属于 FE-CONTRACT-RUNTIME-02。
- `contracts/domain/` 15 份域契约中只有 `payment-request.yaml` 绑定
  `source_of_truth.model`；未绑定即不被投影，属可见的未投影而非静默猜测。
