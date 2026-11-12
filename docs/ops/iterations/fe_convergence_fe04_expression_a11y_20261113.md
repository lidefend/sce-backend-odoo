# FE-04 Expression And Shared Control Convergence

## Identity

- Repository: `sce-backend-odoo`
- Branch: `fix/fe-convergence-fe04-expression-a11y-20261113`
- Baseline: `07fb8879079d127af9c42a881724b8e9e0b37d16` (FE-03 candidate)
- Stage identity: baseline HEAD with this topic's explicit dirty scope

## Layer And Scope

- Formal Product Layer: P0 platform kernel product
- Layer Target: shared recursive presentation, request ownership and accessible interaction
- Module: `frontend/apps/web`
- Standard vs User-Specific: platform engineering standard
- Why here: these are generic renderer and interaction semantics
- Why not elsewhere: contract facts already exist; page/customer compensation would create parallel authorities
- Blast radius: recursive form actions, attachment viewer, hierarchy tree, chart trend colors and focused tests
- Excluded: backend contracts, full browser matrix, database, deployment and writes

## Acceptance

1. Every recursive form branch forwards the action state resolver.
2. Attachment viewer responses are owned by the latest open request and close.
3. Hierarchy branches expose keyboard expand/collapse.
4. Chart trend color is deterministic for data position and values.
5. Focused tests, lint, strict typecheck, build and `ci.local.iteration` pass non-zero.

## Evidence

Results are recorded through `make agent.run.begin` and `make agent.run.record`. Original logs stay under `.runtime/agent-runs/FE-CONVERGENCE-FE04-20261113/`.

| Check | Result |
| --- | --- |
| `verify.frontend.native_form_structure_responsibility.unit` | passed; 18 checks, all 4 recursive renderers forward action-state resolver |
| `verify.frontend.professional_relation_lifecycle.unit` | passed; 64 checks including attachment viewer request lease |
| `verify.frontend.hierarchical_worksheet.unit` | passed; 54 checks including keyboard expand/collapse |
| `verify.frontend.chart_dataset.unit` | passed; repeated/out-of-order color calls are deterministic |
| `verify.frontend.rich_text.browser` | passed; 10 checks, 0 console errors |
| `verify.frontend.native_form_action_presentation.browser` | passed; 45 assertions across 1440/390 viewports |
| `verify.frontend.lint.src` | passed; 0 errors, 4 pre-existing warnings |
| `verify.frontend.typecheck.strict` | passed |
| `verify.frontend.build` | passed; 5,387 modules transformed |
| `make ci.local.iteration` | passed; 11 affected targets |

Evidence notes:

- The historical notebook assertion in `native_form_structure_responsibility_test.ts` still expected the previous literal. It now asserts the current `Number(item.value)` behavior and the recursive action-state resolver invariant.
- Chart color callbacks no longer retain previous-call state; color is derived from the requested data index and adjacent value.
- Viewer open/close uses a request lease, so stale responses cannot publish payload/error/loading or create preview resources for a newer/closed dialog.
- Tree branch buttons expose `aria-expanded` and ArrowRight/ArrowLeft expand/collapse.
- Generated complexity/component inventories refresh only affected source identities and locations.
- Candidate frontend carrier startup is environment-blocked by an existing pidfile owned by the detached `sce-backend-odoo-acceptance-scope-20261109` worktree. The governed target correctly refuses cross-worktree takeover; that instance was not stopped.

Not run:

- Deployed browser journeys for keyboard traversal, stale viewer responses and repeated chart rendering.
- Independent review and remote CI.

## Rollback

Revert the topic branch. No persistent data or service state is involved.
