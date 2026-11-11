# 场景层职责与两类发布

所有者于 2026-11-05 明确：**原生发布能力，场景组合产品。两个发布必须分别判断、分别留证。**

本批基于 `ee79dda079873c90cbe2f00d6fb4461a9856fee0`，只收口 P1 场景启用诊断，保留现有模型、发布载体、V2 和公共 Runtime。结果索引：`.agent/runs/SCENE-DIAGNOSIS-BOUNDARY-20261105/run.json`。

## 职责

业务模型实现计算、约束、事务、状态转换和审计；事实配置选择已有能力的规则；场景层组合能力、组织办理步骤与工作台、声明依赖和调用关系。契约层投影这些生效声明；前端负责公共呈现与交互。

`sc.product.scenario / entry` 是业务分类与入口归属，不等于组合产品的 `sc.scene / tile / version`。企业启用是一家公司对已具备资格能力的选择，也不是发布。

### 问题定位硬规则

任何场景入口、页面或导航问题先做一次二分判定：

1. **事实不足**：所需入口、route、menu/action、model/view、ACL/group 或产品发布身份在事实层不存在或互相矛盾。此时回对应事实所有者层修复，场景层不得补声明。
2. **事实完整、编排不足**：事实已存在且唯一，但未被场景、目录、分组或最终导航正确组合。此时只在场景编排层修 composition。

场景层不得新产生 `route`、`menu_xmlid`、`action_xmlid`、`model`、`visibility`、`permission` 或 `group` 事实。它只能引用事实层稳定身份，并声明 layout、zone、provider、相关场景和调用顺序。

### Route 不属于事实层

原生 `ir.ui.menu / ir.actions / ir.ui.view / res.groups / ACL` 决定“有哪些入口、谁能使用、
入口承载什么动作”，但不决定前端 URL。场景编排通过稳定身份引用这些既有入口，并且不复制
菜单、动作、模型、权限或场景页实现。

最终导航投影从已经场景化的节点派生 URL：

- 场景节点：`/s/{scene_key}`。
- 普通原生动作节点：`/a/{action_id}?menu_id={menu_id}`。
- 目录节点：`/m/{menu_id}`。

`sc_web_route`、场景数据中的硬编码 route 和产品入口源中的 route 字段都不是合法维护载体。
`system.init` 只返回同一棵最终场景化 `navigation.nav` 及其同源 `route_authority`，不再从
action context、场景注册或另一份路由表读取第二套 URL。

场景化前的正式产品发布选择只回答“候选入口是否具备发布资格”，不能直接称为最终 P1
产品策略或用户可见面。最终 P1 产品策略必须从场景化后的 `navigation.nav` 反向投影；
其中的 menu/action/scene/route 身份、入口计数和前端实际收到的导航必须同源。角色可达
入口数量与产品发布总数也是不同维度，不能用发布总数反推后端能力或用户可见结果。

有明确原生事实投影或原生直达 handoff 声明、且无生效编排内容的入口，无须另建或发布重复的 `sc.scene`。不能仅凭存在 action 判断纯原生。原生入口绑定与资格正确即可通过产品依赖诊断，但访问时仍须经过有效发布策略、企业启用、用户权限和作用域检查。声明专用 intent、区块、数据源、角色组合或后续步骤的入口不能仅因附带兼容 action 就被降格为纯原生页面。诊断复用现有场景加载器及 provider 声明，明确组合内容优先；缺少正向原生证据时保守要求组合发布。

## 发布层次

| 层次 | 回答的问题 | 当前证据 | 不代表什么 |
| --- | --- | --- | --- |
| 原生能力发布 | 某项能力是否取得交付资格 | 当前入口的标准版资格及原生菜单/action 事实 | 已完成场景编排、已有组合产品版本、某用户可以操作 |
| 场景组合产品发布 | 一组能力是否形成已发布的组合产品版本 | `sc.scene` 的生效版本、版本归属、`product_release_state`、`product_edition` | 可以绕过原生能力资格、企业启用或底层权限 |
| 编排快照发布 | 是否生成并选择了一份编排快照 | `sc.scene.state` 与 `active_version_id` | 快照已经具备标准版产品发布资格 |

标准版组合诊断必须同时满足原生入口资格与组合自己的标准版发布条件；两个维度不互相覆盖。`PREVIEW`、`OPTIONAL_CAPABILITY`、`NOT_READY` 不能冒充 `STANDARD_RELEASE`；非 `construction.standard` 版本也不能冒充标准版。版本必须属于当前场景。

