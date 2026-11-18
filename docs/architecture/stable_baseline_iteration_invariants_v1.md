# Stable Baseline Iteration Invariants v1

- Status: hard lock
- Applies to: P0-P4 source, schema, permission, workflow, frontend and delivery-tool changes
- Authority: `AGENTS.md`; this document defines the minimum responsibility set that an
  incremental iteration may not narrow away

## 1. Purpose

An iteration may select a narrow implementation surface. It may not select a narrow
validation responsibility surface by omitting tests that already own the changed
behavior.

A focused test proves the new assertion. The owning module baseline proves that the
new assertion did not break already accepted behavior. Both are required when the
change reaches a product module's runtime behavior.

## 2. Baseline identity

Every candidate must declare and bind:

1. the accepted mainline/base commit;
2. the exact candidate branch and full HEAD;
3. one governed runtime identity where runtime evidence is required;
4. the complete owned and excluded path scope; and
5. the later exact-head remote identity used for review and merge.

A different mainline base, candidate head, database, company or role is a different
baseline. Evidence may be carried forward only through the recorded dependency and
input comparison rules.

## 3. Minimum validation responsibility

| Changed surface | Minimum responsibility before downstream acceptance |
| --- | --- |
| P0/P1 Odoo model, service, handler, permission, security, workflow or state behavior | Valid reusable owning-module baseline coverage plus every existing affected test family, plus focused changed-behavior tests; full module ORM is the fallback when the dependency map is missing or incomplete |
| P0 contract/schema or frontend contract consumer | Contract/schema/action/status checks for producer and consumer, plus focused tests |
| Frontend TypeScript/Vue source | Lint, strict typecheck, affected unit tests, build; affected browser journey when behavior is user-visible |
| Data migration, replay, fixture or acceptance environment | Owning migration/repair checks, governed environment identity, write readback and restoration |
| CI, verification, evidence or delivery tooling | Owning tool tests, affected consumer tests and an unrelated-input reuse counterexample when invalidation logic changes |

The following are supplements, not substitutes:

- a new test tag;
- a happy-path sample;
- a schema-valid hand-written response;
- a frontend build without its server contract;
- a remote workflow name without an exact-head successful conclusion; or
- a receipt whose declared inputs omit the affected existing test family.

The module baseline is a coverage obligation, not an instruction to rebuild and
rerun every test for every edit:

- a previous complete module receipt may satisfy unchanged coverage when its
  module authority, environment identity, test bytes and evidence logs still match;
- changed model behavior invalidates only the existing test families that declare a
  dependency on the changed model, symbol or behavior;
- the focused changed-behavior tests run in addition to those affected families;
- if the dependency map cannot prove the affected family set, the full owning module
  ORM baseline becomes required; and
- the first candidate in a new module/environment baseline still requires one
  complete module run to establish reusable coverage.

## 4. Contract and business invariants

- The runtime contract is the product fact source; frontend code does not invent
  missing state, action, permission or reason semantics.
- Declared action identity, record action identity, evidence-gate reference and
  executable target must reconcile.
- Availability projection and real execution use the same model-owned business
  judgment.
- A create action catalog is not execution authorization for a saved record.
- One primary statusbar is projected from the real model state field.
- Denied actions retain stable reason codes and readable explanations; unauthorized
  actions are omitted according to the declared scope.

## 5. Evidence invalidation and reuse

- Reuse is keyed by declared inputs, assertions, dependent checks and governed
  environment identity.
- An unrelated target edit in the same Make fragment does not invalidate a receipt;
  a change to the selected target's reached recipe, prerequisite, variable or include
  override does.
- A change to an existing test family invalidates the module baseline. A new focused
  test does not replace that baseline.
- Logs referenced by a receipt are immutable evidence. Overwriting a log invalidates
  the receipt even when the source code is unchanged.
- Documentation-only changes do not invalidate runtime evidence.
- Expired wall-clock age alone does not invalidate code-bound evidence.
- Reusable test environments are part of baseline efficiency. Their identity binds
  the pinned image/dependency set, schema and module state, fixture scope, database
  role, and runtime profile. Matching identities may reuse a prepared template or
  database; a mismatch requires governed rebuild. Reuse must not skip fixture
  restoration, isolation or source identity checks.
- The registered local.test lane defaults to this template-backed clone. The
  template-free path remains an explicit diagnostic override. In the BE-CLOSE-01
  baseline, one schema-changing template preparation took 246.9 seconds, while
  the next isolated ORM receipt took 19.3 seconds instead of rebuilding for
  roughly four minutes.

## 6. Mandatory pre-iteration gate preflight

Before the first implementation edit, the executor must produce a reviewable table:

| Gate | State | Owner target | Reason |
| --- | --- | --- | --- |
| exact base/head identity | required | identity check | always |
| owning module baseline coverage | required/excluded | reusable receipt or registered module target | required for P0/P1 behavior |
| existing affected test families | required | exact test targets | derived from the changed model/symbol map |
| focused changed tests | required | registered target(s) | always for behavior |
| contract/schema/consumer | required/excluded | registered target(s) | if declared or consumed |
| frontend lint/type/build | required/excluded | registered target(s) | if frontend source changed |
| runtime/browser journey | required/excluded | governed entry | if user-visible behavior changed |
| remote required gates | required | exact-head PR checks | publication and merge |

`not_run` is valid only with a concrete exclusion reason. A known failed or missing
required gate blocks later gates. Unknown impact is treated as required, not skipped.

## 7. Enforcement

- The active run must identify the reusable module baseline receipt or register the
  module baseline target with its complete inputs.
- The local impact planner must select every affected existing test family. When it
  cannot derive that set, it must select the owning module baseline and fail closed
  if the required coverage target is absent from the selected plan.
- Focused targets run in addition to, never instead of, affected existing coverage.
- `ci.local.iteration`, generated-evidence preparation, exact-head PR checks and
  independent review remain separate required layers.

## 8. Completion statement

A status may say "incremental validation passed" only when the responsibility table
was complete and every required entry actually passed or has an explicitly accepted
external gate still pending. Local green focused tests do not establish batch,
mainline, deployment or user-acceptance completion.
