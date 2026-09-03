# P1 Settlement Terminal Fact Immutability — Batch-G

## Boundary

- Entry HEAD: `0fdc129d675efc27209028828d2e53dabea2d956`
- Entry fingerprint: `be361b8616483072c0359e8d3d99a904a8742ad0d03dd01d1ce4737a03d77f20`
- Formal Product Layer: P1 construction industry standard product
- Layer Target: `smart_construction_core` settlement and payment fact models
- Standard vs User-Specific: construction-industry standard settlement semantics
- Why Here: settlement terminality, payment reservation and correction boundaries are construction commercial facts
- Why Not Elsewhere: the frontend cannot enforce fact integrity; P0 cannot own construction semantics; P2/P3 cannot override the standard; P4 may verify but cannot own the model
- Blast Radius: settlement header/detail lifecycle, payment submission locking, existing settlement test fixtures; no public frontend or startup contract change

## Single objective

Make approved, completed and cancelled settlement facts immutable and non-deletable, while serializing settlement cancellation against every active payment relation.

## Model freeze

1. A settlement starts in draft. Runtime callers cannot create a non-draft settlement or write its state directly.
2. State transitions are performed only by model actions using a module-private object authority and a locked settlement row.
3. Approved, completed and cancelled headers reject economic writes and deletion. Only note and attachment annotations remain writable.
4. Detail creation, mutation and deletion are rejected once the parent is approved, completed or cancelled.
5. Settlement cancellation and payment submission lock the same settlement rows in sorted order.
6. Submitted, approved or completed payments block cancellation whether linked on the payment header or historical outflow detail.
7. A cancelled settlement cannot support a new payment submission.
8. Integrity checks use narrowly scoped elevated aggregation against known settlement IDs, so caller record rules cannot hide blocking payment evidence.
9. The class has one canonical `create()` implementation; the shadowed dead implementation is removed.

## Verification evidence

- `make verify.workspace.worktree.guard`: PASS, 17/17.
- Governed `local.dev` incremental module upgrade: PASS through `17.0.0.156`, including demo authority verification.
- `p1_settlement_fact_immutability_v1`: PASS, 4 methods / 6 Odoo test stats, 0 failed and 0 errors.
- Impacted state/finance regression: PASS, 86 methods / 92 Odoo test stats, 0 failed and 0 errors.
- Full `sc_gate`: PASS, 339 methods / 435 Odoo test stats, 0 failed and 0 errors.
- Static business-fact audit unit: PASS, 15 tests.
- Business-fact model standard: PASS, 372 models and 36 projections with zero implementation gaps.
- Native Odoo `/web` write journey remains unavailable because the registered P4 target does not exist. No hand-built runtime command is accepted as substitute evidence.

## Rollback

- Batch-G is isolated from the later contract/change journal, budget authority and native-access batches.
- Revert the Batch-G commit to restore the prior runtime behavior. No schema downgrade or destructive database command is required.
- Existing terminal records are not rewritten by this batch.
