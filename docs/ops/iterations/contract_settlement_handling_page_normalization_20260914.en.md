# Contract Settlement Handling Page Normalization (2026-09-14)

Chinese: [contract_settlement_handling_page_normalization_20260914.md](contract_settlement_handling_page_normalization_20260914.md)

## Objective and boundary

- Single product result: the formal income- and expense-settlement entries present project, contract/counterparty, and settlement basis before settlement lines, amounts, handling notes, and downstream traceability.
- Baseline: `origin/main@c616b652fa2b7364a5f6629c56750874c5dd6113`; branch: `codex/contract-settlement-page-normalization-v1`.
- P1: `smart_construction_core` owns authoritative income/expense sections, field membership, line-column order, and placement of the existing attachment entry.
- P0: `smart_core` only associates explicit anchors with one unambiguous structure role; the shared frontend consumes parent-record modifiers, selects the actually visible relation occurrence, and keeps same-name fields in different business regions distinct.
- P4: focused tests, read-only/unsubmitted browser evidence, generated evidence, delivery documents, and final gates.
- Excluded: settlement calculations, amount semantics, save, approval, permissions, historical snapshots, business data, fixtures, contract changes, payment, invoicing, the general workbench, and low-code features.

## Why the existing contract capability did not cover settlement

| Chain | How contracts were covered | First settlement divergence | Repair to the existing mechanism |
| --- | --- | --- | --- |
| P1 structure | Native business containers had stable anchors and fields mapped to explicit sections | Settlement policy had field membership, but native containers had no explicit association with policy groups; the assembler annotated fields only, after which the task floorplan reclassified them by field type/editability | P1 declares `data-sc-form-structure-group` only on authoritative business groups. P0 stamps the container only when an explicit anchor, explicit group name, and exactly one descendant structure identity agree; layout-only and ambiguous groups fail closed and remain untitled |
| Parent-dependent columns | Generic modifier parsing/evaluation already existed | one2many rendering used the static column list and did not project evaluated `invisible` / `columnInvisible` against current parent form values | Reuse `one2manyEffectiveColumn` to derive reactive visible columns from current parent values; changing the parent reevaluates rather than permanently hiding a column |
| Repeated relation occurrences | Navigation already limits itself to presentable fields | Global field-level de-duplication could choose the wrong tag/table occurrence in one region and incorrectly merge the same field across two valid regions | Filter invisible occurrences first; choose within one region using a generic deterministic structured-subview/one2many/tag score; scope identity to the nearest explicit business anchor or structure slot/group, preserving distinct regions |

No settlement model/field special case, duplicated floorplan, or forced `presentationMode` was added.

## Product result

- The formal income entry resolves `settlement.income`; the formal expense entry resolves `settlement.expense`, with expense defaults, category, and “Project and Supplier/Subcontractor” terminology kept separate.
- The shared native view now reads “Project and Contract Counterparty → Settlement Basis → Settlement Lines and Amounts → Handling Notes”; populated execution, invoice, payment-request, adjustment, purchase-order, and system sections remain collapsed and navigable.
- Line identity, quantity, unit price, amount, and application facts precede source contracts. The model has no unit field, so none was invented.
- `contract_id` and `general_contract_id` remain mutually conditional on `parent.contract_source_kind`, including unsaved parent-value changes through the same modifier evaluator.
- `attachment_ids` has one Handling Notes ownership and reuses its existing widget/authorization; no upload capability or data migration was introduced.
- Purchase-order tag/table occurrences in one region yield one actual target; the same field in distinct authoritative regions retains distinct targets; all-hidden occurrences make no dead link, while non-empty collapsed sections remain navigable.

## Amount facts and boundary

| Field | Current definition/source | Treatment in this batch |
| --- | --- | --- |
| `amount_total` | stored compute summing `line_ids.amount` | Existing label, value, and calculation retained |
| `settlement_amount` | independent stored money field without a compute; read-only after approve/done/cancel | Displayed in the same amount region, but not asserted to be the same stage or canonical amount |
| `submitted_amount` / `approved_amount` | stage-specific submitted and approved facts | Values, labels, and read-only conditions unchanged |

The sample showing “Settlement Amount ¥0.00” beside “Amount Total ¥1,000,000.00” is not inferred to be a calculation defect. Stage meaning and primary-amount selection remain a separate product decision.

