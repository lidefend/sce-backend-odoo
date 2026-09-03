# P1 Business Fact Authority Inventory — Batch-D

## Identity and boundary

- Audit HEAD: `aa182665401640d3bde058c61135bf49c389d9e5`
- Formal Product Layer: P1 construction industry standard product
- Layer Target: `smart_construction_core` business models, native Odoo surfaces, security and ORM behavior
- Standard vs User-Specific: common construction-industry fact semantics
- Why Here: project funding, payment allocation, contracts, site execution and finance recognition are industry facts
- Why Not Elsewhere: no industry meaning belongs in `smart_core`, frontend inference, customer configuration or P4 replay tooling
- Audit mode: read-only; no database or runtime mutation

## Result

The registered model audit passes structurally, but field presence is not sufficient evidence of authoritative facts. Three independent read-only reviews found no S0 issue and identified the following S1 families.

### Project funding baseline and actual allocation

- `project.funding.baseline` can be created or directly written into `active`; one-active-per-project is a lock-free `search_count` check.
- Active or closed baseline identity and amounts, and their plan lines, remain editable after actual allocations exist.
- Plan-line totals, baseline cap, per-line allocations and per-payment allocations do not share one complete conservation boundary.
- `project.funding.actual.event.allocation` has no stable business identity, remains directly editable/deletable, and payment reversal requires deleting allocation history.
- There is no explicit plan version, effective/closed date, plan period, allocation period or unresolved-history state.
- Existing tests are mostly structural and do not prove concurrent activation, concurrent over-allocation, terminal immutability, reversal evidence or query growth.

This is the selected next implementation slice because it directly governs both payment commitment ceilings and actual cash allocation, requires a real model upgrade, and can be accepted without frontend or contract changes.

### Canonical finance projection lifecycle

- `sc.finance.business.fact` currently projects non-final tax deductions and tender guarantees, so draft, confirmed-only or cancelled sources can appear as canonical facts.
- The projection audit repeats the same all-row predicate and therefore certifies the wrong lifecycle.
- Contractor-responsibility summaries can add different source currencies while displaying `MIN(currency_id)`.
- Self-funding refund, invoice ceiling and active funding baseline checks contain check-then-write races.

This remains an independent later slice. It must not be mixed into the funding-baseline model upgrade because it owns different sources, projections and rollback boundaries.

### Native access and isolation

- `sc.construction.diary` has project-role ACLs but no project membership record rule.
- `sc.treasury.reconciliation` has finance/business ACLs but no company/project record rule and its final menu parent is inactive.
- `sc.general.contract` uses all-record role domains despite a required company.
- `sc.expense.claim` allows a business initiator to read/write all same-company claims without own/project-follower isolation.
- Invoice and tax entries are exposed to a role whose record rule is `id=False`.
- Outside the completed cost-ledger flow, major fact tests do not prove `load_menus`, active ancestry and real-role lifecycle together.

These are retained as separately acceptable security/native-flow slices. They are not compensating changes for the funding model.

## Selected next product slice

### Batch-E — Project Funding Baseline & Actual Allocation Authority v1

Required model result:

1. Stable baseline version identity, plan period and explicit activate/close lifecycle.
2. Project-row serialization plus a database backstop for one active baseline per project.
3. Active/closed baseline and line immutability; revisions use a successor baseline rather than rewriting history.
4. Four-level amount conservation: line plan vs baseline, line allocation vs line plan, payment allocation vs posted payment, and baseline allocation vs baseline cap.
5. Stable allocation identity and service-controlled create/correction/reversal; ordinary write/unlink denied.
6. Payment reversal preserves original allocation and records a reversing allocation so net authority becomes zero.
7. Only posted actual payment events enter effective allocation.
8. Unresolved history is explicitly quarantined; ownership, period and currency are never guessed.
9. Batch ORM behavior and concurrent activation/allocation have fixed query and lock-order evidence.
10. Native finance reader/user/manager journeys prove active menu ancestry, `load_menus`, action/views, permissions and lifecycle.

Blast radius is limited to `funding_baseline.py`, necessary `payment_ledger.py` collaboration, their P1 native views/security, versioned migration, focused tests and governance evidence. `project.cost.ledger`, contract execution position, invoice/receipt aggregation, custom frontend and runtime profiles are excluded.

## Validation and rollback

- Batch-D inventory evidence binds the clean Batch-C commit and three independent read-only audits.
- The next implementation must start from that exact committed baseline and use only governed `local.dev` targets.
- Every database-writing validation remains serialized.
- Batch-E is a separate commit rollback unit; schema evolution is forward-fixed through the governed module upgrade.
- The known missing P4 business-fact replay entry remains external and continues to block `make pr.push`.
