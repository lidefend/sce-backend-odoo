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

Status: completed on the shared backend candidate.

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
- At candidate `3086e339ea3009244ee2597a9632aaa94e372bd4`, the backend sample reports 15 assertions and three schema-valid entries; the browser journey reports one created record and one cleaned record with no failed intent.

## Final local verification

- `make ci.local.iteration`: pass on `3086e339ea3009244ee2597a9632aaa94e372bd4`; log `.runtime/agent-runs/CLOSE-03-PROJECT-INTAKE-DRAFT-RESTORE-20261119/ci.local.iteration.3086e339e.log`.
- Frontend affected receipt: `verificationPassed=true`, `unmappedPathCount=0`; non-zero lint, strict typecheck and affected test families executed or reused under the registered input scope.
- `make ci.delivery.freeze.prepare`: pass; all content-bound generated evidence is current; log `.runtime/agent-runs/CLOSE-03-PROJECT-INTAKE-DRAFT-RESTORE-20261119/ci.delivery.freeze.prepare.3086e339e.log`.
- Raw intake samples: `.runtime/agent-runs/CLOSE-03-PROJECT-INTAKE-DRAFT-RESTORE-20261119/intake_autosave_samples/`.
- Browser summary and screenshots: `.runtime/agent-runs/CLOSE-03-PROJECT-INTAKE-DRAFT-RESTORE-20261119/browser_journey/`.
- Acceptance identity: database `sc_frontend_acceptance`, login `fixture_role_config_admin`, company `FE Company A`; backend `http://127.0.0.1:18082`, frontend `http://127.0.0.1:5175`.
- `construction.standard` and compatibility key `construction.preview` each expose 132 released entries with `RELEASED_FOUNDATION` maturity and zero preview-only menu rows.

## Completion boundaries

- Batch verification is locally complete once the generated-evidence commit is clean and frozen.
- Mainline integration remains pending until independent review, the current PR head's four required checks, and protected merge succeed.
- Deployment and product-delivery status remain unchanged; this batch does not deploy or claim a released product version.
- Known non-blocking external mismatches remain the cost-center XML identity guard, view-orchestration semantic annotation guard, and platform no-native synthetic fixture guard.

## Results

Local implementation and batch acceptance evidence are complete. The run remains `verification_pending` for exact-head independent review, PR checks and protected integration.
