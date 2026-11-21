# ARCH-CLOSE-01 Extension Lifecycle & Hook Authority

## Batch identity

- Branch: `feature/arch-close-01-extension-lifecycle-20261121`
- Baseline: `09be7ab696bb9201efe1cdd66c22ff8e3c3d6d88`
- Formal product layer: P0/P1/P4
- Environment: offline source plus the owner-authorized disposable
  `sc-local-test/sc_test` profile and two temporary clones from its
  `smart_construction_bundle` template
- Persistent product/database mutation: none
- Status: `verification_pending`

## Objective

Make installed Odoo modules the execution authority, bind Handler and Hook
runtime state to the current Odoo Registry lifecycle, and declare Hook
invocation semantics without introducing another extension framework.

## Layer declaration

| Item | Value |
| --- | --- |
| Layer Target | `smart_core` extension runtime, provider ownership, database guard |
| Module | `smart_core`, `smart_construction_core`, `smart_construction_scene` |
| Standard vs User-Specific | generic platform extension mechanism |
| Why Here | module discovery, Handler routing and Hook invocation are P0 mechanics |
| Why Not Elsewhere | customer, frontend and business models do not own module lifecycle |
| Blast radius | extension discovery, Handler dispatch, Hook resolution, guard and tests |

## Implemented result

| ID | Work | Status |
| --- | --- | --- |
| A01 | Installed-module filtering and explicit configuration diagnosis | implemented |
| A02 | Registry-scoped Handler/Hook extension runtime | implemented |
| A03 | Hook mode declaration and duplicate-provider guard | implemented |
| A04 | Four Core/Scene Hook ownership corrections | implemented |

Effective extension modules are the intersection of currently installed Odoo
modules and `sc.core.extension_modules`. A missing or non-installed enabled
module fails with `EXTENSION_CONFIGURATION_INVALID`.

Extension Handler state is stored on the current Odoo Registry. New Registries
start without another database's state, and an enablement change on the same
Registry rebuilds its context. Base Handler lookup is lazy to avoid the
`extension_loader -> handler_registry -> handlers -> extension_loader` startup
cycle.

Hook contracts declare `single_owner`, `ordered_merge`, or `run_all`. The guard
currently validates 87 call sites, 84 single-owner Hook names, 3 ordered
merge Hooks, and 4 run-all Hooks. Duplicate owner providers, undeclared
providers, incompatible signatures, provider exceptions, unknown Hooks, and
cross-mode entrypoint use fail explicitly.

The four Core/Scene conflicts are resolved as documented in
`docs/architecture/arch_close_01_extension_lifecycle_v1.md`. Scene navigation
continues through its real consumer chain, while the Scene Registry-derived
mapping overrides static Scene compatibility input after the Core map.

Runtime consumers were migrated from the process-global catalog to the current
Registry: intent routing, terminal shell, login catalog, machine-credential
scope, intent authorization, system-init fact collection, capability explorer,
release read model, and contract snapshot export. The snapshot exporter no
longer enables an installed industry module implicitly when enablement is empty.

## Exclusions

- No customer module or customer history change.
- No business model, ACL or record-rule change.
- No Contract V2 or frontend behavior change.
- No product release or edition snapshot change.
- No persistent database, deployment or production action.

## Validation

