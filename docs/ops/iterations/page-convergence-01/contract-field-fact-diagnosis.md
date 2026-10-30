# PAGE-CONVERGENCE-01 · 概览计数字段缺失事实对照（独立诊断）

结论：三个概览计数字段缺失是契约组装阶段的条件子树裁剪问题，与业务计算、原生视图
声明、字段权限无关。配置层不能生成这些业务事实；是否修复应作为独立契约基础设施议题。

## 1. 业务计算来源（正常）

| 字段 | 定义 | 计算 |
| --- | --- | --- |
| `sc_overview_cost_count` | 概览成本条数 | `project_core.py::_compute_overview_counts` |
| `sc_overview_payment_pending_count` | 概览待审批付款数 | 同上 |
| `sc_overview_task_in_progress_count` | 概览进行中任务数 | 同上 |
| `sc_overview_contract_count` | 概览合同份数 | 同上 |

pm1 通过 JSON-RPC 读取本地记录 id=21 返回值真实存在：`sc_overview_contract_count=4`、
`sc_overview_cost_count=6`、`sc_overview_payment_pending_count=0`、
`sc_overview_task_in_progress_count=0`。计算口径无异常。

## 2. 原生视图声明（正常）

`addons/smart_construction_core/views/core/project_overview_views.xml` 中四卡均声明了对应
`<field name="sc_overview_*_count" readonly="1" nolabel="1"/>`。

## 3. 交付契约（异常）

pm1 真实契约 JSON 中四个 `sc_overview_*_count` 节点数均为 0，既不在 `containerTree`，
也不在 `widgetStatus` 或字段集合。仅 `sc_project_contract_entry_available` 已进入 `mainData`
（值 false，经上一轮有界 fact 水合修复）。

## 4. 裁剪原因（已定位，未修改）

- 解析阶段：`div` 按普通容器递归解析，无 opaque HTML 特判。
- 组装阶段：计数字段位于 `<div invisible="sc_overview_* == 0 / != 0">` 条件子树内；
  组装器在服务端无法求值这些计算字段条件时，将整棵条件子树/字段从交付契约裁掉。
- 结果：字段没有进入契约，后续任何 hydration 都无从谈起。

## 5. 边界结论

- 这是通用契约组装缺陷，不是页面配置问题，也不是业务计算问题。
- 修复应独立提交：条件子树字段在服务端无法求值时，应保留为隐藏 fact 字段进入契约并
  由前端按运行时值求值，而不是裁剪；且不得用该策略改变服务端权限判断。
- 在独立修复落地前，页面应保持“数值不可用”的准确状态，不伪造 0/false。
