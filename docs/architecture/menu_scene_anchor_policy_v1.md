# Menu Scene Anchor Policy v1

## Goal

Keep business navigation scene-driven. Menu is an entry anchor, not a business action carrier.

Boundary authority: `docs/architecture/navigation_dual_track_contract_v1.md` §2.7/§2.8
(目标态职责表与切换判据)。本文件是该边界在菜单锚点上的落地规则，不得与之冲突。

## Identity (Single Source)

- 入口身份 = **契约声明的 scene 身份**（正式菜单契约的 `target_scene_key` 字段）。
- 授权匹配 = `(menu_id, action_id)`：授权只能挂在原生 action → `res_model`
  （`ir.model.access` + record rule）与 `ir.ui.menu._visible_menu_ids()`，**永久保留**。
- 执行目标 = `entry_target` 判别联合（`action` / `scene` / `record` / `url`）。
- 来源关系 = scene 必须声明 `primary_action` / `source_ref` / `fallback_strategy`。
- 前端只有一条匹配规则：`action_id > 0 ? 匹配 action_id : 匹配 menu_id`；
  不得新增第二套身份匹配规则。

## Hard Rules

1. Business menu nodes must resolve to `scene_key` **declared by the contract**
   (`target_scene_key`)，不是节点上恰好携带的裸 `scene_key`。
2. Frontend menu click must prefer the contract-declared `scene_key` over `action_id`.
3. `action_id` remains fallback only for legacy nodes without a contract-declared scene mapping.
4. New business menu entries must declare `menu_xmlid -> scene_key` **in the contract**,
   not in code constants.
5. Scene mapping must point to a valid scene in scene registry.
6. `action` remains native source of truth and the authorization base;
   it must not be replaced by scene (see dual-track §2.4/§2.5).
7. Frontend must stop and report a contract defect when an entry has no contract basis;
   it must not infer or self-repair.

## Runtime Order

1. menu node own contract-declared `scene_key`
2. first descendant with `scene_key`
3. own `action_id` (legacy fallback)
4. first descendant with `action_id` (legacy fallback)

## Transition → Target Switch

- 过渡期允许 `action/menu` 与 scene 并存；`target_scene_key` 覆盖 < 100%。
- 切换到目标态必须同时满足 `navigation_dual_track_contract_v1.md` §2.8 的四条判据。
- 过渡期内契约声明数只增不减，代码常量映射只减不增。

## Guarding

- `make verify.menu.scene_resolve`
- `make verify.frontend.release_navigation_policy.guard`
- `make verify.contract.authority_hierarchy.guard`
- `scripts/release/test_locked_menu_policy_contract.py`（`SceneEntryIdentityContractTests`）
