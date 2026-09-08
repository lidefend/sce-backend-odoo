# System frontend experience delivery matrix

Scope: shared frontend surfaces across the system, with representative browser evidence. Business contracts, permissions and state transitions remain authoritative. Local commits only; no remote publication or fixture mutation.

Baseline: `2d380e5b59e5d4ce8b34516424dc5aaad51abdb8` on `feature/frontend-page-experience-iteration-v1`.
Complete baseline fingerprint: `112758622e9a3dc6c1ce8437120cfe0f553760fcd7a8d7dc0a1268d14e003a39`.

## Acceptance matrix

| Area | Shared owner | Acceptance condition | Current evidence / outstanding work |
| --- | --- | --- | --- |
| Navigation | AppShell, ActivityPageTabs | Mouse/keyboard activate correct route; focus follows stable page key; Escape reaches main | Prior real payment-list/detail route and focus checks passed; wider page sampling in this batch |
| List layout | ListPage, ProductListHeader | One horizontal gutter and content surface; controls align; no document overflow | Prior desktop/320/390 checks passed |
| List recovery | ListPage, ScEmptyState | Query survives zero results; clear restores authoritative results | Prior 70 → 0 → 70 browser journey passed |
| Table access | ScTable, CollectionRowCell | Complete identifiers retained; record opens correctly; actual scroll region keyboard-accessible | Prior real record 754 and scrollLeft 0 → 40 checks passed; visible overflow affordance remains queued |
| Detail | ProductPageHeader, ObjectTaskPage | Summary, state, task and action remain readable; no field-span override | Prior readonly 754 desktop/390 checks passed; edit interaction not claimed |
| Loading | ProductLoadingSkeleton, ScSkeleton | One meaningful loading announcement; decorative skeleton ignored; reduced-motion respected | Shared implementation and targeted validation in this batch; timed layout continuity remains pending |
| Error / recovery | StatusPanel | Recovery feedback is visible without debug mode; busy action remains identifiable; narrow touch target usable | Shared implementation and targeted validation in this batch; no deliberate business failures |
| Workbench | DashboardPattern, home renderer | Meaningful task hierarchy; visible actions; no narrow overflow | Live sampling in this batch |
| Theme / zoom | semantic token bridge | Default and alternate theme preserve legibility and layout | Live theme sampling in this batch; zoom matrix remains pending |
| Hierarchical workspace | HierarchicalWorksheet, ProductListHeader | Search sizes align; selected scope/data preserved; filtered zero results distinguish from no data | Added after live income-contract inspection; browser recovery below |

## Batch execution

1. Audit the four existing pattern owners: collection, dashboard, task-form and workspace-form. Do not add another page framework.
2. Correct shared loading/recovery presentation and exercise registered state/header/primitive guards.
3. Inspect workbench, collection and detail in the current authenticated browser, including a narrow viewport and an alternate theme; restore the initial list and theme afterward.
4. Record exact passes, failures and untested conditions below. A shared component pass is not whole-system or multi-role acceptance.

## Boundaries

- P0: generic component rendering and access, no model/menu/customer special cases.
- P4: this matrix and delivery log only, no new verification entrypoint or runtime.
- Existing daily targets and local.dev runtime are reused. No module upgrades, database reset or full contract snapshot export.
- Readonly browser routes are used for this batch. No draft creation or payment mutation.
- Existing unrelated style-system line-count blocker remains separate; this batch is not a release qualification.

## Results

### Implemented in this batch

- StatusPanel publishes recovery-action feedback outside HUD-only markup, disables retry while the parent surface is busy, and uses narrow 44px recovery controls.
- ProductLoadingSkeleton marks decorative skeleton content hidden from accessibility; the primitive bridge suppresses skeleton animations under reduced-motion preference. Loading text remains available.
- ProductListHeader's fallback search now uses the same collection-search appearance and 36px/44px height token for input and buttons. Vendor control sizes remain in the adapter.
- HierarchicalWorksheet removes duplicate enclosing strokes, retains internal dividers, uses one label/value pair per row below 640px, and distinguishes query-zero results with a status announcement.

