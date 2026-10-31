# 55 · Slots / FieldGroups / ContainerTree Responsibility

## 职责总表

| 层 | 结构 | 权威职责 | 非职责 | 当前证据 |
| --- | --- | --- | --- | --- |
| 页面业务组合 | `formStructureContract.slots` | Identity、业务 Section、区域顺序、字段引用、slot role | 不决定容器/布局拓扑 | 付款申请 RUNTIME，其余 NOT_VERIFIED |
| 字段业务分组 | `dataContract.dataMeta.fieldGroups.groups` | 字段业务分组事实 | 不作为独立布局依据 | 静态消费链存在，运行时影响 NOT_VERIFIED |
| 字段主归属 | `fieldOwnership` | 字段唯一 primary owner（ownerSlotRef / ownerGroupRef） | 不承载 displayRole，不表达辅助投影 | 五个样本均缺失 |
| 布局拓扑 | `layoutContract.containerTree` | 容器层级、布局拓扑、渲染组织 | 不承载业务语义、不决定字段业务归属 | NativeFormTreeRenderer RUNTIME |
| 前端表现 | Vue Renderer + 标准组件 | 组件投影、视觉、交互、响应式映射 | 不决定业务区域/字段归属/布局拓扑 | RUNTIME（消费） |
| 权限（独立） | 服务端 ACL / Record Rules / field groups / 只读 | 最终授权决定权 | 不选择布局、不决定页面结构 | NOT_VERIFIED |

## Slots

- 是业务页面组合结构的权威来源。
- Identity 必须由 `slot:identity` 显式声明，不得由字段名推断。
- Business Section 由 `slot:<section_id>` 声明。
- 承担区域顺序与字段展示投影的声明。
- 不承担容器/布局拓扑：布局属于 containerTree。

## FieldGroups

- 是字段业务分组的权威事实，通过 `ownerGroupRef` 被 fieldOwnership 引用。
- 与 slots 是互补关系：slots 声明区域，groups 声明字段分组，ownership 绑定二者。
- 运行时是否参与最终 Renderer 仍为 NOT_VERIFIED。
- 不允许作为独立布局依据，也不得与 containerTree 形成第二套布局来源。

## FieldOwnership

- 是字段唯一主展示归属的权威来源，每页面作用域每字段仅一条记录。
- `ownerSlotRef` 指向 slots；`ownerGroupRef` 指向 groups（identity 可省略）。
- 合法重复投影（只读摘要、关联引用、明细引用）由 slots 的 fieldRefs 与 role
  表达，不通过第二条 ownership 记录模拟。
- 不重新引入 displayRole。

## ContainerTree

- 是布局拓扑权威来源，是 NativeFormTreeRenderer 的直接输入。
- 不包含业务语义；不得用布局位置反推字段业务归属或产品语义
  （对齐 ARCH-DECISION-003）。
- 是否引用 slots：当前无映射证据，NOT_VERIFIED。应建立显式引用/一致性校验。
- 允许独立于 slots 存在（支撑渲染），但不允许独立决定字段业务归属。
- 需要 Guard 验证容器与业务区域的一致性。

## Frontend Renderer

RENDERER 可以决定：

- 标准组件选择与投影。
- 视觉表现、交互行为。
- 响应式断点折叠、间距、孤儿行填充等 adopter 表现映射。

RENDERER 不可以决定：

- 页面有哪些业务区域。
- 字段属于哪个 slot / group / 主归属。
- Identity 字段集合。
- 布局拓扑的生成（消费 containerTree，不自行拼装）。

多结构来源消费优先级：

- 业务组合：以 slots + fieldOwnership 为唯一事实。
- 布局：以 containerTree 为唯一布局方言（ARCH-DECISION-003）。
- 配置缺失时：正式页面必须 fail-closed（ContractGapError / 显式诊断），不得
  隐式补齐；Legacy Compatible 页面可走显式 fallback 并输出 WARNING。

## 边界禁令

- 禁止前端把字段名、源码存在、变量名或注释当作运行时事实推断结构。
- 禁止用 containerTree 替代 slots 判定 Formal 资格。
- 禁止用 fieldGroups 替代 slots 或 containerTree 的任何一项。
- 禁止把 permissionSemanticsPreserved=true 当作权限证明。
