# 后端场景化分层与命名边界 v1

本文件收敛后端"场景化"里长期混用的 `scene` 与 `surface` 两个词，明确每个
对象的归属层、权威与禁止项。它是 `contract_authority_hierarchy_v1.md` 与
`app_shell_vs_page_scene_contract_v1.md` 的下位澄清，不替换两者；
`form_structure_surface_contract_boundary_v1.md` 是本文件 §4 中 `surfaces`
一条的展开。

## 1. 结论：绕在哪，界限钉在哪

后端并不缺场景机制，缺的是**一张总表**：同一个词 `scene` 承担了三个不同对象，
`surface` 承担了四个不同对象，且它们分散在 P0 机制、P1 行业策略和发布物三层，
没有统一的命名与权威规则。结果是"有数据定义就出现"和"预览面大于标准产品逻辑"
这类漂移无法定位到唯一责任层。本文件给出总表与三条硬规则。

## 2. `scene` 的三个不同对象

| # | 对象 | 载体 | 归属层 | 权威（可以决定） | 禁止 |
| --- | --- | --- | --- | --- | --- |
| S1 | 导航通道 | `sc.menu.config.scene` 枚举 `web/pm/finance/mobile` | P0 `smart_core/app_config_engine` | 菜单缓存的切分维度 | 不得当作业务场景身份；不得在别处用业务前缀再推导一次 |
| S2 | 业务场景身份 | `scene_key`（`scene_catalog_v2.json`、`smart_construction_scene` 内容、`/s/<scene_key>`） | P0 `smart_scene`（解析/编排内核）+ P1 `smart_construction_scene`（行业内容） | 入口 / 路由 / 动作绑定身份 | 不得作为 `ui.contract.v2` 页面体权威；只能做绑定与授权校验 |
| S3 | 发布场景快照 | `sc.scene.snapshot`、`SceneSnapshotService`、`release_surface_scene_contract` | P0 `smart_core/delivery` | 发布物的场景版本与通道 | 不得当作运行时页面体或可见性权威 |

已知隐式耦合：S1 由 S2 的 `scene_key` 前缀推导
（`app_nav_config._normalize_scene`：`project.*/projects.*/my_work.*→pm`、
`finance.*→finance`、`mobile.*→mobile`，其余 `web`）。这是"绕"的一个来源，
按既有兼容保留，登记为待收敛项，本轮不新增语义、不改菜单缓存维度。

## 3. `surface` 的四个不同对象

| # | 对象 | 载体 | 归属层 | 权威 | 禁止 |
| --- | --- | --- | --- | --- | --- |
| F1 | 契约渲染面 `contract_surface` | `resolve_contract_surface` → `user` / `native` | P0 `smart_core/utils/contract_governance` | 选择契约渲染通道 | 不得承载角色授权 |
| F2 | 角色面 `role_surface` | `system.init.role_surface` | P0 `smart_core` 机制 + P1 角色导航面声明 | 角色码、落地场景、候选场景、导航覆盖 | 不得当作页面区块声明 |
| F3 | 交付面 `scene_surface` | 交付策略 `surface`（`default`、`workspace_default_v1`、`construction_pm_v1` 等，`sc.scene.delivery.surface.default`） | P0 `scene_delivery_policy` 机制 + P1 策略文件 | 场景导航白名单 / 深链白名单 | 不得与 F1/F2 混读；不得用业务 `scene_key` 当值 |
| F4 | 表单声明面 `formStructureContract.surfaces` | `ui.contract.v2` → `formStructureContract.surfaces` | P0 `smart_core` 机制 + P1 策略 hook | 声明式页面区域（协作 / 审计等） | 不得放进 `layoutContract`；不得由运行时数据决定可见性 |

## 4. 三条硬规则

**R1 页面体规则**：`source_type=ui.contract` 的页面体只来自 `ui.contract.v2`
投影；`scene_key` 只参与绑定/授权校验（`_validate_scene_action_binding`）。

**R2 入口规则**：可打开的入口（scene / route / action / menu）由
scene-ready contract + 交付面（F3）过滤 + 角色/能力共同决定，缺一不可。

**R3 可见性规则（单条，fail-closed）**：

```
可见 = 契约声明了该区域
       AND （该区域无 audit 子声明 OR audit.authorization.state == 'allow'）
       AND 无其它已声明治理规则抑制
```

运行时数据（如时间线长度）不是可见性权威：未授权即使有数据也不可见；已授权
即使无数据也必须显示（带自身空态）。未知或未解析的授权状态按不可见处理。

## 5. 命名规则（新增契约键）

- 新增契约键禁止裸用 `scene` / `surface`：必须层限定，取值于
  `scene_key`、`scene_channel`、`scene_snapshot`、`contract_surface`、
  `role_surface`、`scene_surface`、`formStructureContract.surfaces`。
- 新增 `surface*` 键前必须在 §3 登记对象与归属层；未登记的 `surface` 视作
  F4 之外的非法键。

## 6. 执行点（谁在锁）

- `make verify.contract.authority_hierarchy.guard` — §4 权威链。
- `make verify.backend.scene_surface_boundary.unit` — §2/§3 的通道词汇表闭包、
  已注册交付面 fail-closed、未注册面的已知边界（行为断言，非文本断言）。
- `make verify.frontend.form_structure_surface_contract.unit` — R3 的声明消费与角色门。
- `addons/smart_core/tests/test_scene_delivery_policy.py` — 交付过滤的运行时语义。

## 7. 已知边界与待裁决缺口（不掩盖）

1. **未注册交付面 fail-open**：`_normalize_surface` 是开放命名空间，
   `_select_surface_policy` 对未注册面返回 `enabled=False`，交付白名单随即失效。
   调用方显式传入一个未注册的 `surface`（甚至一个业务 `scene_key`）即可绕过 F3
   的产品面白名单。角色/能力门仍然生效，但只声明了 `delivery_mode`、未声明
   `access`/`required_capabilities` 的场景会因此多出。是否收紧为"策略源存在时，
   未注册面按 fail-closed 排除"属于产品可见性决策，需显式裁决后再改机制，
   本轮只把它登记并锁定为已知边界。
2. **交付策略默认关闭**：`resolve_delivery_policy_runtime` 在无参数、无
   `ir.config_parameter`、无环境变量时 `enabled=False`，`filter_delivery_scenes`
   原样返回全部场景。`smart_construction_scene` 已 seed
   `sc.scene.delivery.policy.enabled=1`；纯 `smart_core` 部署无产品策略时为平台
   最小面。此默认作为显式边界由测试锁定，不作为"环境通过"的依据。
3. **S1 由 S2 前缀推导**（见 §2）：隐式耦合，登记待收敛。
4. **`SURFACE_POLICY_FILE_DEFAULT` 指向的 `workspace_default_v1` 策略文件不存在**，
   默认面实际落在内置白名单。登记为待收敛项。