### Actual browser evidence on this candidate

| Page | Observed route | Result |
| --- | --- | --- |
| Data overview | `/a/602`, menu 329 | Readonly empty collection, clear no-data message, no create action; shared surface present; 1088px document has no horizontal overflow |
| Workbench items | `/a/859`, menu 465 | Two existing items rendered; neutral and accessible-contrast profiles inspected at 1088px; controls/text remain visible; neutral restored |
| Income contracts | `/a/609`, menu 660 | Distinct hierarchical workspace, 46 contracts; search input/button both 36px; outer header/body borders zero; query 46 → 0 displays 没有符合当前条件的记录 with role=status; clear restores 46 and empty keyword |
| Payment detail | `/f/payment.request/754` | DEMO-PR-FLOORPLAN-003, completed status and 10,000 amount visible after shared changes; no document overflow at 1088px |
| Payment collection | `/a/809` | Returned to original collection after sampling; no business write |

### Targeted checks

- State/dashboard: keyboard 11 cases; route identity 7; retained-page cases 7+8+2+2+3; 24 Python tests; state and dashboard guards PASS.
- Primitive adapter: 46 components and 25 tests PASS.
- Page pattern parity: 8 tests / 13 surfaces PASS.
- Hierarchical worksheet: 4 interaction cases and existing domain-tab assertions PASS.
- Strict TypeScript checking and diff whitespace PASS.

### Explicit remaining gaps

- Home `/s/workspace.home` in a supplemental tab redirected to login: that tab did not inherit the original tab's authentication. No credentials copied or login bypass attempted; homepage browser acceptance remains pending.
- A responsive override during cross-page sampling affected a different browser surface: original authenticated page still measured 1088px. This batch therefore does not claim narrow runtime acceptance for the newly changed hierarchical workspace, only the CSS implementation and targeted checks.
- Reduced-motion behavior and non-HUD recovery feedback have code/targeted-guard validation, not forced runtime error or OS-setting evidence. Timed loading-layout continuity remains pending.
- Alternate profile sampling covers one populated page, not all themes, zoom levels or roles. No WCAG-wide or whole-system certification is claimed.
- Edit/save/unsaved-change interactions, visible overflow hints and additional business-module samples remain in the queue.

### Follow-up: responsive worksheet and visible table scrolling

- Baseline `d324f993bc13185a57931956d4806feb26f55d46`; complete fingerprint `9b5715f9569565b322f2807fdbb40d47175bdf3c70a60a80c5910165f3a5b110`.
- Authenticated tab viewport control recovered. Income contracts at 390/320px: document width equals viewport; detail label/value grid measures 84+216 / 84+146px; search input/button both 44px at 320px. This closes the worksheet narrow-layout evidence gap above.
- P0 ScTable now shows horizontal browsing controls only when the rendered table exceeds its viewport. Resize handles extending outside a fitting table do not trigger the controls. Scroll/resize observers update direction availability and disconnect on unmount; existing topContent slot is preserved.
- Real 320px contract click moved scrollLeft 0 to 211; left button became enabled; left click restored the starting position. Desktop contract traversal reached the right edge (scrollLeft 2197.5, integer max 2197) and disabled the right button. Narrow controls measure 44px.
- Payment collection reuses the hint at 1088px; 1600px fitting table and 390px mobile cards hide it. No document overflow. Original viewport restored; explicit browser error log empty.
- Existing primitive adapter: 46 components / 25 tests PASS; worksheet: 4 interaction cases and domain-tab assertions PASS; strict typecheck and diff whitespace PASS. No business writes or remote operations.
- Offscreen activity-tab automation first scrolled its label into view without navigation; clicking the visible title reached the correct contract route. Do not classify this observation alone as a product navigation failure. Narrow tab-strip visibility remains under review.
