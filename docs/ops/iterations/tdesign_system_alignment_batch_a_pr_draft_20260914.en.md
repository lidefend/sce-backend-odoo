# Draft PR: Align shared TDesign typography, surfaces, and section navigation

Chinese: [tdesign_system_alignment_batch_a_pr_draft_20260914.md](tdesign_system_alignment_batch_a_pr_draft_20260914.md)

## Summary

This PR aligns page typography, control text, card/section surfaces, and section-navigation overflow on the existing contract system and TDesign 1.20.5 bridge. Read-only long values now remain inside their own field slots.

It does not upgrade dependencies or change the shell, palette, P1 XML, business sections/field order, permissions, actions, save chain, or business data.

## User-visible improvements

- Lists, handling forms, and read-only details share a clear page-title, section, body, and supporting-text hierarchy.
- Long forms use a continuous work surface without stacking parent-card, section, and child-card borders/shadows; table, detail, and overlay boundaries remain distinct.
- Section-navigation browse buttons no longer cover end labels and keep the existing public button capability for mouse, touch, and keyboard use.
- At either edge, browse controls no longer lose keyboard focus through node removal and express the boundary with public `aria-disabled` state.
- Long contract names, unbroken identifiers, and relation names wrap naturally inside their own field slots without colliding with neighbors.
- Date, relation, and textarea controls in a composite form share body scale, control baselines, and field boundaries.

## Architecture impact

- Formal Product Layer: P0 shared presentation; P4 focused guards and delivery evidence.
- P0 consumes only existing tokens, appearances, contract structure, and public TDesign APIs. It has no model-name, field-name, XML-ID, or business-fact special case.
- P1/P2/P3 are unchanged, and none of the three representative pages receives dedicated CSS.
- Blast radius is constrained by the income-contract hierarchy list, expense-settlement create/read-only pages, and a material-inbound composite form.

## Verification

- `make ci.local.iteration`: PASS, 16 tests.
- Form canvas, product page header, professional base field, canonical presenter, native section navigation, primitive/page-pattern, and strict type checks: non-zero PASS.
- The 1088×791 product samples and long-value correction completed user screenshot review.
- On candidate `b7f167b8873b0578850aee4e5b37fa3f082df7cd`, both light and dark 1440×960/390×844 matrices contain eight passing samples with zero writes/errors and byte-identical complete before/after fingerprints.
- Forward/reverse overflow browse at 1088×791 and 390×844 proves both edge controls remain focused, connected, and correctly disabled; shared-button state uses a public prop.
- All five create-page navigation targets per sample are unique, fully visible, and stable below sticky surfaces; the read-only page checks every actually visible target.
- Eight eligible date/relation/textarea controls on the material-inbound composite form have no slot or baseline failure on desktop/mobile; nothing was saved.
- Freeze preparation, the single final Quick, and independent review are recorded off-repository against the final clean exact HEAD. This draft is not edited afterward to backfill results.

## Evidence

- Report: `docs/ops/iterations/tdesign_system_alignment_batch_a_20260914.md`
- Light matrix: `/home/lidefend/workspace/sce-offrepo/artifacts/playwright/tdesign-alignment-final-bound-light-b7f167b8/evidence-binding.json`
- Dark matrix: `/home/lidefend/workspace/sce-offrepo/artifacts/playwright/tdesign-alignment-final-bound-dark-b7f167b8/evidence-binding.json`
- 1088/390 focus probe: `/home/lidefend/workspace/sce-offrepo/artifacts/playwright/tdesign-section-browse-focus-b66f1640/summary.json`
- First light environmental failure: `tdesign-alignment-final-light-1440-390-85b05110`; diagnostic only, never presented as passing evidence.

## Not included

- Save, approval, permissions, role matrix, database, fixture, release, or deployment acceptance.
- TDesign upgrade, shell/palette/activity tabs, Dialog/Drawer lifecycle, low-code, or a new template engine.
- `ScFormField` help/error association, which remains a separate P0 interaction batch.

## Risk and rollback

- Shared CSS/component risk is constrained by three page kinds and the composite form. Business contracts and write paths do not change.
- Roll back read-only field boundary → navigation → surfaces → typography. No database rollback is required.

## Delivery status

`READY_FOR_REMOTE_DELIVERY_DECISION_AFTER_EXACT_HEAD_GATES`. Push, PR creation, Ready, merge, deployment, and release require separate authorization; stop on HEAD drift, conflict, or a new blocker.