## 诊断契约

沿用 `scenario.dependency.diagnosis.get`，新增独立的 `publication` 两部分：

- `native_capability.entry_qualified`：当前原生入口资格；`authority` 与 `coverage` 明确证据来源和覆盖范围。
- `scene_composition.applicable`：是否需要组合产品发布。纯原生入口和导航业务分类为 false，其他组合字段为 null，不能显示为“组合发布已通过”。
- 适用时分别返回 `snapshot_published`、`standard_released`、`active_version_id`、`release_state`、`edition`。

既有 `enable_allowed` 只是当前公司启用的依赖诊断结果，不是用户访问授权。既有证据 `scene_published` 仅表达组合快照状态，不再用于代表所有入口的发布资格。

### 三条读取链

1. **导航业务场景**：`business.v1:<code>` → 已维护场景及关联 → 同一 business catalog 的发布成员判断；不要求另一份组合场景。修复旧诊断漏传 env 导致此分支失败的问题。
2. **纯原生入口**：现有生效声明与原生直达证据 → 真实原生菜单/action 绑定及发布资格；不查询重复场景版本。绑定缺失或不一致拒绝。
3. **场景组合**：入口资格 → 当前场景及有效版本 → 所属场景、标准版状态和 edition 判断；编排草稿、缺少有效版本、预览或错误版本均不能通过。

## 本批未声称完成的范围

当前原生资格解析仍使用 `product_menu_source`，不是本批新建的能力发布模型，也不是所有底层能力的完整证明。普通入口的 `coverage=entry_menu_only`；业务分类的 `coverage=business_scenario_released_members` 表示存在可发布成员，不能推成所有成员已发布。

组合全部传递依赖的发布证明、版本内容完整性、产品目录向数据库权威收敛、场景编辑发布工作台和实际执行链的统一发布门禁，仍须沿已有发布/验证机制另批收口。此次不新增另一套发布表，不把只读诊断升级为发布动作，不删除现有权限检查。角色与业务运行条件的诊断占位信息不作为已完成业务验收的证据。

## BE-U04 发布内容与用户投影补充分界

场景版本发布只冻结产品定义：所有 active 且 visible 的 tile 都进入版本，tile 定义不携带
`allowed`、`user_visible`、`state`、`reason_code` 等用户访问结论。发布者当时看不到的 tile
不能从快照中消失。

已发布版本的运行读取再按当前用户调用能力访问投影，重新计算 tile 状态和可见性。产品发布资格、
企业启用、当前用户权限和作用域仍是独立维度。本补充不重写历史已发布版本；历史版本若已缺少
tile，需要另行识别并通过重新发布修复。

## 验证与回退

使用现有 `verify.navigation.publication_consumers.unit` 验证各分支、两类发布状态组合、原生绑定失效；使用 `acceptance.frontend.fixture_orm` 验证真实模型、目录与诊断一致、纯原生入口无需重复组合发布、组合版本/edition/归属拒绝。

本批没有 schema、种子或持久业务数据变更，不需要重复模块升级或重建验收环境。ORM 修改在 TransactionCase 中回滚。回退本批代码会恢复旧诊断规则，不改变已发布快照或企业启用记录。未变的第一批证据保留来源，不能用旧结果冒充新诊断已验证。

## 本轮发现的实际发布差异

现有 `enterprise.setup` 能从原生 action/view 投影，但当前 `product_menu_source` 未给对应菜单标准发布资格。诊断因此可以同时报告原生结构有效、组合发布不适用、原生资格未满足。该差异留待产品目录权威收敛，不在本批自动扩大发布集合。

独立复核发现并修正了“兼容 action 误判纯原生”的风险：真实驾驶舱 provider 与 `projects.dashboard_focus` 编排快照作为负例；原生直达 handoff 必须同时满足实际 primary action、final_scene、兼容目标及生效声明身份一致。测试保留前次失败，不能通过删除发布条件获得绿色。

## 本地验证结果

轻量 L1 通过；169 项定向离线测试通过；最终受管 ORM 42 项通过，0 failed / 0 errors。新增真实用例分别验证业务分类与目录一致、原生结构不替代发布资格、组合版本与 edition/归属、受限区块不抹掉组合发布要求。来源与原始失败/修复重验日志保留于本批 run，未声称远端 CI、主线集成或部署完成。
