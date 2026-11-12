# FE-03 Draft And Submission Consistency

## Identity

- Repository: `sce-backend-odoo`
- Branch: `fix/fe-convergence-fe03-draft-submit-20261113`
- Baseline: `615d9e5f9b1f1c847e7f2c0086c9daa7ce1a4bc7` (FE-02 candidate)
- Stage identity: baseline HEAD with this topic's explicit dirty scope

## Layer And Scope

- Formal Product Layer: P0 platform kernel product
- Layer Target: shared activity identity, created-record navigation and edit-session merge behavior
- Module: `frontend/apps/web`
- Standard vs User-Specific: platform engineering standard
- Why here: cache, navigation, input locking and upload merging are generic client ownership mechanics
- Why not elsewhere: no business declaration is missing; page/customer rules would duplicate runtime semantics
- Blast radius: activity KeepAlive/cache identity, ordinary create handoff, rich-text saving input, attachment relation upload merge and focused tests
- Excluded: backend contracts, FE-04, database, deployment and write journeys

## Acceptance

1. App and router derive activity identity from one resolver.
2. Confirmed close advances the exact cache epoch used by App.
3. Ordinary create success uses managed SPA replacement and preserves other drafts.
4. Saving rich text rejects new input that a success response could discard.
5. Concurrent attachment uploads preserve latest links and do not resurrect removals.
6. Focused tests, lint, strict typecheck, build and `ci.local.iteration` pass non-zero.

## Evidence

Results are recorded through `make agent.run.begin` and `make agent.run.record`. Original logs stay under `.runtime/agent-runs/FE-CONVERGENCE-FE03-20261113/`.

| Check | Result |
| --- | --- |
| `verify.frontend.state_dashboard.unit` | passed; 84 checks including activity identity and exact cache epoch |
| `verify.frontend.record_form_return.unit` | passed; 21 checks including managed SPA create replacement |
| `verify.frontend.create_record_user_journey.unit` | passed; 67 checks for generated identity and partial-failure recovery |
| `verify.frontend.overview_rich_text.unit` | passed; saving editor lock covered |
| `verify.frontend.professional_relation_lifecycle.unit` | passed; 61 checks including attachment merge cases |
| `verify.frontend.lint.src` | passed; 0 errors, 4 pre-existing warnings |
| `verify.frontend.typecheck.strict` | passed |
| `verify.frontend.build` | passed; 5,385 modules transformed |
| `make ci.local.iteration` | passed; 12 affected targets |

Behavior evidence:

- Router registration and App KeepAlive consume the same activity resolver; persisted records, create forms and my-work no longer diverge.
- Confirmed close advances the exact full activity key that App reads; no short-key second epoch hides the old cached instance.
- Ordinary create success uses managed router replacement, so other activity-page drafts are not discarded by a document reload.
- A saving restricted editor sets `contenteditable=false` and suppresses input publication.
- Attachment upload completion merges against the latest relation IDs, preserving concurrent additions and removals.
- Generated complexity/component inventories refresh only affected source identities and line locations.

Not run:

- Deployed browser journeys for close/reopen, create with another dirty tab, rich-text save and concurrent attachment upload.
- Independent review and remote CI.

## Rollback

Revert the topic branch. No persistent data or service state is involved.