| Gate | Result | Evidence |
| --- | --- | --- |
| L0 | PASS | branch/HEAD/status resolved; no out-of-scope paths |
| L1 | PASS | `git diff --check`; changed Python compiled; changed shell scripts `bash -n` |
| L1 | PASS | extension runtime, Hook contract, Hook resolver, and module-guard receipts |
| L1 | PASS | ORM result-guard regression: nested dynamic Registries no longer mask the selected database count; 31 self-test checks |
| L1 | PASS | verification-lane coverage registry reviewed: 10 new focused targets registered, frozen identity 673 → 683, 74 guard tests |
| L1 | PASS | `python_name_binding_guard.py` over 3,437 files |
| L2 | PASS | extension consumer receipt: 135 tests, non-zero |
| L2 | PASS | real Registry context ORM: 4 tests |
| L2 | PASS | affected native-alignment Hook ORM family: 4 tests |
| L2 | PASS | real Scene Hook consumer ORM: 4 tests |
| L2 | PASS | Scene fact boundary and construction Core responsibility guards |
| L2 | PASS | backend contract boundary report: `error_count=0` |
| L2 | BLOCKED BASELINE | `verify.backend.architecture.static` reports two pre-existing P0 industry literals: `platform_capability_explorer.py: construction.standard` and `release_operator_read_model_service.py: smart_construction_core.sc.product.scenario`; both exist at baseline `09be7ab6` |
| L2 | PASS | `verify.frontend.dev.incremental.unit`: 204 tests; dirty exact-identity resume, commit-preserving runtime identity, rewritten-commit same-tree resume, runtime/authority invalidation, interrupted/failed row rejection, non-ancestor rejection and automatic offline registration covered |
| L2 | PASS | first post-fix `ci.local.iteration`: 19 affected targets executed, all passed; new receipt `20261121T091952Z-4104900-784721989` |
| L2 | PASS | same-identity continuation: `executed=2`, `resumed=17`; only the two ORM targets without explicit readbacks ran again, both passed |
| L1 | PASS | guard registry reconciled after three contract-snapshot tests became Make-referenced; audit reports 1651 scripts, 87/87 orphans and 168/168 dispositions closed |
| L5 | ENVIRONMENT DEFECT | first explicit Quick bootstrap hit a root-owned empty ignored `artifacts/` directory; ownership was corrected without deleting evidence |
| L5 | BASELINE EVIDENCE DEFECT | second Quick run exposed three stale orphan acknowledgements; `guard.registry.seed` removed only the stale entries |
| L2 | FAILED BASELINE | full `smart_core` baseline on the bundle template: 65 failed / 88 errors of 642 tests; the same broad pre-existing debt is recorded in prior runs, while every changed-family target passed |
| L2 | FAILED BASELINE | full `smart_construction_scene` baseline: 1 error of 16 tests in `TestAdminClose01PlatformToEnterprise` (`scenario_catalog["rows"]` missing); all four new Hook authority tests passed |
| L3 | PASS | two cloned databases, independent Registries, enablement changes, construction/owner isolation, native install/upgrade/uninstall, and post-lifecycle rejection: 1 lifecycle test |
| L3 | PASS | both temporary database clones were terminated and dropped with authoritative `pg_database` absence readback |
| L4 | N/A | no browser or product-journey change |
| L5 | NOT RUN | independent exact-head review and required remote checks |

The verifier-authority change invalidates pre-fix aggregate receipts once. A
new interrupted receipt produced by this implementation can resume its passed
targets under the same dirty runtime identity; the fix does not relabel the old
authority or copy old rows into a new receipt.

Managed receipts:

- `extension_runtime_context`: 7 tests
- `hook_contracts`: 6 tests
- `hook_resolver`: 7 tests
- `extension_modules_guard`: 2 tests
- `extension_consumers`: 135 tests
- `agent_ledger`: 18 tests
- `agent_resume`: 67 tests
- `extension_runtime_context_orm`: 4 tests
- `extension_native_alignment_orm`: 4 tests
- `extension_hook_authority_orm`: 4 tests
- `extension_lifecycle_orm`: 1 multi-database lifecycle test
- `orm_guard_self_test`: 31 checks
- `frontend_dev_incremental_unit`: 204 tests

## Runtime lifecycle result

The owner-authorized runtime matrix cloned the current managed
`sc_test_template__smart_construction_bundle` twice inside
`sc-local-test/sc_test`. It verified:

- DB-A and DB-B have independent Handler maps.
- An enabled but uninstalled `smart_owner_core` is rejected.
- Native install causes owner Handlers to appear without construction leakage.
- Returning to DB-A preserves its construction state.
- A same-Registry enablement change rebuilds and removes old extension Handlers.
- Native upgrade preserves registration, and native uninstall removes execution
  eligibility and returns to explicit configuration failure.
- Temporary clones are removed and absence is read back.

No customer module, persistent customer data, release snapshot, ACL or business
record change is included.

## Rollback

Revert this bounded P0/P1/P4 candidate as one unit. No persistent customer
data, release state, ACL, or business records were mutated. Temporary runtime
databases were removed after the lifecycle test.
