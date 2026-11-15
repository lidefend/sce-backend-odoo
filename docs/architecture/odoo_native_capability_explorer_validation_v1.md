# Odoo-Native Capability Explorer 源码验证 v1

状态：代码级验证通过

验证基线：`audit/platform-capability-studio-01-20261115@6689f601b`

运行环境：`demo / sc_demo`

日常运行时：`2571346afc8c69cea20e32fcba36082c949cf825`

## 1. 验证目标

证明平台能力浏览器不需要新建一套能力 Registry，可以直接使用：

- Odoo 已安装模块。
- `ir.model`、`ir.model.fields`、`ir.ui.view`。
- `ir.actions.*`、`ir.ui.menu`。
- `ir.model.access`、`ir.rule`、`res.groups`。
- 模块 manifest 依赖。
- 现有 `sc.product.scenario` 与产品发布状态。

本次只验证源码和数据关联，不建设管理页面。

## 2. 验证方法

新增只读探针：

`scripts/verify/odoo_native_capability_explorer_probe.py`

探针复用：

- `RuntimeCapabilityCatalogService`：发现业务根下的原生 Action/Menu 入口。
- `load_published_menu_release_states()`：读取当前入口发布状态。
- `sc.product.scenario.entry`：读取入口所属业务场景。
- Odoo 原生模型：补齐模块、模型、字段、视图、ACL、Record Rule 和依赖。

入口只有在以下技术事实完整时才标记为 `draft_selectable=true`：

- Menu 和 Action XMLID 都存在。
- 所属模块已安装。
- Action 存在且类型受支持。
- Menu 指向同一个 Action。
- Window Action 的模型存在。

`draft_selectable` 只表示可以进入场景草稿选择器，不等于 Preview/Standard 产品资格。

## 3. 实测结果

| 指标 | 结果 |
|---|---:|
| 全部安装模块 | 77 |
| 为业务入口提供能力的模块 | 3 |
| 全部模型 | 758 |
| 被业务入口使用的模型 | 167 |
| 原生业务 Action/Menu 入口 | 282 |
| 稳定 Menu + Action 身份 | 282 |
| 唯一 Action | 282 |
| 关联 View | 776 |
| 模型 ACL 行 | 581 |
| Record Rule | 348 |
| 可进入场景草稿 | 282 |
| 技术阻断入口 | 0 |
| 已绑定业务场景 | 75 |
| 未绑定业务场景 | 207 |

发布与场景交叉结果：

| 入口状态 | 数量 |
|---|---:|
| 已发布且已场景化 | 73 |
| 已发布但未场景化 | 201 |
| 发布状态未知且已场景化 | 2 |
| 发布状态未知且未场景化 | 6 |

这里的“201 个未场景化入口”只是入口发现池，不是 201 项业务能力或 201 个候选产品。

## 4. 数据关联能力

每个入口当前可以自动返回：

- Menu XMLID、名称、完整路径。
- Action XMLID、类型和模型。
- 所属模块、模块版本和依赖模块。
- 模型是否存在、字段数量。
- 模型关联的 View 数量。
- ACL 行数量及授权组 XMLID。
- Record Rule 数量。
- 当前发布状态。
- 所属业务场景及中心。
- 是否可进入场景草稿。

因此，“模块安装后 Odoo 已知道的事实”足以支撑能力浏览器的基础发现、过滤和详情展示。

## 5. 写入与边界

- `new_capability_registry=false`。
- `persisted_rows=0`。
- 探针没有 `sc.capability` 依赖。
- 探针没有创建、更新或删除业务数据。
- 能力事实仍由 Odoo 元数据拥有。
- 场景组织仍由现有业务场景模型拥有。

## 6. 限制

- `draft_selectable` 是原生技术资格，不是产品发布资格。
- ACL 行数量不等于完整授权结果，实际访问仍需 Record Rule、公司范围和操作门禁。
- 本次只验证一个日常租户数据库，不代表所有租户的安装集合相同。
- 尚未验证能力浏览器的信息架构、搜索体验、大数据量分页或前端交互。
- 尚未实现“加入场景草稿”写操作，本阶段只证明候选入口可以被后端可靠选出来。

## 7. 结论

Odoo-Native Capability Discovery 路径成立。

平台能力浏览器可以由 Odoo 原生事实自动生成，并与现有场景服务关联；不需要恢复或扩展 63 项平行能力 Registry。下一步可以进入最小后端只读 API 和领域分组设计，但管理页面与场景草稿写入应作为独立阶段。
