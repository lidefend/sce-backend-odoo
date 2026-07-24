# RC6 legacy AR/AP projection ownership decision

## Decision

`public.sc_ar_ap_project_summary` remains a physical table owned by
`smart_construction_core`. The selected strategy is
`C_WITH_B_DATA_PRESERVATION`: correct the ownership/orchestration design while
preserving the historical carrier and all of its data.

The frozen RC6 candidate
`fb1f2b5a6e93fb4d7865023e6cda2961848c3cb8` is superseded due to a legacy
projection compatibility defect. Its declaration and image are immutable and
are not rewritten.

## Evidence lineage

- Failed image:
  `ghcr.io/lidefend/sce-product@sha256:02edec2628b276834abd10ec3cc9ef96517fb499c6b0e8a60b19d59e3694fdeb`
- Failed rehearsal evidence SHA-256:
  `efe70143708f1d4287ee1075909b4c7535eec3c9c74ddaf6abf325816aeb271d`
- v1 evidence package SHA-256:
  `c0a737dea2c08e1b349c0b660f9f0ea64332ead899cc75ab01bb7db5bfd17743`
- normalized v2 evidence package SHA-256:
  `d951dfd99563f0c93c9f55207210b0188f3947c3a1c6d93cd8783889872f1de0`
- v2 parent lineage points to the v1 package. The v2 package changes only the
  evidence carrier; it does not recompute business facts.

The evidence proves:

- the relation was created by `smart_construction_core 17.0.0.61`, from origin
  commit `808115c7cfcdafe0e7ca6d9fb97a972713c38bb4`;
- deployed code at
  `6095e2013d64c06a5ea936addd35858959d2a28f` still rebuilt the relation from
  authoritative and legacy fact tables during registry initialization;
- the restored relation is an ordinary table with 12,328 rows;
- no exact external P2 owner, uninstall contract, or handoff contract is
  proven;
- the RC6 fallback was a zero-row typed view with incompatible column types;
- key, aggregate, null, company, and project semantics were not equivalent,
  and the historical data was not reconstructable by that fallback.

## Historical implementation and failure

The origin implementation defined the AR/AP business calculation from
contracts, receipts, invoices, treasury entries, legacy tax/surcharge facts,
supplier pricing, self-funding, and project fund-balance facts. Its business
key was project plus normalized counterparty identity. It calculated contract,
invoice, receipt/payment, tax, surcharge, self-funding, and balance metrics.

The deployed 17.0.0.61 implementation changed the object to a physical
`CREATE TABLE AS` carrier and rebuilt it with an unconditional object drop.
That retained business results but introduced object-identity, ACL,
dependency, concurrency, and availability risks.

Commit `5e7533aef0bda85f3fce1e29aa770e6e921f6efb` added
`SC_ALLOW_EXTERNAL_PROJECTION_HANDOFF=1` to one rehearsal profile. It did not
add an owner module marker, migration, provider readiness record, structure
contract, or evidence that an external module had taken ownership. The
generic optional-projection code therefore converted “handoff may be allowed”
into “handoff has occurred.” RC6 then attempted to replace the absent provider
semantics with a typed-empty view.

## Runtime ownership contract

The core model no longer calls the optional typed-empty view initializer. Its
initialization obtains a transaction advisory lock and:

1. preserves a known compatible physical table in place;
2. creates the core-owned physical schema for a genuinely absent relation;
3. does not convert even the obsolete zero-row typed placeholder; that state
   needs a separately proven, versioned ownership migration;
4. rejects unknown structure or relation kinds with schema, relation,
   relkind, calculated fingerprint, and stage.

The generic external handoff path now requires all of:

- module technical name;
- installed minimum version;
- provider/schema version;
- owner marker stored on the relation;
- relation contract version;
- exact structure fingerprint;
- readiness marker.

The environment switch merely enables validation. It is never proof of
ownership. Missing, incomplete, inconsistent, or uninstalled providers fail
closed. A future P2 handoff needs a separate versioned migration and must not
reuse this incident fix as authorization.

## Refresh and migration behavior

Migration `17.0.0.73` is transactional and idempotent. It preserves the known
legacy table and creates no same-name view. Unknown table structures,
materialized views, partitioned tables, foreign tables, and unexpected views
remain fail-closed.

The safe refresh primitive keeps the official relation identity. It computes
into a transaction-local staging table, validates row thresholds, null and
duplicate keys, business-key uniqueness, and project references, then updates
the official table in the same transaction. PostgreSQL MVCC keeps existing
readers on the prior committed contents; failures roll back the refresh. It
uses no `DROP TABLE`, `DROP ... CASCADE`, or `TRUNCATE`, and concurrent refresh
calls serialize on the same transaction advisory lock.

The historical calculation is not run automatically during registry startup.
That avoids silently recalculating 12,328 proven rows while the authoritative
refresh source/version is being governed. A reviewed, versioned SELECT must be
supplied explicitly to the safe refresh primitive. Until a future P2 handoff
is separately proven, `smart_construction_core` remains the provider.

## Validation and release limits

Tests cover known and unknown tables, 12,328-row preservation semantics,
typed-placeholder rejection, unknown relkinds, repeated upgrade,
environment-only handoff rejection, incomplete and complete machine
contracts, and rejection of non-read-only refresh input.

An internal-only PostgreSQL/Odoo regression used a deterministic synthetic
12,328-row carrier with the evidence schema. Fresh install, the first
17.0.0.72-to-17.0.0.73 upgrade, and the repeated upgrade all completed with
`relkind=r`. Before and after both upgrades:

- row count remained `12328`;
- synthetic key digest remained
  `d964f3d38e4d5919d0008e91201fc29a720d64ba56995062dd04db9c1e8b6d40`;
- synthetic aggregate digest remained
  `67b4da7a011f86251a4616566c26a78c420ffc47dea51da4b08893b39fae9079`;
- owner, ACL count, and the index-definition digest remained unchanged.

A failed staging validation was rolled back without changing the carrier.
Two concurrent real-database refresh calls serialized on the advisory lock;
the second completed only after the first four-second lock holder. The
repository `make ci`, contract-drift guard, boundary audit, and local quick
gate passed. The fixed evidence digests remain the governing historical-data
assertions; the synthetic digests above are regression-fixture identities,
not substitutes for the next full backup-clone rehearsal.

This repair produces source code only. It does not freeze RC6.1, build an
image, access DAILY or production, or authorize DAILY promotion. The next
candidate must receive a new immutable image digest, identity freeze, and a
full clone upgrade rehearsal from its first step.
