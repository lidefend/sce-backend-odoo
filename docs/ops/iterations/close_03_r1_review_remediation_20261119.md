# CLOSE-03-R1 review remediation

## Identity

- Goal: `CLOSE-03-R1-REVIEW-REMEDIATION-20261119`
- Branch: `fix/close-03-r1-review-remediation-20261119`
- Baseline/main: `61d1b98d3c80e3e2c1f6e0f6947a9ce2221d7138`
- Reviewed CLOSE-03 candidate: `97363dc8765eded3d83f6242f16be64e229d2e29`
- Reviewed merge: `61d1b98d3c80e3e2c1f6e0f6947a9ce2221d7138`

## Boundary

- Formal Product Layer: P1 construction standard with P0 native-modifier consumption.
- Layer Target: migration changed-set validation, effective readonly allow-list, and shared intake draft lifecycle/restore.
- Module: `smart_construction_core`, `frontend/apps/web`, `scripts/verify`.
- Standard vs User-Specific: construction-product standard; not a customer-specific fork.
- Why Here: P1 owns the persisted policy migration and native autosave declaration; the shared frontend owns draft lifecycle and current-contract consumption.
- Why Not Elsewhere: the frontend cannot compensate for a rejected migration, and the migration must not reject or delete valid maintained rows to match a canonical seed count.
- Blast Radius: standard and quick project-intake create, saved project records, payment create, canonical product policy migration and browser detail return.
- Exclusions: CLOSE-04, renderer expansion, production deployment, full-entry matrix and product-delivery claim.

## Reviewed findings

### S2-1 migration rejects maintained policies

The merged `.183` migration required exactly 132 rows in each runtime policy and
required every row to be released. Valid maintained hidden rows and additional
rows could therefore block upgrade.

Required result:

- validate only XMLIDs added or changed by the current migration pass;
- changed menu and capability rows become released with canonical maturity;
- unchanged controlled menu/capability rows remain byte-equivalent;
- valid hidden/retired, disabled and extra maintained rows survive;
- repeating the actual migration entry yields no changes.

### S2-2 reverted clean input is restored from stale draft

After a value was persisted and then reverted to the original clean baseline, the
old draft remained and refresh restored the no-longer-visible value.

Required result:

- initial clean does not persist defaults or delete a pending restore candidate;
- after a draft existed, returning all values to original clean clears the exact key/token;
- stale operations cannot remove another instance or a newer draft.

### S2-3 native readonly truth values enter draft allow-list

The producer compared readonly with `is True`, so native `readonly="1"` could pass
through and produce an autosave declaration for a field that is not writable.

Required result:

- handle `True/1/"1"` and `False/0/"0"` through the existing modifier evaluator;
- unresolved expressions fail closed;
- real XML `readonly="1"` removes the field from the final allow-list;
- frontend restore intersects old values with the current writable contract.

## Backend stage

Status: completed on the shared R1 candidate.

- The promotion helper now returns per-product changed XMLIDs.
- Migration `.183` snapshots maintained menu/capability rows, runs promotion,
  and validates only changed XMLIDs. Every changed menu and capability must be
  released with canonical maturity; every unchanged maintained row must remain
  byte-equivalent.
- Legal hidden/retired, disabled and extra rows are preserved, and replaying the
  actual migration entry produces no further changes.
- Intake allow-list projection now evaluates every declared readonly source
  through the existing strict modifier evaluator and fails closed unless the
  result is definitely false.
- A real XML `readonly="1"` sample produces `owner_id_declared=false` and removes
  `owner_id` from the final autosave field allow-list.

## Frontend stage

Status: read-only preparation pending backend handoff.

## Verification

- Focused native XML readonly/autosave contract tests: PASS, 12 tests.
  Log: `.runtime/test-baseline/1795046470254202249/odoo.log`.
- Actual `.183` migration entry tests: PASS, 7 tests. The cases cover the
  unmaintained canonical policy, hidden and extra maintained rows, changed
  menu/capability validation, canonical preview rejection and second-run
  idempotence. Log: `.runtime/test-baseline/1795046492196576512/odoo.log`.
- Product menu contract guard: PASS, 8 tests.
- Daily runtime entry declaration guard: PASS, 32 tests.
- Full `smart_construction_core` owning-module baseline remains failed with
  pre-existing debt and is not claimed as covered.

## Completion boundaries

- BE-CLOSE-03-R1 is complete and hands off to FE-CLOSE-03-R1.
- Batch acceptance remains pending until both frontend findings close and the
  governed browser regression passes.
- Mainline integration and deployment are not claimed by this record.
