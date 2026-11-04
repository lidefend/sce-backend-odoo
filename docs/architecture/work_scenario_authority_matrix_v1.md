# 工作场景权威矩阵 v1

状态：S2-02 设计产物
上游：ARCH-DECISION-010、ARCH-DECISION-011、product_navigation_authority_v1.md

## 1. 七类事实权威

| 事实类型 | 唯一权威 | 现有载体 | 消费方 |
|---|---|---|---|
| 业务域 Domain | 原生顶级菜单 | `menu_business_taxonomy.xml` / `menu_product_navigation_v2.xml` | 侧边栏、场景投影 |
| 菜单 Menu | 原生 `ir.ui.menu` | `menu_*.xml` | 导航投影、场景注册、侧边栏 |
| 场景 Scene | 原生 menu/action/model/view/group + 产品发布 | `scene_registry_content.py` 等（多载体，S2-03 待收敛） | `scene_provider.py`、nav maps |
| 能力 Capability | 原生 model/action + 能力成熟度 | `capability_maturity.py` + `sc_capability_group_seed.xml` + 目录 JSON | 场景组合引用 |
| 角色 Role | 原生 `res.groups` + ACL/record rules | `sc_role_groups.xml` | 角色表面投影、前端 |
| 导航 Navigation | 版本化产品策略 ∩ 原生事实 | `final_menu_navigation_service.py` + route authority | 前端纯渲染 |
| 产品策略 Product Policy | `product_menu_source.json` + `product_navigation_authority_v1.md` | 131 条 entry release_state | 发布、导航、交付契约 |

## 2. 两层发布权威（ARCH-DECISION-011）

| 层次 | 唯一权威机制 | 负责事项 |
|---|---|---|
| 能力发布 | `capability_maturity.py` | 能力资格、成熟度、证据、发布指纹 |
| 能力目录 | `capability_catalog_v1.json` | 能力身份与目录 |
| 产品发布 | `product_menu_source.json` | 产品入口和发布状态 |
| 产品策略 | `ProductPolicyService` | standard / preview 产品范围 |
| 场景发布 | `scene_snapshot_service.py` | beta / stable 场景快照 |
| 产品交付 | `scene_contract_builder.py` | 生成正式交付契约 |
| 版本晋升 | `edition_release_snapshot_promotion_service.py` | 产品版本晋升 |

不新增：Capability Release Center、Product Release Center、第二套 Capability/Product Registry、第二套版本管理。

## 3. 能力资格 × 产品引用矩阵（DECISION-S2-02）

| 能力资格 | Preview 产品 | Standard 产品 |
|---|---|---|
| 未发布 | 禁止 | 禁止 |
| Preview 发布 | 允许，受预览范围约束 | 禁止 |
| Standard 发布 | 允许 | 允许 |
| 已停用/退役 | 禁止新交付 | 禁止新交付 |

以现有成熟度机制的实际状态为准，不自行创造状态。

## 4. 三项补充裁定

1. 入口解析与记录上下文解析分离（DECISION-S2-05）：`projects.list`/`projects.ledger` 是入口场景，
   `projects.detail` 是记录上下文场景；共享菜单必须显式入口绑定，禁止先到先得。
2. 能力证据指纹（DECISION-S2-06）：复用 `capability_maturity.maturity_fingerprint`；
   产品依赖证据 = 能力身份 + 发布版本/回执 + maturity fingerprint + 资格状态 + 产品快照版本。
3. actor_refs（DECISION-S2-07）：引用 `IdentityResolver` 规范角色编码 + `res.groups` XMLID；
   `ROLE_SURFACE_OVERRIDES` key 对齐规范编码，但不作为授权权威。
