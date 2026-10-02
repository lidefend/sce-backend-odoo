# Backend Contract SLO Telemetry — Core (L5 gap 1)

Run: `.agent/runs/BACKEND-CONTRACT-SLO-TELEMETRY/run.json`
Branch: `fix/contract-slo-telemetry`
Baseline: `c2410190feb7f7db2407083cca65f5ca624bb8c8`
Date: 2026-10-02

## Purpose

`docs/architecture/backend_contract_lifecycle_authority_v1.md` records the
backend unified page contract lifecycle at L4 and lists three L5 gaps. The first
is the missing contract-version SLO telemetry: success rate, degradation rate and
integrity-failure rate aggregated per contract version.

This batch delivers the **decision-independent core** of that feature and nothing
else:

- the identity a delivery is aggregated under;
- the outcome classification (`success` / `degraded` / `integrity_failure`);
- the aggregation, with exact-sum counts and rates that are never fabricated for
  an empty window.

## Boundary

- Formal Product Layer: **P0** platform kernel product (`smart_core`), with P4
  verification tooling.
- No contract protocol change, no new Odoo model, no module upgrade, no new
  compose project / database / port / volume / credential.
- The module is pure standard library, so the semantics are offline-verifiable
  and reusable by any sink (structured log, metrics pipeline, future read model).

## Exclusions

- Emission at the runtime delivery boundary (touches `ui_contract_v2`).
- Long-term persistence, trend reporting and any read intent.
- Aggregating by the published `ui.business.config.contract` version number: the
  runtime lifecycle evidence does not carry it, so this batch keys on the
  identity that is actually present and leaves the additive field to a separate
  decision. `delivery_identity` already carries an optional `publishedVersionRef`
  so that decision stays additive.

## Results

### Delivered

- `addons/smart_core/core/contract_slo_telemetry.py` — pure standard-library core:
  - `delivery_identity()` reads the aggregation identity from the lifecycle
    evidence already emitted by `contract_lifecycle.build_lifecycle_evidence`
    (schemaId / schemaVersion / contractVersion / sourceType / sourceSha256 /
    stage), fails closed when that identity is incomplete, and carries an
    optional `publishedVersionRef` so published-version keying stays additive.
  - `classify_delivery()` returns `success` / `degraded` / `integrity_failure`,
    with integrity failure outranking degradation.
  - `aggregate_observations()` reports exact per-identity counts and
    `successRate` / `degradationRate` / `integrityFailureRate` over accepted
    observations only; an empty input yields no version rows rather than
    fabricated zero rates, and malformed observations are counted and sampled
    (capped) instead of being silently dropped.
- `scripts/verify/test_contract_slo_telemetry.py` — 18 offline tests.
- `make/dev_test.mk` — `verify.backend.contract_slo_telemetry[.unit]`.

### Evidence

- `make ci.local.iteration` → PASS, `change_state=dirty`.
- `make verify.backend.contract_slo_telemetry.unit` → PASS, 18 tests.
  Receipt `.runtime/agent-runs/BACKEND-CONTRACT-SLO-TELEMETRY/slo_core.json`
  (log `logs/slo_core.log`).
- Negative-first proof (`logs/negative_first.log`): removing the integrity-first
  branch and the malformed-row outcome check makes 2 tests fail; the core was
  restored byte-identical (`diff` empty) and the suite returned 18/18 OK.
- The identity test seals a real contract through `contract_lifecycle` and reads
  the identity back from `meta.lifecycle`, so the SLO identity is bound to the
  emitted evidence rather than to a synthetic dictionary. The suite also asserts
  the core imports no `odoo` module.

### Not delivered (deferred, deliberate)

- Emission at the runtime delivery boundary and any long-term persistence or
  trend read model.
- Contract-version keying by the published `ui.business.config.contract` version
  number (needs an additive lifecycle field; separate decision).

Consequently the L5 gap remains open: the L4/L5 statement in
`docs/architecture/backend_contract_lifecycle_authority_v1.md` is intentionally
unchanged.
