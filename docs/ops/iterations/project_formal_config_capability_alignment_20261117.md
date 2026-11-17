# 项目台账正式配置与契约能力对齐（2026-11-17）

## 目标与边界

- Formal Product Layer: P1 建筑行业标准产品。
- Layer Target: 项目台账正式 Form/Overview 视图数据；项目正向 presentation 目标。
- Module: `smart_construction_core`。
- Standard vs User-Specific: 行业标准正式页面声明。
- Why Here: 当前正式页面仍声明 `sc_insight_banner`、`sc_stage_requirements`、`sc_next_actions`，而当前已验证交付契约不包含这些内嵌部件组件。
- Why Not Elsewhere: 不回滚 daily 候选，不增加 capability、Renderer、Widget 实现、逐模型前端特判或运行时数据库特例。
- Blast Radius: 项目台账 Form/Overview 的三个内嵌增强节点及其正向验收目标；字段、权限、阶段计数、阶段要求和项目动作必须保留。

## 当前故障

- 日常运行候选：`a19bf2d976cbda9d99bdc24deab7903143a21cb7`。
- `project.project:15` 返回 HTTP 409，错误为 `COMPONENT_CAPABILITY_REQUIRED`。
- 最终契约包含当前客户端未支持的内嵌部件组件 `sc.insight.summary`、`sc.action.list`。
- 这不是记录版本冲突；也不得把预期 `ContractGap` 计为项目页面可用。

## 处理方式

正式项目视图数据不再提供这三个内嵌部件：

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
| 正式视图声明撤出 | 已完成 | 三个未支持内嵌节点已从 P1 XML 撤出 |
| 正向验收目标修正 | 已完成 | `project-form` 不再允许预期 ContractGap |
| 定向静态验证 | 已通过 | 产品视图结构 26 项；presentation/capability 81 项；增量映射 168 项；Agent 台账 18 项 |
| 候选发布到日常环境 | 未执行 | 保留 `a19bf2d9` 为代码基线 |
| 项目台账真实流程 | 未执行 | 发布后验证 |

## 配置数据升级边界

本轮修改的是 `smart_construction_core` 的 Odoo View 声明，必须通过模块升级写入
`ir.ui.view`，不能只同步代码或执行临时 SQL。日常发布将显式使用：

```text
DAILY_RUNTIME_PUBLISHED_FACE_UPGRADE_MODULES=smart_core,smart_construction_core
```

现有发布面收敛入口会调用受管 duty upgrade；该入口在写入前创建并校验 duty 自身的恢复点。
升级完成后，以实际 V2 契约和项目页面结果为验收依据。

## 下一步

提交基于 `a19bf2d9` 的干净候选，运行精确 HEAD 的受管增量检查与模块升级，然后完成项目列表、详情、编辑回读和返回验证。
