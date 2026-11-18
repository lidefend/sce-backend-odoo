# CLOSE-03：项目立项新建输入恢复

## 运行身份

- Goal: `CLOSE-03-PROJECT-INTAKE-DRAFT-RESTORE-20261119`
- Branch: `feature/close-03-project-intake-draft-restore-20261119`
- Baseline: `c365db1eae1ae8c4e2efab649c609ea1aebd8a0b`
- Worktree: `/home/lidefend/workspace/sce-backend-odoo-acceptance-scope-20261109`
- Writer: one writer; BE-CLOSE-03 and FE-CLOSE-03 are serial stages on one candidate and one PR.

## 边界声明

- Formal Product Layer: P1 construction standard with a P0 Contract V2 transport/projection mechanism.
- Layer Target: project-intake local-draft policy, `runtimeContract.intakeAutosave`, and the shared create-form restore/save/cleanup runtime.
- Module: `smart_construction_core`, `smart_core`, `frontend/apps/web`, focused verification tools and this run record.
- Standard vs User-Specific: construction-product standard; not a customer preference or low-code experiment.
- Why Here: P1 owns the allowed project-intake fields and 24-hour policy; P0 owns the generic contract carrier; the frontend owns browser persistence and interaction mechanics.
- Why Not Elsewhere: the frontend cannot infer fields, expiry or recovery semantics; P2/P3 are not the source of the standard; no Odoo record is created while collecting local input.
- Blast Radius: released project-intake create, project-intake saved-record form, payment request create, and preview quick-create isolation.
- Product-surface promotion: all 40 entries previously classified as preview-only are promoted to standard release and capability maturity `RELEASED_FOUNDATION`; the compatibility `construction.preview` product key remains readable with the same released entry set, but no preview-only menu difference remains.
- Exclusions: attachments, binary values, unsaved x2many commands, workflow state in local drafts, edit-mode autosave, search, renderer, full-entry acceptance, deployment and product-delivery claims.

## 稳定基线门禁责任表

| Gate | State | Owner target | Reason |
| --- | --- | --- | --- |
| exact base/head identity | required | `make agent.run.resume` | always |
| owning module baseline coverage | required | registered `smart_construction_core` ORM baseline/full affected family set | P1 policy and fields change |
| existing affected test families | required | project-intake governance, contract assembly, create lifecycle/save/dirty tests | changed declaration and consumer |
| focused changed tests | required | new non-zero policy/storage/lifecycle tests | distinguishes correct from pre-fix behavior |
| contract/schema/consumer | required | V2 schema, assembler/runtime, native-action and frontend contract guards | producer and consumer change |
| frontend lint/type/build | required | registered frontend Make targets | TypeScript/Vue source changes |
| runtime/browser journey | required | governed project-intake browser entry | user-visible recovery behavior |
| remote required gates | required | exact-head PR checks | publication and merge |

## BE-CLOSE-03

Status: policy and Contract V2 projection implemented; real samples pending exact-candidate runtime.

Required declaration:

- `enabled` and create-only applicability;
- `scope` from the existing project-intake business scope;
- explicit allowed field descriptors with type, relation and value constraints;
- local storage mechanism, 24-hour retention, restore prompt semantics and policy compatibility version.

Entry boundaries:

- Standard released project intake: explicitly enabled after effective-form and field-right intersection.
- Quick project create: promoted to standard release and explicitly enabled with its own smaller allowed field set; it does not inherit the standard project-intake policy merely through model/create-mode matching.
- Saved project record: disabled.
- Payment request create: disabled.

## All-preview release promotion

Status: surface generated and focused guards passed; complete release-surface gate family and exact-candidate runtime readback pending.

- Every entry formerly marked preview-only is now released.
- Capability maturity is `RELEASED_FOUNDATION` for all promoted entries.
- The canonical release entry count advances from 92 to 132.
- `construction.standard` exposes 132 released entries.
- The compatibility `construction.preview` product key remains present with the same 132 released entries, while its product `state` remains `preview`.
- The quick project-create entry is therefore also standard-released and receives an explicit five-field local-draft policy instead of inheriting the nine-field standard project-intake policy.
- Runtime audit on the first candidate exposed persisted `construction.standard` still at 92 entries while `construction.preview` was 132. The maintained-policy synchronization intentionally does not overwrite existing rows. Migration `17.0.0.183` therefore adds only missing formal identities to standard and promotes rows explicitly still marked preview; unrelated operator edits remain untouched.
- Migration `17.0.0.183` ran on both `sc_dev_demo` and `sc_frontend_acceptance`. Post-migration runtime policy probe reports `construction.standard` and `construction.preview` both at 132 menu/capability entries, 119 delivered menu leaves, and zero menu rows left in preview state for the promoted set.
- The broader platform runtime probe still fails its pre-existing empty-native-navigation counterexample: active policy menus are emitted in the synthetic no-native branch, and the probe only authorizes inactive/action-only carriers without native facts. The same condition predates this migration; it is recorded rather than misreported as a policy-count failure.

## FE-CLOSE-03

Status: read-only preparation started after backend registration.

Consumption points under review:

- `ContractFormPage.vue` draft identity and policy projection;
- `intakeAutosave.ts` expiry, type, corruption and storage-error behavior;
- `useRecordPageLifecycle.ts` defaults-before-restore ordering;
- `useRecordFormActions.ts` post-create cleanup and attachment partial failure;
- existing dirty, onchange, request-generation and form-instance identity tests.

## FE results

- Intake policy/storage runtime: 24 focused cases pass, including identity isolation, 24-hour expiry, corrupt/incompatible payload, storage quota failure, false/0/empty preservation, stale-token cleanup refusal and restore/discard.
- Default hydration/create/dirty/occurrence families pass.
- The acceptance journey exposed `ONCHANGE_SPEC_INVALID`: the client listed `validation_status` in `changed_fields` while omitting it from values. The common onchange request now filters changed names that are absent or undefined in the serialized values payload; a regression case covers the native intake shape.
- Browser journey passes: save, refresh, restore prompt, typed/relation restore, local validation failure without create, corrected real create/readback, draft cleanup, new-form absence, payment-create isolation and saved-record isolation. The created synthetic project was removed through the governed unlink intent and readback returned zero.
- The acceptance backend sample and browser journey were rerun at `337ae1e4d5282a0636d14ae0dd758378333647a7`; both passed.

## Results

Run registered. No product implementation or acceptance result is claimed yet.
