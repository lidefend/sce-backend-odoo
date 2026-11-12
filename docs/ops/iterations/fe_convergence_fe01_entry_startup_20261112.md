# FE-01 Entry And Startup Convergence

## Identity

- Repository: `sce-backend-odoo`
- Branch: `fix/fe-convergence-fe01-entry-startup-20261112`
- Baseline: `1dcb22afd91c46c0f60df35d30a8af0ec972375f`
- Stage identity: baseline HEAD with this topic's explicit dirty scope
- Worktree inventory: main product-delivery worktree; the detached acceptance worktree is read-only and excluded

## Layer And Scope

- Formal Product Layer: P0 platform kernel product
- Layer Target: shared frontend entry identity, route authority validation and session bootstrap transaction
- Module: `frontend/apps/web`
- Standard vs User-Specific: platform engineering standard
- Why here: all affected defects discard or misorder already-declared contract facts in generic consumers
- Why not elsewhere: no business rule is missing; frontend scenarios must preserve, not replace, backend declarations
- Blast radius: scene handling-entry launch, route authority validation request, authoritative startup completion and their focused tests
- Harness boundary: top-level standard-preview input validation must precede recursive Make execution; inherited Make exports are not user input
- Generated evidence: complexity/decision inventories refresh source counts, line locations and the SceneView size reduction caused by extracting the entry resolver
- Excluded: FE-02 through FE-04, backend contracts, PR 875, database/runtime writes and business data

## Acceptance

1. A child handling entry with explicit action identity reaches that action even when the parent scene has a hint.
2. An internal scene descriptor wins over the parent scene hint.
3. `route.authority.validate` carries the selected action/menu pair and required query context.
4. HTTP, decode and validation failures end initialization in a visible error state with retry available.
5. A stale initialization cannot overwrite a newer ready state.
6. Focused tests execute non-zero; lint, strict typecheck and production build pass.
7. The standard-preview harness keeps fail-closed explicit input checks while not reclassifying a parent Make export as a user override.

## Evidence

Results are recorded through `make agent.run.begin` and `make agent.run.record`. Original logs stay under `.runtime/agent-runs/FE-CONVERGENCE-FE01-20261112/`.

| Check | Result |
| --- | --- |
| `verify.frontend.scene_shell_contract.unit` | passed; 6 entry-priority checks |
| `verify.nav.pro01r.route_authority.unit` | passed; real validation helper preserves action + menu + required query |
| `verify.frontend.workspace_scenario_lifecycle.unit` | passed; 295 frontend/backend checks including 3 startup-transaction cases |
| `verify.frontend.standard_preview.unit` | passed; 177 harness checks |
| `verify.frontend.lint.src` | passed; 0 errors, 4 pre-existing warnings |
| `verify.frontend.typecheck.strict` | passed |
| `verify.frontend.build` | passed; 5,384 modules transformed |
| `make ci.local.iteration` | passed; 12 affected targets |

Recovery observations:

- The route-authority test's existing CommonJS target required changing the new asynchronous assertion from top-level await to promise consumption.
- The split-usage guard rejected an unnecessary `.split('?')`; the resolver now uses an index/slice path without registering a new mechanism.
- The standard-preview harness exposed a P4 boundary defect: a top-level `.env.dev` default became an inherited export in recursive Make and was misread as a user override. Input validation now runs before recursion and the internal target remains guarded unless the parent explicitly marks validation complete.

Not run:

- Browser journeys against a deployed candidate.
- Independent review and remote CI.
- Full local Quick, which is optional for ordinary incremental candidates.

## Rollback

Revert the topic branch. No persistent data or service state is involved.
