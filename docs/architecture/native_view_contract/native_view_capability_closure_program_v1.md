# 原生视图契约能力闭环专题 v1

[English](native_view_capability_closure_program_v1.en.md)

## 1. 目标

本专题把“原生视图可以解析”提升为“正式产品原生能力可以被契约和通用前端完整承载”。

唯一产品结果：正式产品中的每一个原生视图能力，都必须能够追溯到规范化契约和渲染结果；不能承载的能力必须失败关闭，并返回稳定原因码。

## 2. 产品边界

- Formal Product Layer：P0 平台内核产品。
- Supporting Layer：P4 契约导出、证据和门禁工具。
- Layer Target：`smart_core` 原生视图契约链、通用前端 renderer registry、产品级契约门禁。
- 不进入 P1：不修改施工行业模型、业务状态、字段含义或默认流程。
- 不进入 P2/P3：不承载客户偏好或管理员运行时配置结果。
- 不由前端补语义：前端不得根据 model、menu、XML ID、角色、标签或 route 推断业务含义。

## 3. 评价单位

专题不再以“页面能否打开”作为能力覆盖证明。最小评价单位为能力原子：

```text
native capability atom
-> normalized contract atom
-> semantic contract atom
-> renderer capability
-> interaction capability
-> verification evidence
```

能力原子至少包含：

- 结构：header、sheet、group、notebook、page、relation、chatter。
- 字段：顺序、标签、widget、domain、context、options。
- 修饰符：readonly、required、invisible、column_invisible。
- 动作：object、action、row、batch、toolbar、stat button。
- 集合：tree、search、kanban、pivot、graph、activity。
- 权限：visible、editable、executable、reason_code。

## 4. 分批路线

| 批次 | 单一目标 | 退出条件 |
| --- | --- | --- |
| Q0 | 建立专题分支、目标和边界 | 最新主线、独立 worktree、目标和回滚边界冻结 |
| Q1 | 建立正式产品能力损耗账本 | 每个正式视图面和能力原子都有终态，零静默丢失 |
| Q2 | 收口修饰符、动作和权限 | 修饰符可求值，动作可裁决，所有拒绝都有原因码 |
| Q3 | 收口 form/tree/search/kanban | 主路径不依赖模型或页面特判，结构和交互证据齐全 |
| Q4 | 收口 pivot/graph/activity | 复杂视图从 readable fallback 逐项进入正式 renderer |
| Q5 | 建立 widget registry 和发布门禁 | 所有 widget 明确 ready/fallback/unsupported，退化阻断发布 |

## 5. Q1 损耗账本

每条记录必须包含：

```json
{
  "contract_ref": "menu.xmlid::view_type",
  "capability_key": "modifier.readonly",
  "native_count": 1,
  "normalized_status": "ready",
  "semantic_status": "ready",
  "renderer_status": "ready",
  "interaction_status": "ready",
  "reason_code": "",
  "evidence_refs": []
}
```

允许的终态只有：

- `ready`：已完整承载并有验证证据。
- `fallback`：有明确可读降级、稳定原因码和退出计划。
- `unsupported`：失败关闭，不得伪装为可用。

禁止 `unknown`、缺省状态和无原因码降级。

## 6. 治理与环境

- 只复用 `local.clean`：project `sc-local-clean`，database `sc_clean`，dbfilter `^sc_clean$`。
- 禁止创建新的 Compose、数据库、端口、卷、凭据、fixture 或 runtime profile。
- 共享数据库写入、模块升级和正式运行态验收必须串行。
- 每个批次必须绑定完整 tracked、staged 和 untracked 指纹。
- 任何测试零收集均按失败处理。
- 代码、契约、门禁和前端行为必须分别给出结论。

## 7. 完成标准

- 正式菜单策略覆盖完全且无重复冲突。
- 所有原生能力原子都有终态。
- 静默能力损失为零。
- 所有 fallback/unsupported 都有稳定原因码。
- `native_view` 与 `semantic_page` 形成唯一规范运行时结构。
- 前端 renderer 只按正式契约语义选择组件。
- clean install、定向测试、契约漂移和用户旅程证据全部绑定同一候选指纹。
