# FE-SYSTEMIC-CONVERGENCE M7：390/1440 中心旅程对等

## Boundary

- Formal Product Layer: P0 platform kernel product
- Layer Target: responsive parity and representative business journey continuity
- Module: shell, workspaces, collections, forms, overlays and navigation
- Contract V2, ACL, backend semantics, database and deployment are excluded

## Journey Selection

Ten journeys will be selected from existing governed routes and business-entry
assets. The selection must cover:

1. role home
2. my work
3. collection list
4. record/form detail
5. create form
6. workflow actions or reasons
7. relation selection and return
8. analysis/dashboard
9. configuration surface
10. unauthorized or denied surface

## Validation

- Negative closure candidates: 4 observed; 2 eligible for runtime negative checks.
- 1440x900: 10/10 selected entries completed, zero per-entry failures and zero
  Console errors. The only matrix problem is an authority-coverage limitation
  for one entry.
- 390x844: the same 10/10 entries completed after extending the table detector
  to recognize the product's `CollectionMobileRecordRow`; zero per-entry
  failures and zero Console errors. The same single authority-coverage
  limitation remains.
- Presentation coverage: 6 table, 3 create form, 1 hierarchical worksheet.
- Evidence:
  - `.runtime/m7-matrix-1440-v3/summary.json` SHA-256
    `39931efcf42daab59156d8c85918d3dad042d9ff473a3716c2ea88f22e5708a0`
  - `.runtime/m7-matrix-390-v3/summary.json` SHA-256
    `80224f9116de05ecacd778f91ea16c760232c1509a5d5aa11c3a3473a5fd1c3c`
  - `.runtime/m7-matrix/negative_closures.json` SHA-256
    `09398ae01c7622a09b94325786962b6c4a870c3f682a60029163627edf95a97c`

## Separate P1 Finding

During the first candidate selection, `demo_role_pm` had a capability closure
disjoint from the declared groups of:

- `smart_construction_core.action_sc_expense_claim_reimbursement_request`
- `smart_construction_core.action_sc_expense_claim_advance_fund`

but still received both actions in released navigation. This is a navigation
authority defect outside M7's approved frontend/ACL boundary. It must be fixed
in a separate P1 navigation-authority batch. Evidence:
`.runtime/m7-matrix-1440-v2/summary.json` SHA-256
`18941d7b0ffcfa039f048b3578de1f09ff675a0813f21ccc31a58cc595dc911c`.

The M7 parity sample excludes those two leaked entries and uses 10 other
released entries held by the acting principal.

## Result

Responsive parity verification completed for ten center journeys. The separate
P1 navigation leak prevents declaring overall permission convergence complete.
