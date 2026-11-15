# ENTITLEMENT-01 Read-Only Investigation

Status: `INVESTIGATION_COMPLETE_NO_MUTATION`

Captured at `2026-11-15T23:43:23Z` against the owner-authorized rebuilt
`sc_dev_demo` baseline.

## Conclusion

The historical `sc.entitlement` row is a materialized cache derived from a
subscription plan. It is not itself the ultimate entitlement source and it has
no seed XMLID.

The absence was not shown to block the read-only startup feature-flag path:

- both current plans exist;
- there are zero subscription rows, so `_resolve_plan()` selects the active
  `default` plan;
- the default plan has empty feature flags and limits;
- all six current capabilities have no `required_flag`.

However, several existing read paths call `get_effective()`, which lazily creates
the missing row. Therefore the row is not the ultimate source of current plan
facts, but some callers can attempt a write during a read. Under a principal
without create rights, `permission.check` may therefore fail instead of merely
returning an empty default. That path was not executed, because doing so could
materialize the row.

No entitlement row was created during this investigation.

## Model

`addons/smart_core/models/subscription.py`

- `sc.entitlement.company_id`: required, company-scoped, cascade on company
  deletion.
- `sc.entitlement.plan_id`: optional plan, set null if plan deleted.
- `effective_flags_json` and `effective_limits_json`: materialized plan values.
- `updated_at`: last materialization time.
- SQL constraint: one entitlement per company.
- ACL: internal users read; Smart Core admins read/write/create/delete.
- No Record Rule scoped the model.

## Historical Row Identity

From the authorized untouched `20261115T082948Z` recovery dump:

| Field | Value |
| --- | --- |
| Row ID | `1` |
| Company ID | `1` |
| Plan ID | `1` |
| Plan code | `default` |
| Create/write user ID | `57` |
| Creator XMLID | `smart_construction_demo.sc_demo_user_test_admin` |
| Entitlement XMLID | none |
| Effective flags | null |
| Effective limits | null |
| Updated at | `2026-11-13 17:27:19` |
| Create/write date | `2026-11-13 17:27:16.919185` |

The paired pre-rebuild snapshot still contained the same one row. The current
rebuilt database contains zero rows.

## Creation Source

`smart_core/data/sc_subscription_default.xml` calls
`sc.subscription.plan.ensure_platform_default_plans()`. That method creates or
updates only subscription plans.

It does not create `sc.entitlement` rows.

`ScEntitlement.get_effective(company)` performs the materialization:

1. resolve an active/trial subscription, otherwise the default plan;
2. copy plan feature flags and limits;
3. create the company entitlement when absent;
4. update it when plan values changed.

The creator stored in the historical row is consistent with a Demo user
triggering this lazy path at first access, but the exact original caller is not
provable without an operation log. That attribution remains `UNATTRIBUTED`.

## Current State

- `sc.entitlement`: 0 rows.
- `sc.subscription`: 0 rows.
- `sc.subscription.plan`: `default` and `pro`.
- `sc.subscription.default_plan_code`: absent, so the fallback code is
  `default`.
- Default plan flags: empty.
- Default plan limits: empty.
- `sc.capability`: 6 rows; 0 have `required_flag`.

## Real Consumers

| Consumer | Read behavior | Missing-row behavior |
| --- | --- | --- |
| `permission.check` | `get_effective()` then flags check | Lazily creates row |
| Intent permission guard | `_effective_flags()` -> `get_effective()` | Lazily creates row |
| `system.init` early flags | `platform_feature_flags_for_user_readonly()` resolves plan directly | No row creation |
| `system.init` access facts | `get_payload()` -> `get_effective()` | Lazily creates row |
| Scene orchestration | `platform_feature_flags_for_user()` -> `get_effective()` | Lazily creates row |
| Platform Ops tenants | `get_effective()` when a company is registered | Lazily creates row |
| Company limit helpers | `get_effective()` | Lazily creates row |

The native Odoo ACL/Record Rule decision remains the final record-access and
execution authority. `sc.entitlement` is a product-availability feature-flag
carrier, not a substitute for native permissions.

## Impact Assessment

Current Demo startup impact: `NO_CURRENT_CAPABILITY_DENIAL_IDENTIFIED`.

Reasoning:

- the default plan resolves without a subscription;
- its flags are empty;
- no current capability requires a non-empty flag;
- the read-only startup feature-flag path can derive the same empty effective
  values directly from the plan.

Runtime integrity impact: `RISK_DEFERRED_WRITE_AND_PRINCIPAL_FAILURE`.

`system.init` first resolves flags through the read-only helper, then later
attaches access facts using `get_payload()`. The first path tolerates absence;
the second attempts lazy materialization, and failures are swallowed by the
payload builder. `permission.check` also calls `get_effective()` without that
exception wrapper, so a non-admin principal can receive an access failure if
the row is absent. This exact runtime branch is `NOT_VERIFIED` because invoking
it would mutate or attempt to mutate the persistent database.

## Recommendation

- Do not manually reseed the current row.
- No current capability denial was identified in the read-only startup path,
  but do not yet declare missing entitlement globally harmless.
- Keep the lazy materialization behavior visible as a separate lifecycle
  concern.
- Separately verify `permission.check` under a non-admin principal in a
  disposable environment before choosing between an idempotent bootstrap seed
  and a read-only entitlement resolver.
- If the platform standard later requires an entitlement row after every
  bootstrap, implement it through an explicit idempotent bootstrap/seed path,
  not a manual SQL insert.
- Any change to write-on-read behavior belongs to a separately authorized
  platform task after CP-00 maps the broader lifecycle.

## Boundary

- No database insert, update, delete or restore was performed.
- No ORM method that materializes entitlement rows was called.
- Subscription plans, subscriptions, capabilities, scenes, releases and
  tenant-enablement state were not changed.
