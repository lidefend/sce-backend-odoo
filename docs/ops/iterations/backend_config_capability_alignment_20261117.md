# 后端正式配置与契约能力全量对齐（2026-11-17）

## 目标与边界

- Formal Product Layer: P0 契约消费机制；保护 P1 正式页面可用性。
- Layer Target: 后端全部正式 XML 视图中的内嵌 Widget 声明；项目正向 presentation 目标。
- Module: 全后端 XML 扫描；机制变更位于 `smart_core`，项目数据变更位于 `smart_construction_core`。
- Standard vs User-Specific: 平台/行业/客户正式页面声明均纳入扫描。
- Why Here: 当前正式页面仍声明 `sc_insight_banner`、`sc_stage_requirements`、`sc_next_actions`，而当前已验证交付契约不包含这些内嵌部件组件。
- Why Not Elsewhere: 不回滚 daily 候选，不增加 Renderer、Widget 实现、逐模型前端特判或运行时数据库特例；能力协商使用既有请求字段和最终契约边界。
- Blast Radius: 项目台账 Form/Overview 的三个内嵌增强节点及其正向验收目标；字段、权限、阶段计数、阶段要求和项目动作必须保留。

## 全量排查结果

对 `addons/` 与 `customer_addons/` 共 314 个 XML 文件执行 `<widget ...>` 声明清单。
撤出前只有以下三个不支持的正式声明：

| 文件 | Widget | 处理 |
| --- | --- | --- |
| `project_views.xml` | `sc_insight_banner` | 撤出 |
| `project_overview_views.xml` | `sc_stage_requirements` | 撤出 |
| `project_overview_views.xml` | `sc_next_actions` | 撤出 |

撤出后全后端 XML 已不存在未登记的嵌入式 Widget 声明。后续由全后端结构锁阻止重新引入。

### 继承与运行时配置兜底

仅删除本地 XML 不能证明最终合并视图不会因为其他继承层或运行时配置再次出现节点。
当前客户端继续通过既有 `client_contract_capabilities` 声明已实现组件；后端
`validate_component_capabilities()` 在最终交付前对可选节点的能力进行逐请求投影：

- `sc.insight.summary` 需要 `form.insight.summary.v1`；
- `sc.action.list` 需要 `form.action.list.v1`。

当前客户端未声明这两个能力时，后端从本次响应的容器树和状态表中移除对应节点；
字段、权限、动作、普通容器和其他已声明节点保持原样。将来客户端声明 capability 后，
相同节点继续完整交付并接受既有 payload 校验。这样继承与运行时配置都不会把项目页
变成 HTTP 409 或全页 `ContractGap`。

运行态浏览器进一步发现 Odoo 基础视图 `project.edit_project` 继承字段
`is_favorite`/`boolean_favorite` 与 `name`/`text`。它们不是嵌入节点，也不应删除
基础视图，而是字段自身的 Widget 属性。语义 registry 现将其登记为 `ready`，并按
字段类型使用已有 `sc.input.boolean` 与 `sc.input.text` 组件，同时对 `boolean`
字段类型增加通用派生规则。未知字段 Widget 仍保持 fail-closed。

字段项目进一步发现，one2many 明细的列过滤会在页面首次渲染时早于
`dataMeta.sourceContext` 绑定执行。字段 Context 本身合法时，前端现以该字段
Context 建立首帧求值帧，等正式 store 就绪后继续使用完整 source context；非法
Context 类型仍然拒绝。这样继承明细条件不会把整页变成加载失败。

## 当前故障

- 日常运行候选：`a19bf2d976cbda9d99bdc24deab7903143a21cb7`。
- `project.project:15` 返回 HTTP 409，错误为 `COMPONENT_CAPABILITY_REQUIRED`。
- 最终契约包含当前客户端未支持的内嵌部件组件 `sc.insight.summary`、`sc.action.list`。
- 这不是记录版本冲突；也不得把预期 `ContractGap` 计为项目页面可用。

## 处理方式

正式后端视图数据不再提供这三个内嵌部件：

- 从项目 Form 撤下 `sc_insight_banner`；
- 从项目 Overview 撤下 `sc_stage_requirements`；
- 从项目 Overview 撤下 `sc_next_actions`。

保留已有受支持职责：

- `lifecycle_state`、审批状态、阶段完成数和阶段说明；
- “查看阶段要求”“去补齐资料”“提交立项”“启动项目”等受权限控制的动作；
- 项目概览中的合同、成本、财务、任务卡片及其受支持动作；
- 项目资料维护区、权限、后端校验和记录规则。

同时移除 `project-form` 正例中的 `expectedContractGap`。合成 unsupported 负例仍由独立负例覆盖，不能计入本页面正向验收。

## 结果索引

| 项目 | 状态 | 说明 |
| --- | --- | --- |
| 全后端正式视图扫描 | 已完成 | 314 个 XML；未支持声明仅上述三处 |
| 正式视图声明撤出 | 已完成 | 三个未支持内嵌节点已撤出，当前全后端 XML 无此类声明 |
| 正向验收目标修正 | 已完成 | `project-form` 不再允许预期 ContractGap |
| 全后端静态验证 | 已通过 | 314 个 XML 产品视图结构 26 项 |
| 继承能力兜底 | 已通过 | 能力投影 18 项；节点验证 266 项 |
| 字段 Widget 属性对齐 | 已通过 | `boolean_favorite`、`text` → 通用布尔/文本控件；8 项 provenance、116 项语义 registry |
| one2many 首帧 Context | 已通过 | 55 项明细 hydration/Context 用例；非法 Context 仍 fail-closed |
| presentation 目标 | 已通过 | 81 项 |
| 增量与台账 | 已通过 | 增量映射 168 项；Agent 台账 18 项；续跑入口 58 项 |
| 候选 `af9a096b` 发布 | 已通过 | 恢复点、模块升级、构建和发布面均 PASS；契约回读 HTTP 200 |
| 候选 `9c3540ce` 发布 | 已通过 | 字段 Widget 修正已上线；契约无 unsupported field widget |
| 首帧 Context 修正候选 | 待发布 | 修复 one2many 首帧求值 |
| 项目台账真实流程 | 待完成 | 等待首帧 Context 修正上线后验证 |

## 配置数据升级边界

本轮修改的是 `smart_construction_core` 的 Odoo View 声明，必须通过模块升级写入
`ir.ui.view`，不能只同步代码或执行临时 SQL。日常发布将显式使用：

```text
DAILY_RUNTIME_PUBLISHED_FACE_UPGRADE_MODULES=smart_core,smart_construction_core
```

现有发布面收敛入口会调用受管 duty upgrade；该入口在写入前创建并校验 duty 自身的恢复点。
升级完成后，以实际 V2 契约和项目页面结果为验收依据。

## 下一步

提交基于 `a19bf2d9` 的干净候选；日常发布显式升级 `smart_core,smart_construction_core`，随后完成全后端继承链回读、项目列表、详情、编辑回读和返回验证。