## Validation and evidence carry-forward

| Layer | Entry/evidence | Result |
| --- | --- | --- |
| L1 | `make ci.local.iteration` | PASS, 16 tests |
| L1/L2 | `make verify.frontend.native_section_navigation.unit`, `make verify.frontend.collection_view_semantics.unit`, `make verify.frontend.typecheck.strict` | PASS; covers section fidelity, parent false/true/value change, repeated occurrence in one region, cross-anchored regions with identical field semantics, distinct unanchored semantic child regions, all hidden, and collapsed-with-content; root iteration explicitly passes only the node and cannot leak `forEach` index/array arguments |
| L2 | `TestPaymentSettlementComponentProfile` and focused P0 contract tests | PASS; nine P1 tests and non-zero P0 focused coverage assert category, structure identity, attachment ownership, line order, and parent modifiers |
| L3 | Existing governed `local.dev` incremental upgrade and health | PASS; reused `sc-local-dev/sc_dev_demo/18081`, creating no environment or data |
| L4 prior human samples (not the final gate) | Income/expense light, dark, click-position, and focus summaries under `contract-settlement-*-a99f5da1` | Human product review accepted them and summaries pass with zero writes; because their directories lack before/after full fingerprints and artifact bindings, they are diagnostic/human-review material rather than final L4 identity evidence |
| L4 final product source: expense create dark | `/home/lidefend/workspace/sce-offrepo/artifacts/playwright/contract-settlement-final-e0d844cd-create-dark/evidence-binding.json` | At 1088×791 and 390×844, all five visible sections per viewport resolve uniquely; before/after full fingerprints are byte-identical and hashes bind summary plus six screenshots; pass, zero writes, zero errors |
| L4 final product source: expense read-only navigation | `/home/lidefend/workspace/sce-offrepo/artifacts/playwright/contract-settlement-final-e0d844cd-navigation/evidence-binding.json` | All 11 desktop and 12 mobile visible sections have `targetMatchCount=1` and stable targets below sticky surfaces; before/after fingerprints are identical and seven artifact hashes are bound; pass, zero writes, zero errors |
| L5 | `make ci.delivery.freeze.prepare`, one final `make ci.local.quick`, independent review | Recorded after freeze in off-repository exact-head evidence; this tracked document will not change to backfill results |

From approved income sample `a147c7ea…` to shared expense candidate `a99f5da1…`, product sections and field facts were not rearranged; income/light conclusions remain within their human-review boundary. Independent review produced product source candidate `e0d844cd…`, adding explicit-business-anchor priority and root-`forEach` argument isolation. Both formal dark L4 runs bind `e0d844cd…` with before/after full fingerprints and artifact hashes. The final candidate may differ only by P4 documents/generated evidence; independent review must prove P0/P1 byte identity and bind both source and target fingerprints.

The old dark focus probe first used the nonexistent `.o2m-readonly-card` selector and failed before creating passing evidence; it is classified as a `validation_tool_defect`. After inspecting the public DOM class, the temporary probe used `.o2m-readonly-row` without changing product or repository tooling. Its later summary is retained only as human-review material, not the final L4 identity gate.

## Known limits, risk, and rollback

- The governed expense dataset has no draft, so expense edit mode is uncovered and no fixture is created. Prior income sample evidence is carried; income edit is not rerun here.
- Real save, approval, amount computation, all-role, and historical-snapshot acceptance did not run. Browser work was read-only or unsubmitted, with zero recorded writes.
- Empty period values and amount differences remain sample/product-definition boundaries; no business record changed.
- P0 risk is limited to explicit unambiguous container-role propagation, dynamic parent-modifier column projection, and relation occurrence selection. Counterexamples prove that undeclared pages keep their defaults, ambiguous structures are not stamped, and distinct regions are not merged.
- Rollback order: P0 navigation/dynamic-column consumption, then P0 container-role propagation, then P1 policy/native-view organization. No database rollback is needed.

## Next step

- Review and commit the pre-freeze documents and generated changes to form one clean exact-head candidate.
- Run Quick once on that candidate and bind independent review to the same HEAD/tree/full fingerprint, then await remote-delivery authorization.
