# FEPC-14R：只读路径评估与推荐方案

结论：**推荐方案 A，复用既有只读业务方法，补齐有界的调用和展示适配；不申请扩大 ACL。**
这不是“已经有可直接替换的 Vue 接口”：已找到业务读取方法和 Odoo 消费者，未找到现成的 Vue 阶段要求查询/展示闭环。
本轮是决策稿，不授权实现，不宣称修复完成。

## 基线与证据等级

- `source_fact`：GitHub main、本地 main、origin/main、HEAD 均为 `1e06bcfde151d7669c29825d88c05bf3cd61b455`。
- `current_runtime_fact`：2026-10-28 16:49:47 UTC，GET runtime-version 返回同一源码 SHA、构建 `03045d0ed5c1359b2e2318be631ac6281bf818c39f272f69bfd62d92ac84c208`、`sc_demo/demo`。原始证据 `.runtime/fepc-14/readonly-assessment-runtime.json`。未重新查询数据库 UUID。
- `historical_runtime_fact`：[matched-entry-evidence.json](matched-entry-evidence.json) 记录项目 13 / `DEMO-PJ-STAGE-DONE`、action 588、menu 382 的真实点击403。本轮没有重放按钮、登录或业务 API。
- 工作区仍在 `audit/data-01-demo-facts`，已有本地审阅稿保留。只更新本目录决策文档和现有 FEPC-14 任务索引。
- 本轮 P4 证据整理；未来业务读取归 P1 `smart_construction_core`，通用错误分类消费归 P0 前端。两者独立验证，不把行业判断放入公共渲染器。

## 已有能力及不足

| 能力 | 源码事实 | 可复用性与限制 |
| --- | --- | --- |
| 项目只读方法 | `models/core/project_core.py:1427`，`sc_get_stage_requirements(limit=3)` | ensure_one、项目 read ACL 和 record rule；从实际项目 lifecycle_state 查询 active 要求，按 sequence/id 排序；默认仅3条，完整查看须明确传 limit=0，不能把前三条冒充全量 |
| 完成度判断 | 同文件 `_sc_is_requirement_done` / `_compute_stage_progress` | 现有判断应复用，不能在前端按字段名重新计算；无 target_field 时返回 true 属既有语义，本轮不改 |
| 已有消费者 | `static/src/js/stage_requirements/stage_requirements_widget.js:68` | Odoo ORM RPC 调用上述方法；不是 Vue intent 客户端。其组件空列表无显式文案，不能直接当作目标合法空态已满足 |
| 临时向导 | `models/support/project_stage_requirements.py:42` | 保存项目/阶段快照、要求项明细；没有发现对查看结果必须提交/确认的业务状态；行 action_go 使用项目上下文转到办理入口 |
| 现有配置页 | `views/support/project_stage_requirement_item_views.xml` | 面向业务配置管理员的 tree/form，含 active、target_field 等配置字段；不能把该管理员 action 当作普通项目阅读入口 |
| 通用交付 | `handlers/execute_button.py`、`core/navigation_entry_target.py:263`、`api.data`、`ui.contract.v2` | 具有动作导航、列表读取和契约交付机制；不能据此推断动态过滤列表已保留项目身份、权限上下文和“去完成”语义 |

本表中相对后端路径均在 `addons/smart_construction_core/`，通用交付路径在 `addons/smart_core/`。
搜索范围为现有 smart_core handlers、行业 handlers/services、Vue src 与对应原生组件；未发现专用 Vue 阶段要求查询 handler，结论限定于此范围。

## 临时创建是否必要

`source_fact`：按钮方法在 `project_core.py:1721` 执行 create 后返回 act_window；向导 default_get 查询要求项并构造行记录。
`inference`：就“查看当前阶段要求”而言，项目身份、阶段、要求及完成度均可由现有只读方法产生，未发现必须持久化临时记录的业务依据。不能据此宣称所有向导设计错误。

`unknown`：当前 create 仅显式传 project_id/lifecycle_state，default_get 依赖默认值或 context 的 default_project_id，未证明能收到调用者 vals 中的 project_id。放开 create 后是否有明细仍未验证；本轮不创建向导做试验。

两套输出还有差异：只读方法含 done，并在 action_xmlid 为空时返回项目管理 action；向导行只保存显式 action_xmlid，无 done。不能把 helper 中的回退导航直接暴露成获准的“去完成”。

## 唯一推荐：A，保留权限的只读适配

建议下一实施授权限定为：

1. 复用 `sc_get_stage_requirements(limit=0)`，不复制查询、完成度或阶段规则。薄查询适配归 P1；通过现有 intent 注册和传输机制暴露，不启用任意方法 RPC，不新增协议版本。
2. 请求只带项目身份/正常公司上下文；服务端读取真实阶段，校验项目及要求项读取权限与记录规则。客户端不能选择任意阶段，也不能把动态 domain 当作授权。
3. 服务端返回已授权项目身份、阶段及完整要求集合。只有读取成功且集合为空才能声明合法空态；403/404/异常继续失败。继承既有字段访问限制，不能 sudo。
4. Vue 使用现有契约驱动展示与状态组件接入只读区域；字段/标签/空态由 P1 声明。按钮采用范围由其现有契约动作身份确定，禁止按中文标题、项目 ID 或模型特判触发。
5. 保留原生 Odoo 向导调用方，避免顺手删除兼容入口。本批仅查看，不把 helper 的 action_ref 自动变成可执行链接；若产品要求保留“去完成”，须明确复用现有动作授权并单列导航回归。

**尚需实施验证的边界**：查询到展示的具体适配点、既有展示组件能否完整承载该只读集合尚未经过候选测试；不声称零前端改动。优先复用已有展示载体，若实际需要新通用 schema/渲染机制，停止并回报，不升级成另一轮协议工程。

不推荐把按钮直接重定向到“阶段要求配置”管理页，也不推荐仅返回一个按阶段过滤的配置列表而丢失项目上下文。B 向导授权仅作后备，目前没有证明 A 不足，不进入 B 审批。

## 错误语义最小修复建议

`source_fact`：`frontend/apps/web/src/api/client.ts:22` 的 ApiError 已保存 status、reasonCode、traceId。
`useRecordActionPresentation.ts:183` 和 `useFormActionRuntime.ts` 的动作 catch 只传 errorMessage；
`runtimeStateProtocol.ts` 的 status 事件未携带分类信息。`ContractFormPage.vue:67` 却从 loadError 读取分类，最终匹配 unknown。
相邻 `useRecordPageLifecycle.ts:462` 已有 ApiError → loadError 映射，可复用其字段规则，不复制加载失败时的强制路由跳转。

建议在既有动作错误入口统一传递 status/reason/trace，并在新动作/成功/切换记录时清除旧错误分类，保留异步 owner 防陈旧结果覆盖机制。
继续消费 `error_state_contract.py` 的 permission/business/unknown 分类，不在组件硬编码项目文案，不将服务端英文内部模型信息当作普通用户提示。
诊断 trace 仅按既有 HUD/支持边界显示，不输出认证信息。未知异常不能沿用上一次403。

此错误呈现修复可独立回归，但不能替代查看入口恢复。当前仅提出方案，未改代码。
