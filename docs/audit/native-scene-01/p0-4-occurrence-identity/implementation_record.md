# NATIVE-SCENE-01 / P0-4 · Native Occurrence Identity

Status: batch implementation and targeted verification passed; mainline integration pending.

Date: 2026-11-17

Baseline main: `7dc7f393aafd3ccd4e35fed45d75108993155324`

## 1. Boundary

- Formal Product Layer: P0 platform kernel product.
- Module: `addons/smart_core` and the generic Contract V2 decoder.
- Objective: publish one deterministic native View and occurrence identity shape
  for Form fields/containers, List columns and native buttons.
- Exclusions: Parser/AST rewrite, Renderer redesign, professional view
  implementation, business semantics, persistent models and deployment.
- No business database or business configuration was modified. ORM verification
  used only the governed disposable `sc-local-test / sc_test` profile.

## 2. Producer

The shared producer is `addons/smart_core/core/native_view_occurrence.py`:

- `build_native_view_identity()` at line 74 publishes model/type, resolved View
  ID, XMLID, `viewContentHash`, `viewStructureKey` and
  `crossEnvironmentStable`.
- `build_native_occurrence_identity()` at line 130 publishes kind/name/locator,
  occurrence index, deterministic `occurrenceKey`, source position, provenance,
  authority and Domain/Context/options evidence.
- `viewContentHash` excludes the runtime database View ID. Identical XMLID and
  effective arch therefore retain the same content hash across databases.
- Display copy does not enter the structural skeleton. Label edits change
  `viewContentHash` only; structure and occurrence keys stay stable.
- XMLID-backed identities are marked portable. Runtime-ID-backed identities are
  explicitly non-portable instead of being presented as native-stable facts.
- `occurrenceKey` depends only on XMLID-or-View-ID base identity, kind, name,
  native locator and occurrence index. It never depends on display copy,
  source-position ordering or a frontend-generated random value.

## 3. Assembly

`PageAssembler` publishes the resolved View identity beside each parsed View at
`addons/smart_core/app_config_engine/services/assemblers/page_assembler.py:760`.

`addons/smart_core/core/unified_page_contract_v2_assembler.py` then:

- resolves the active View from the explicit request or `head.view_type`
  sequence at line 1413, so a real Action dispatch no longer defaults a Tree
  request to Form;
- binds the same identity shape to Form field nodes, containers, field widgets
  and native buttons at line 840;
- canonicalizes native locator/index/source-position fields into camelCase
  strict layout fields at line 2512;
- preserves all duplicates of a same-name List column and exposes them as
  `listProfile.columnOccurrences` at line 996;
- merges normalized occurrence identity into existing button evidence instead
  of overwriting button type/id/string/title/help/confirm/region facts;
- omits `nativeIdentity` entirely when no native occurrence exists, rather
  than publishing an empty object that looks authoritative.

The contract protocol moves atomically to `2.4.0`. The Schema SHA256 is
`82bbf586ef1ff56433a22264e62baac57c0400dedebc5098d8a7ea6c51476a66`, and the
assembled-contract cache generation moves to `v67`.

## 4. Strict Consumer

The public Schema adds strict definitions for:

- `nativeOccurrenceIdentity`
- `nativeOccurrenceSourceAuthority`
- `nativeOccurrenceBehavior`
- `listColumnOccurrence`

Form nodes, widgets, native buttons and List column occurrences now reference
those definitions. The frontend decoder:

- strictly decodes identities at `frontend/apps/web/src/app/contracts/v2/schema.ts:651`;
- strictly decodes List occurrences at line 1350;
- validates page-level View consistency, Action-bound View availability,
  occurrence-key uniqueness, XMLID portability, owner/widget identity equality,
  field/column names and Domain/Context/options evidence at line 2648;
- accepts legacy 2.0–2.3 action identity envelopes for compatibility, while
  native layout occurrences and all new 2.4 identities fail closed;
- never generates an occurrence key or fills missing native identity.

`frontend/apps/web/src/app/contracts/v2/client.ts:112` advertises the `2.4.x`
protocol alongside the preserved compatibility ranges.

## 5. Verification

Passed on the current dirty candidate:

