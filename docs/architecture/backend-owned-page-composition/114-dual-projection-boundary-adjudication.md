# 114 · BNVA-019 Stage 3 前置 · 双投影边界裁定

> 状态：已被 `115-single-canonical-native-view-model.md` 取代。职责分离原则
> 保留，但实现从「两套解析管线」调整为「统一内部模型 + 多适配器」。

> 目标：在动手统一 arch 解析之前，先冻结「业务结构投影」与「渲染布局投影」两条
> 投影链的职责边界。本轮只读裁定，不改产品代码。

## 1. 现状：两条合法投影，不是一次简单去重

同一个合并 arch 被两条链路各自消费：

| 投影 | 代码入口 | 产物 | 契约去向 |
| --- | --- | --- | --- |
| Native Canonical Projection (NCP) | `core/native_view_projection.project_native_view` → `build_native_form_structure_contract` | `NativeView`（containers / fields / modifiers_raw / field_metadata） | `formStructureContract`（slots / fieldRoles / fieldOwnership） |
| Layout DOM Projection (LDP) | `view_Parser.contract_Parser.OdooViewParser.parse_odoo_view` | `parsed_structure` + tree/form/kanban/... blocks（columns / widget / toolbar / search） | `layoutContract.containerTree` |

调用链：

- NCP：`ui_contract_v2.py:2631` 与 `:4022` → 只产出 `formStructureContract`。
- LDP：`app_view_config.py:383`、`native_parse_service.py:56` → 产出布局 DOM，再由
  assembler 归一为 `containerTree`。

关键事实：两者都调用 `get_view()` 获取权限裁剪后的合并 arch，都执行
`etree.fromstring`。但产出是**两个不同契约**，不能合并成单一投影。

## 2. 职责边界

### NCP 拥有（业务结构事实）

- 原生容器身份与层级（group name / notebook / page / sheet）。
- 字段 occurrence（同一字段多次出现不丢失）。
- 字段到命名业务容器的归属（fieldOwnership）。
- 业务语义声明（identity / section）——只接受显式配置，不推断。
- 原始 modifiers（`modifiers_raw`，不求值）。

### LDP 拥有（渲染布局事实）

- tree/form/kanban/pivot/graph/calendar/gantt/activity/search 的布局 DOM。
- 列顺序 / 列宽 / widget 语义 / 聚合 / 分组。
- toolbar / header button / search 合并。
- 布局级 modifiers 的原始表达式 + 静态字面量解析（best-effort）。

### 两者共同拥有（L0 事实，各取所需）

- 合并 arch（`get_view()` 权限裁剪结果）。
- 字段描述符（`fields_get()` 字段类型 / label / relation）。
- 原始 modifiers 表达式。

## 3. 裁定

### 3.1 保持两条投影，不合并

NCP 回答「字段业务上属于哪个区域」，LDP 回答「字段渲染上怎么摆放」。这是
ARCH-DECISION-004 的延续：业务组合权威与布局拓扑权威分离。

### 3.2 共享 L0 解析结果，不重复 fromstring

同一请求内，`get_view()` 只取一次，合并 arch 只 `etree.fromstring` 一次，
解析出的 root 同时喂给 NCP 与 LDP。当前 `contract_Parser` 已把 root 贯穿传给
各子解析器；NCP 仍独立 `etree.fromstring`，需要收敛为「接收已解析 root 或共享
同一解析产物」。

### 3.3 不允许跨投影推导

- LDP 不得推导 fieldOwnership / businessRole / identity。
- NCP 不得推导 columns / widget / toolbar / search 语义。
- 两端 modifiers 都保留 raw；静态解析只是辅助，不由任何一端当作运行时权威。

### 3.4 字段生命周期分类只由 NCP 决定

ViewField / BusinessField / HydrationField / TechnicalDependency / RelationField
是业务结构视角的分类，归 NCP（见 109 文档）。LDP 只消费其结果，不重新分类。

## 4. 可测试边界断言

1. 同一请求内 `get_view()` 调用次数为 1（NCP 与 LDP 共享同一合并 arch）。
2. NCP 的 `NativeView.containers/fields` 与 LDP 的 `parsed_structure` 来自同一
   root，结构身份一致。
3. LDP 输出不含 fieldOwnership；NCP 输出不含 columns/widget 渲染配置。
4. 同一字段在两端都保留 occurrence，不因共享 root 而丢 occurrence。

## 5. Stage 3 实施边界（据此收敛）

1. 给 `project_native_view` 增加「可接收已解析 root」的入口（可选参数），
   避免同一请求二次 `etree.fromstring`；默认仍自解析以保持单测独立。
2. `ui_contract_v2` 把 LDP 已解析的 root（若同请求可用）传给 NCP，或反之。
3. 不把 `view_Parser` 的 tree/form/kanban 解析器迁移进 `native_view_projection`；
   不把 NCP 的结构投影塞进 `view_Parser`。
4. 两端共享一个「arch 解析缓存」只在同请求内生效，不跨请求缓存权限裁剪结果。

## 6. 明确不做什么

- 不新增平行公开 Schema。
- 不把 `containerTree` 与 `formStructureContract` 合并成一个结构。
- 不用 sudo 补齐权限裁剪结果。
- 不为了「只解析一次」而让 LDP 重新承担业务结构推导。

