# 工作场景冲突审查报告 v1

状态：S2-02 设计产物，S2-03 实施前门禁的输入

## 1. 冲突审查结论（逐条对照）

| 冲突域 | 现状 | 审查结论 |
|---|---|---|
| Domain 权威 | 原生顶级菜单（侧边栏派生） vs 产品策略中心归属 | 职责已分离：原生菜单给身份/名称/顺序，产品策略给入口发布；WS-01 的 `domain_ref` 只引用原生菜单，不新建归属表 |
| Menu↔Scene 非 1:1 | 6 个菜单被多场景共享，nav map 用“先到先得” | WS-01 用 `entry_refs` 显式声明入口，`page_scene_refs` 显式声明页面，不做关键词/名称推断；共享菜单的解析仍待 S2-03 冻结唯一解析规则 |
| 角色表面 | `ROLE_SURFACE_OVERRIDES` 硬编码菜单清单 | WS-01 `actor_refs` 只引用现有角色 code，场景不定义权限；机制层角色表面收敛为 S3 独立事项 |
| 能力 Registry | 能力种子 + 目录 JSON 多载体 | WS-01 `capability_refs` 只引用已发布能力 + 证据绑定，不复制能力定义 |
| 场景身份多载体 | 7 类载体声明同一 scene_key | WS-01 只引用 `projects.intake/list/detail` 三个已有 scene_key，不新增载体 |
| 产品发布授权 | `product_menu_source.json` 131 条 release_state | WS-01 入口必须已在产品发布中，场景不自行发布入口 |

## 2. 三条遗留问题（已裁定，DECISION-S2-05/06/07）

1. 入口解析与记录上下文解析分离（S2-05）：`projects.list` / `projects.ledger` 是入口场景，
   `projects.detail` 是记录上下文场景；入口绑定必须唯一，记录详情必须携带真实 `model + record_id`，
   共享 menu/action 若仍多入口，必须增加显式入口绑定身份，禁止先到先得。
2. 能力证据指纹（S2-06）：直接复用 `capability_maturity.maturity_fingerprint`，禁止第二套指纹；
   产品依赖证据绑定 能力身份 + 发布版本/回执 + maturity fingerprint + 资格状态 + 产品快照版本，
   指纹变化触发产品依赖重新验证。
3. actor_refs 角色身份（S2-07）：引用 `IdentityResolver` 规范角色编码与 `res.groups` XMLID；
   `ROLE_SURFACE_OVERRIDES` key 必须对齐规范角色编码，但不作为授权权威，其菜单/拒绝/首页清单按
   ARCH-DECISION-010 收敛。

## 3. 未解决风险

1. 能力目录过期（P0）：`capability_catalog_v1.json` 42 条、`main_action.intent` 统一为通用兜底
   `ui.contract`、`status` 全部 ready、`maturity_fingerprint` 全部缺失；而
   `product_capability_matrix_v2.md` 声称 63 个能力。WS-01 已改用真实 intent/action/model 为能力身份，
   能力目录修订列为独立任务。
2. 角色编码三套并存（P1）：`IdentityResolver`（pm/owner/finance...）、`ROLE_SURFACE_OVERRIDES`
   （project_member/business_config_admin...）、能力目录 `required_roles`
   （project_manager/construction_manager...）。WS-01 按 DECISION-S2-07 使用 IdentityResolver 规范编码 +
   res.groups XMLID，其余两套待收敛。
3. 场景 `name` 口径仍有两套（场景注册表 `name` vs 原生菜单 `name`），留 S3 收敛。