| Layer | Entry | Result |
| --- | --- | --- |
| L1 pure | `make verify.native_occurrence.contract.unit` | 9 tests passed |
| L1 schema | `make verify.unified_page_contract.v2.schema` | schema guard passed; 4 tests |
| L1 assembler | `make verify.unified_page_contract.v2.assembler` | 4 synthetic source projections passed |
| L1 lifecycle | `make verify.backend.contract_lifecycle.authority` | score 100, 8/8 dimensions |
| L1 frontend | `make verify.frontend.contract_record_action_state.unit` | 38 cases passed |
| L1 frontend | `make verify.frontend.contract_v2_occurrence_authority.unit` | passed |
| L1 frontend | `make verify.frontend.contract_field_occurrence_identity.unit` | passed |
| L1 frontend | `make verify.frontend.typecheck.strict` | passed |
| L2 ORM | `make verify.native_occurrence.contract.orm` | 3 non-zero disposable Odoo tests passed |
| L2 iteration | `make ci.local.iteration` | 26 affected targets passed; exact before-freeze candidate |
| V2 integration | `make verify.unified_page_contract.v2.professional_backend` | full UPage V2 static/contract aggregate passed |
| Governance | `make audit.verification.lane_coverage.check` | within frozen baseline |

The ORM receipt on the last isolated run is
`.runtime/test-baseline/1794855003107430908/receipt.json`; earlier runs remain
as historical failure/repair evidence rather than being overwritten.

## 6. Failure Classification and Repair

- `validation_tool_defect`: the first fixture used a non-existent
  `res.partner.action_confirm`; the fixture now uses `action_archive`.
- `product_defect`: the real dispatch chain ignored `head.view_type`, retained
  snake_case container locators, dropped List occurrences and replaced button
  evidence. These were fixed in the generic producer/assembler.
- `baseline_evidence_defect`: the render-authority matrix had not declared the
  new identity fields, and a future-version test still expected 2.3 to be the
  ceiling. The generated matrix and version expectation were refreshed.
- `validation_tool_defect`: the local incremental planner did not route the new
  producer/test paths or wire the new Make targets. The planner mapping and
  verification lanes were updated; the coverage audit passes.
- `product_defect`: the first remote backend shard exposed two consumers that
  still read the legacy snake_case identity fields. Native button backend
  identity was collapsing to the generic button key, and Pivot/Graph assembly
  attempted to resolve Form/List occurrence identities. The producer now reads
  both camelCase and legacy locator/index fields, and occurrence binding is
  explicitly limited to Form/List views.
- `product_defect`: a subsequent admin-visibility shard exposed legacy
  `viewIdentity` metadata that has no P0-4 `viewType`. The assembler now skips
  that legacy carrier instead of claiming it as a native occurrence identity;
  a focused regression test binds this distinction.
- `product_defect`: a real `project.project` browser load exposed nested Form
  widgets inheriting their container occurrence instead of their owning field
  occurrence. The generic assembler now resolves each widget through
  `ownerContainerId`, publishes only its field identity, and omits the carrier
  when no owning field identity exists.
- `product_defect`: the strict frontend Decoder compared every widget identity
  with its current row identity. For direct field widgets carried by a native
  container this rejected the valid field occurrence because it differed from
  the container occurrence. Widget equality is now enforced only on field-owned
  rows; container-carried direct widgets retain their own field identity.
- `product_defect`: handler finalizers could merge legacy Action rules or drop
  List column occurrences after the assembler's initial identity pass. The
  final response boundary now rebinds native occurrences once from the same
  deterministic producer. The assembled cache advances to `v65`.
  A second verification pass placed the rebind after all guidance/status
  projections at the final response boundary.

The repair was verified with:

- `make local.test.test MODULE=smart_construction_core TEST_TAGS=product_reports`
  — 2 tests passed;
- `make local.test.test MODULE=smart_construction_core TEST_TAGS=p1_payment_request`
  — 63 tests passed;
- `make local.test.test MODULE=smart_construction_core TEST_TAGS=payment_settlement_component_profile`
  — 7 tests passed;
- the focused native occurrence ORM test now also asserts the stable
  `native_button:...` backend identity and ignores a legacy identity carrier
  without `viewType`.

## 7. Coverage Limits and Next Step

- L3 browser consumption and L4 real-role business journeys were not re-run in
  this P0-4 batch. The real ORM Action → View → Contract chain is covered, while
  browser behavior remains a later integration/acceptance concern.
- No Parser/AST rewrite, professional Renderer or scene-composition expansion is
  included.
- Batch status: implementation and targeted verification passed.
- Mainline status: pending freeze, independent review, PR and required CI.
- Deployment and user acceptance: not performed.

Next exact step: run `make ci.delivery.freeze.prepare`, review generated
evidence, commit the P0-4 candidate, and publish it through the governed PR
entry.
