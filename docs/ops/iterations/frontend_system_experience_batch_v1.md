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

### Follow-up: route-owned page titles

- Baseline `c79e2e6bd87afcac4885b0897780c54dc6947265`, fingerprint `17cdcd8e42da9a3470a6ef0feb84beae24463ea427ec012c9c163490cf42c884`.
- Real defect: payment collection to `/my-work` showed work items but retained payment title in h1, breadcrumb and document title. The departing ActionView could publish using the already-updated shared route before deactivation.
- P0 ActionView publication now requires active action route plus matching instance action/menu key. Reuses existing route-runtime ownership; no routing or permission change.
- Existing retention test entry now covers 9 ownership cases, including the pre-deactivation race against work/home/form destinations. State/dashboard tests, page-identity 23+12 assertions and guard, strict typecheck PASS.
- Runtime after reload and a fresh payment-list to My Work transition: `/my-work`, h1 and document title are 我的工作; identity source product-fallback; 390px document equals viewport. Four existing work items remain visible; no business action executed.

### Follow-up: My Work visual structure and keyboard access

- Baseline `304369fe73009503f1912e9fc44d537915f1fc8f`; fingerprint `e582a71cf94c65871092856d721ce5717570a43237bce66b79f8cb175b87e0af`.
- P0 generic work-workspace presentation now uses ScButton metric appearance for actionable counts and existing ScCard record appearance for work items. Removes nested ScPanel borders/padding. Counts adapt to available sections; selected state uses a single border/subtle fill and aria-pressed. Keyboard focus uses one 2px outline, no additional shadow.
- Filter controls use existing form-field appearance. The adapter now applies the form-height token to the actual TDesign input/select control; workspace mobile token is 44px. Desktop controls measure 36px, mobile controls 44px.
- Real `/my-work` browser: 4 items to filtered empty with keyword retained, clear restores 4; initiated section shows authoritative zero state, then returned to todo. At 320/390/1088px document width equals viewport. Work cards contain no nested cards; original data facts/actions remain. Tab focuses the next metric with visible 2px outline and computed box-shadow none.
- Registered primitive adapter (46 components, 25 tests), page-pattern parity (8 tests, 13 surfaces), strict typecheck and diff whitespace PASS. Browser error log explicitly empty. No business action invoked; viewport restored.

### Follow-up: homepage scrolling and runtime state acceptance

- Baseline `0b2628083a4f831525277d4289e1792e517a82e9`; fingerprint `a8cad6ca79b9831ee9bf9555eb828c7907f8e8d9cc3ff30bc9726b9f42c5a781`.
- Opened `/s/workspace.home` in the original authenticated tab, resolving the prior homepage access gap. Current counts: todo 4, initiated 0; first 3 tasks previewed with authoritative amount/state and work entry. Desktop 1088px and narrow 320px inspected.
- P0 shared visually-hidden utility: static absolute coordinates on status/money labels inside the home scroller enlarged the document to 897px at an 844px viewport, creating a second scrollbar. Anchoring hidden labels at top/left zero keeps their accessible text and reduces document height to 844px and width to 320px. My Work also has document height equal to viewport.
- Targeted parity 8 tests / 13 surfaces and state/dashboard checks (including 9 action identity ownership cases) PASS. Diff whitespace PASS.
- Real refresh observation: temporarily paused an existing list data-read request through browser developer controls. The list retained its 70-record content with busy state and 正在刷新数据; it did not blank the existing list.
- Real first-entry observation: paused 2 reads during activity navigation to income contracts. ProductLoadingSkeleton announced 收入合同，正在载入数据; decorative ScSkeleton had aria-hidden=true. With prefers-reduced-motion emulation, sampled skeleton elements and pseudo-elements had animationName=none. All interception/media overrides cleared immediately afterward. Whole-page navigation throttling was not used as loading-layout proof.
- Real error recovery: failed exactly one my.work.summary read in the browser (InternetDisconnected, no backend/business mutation). My Work displayed role=alert, 当前无法读取工作事项，请检查网络后重试 and an enabled retry button. At 390px retry measured 44px. Retrying normally removed the error panel and restored 4 items. Explicit browser error log returned empty afterward.
- These observations close basic loading, reduced-motion and retry runtime gaps. Suggested-action feedback remains unexercised; no continuous layout-shift metric or release-wide certification is claimed. Network latency, request interception, media override and viewport were restored.

### Follow-up: homepage tab state and theme sampling

- Baseline `204f2921940e1e71bc34380692831c52654333e1`; fingerprint `f43cbfb95adf308d11d4a9b8b81a6513f976c3e28a550587875410a407b4dab8`.
- P0 AppShell supplies an empty displayed activity key on home/scene-home, which intentionally do not register activity pages. Stored active-page identity and dirty-navigation safeguards are unchanged. Real homepage now has zero pressed titles and zero vendor active tabs; clicking My Work returns `/my-work` with exactly its title pressed.
- Existing state/dashboard suite and strict typecheck PASS; diff whitespace PASS.
- My Work at 390px: business-soft and accessible-contrast inspected, no document overflow; metric selection and 44px filter controls remain clear. Enterprise-neutral restored.
- New confirmed gap: prefers-color-scheme changed to dark while the UI still showed 跟随系统, but the page stayed light. Source theme.ts reads the system preference only when applyTheme runs; no change listener exists. Dynamic system-theme following is the next P0 batch. Temporary media override and viewport restored; no permanent browser setting changed.

### Follow-up: live system theme and scene inheritance

- Baseline `08a207fcf8d45cd74972debb6f642a5fec82e7e7`; fingerprint `a6c6a428b55258f28b4634d3afe3756592a6fa8ebaa79f8f27aa027878ab0f16`.
- P0 theme module now subscribes to system preference changes for the mounted shell. It updates only system mode; manual light/dark remain authoritative. Shell unmount removes the listener. Existing theme-profile gate now runs the real transpiled module through 9 runtime assertions (following, manual override, profile preservation and disposal).
- Dark detail sampling exposed a second issue: SceneUiProvider injected fixed light colors, overriding vendor variables underneath otherwise correct global dark tokens. Provider color aliases now consume semantic tokens, retaining palette values as standalone fallbacks. Density/radius and contract field/action structure are unchanged.
- Actual system preference change: My Work resolves system/dark without reload; card background rgb(17,24,39), text rgb(249,250,251). Manual light stayed light through another system dark change.
- Actual payment detail 754: previously white task/context/list surfaces with nearly unreadable text become dark surfaces with light text; application amount 10,000, completed state and current-task facts visible. Desktop and 390px checked; narrow document width/height equal viewport, zero white ScCard panels.
- Restored system mode, enterprise-neutral, light system preference and original viewport. Explicit browser error log empty. No business action or data write.
- Registered checks PASS: theme runtime 9 assertions and 3 profile guard, scene bridge 38 cases, canonical form presenter 142 cases, boundary tests 13, feature flags 7, strict typecheck and diff whitespace.
- Next: unsaved-leave interaction without saving business data, browser enlargement/reflow, and consolidate the matrix into current results rather than treating historical pending rows as current truth.
