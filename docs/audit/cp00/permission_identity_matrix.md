# CP-00 permission and identity matrix

Baseline: `1bfe1f500320a35d59bef156db3c5ba746735668`

## 1. Identity predicates

### Platform-control administrator

Requires all three components:

```text
smart_core.group_smart_core_admin
AND current database == declared platform-control database
AND resolved identity audience == platform-admin
```

Source:

- `addons/smart_core/security/platform_admin.py:142`
- `platform_admin.py:179`

The audience must resolve. An unresolved audience fails closed:

- `platform_admin.py:126`

### Tenant configuration administrator

Current implementation:

```text
smart_core.group_smart_core_admin
AND current database is not the declared platform-control database
```

Source:

- `platform_admin.py:199`

The platform-control and tenant-config predicates are mutually exclusive.

### Business configuration administrator

Scenario navigation and tenant enablement use:

```text
smart_construction_core.group_sc_cap_business_config_admin
```

Sources:

- `addons/smart_construction_core/views/support/product_scenario_views.xml:60`
- `addons/smart_construction_scene/handlers/scenario_activation.py:95`

This is not the same identity as `smart_core.group_smart_core_admin`.

## 2. Capability and Scene administration

| Operation | Required authority in current source | Notes |
| --- | --- | --- |
| View `sc.capability` and `sc.scene` | Internal user read ACL | Raw read does not establish product authority |
| Create/update/delete `sc.capability` | `smart_core.group_smart_core_admin` | `addons/smart_construction_core/security/ir.model.access.csv:78` |
| Create/update/delete `sc.scene` | `smart_core.group_smart_core_admin` | same ACL file, line 82 |
| Publish Scene | `sc.scene.action_publish` through model access | No separate qualification permission |
| Import/export legacy Scene packs | Tenant configuration administrator | `scene_template_controller.py:443` |
| Modern Scene package intent | `smart_core.group_smart_core_scene_admin` | `addons/smart_core/handlers/scene_package.py:25` |
| Maintain `sc.product.scenario` | `group_sc_cap_business_config_admin` | `addons/smart_construction_core/security/ir.model.access.csv:777` |
| Set Scene exemption | Native menu model write authority | `product_scenario.py:252` |

The source shows three different administration concepts:

1. platform-core/Scene technical administration;
2. tenant configuration administration;
3. construction business-configuration administration.

They must not be collapsed into one frontend flag.

## 3. Explorer

Explorer authorization accepts either tenant configuration administration or
platform control administration:

- `addons/smart_core/handlers/platform_capability_explorer.py:30`
- `platform_capability_explorer.py:80`

The route uses `managementAdminOnly`, which accepts platform or tenant admin:

- `frontend/apps/web/src/router/index.ts:344`
- `frontend/apps/web/src/app/adminRouteAccess.ts:30`

Explorer has no write authority:

- `platform_capability_explorer.py:44`

## 4. Release Operator

All Release Operator read and write handlers require
`user_is_platform_control_admin`:

- `addons/smart_core/handlers/release_operator.py:70`
- `release_operator.py:89`

Route is platform-admin-only:

- `frontend/apps/web/src/router/index.ts:343`

However, direct model access for release records is granted to
`smart_core.group_smart_core_admin`:

- `addons/smart_core/security/ir.model.access.csv:14`

Native forms and model buttons expose direct release transitions:

- `addons/smart_core/views/platform_company_access_views.xml:519`
- `addons/smart_core/models/release_management.py:317`

This difference means:

- custom Release Operator enforces platform database plus audience;
- native release models enforce only group ACL.

The runtime reachability of the native release menus and `/a/...` actions for a
tenant administrator is **NOT_VERIFIED**. The source-level policy difference is
confirmed.

## 5. Release approval

Current policies:

| Action | Approval required | Executor roles | Approver roles | Self approval |
| --- | --- | --- | --- | --- |
| Preview promote | No | pm, executive, admin | None | Allowed |
| Standard promote | Yes | pm, executive, admin | executive, admin | Allowed |
| Rollback | Yes | executive, admin | executive, admin | Allowed |

Source:

- `addons/smart_core/delivery/release_approval_policy_service.py:86`

`can_approve` checks only group-role intersection. It does not compare the
requester with the approver:

- `release_approval_policy_service.py:157`

No code reads `allow_self_approval` beyond copying it into a policy snapshot.

Current result: one platform-control administrator can request, approve and
execute a release.

## 6. Tenant enablement

`scenario.activation.set` requires the construction business-configuration
administrator:

- `addons/smart_construction_scene/handlers/scenario_activation.py:95`

It also validates:

- explicit JSON boolean;
- Scene key;
- company within the user's allowed companies;
- product released;
- dependency diagnosis for `scene_entry.v1`;
- business scope for reserved `business.` keys.

The platform administrator does not automatically satisfy this group.

The company-scoped enablement record has a record rule:

- `addons/smart_construction_scene/security/sc_scene_company_enablement_rules.xml:4`

But current writes use `ir.config_parameter`, not that model:

- `addons/smart_construction_scene/services/tenant_scene_activation.py:46`

The model rule therefore does not currently control the active write carrier.
Handler-level company resolution and group checks are the effective runtime
guard.

## 7. User delivery

Final user access combines:

```text
published route authority
AND tenant business scenario enablement
AND native menu visibility
AND action group restriction
AND model ACL
AND record rule
AND company scope
AND operation-specific business validation
```

Sources:

- `addons/smart_core/delivery/effective_delivery_service.py:82`
- `addons/smart_core/delivery/menu_service.py:404`
- `addons/smart_construction_scene/services/business_scene_enablement.py:150`

A product release or tenant enablement never grants record access.

## 8. Why one platform administrator cannot complete the full delivery

The current split is intentional:

1. platform control decides which product release is globally active;
2. a tenant decides which released business Scenarios it enables;
3. Odoo grants the current user only the native groups, ACL, rules, companies
   and business operations that user actually holds.

This is a legitimate security boundary. The limitation is not that three
principals exist. The limitation is that there is no governed handoff object
that records:

```text
exact release identity
-> tenant acceptance
-> role assignment plan
-> user delivery verification
```

The future Product Assembly Workspace may present these steps in one UI, but
each step must run with the current principal's authority.

## 9. Authority findings

| Finding | Status |
| --- | --- |
| Final record authorization remains with Odoo | PASS |
| Explorer is read-only | PASS |
| Tenant enablement narrows route authority only | PASS |
| Frontend does not infer qualification | PASS |
| Platform release control and tenant enablement are separated | PASS |
| Release Operator and native release form enforce the same control | GAP |
| Self-approval is prohibited when an approver is required | GAP |
| Enabling a business Scenario proves complete member qualification | GAP |
| Tenant enablement has one enforced write carrier | GAP |
| A cross-principal lifecycle handoff is persisted and verifiable | GAP |
