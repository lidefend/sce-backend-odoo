# 契约流水线不变量与钉法 v1

## 作战思路（一句话）

契约是动态生成的，但生成流水线每一步的「忠实性」是不变量。测试只钉不变量，
不钉动态产物。确认契约正确后，剩下的只是前端忠实表达。

反复来回的根源是把「动态产物」（某个角色/某条记录下最终渲染出来的字段清单、
数据库 ID）当成了「不变量」去钉。产物变了就改钉，于是永远在改。

## 流水线五步，每步钉什么

| 步 | 输入 → 输出 | 不变量（钉这个） | 动态（不钉这个） |
| --- | --- | --- | --- |
| 0 模型 | `ir.model` + `_fields` | 字段名/类型/关系存在于 `_fields` | 无（模型是静态声明） |
| 1 结构 | 原生视图 arch | arch 声明了哪些字段进结构 | 无（arch 是结构权威） |
| 2 组合 | `get_view`/`fields_view_get` | 组合后的 arch 是解析器的唯一输入，含继承视图与 tier 注入字段 | 组合结果随当前用户 groups 变化（角色/权限上下文） |
| 3 解析 | 组合 arch → `arch_parsed`（契约块） | `arch_parsed.layout` 的 field 节点 == 组合 arch 的可见字段（去 `invisible="1"`、去重、保序），解析器不增删 | 具体字段集合随上下文变 |
| 4 组装 | `arch_parsed` → `data.layoutContract.containerTree` | rendered 字段 == `arch_parsed.layout` 的可见字段，组装器不增删 | 最终 rendered 字段集合随上下文变 |
| 5 前端 | `containerTree` → 页面 | 前端忠实渲染 containerTree，不自造 | 具体渲染结果由契约决定 |

## 不变量清单（测试只钉这些）

1. **解析忠实性**：`arch_parsed.layout` 字段序 == 组合 arch 可见字段序（第 3 步不增删）。
2. **组装忠实性**：`containerTree` 字段序 == `arch_parsed.layout` 可见字段序（第 4 步不增删）。
3. **模型一致性**：rendered 字段 ⊆ 模型 `_fields`（第 0 步声明兜底）。
4. **状态一致性**：`statusContract.widgetStatus` 的 widget 与 rendered 字段一一对应。

## 钉法（测试怎么写）

- 钉「第 N 步输出 == 第 N-1 步输出经该步变换后的结果」，即相邻两步之间的忠实性。
- 不钉「某角色/某记录下的最终字段清单」，那是第 4 步的动态产物。
- 不钉数据库 ID（view/action 的 `id`），按 XMLID 动态解析。

具体到 rendered 字段：期望值应该从第 3 步的契约块 `arch_parsed.layout` 推导，
再与第 4 步的 `containerTree` 比较。二者共用同一份「组合 arch + 完整角色/权限上下文」，
所以比较的是「组装是否忠实于契约」，而不是「契约等于一个手写清单」。

## 调用契约生成机制的正确姿势

直接调用 `app.view.config._generate_from_fields_view_get` 必须补齐完整上下文，
否则拿不到正确结论：

- 用请求用户 env（不是 `sudo`）——视图组合按 groups 裁剪继承节点。
- `contract_projection_readonly=True`。
- `contract_view_id` = 显式视图 ID（缺省才走 `requested_view_id` 回退）。
- `view_data` 用 `_safe_get_view_data(model, view_type)` 同源取数。

任何一处用 `sudo` 或换用 `get_view`，都会丢掉角色/权限上下文，导致推导结果与
组装器实际渲染不一致。
