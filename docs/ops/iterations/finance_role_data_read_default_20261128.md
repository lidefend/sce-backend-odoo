# Standard role action/search permission closure — 2026-11-28

Branch: `fix/finance-role-data-read-default-20261128`

Baseline: `bf3e78c2a9e81448f36425b05e133170aee39875` (`origin/main`)

## Layer declaration

| Field | Value |
| --- | --- |
| Formal Product Layer | P1 construction-industry standard product |
| Layer Target | standard role capability composition and product action/search dependency closure |
| Module | `smart_construction_core` |
| Standard vs User-Specific | construction standard |
| Why Here | Standard roles, their menu/action bindings and product-owned button gates are construction-industry product defaults. |
| Why Not Elsewhere | The frontend cannot invent labels or permission; P0 must not weaken dictionary ACL; P3 is not a repair carrier for a standard-role omission. |
| Blast Radius | Standard roles receive the existing domain read/user capabilities required by reachable actions; inaccessible accounting entry scopes and ungated write buttons are removed from non-owning roles. ACLs, record rules and frontend sources remain unchanged. |

## Problem

On a fresh clean business scene, a finance operator could open a payment request
but its contract relation search failed with HTTP 403.

The exact chain is:

1. Opening the relation picker without text reads `id`, `name` and
   `display_name`; this succeeds.
2. Typing a contract label invokes the generic `api.data` search-term builder.
3. The builder expands the query to the native contract search view, including
   `category_id` and `contract_type_id`.
4. Both fields are many2one relations to `sc.dictionary`.
5. Odoo evaluates those relation subqueries and checks dictionary read ACL before
   returning any contract row. The finance-operator role lacked the existing
   data-center read capability, while the finance-manager role included it, so
   the whole search failed with `AccessError` and surfaced as HTTP 403.

Contract `display_name` uses the contract subject, number, project display name
and partner display name. It does not directly read `sc.dictionary`; direct
`search_read` of `id`, `name` and `display_name` succeeds for the same finance
user.

This is a standard product-data inconsistency, not a frontend payload problem:

- the payment request form and relation payload were correct;
- the finance operator could read the contract ACL and display name;
- Odoo failed while evaluating the contract search-view relation fields backed
  by `sc.dictionary`;
- adding the existing capability through runtime administration removed the need
  for tenant-specific repair.

The broader default-role audit found additional deterministic inconsistencies:

- project, cost, owner and experience entry scopes included accounting-entry
  menus although their role capability composition could not read
  `account.move` or `account.move.line`;
- project and operations roles could reach cost, settlement and material
  actions that declared create/edit without the matching capability;
- finance users could reach material-rental settlement fields but lacked its
  read capability;
- project users and operation users reached dictionary-backed contract and
  settlement searches without data-center read;
- product-owned write buttons in contract, cost-plan, construction-diary,
  project and material forms were ungated.

## Validation responsibility

| Gate | State | Owner target | Reason |
| --- | --- | --- | --- |
| Exact base/head identity | required | branch and full SHA preflight | always |
| Focused capability-role test | required | `TestCapabilityRegistryService` | proves the default role implies dictionary read |
| Search-view dependency closure | required | `TestCapabilityRegistryService` | proves every many2one target in the contract search view is readable |
| Real free-text contract search | required | `api.data` list path | proves an initialized business company returns the matching contract without a 403 |
| Read-only containment | required | `TestCapabilityRegistryService` | proves the dependency does not grant dictionary write |
| All standard role action targets | required | `TestCapabilityRegistryService` | every reachable product action target model is readable |
| Declared action operations | required | `TestCapabilityRegistryService` | action `create`/`edit` context matches target ACL |
| All reachable search relations | required | `TestCapabilityRegistryService` | every search-view many2one target is readable |
| Native low-code affected views | required | 130 focused ORM tests | button/group and form productization regressions |
| Incremental planner unit target | passed | `verify.frontend.dev.incremental.unit` | validates changed-path mapping and execution control |
| Local incremental iteration | passed | `make ci.local.iteration` | 15 affected targets exited zero |
| Existing affected tests | required | capability registry / business role selectors | role composition consumer |
| Owning module baseline | deferred remote | `smart_construction_core` module baseline | P1 production security-data change |
| Clean runtime journey | required after local pass | payment-request contract lookup | user-visible failure reproduced |
| PR and scheduled mainline | required | exact-head PR CI and main full release | independent integration |

## Implementation

- Added existing data, cost, finance, material, settlement user and button-gate
  capabilities to the standard roles that expose the corresponding action.
- Removed accounting-entry entry scopes from project, cost, owner and experience
  roles that do not carry accounting read.
- Narrowed invoice registration and input-report actions/menus to finance
  operator/manager roles that own their create/edit operation.
- Gated product-owned write buttons to contract, cost, project, diary and
  material capabilities; marked read-only navigation methods explicitly.
- Completed all standard role compositions and action/menu/search dependency
  assertions through the real installed graph.
- Registered the affected model/view paths in the incremental planner so local
  iteration cannot silently omit their product-view and capability families.
- Added non-zero regression coverage that creates an initialized synthetic
  business company, assigns only the standard finance-operator role, inspects
  the native contract search view relation closure, and executes the real
  `api.data` list path with a free-text contract search.
- The regression creates one matching and one non-matching contract and asserts
  only the matching contract is returned. It also asserts that dictionary write
  remains denied.
- Targeted ORM result: 10 tests passed (`TestCapabilityRegistryService`).
- Role capability ORM result: 7 tests passed.
- Affected native-lowcode views: 130 tests passed.
- Role capability authority guard: 11 guard tests plus 4 entry tests passed.
- Incremental planner unit target: 286 tests passed.
- Final expanded `ci.local.iteration`: 15 required targets exited zero; receipt
  `.runtime/frontend-dev-validation/executions/20261127T230142Z-445677-109311235/receipt.json`.
- `make ci.delivery.freeze.prepare`: passed; generated reports refreshed and
  consistent at the current unfrozen candidate.
- No ACL, record rule, workflow or frontend source was changed.

## Separate P0 contract-projection gap

Backend button execution already re-reads the product action contract and
enforces `ExecuteButtonHandler` access mode, so a denied click fails closed.
However, the native form parser still publishes some object buttons and
many2one fields before an explicit per-user contract permission verdict is
applied. This can make the frontend advertise a button that execution will
reject, especially in native accounting views.

That belongs to the P0 action/relation contract producer, not to role
composition or ACL changes. The independent fix must:

1. attach an explicit `allowed`/`enabled` verdict to every published native
   object button using the same access-mode authority as `ExecuteButtonHandler`;
2. suppress or mark unavailable relation fields whose target model is not
   readable by the current principal;
3. verify the resulting runtime `actionRuleList` and form relation entries for
   representative read-only and read-write roles;
4. prove the frontend consumes those verdicts before claiming the operation is
   delivered.
