# TDesign System Alignment Batch A Delivery Report

Chinese: [tdesign_system_alignment_batch_a_20260914.md](tdesign_system_alignment_batch_a_20260914.md)

## Scope and identity

- Branch: `codex/tdesign-system-alignment-v1`; baseline: `origin/main@6885840fe57f1e00ae8ce78bc76687e8a4a66332`.
- Product-source candidate: `85b051104f29934e84ffaf81aff4ec8827290e51`, tree `cd2be7d220c89a907e04a5d9ae2a23a44412a3b2`, complete worktree fingerprint `eb216c2897ffa47c9e45978a3dcdca3336b35a60e07f2eec5979786ac75063a7`.
- Formal Product Layer: P0 shared presentation. Layer Target: existing design tokens, public TDesign bridge, shared page header, card appearances, generic form section/field layout, and section navigation.
- Standard vs User-Specific: platform-wide standard. No P1/P2/P3 business fields, customer preference, or runtime configuration is introduced.
- Why Here: inconsistent typography, surfaces, and navigation consumption originates in shared P0 presentation code.
- Why Not Elsewhere: P1 XML, contract fields/sections, permissions, actions, and business semantics remain authoritative; no page CSS or model special case masks them.
- Blast Radius: shared list, form, read-only typography/surfaces/field boundaries and every consumer of `FormSectionNavigation`. One representative of each page kind plus a composite form constrains the impact.

## User-visible result

- Page title, section, body/control, and label/supporting text now consume the 24/16/14/12 product semantic hierarchy. Widgets, formatting, validation, and title content are unchanged.
- The main workspace retains one structural boundary; business sections use a continuous surface and one separator while nested tables, overlays, and special states preserve functional boundaries.
- Section-navigation browse controls occupy their own space. End labels are not covered, and desktop/touch target sizes continue to use existing tokens.
- Long Chinese text, unbroken identifiers, and relation names wrap inside their own read-only field slots without covering a neighbor or hiding facts.
- The modest vertical increase on create forms comes from line height and natural wrapping. No duplicate section/card padding was found, and no fixed height or smaller type was used to compress it.

## Ownership

| Layer | Change | Boundary |
| --- | --- | --- |
| P0 tokens / bridge | Align product title, section, body, supporting text, and public control CSS variables | No TDesign upgrade, palette change, or theme lifecycle change |
| P0 shared components | `ProductPageHeader`, `ScCard`, `FormSection`, `ProfessionalBaseFieldControl` | No model name, field name, XML ID, or business-value inference |
| P0 form renderer | Continuous sections, shrinkable grids, and in-slot wrapping for read-only values | No contract section/order/widget/save change |
| P0 navigation | Dedicated overflow-control space while retaining existing anchor/scroll logic | No TabPanel replacement, routing, or section-identity change |
| P4 | Focused guards, read-only browser evidence, this report, and PR draft | No database write or expanded business acceptance |

The four product commits are independently reversible: `67301212` (A1 typography), `d63a1dbb` (A2 surfaces), `244cf29d` (A3 navigation), and `85b05110` (read-only field boundary).

## Validation and evidence

| Layer | Entry or evidence | Result |
| --- | --- | --- |
| L0 | HEAD, tree, complete tracked/staged/untracked fingerprint | Product-source candidate is clean and fixed |
| L1 | `make ci.local.iteration` | PASS, 16 tests |
| L2 | Form canvas, product page header, professional base field, canonical presenter, native section navigation, primitive/page-pattern guards, and strict typecheck | Non-zero PASS; shrinkability, title tokens, navigation space, and preserved structure are covered |
| L3 | `make local.dev.health` and exact-head candidate frontend | Existing `sc-local-dev/sc_dev_demo` healthy; candidate frontend started and stopped through governed targets. Module upgrade was not applicable because no module/schema changed |
| L4 light | `/home/lidefend/workspace/sce-offrepo/artifacts/playwright/tdesign-alignment-final-light-1440-390-85b05110-retry1/summary.json` | Eight page/viewport samples at 1440×960 and 390×844: pass, zero writes, zero errors; root overflow=0, h1=1, and tokens loaded throughout |
| L4 dark | `/home/lidefend/workspace/sce-offrepo/artifacts/playwright/tdesign-alignment-final-dark-1440-390-85b05110/summary.json` | Same eight samples pass with zero writes/errors; long values, controls, surfaces, navigation, and horizontal content remain reachable |
| L4 composite | `material-inbound-composite-form` in both summaries | Eight eligible date/relation/textarea controls have zero slot or baseline failures on desktop/mobile; expanded for inspection only, never saved |
| L5 | `make ci.delivery.freeze.prepare`, one final `make ci.local.quick`, independent review | Recorded after freeze by off-repository exact-head receipt/review; this tracked report is not changed to backfill results |

All five expense-settlement-create navigation targets are unique, fully visible, and positioned below sticky surfaces in every theme/viewport. The read-only detail also passes for every actually visible target; light desktop exposes 12 while the other samples expose 11, so the report does not turn a data-dependent count into a standard. The income-contract mobile table exposes its horizontal-browse affordance and controls without root-page overflow.

The first light matrix observed `ERR_NETWORK_CHANGED` and dynamic-component loading errors. Its summary remains under `tdesign-alignment-final-light-1440-390-85b05110` and is classified as `environment_defect`. Only after the governed health check recovered on the same HEAD was a single retry run. The passing evidence does not overwrite or hide the failed attempt.

A focused pre-freeze check also found that the page-header guard still required the old property order under `.readonly-value`, so it rejected the same rule after shrinkable-slot properties were inserted. This is classified as `validation_tool_defect`. The P4 assertion now requires both the body token and `max-width/min-width` slot constraints and includes a negative test; all 11 guard tests and the direct guard pass, without another product-source change.

## Boundaries and rollback

- Save, approval, permissions, role matrix, database, fixture, module upgrade, release, deployment, and publication were not tested. Browser samples are read-only or unsaved interactions.
- No P1 XML, business section, field order, shell, palette, activity tab, Dialog/Drawer lifecycle, or low-code runtime changed.
- `ScFormField` help/error association remains a separate future P0 interaction task.
- Roll back in reverse order: `85b05110` → `244cf29d` → `d63a1dbb` → `67301212`. No business-data rollback is required.

## Freeze policy

This report, its translation, the PR draft, and generated evidence are committed before freeze. Afterward, Quick runs exactly once and independent review must prove the final candidate differs from `85b05110…` only by P4 documents/generated evidence. The candidate will not change merely to backfill SHAs or results.
