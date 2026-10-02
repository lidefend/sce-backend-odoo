# Backend Contract Supply-Chain Attestation and N-1/N+1 Compatibility (L5 gap 2/3)

Run: `.agent/runs/BACKEND-CONTRACT-SUPPLY-CHAIN-ATTESTATION/run.json`
Branch: `fix/contract-supply-chain-attestation`
Baseline: `e93b5e83f572df284d37d9d3c572898858be2179` (`origin/main`)
Date: 2026-10-02

## Purpose and relationship to the SLO telemetry record

This batch carries one already-authored topic onto the current `main` baseline. The
topic history, boundary and layer commit are recorded in
`docs/ops/iterations/backend_contract_slo_telemetry_20261002.md` (see its
"Integration status after PR #533 and the topic (c) carry" section) and are not
copied here; this file is the run's living record index.

Topic (c) of the backend contract lifecycle L5 gaps — signature-level supply-chain
provenance and the N-1/N+1 consumer-compatibility drill — was authored on
`fix/contract-slo-telemetry` at layer commit `d8827e637`, after that branch's other
topics had already been squash-merged into `main` by PR #533. It was therefore never
integrated. This batch re-establishes it on `main` by content.

## Carry-in basis (why this is not a replay)

The old branch is not an ancestor of `main`: PR #533 squash-merged it, so every
"behind" claim based on commit counts would be wrong. The carry was decided per file
against the merge base `002b2c64a`:

- 7 files exist only on the topic branch (the two pure P0 cores, their two units,
  the runtime probe and its schema guard, and the `view_orchestrator.py` carrier fix):
  taken as authored.
- 8 shared files differed only because `main` still held an *older* snapshot of this
  same work: the topic branch's version is the newer one and is taken.
- All remaining shared files were changed on `main` by unrelated later PRs
  (#529/#531/#532/#533). `main`'s version is authoritative and is kept; `main`'s
  generated reports were then re-derived instead of copied from either side.

No file was merged by hand except `make/dev_test.mk`, where `main`'s
`CANDIDATE_GIT_HEAD=$(shell git rev-parse HEAD)` wiring is preserved and the four
`verify.backend.contract_supply_chain.*` targets are appended.

## Boundary

- Formal Product Layer: **P0** platform kernel product (`smart_core`), with P4
  verification tooling.
- Layer Target / Module: `addons/smart_core` (`core/`), `scripts/verify`, `make`.
- Standard vs User-Specific: platform mechanism; no industry or customer semantics.
- Why here: the attestation binds the contract schema digest, the delivered contract
  digest, the artifact digest and the deployed revision, all produced by the
  `smart_core` contract lifecycle mechanism that already owns the lifecycle seal.
- Why not elsewhere: no P1/P2 business semantics, no frontend rendering rule, no
  low-code shortcut, no P4 ops script as semantic authority.
- Blast radius: two new pure-stdlib modules and four verification assets, plus the
  4-line `view_orchestrator.py` carrier fix; no protocol version, Odoo model/field or
  XML change, so no module upgrade is implied. Offline units bound the semantics;
  the runtime probe re-derives them from a real running deployment.

## Exclusions and open items

- No external trust root: the attestation is self-signed, so L5 is not declared.
- Topic (e), the re-baseline decision for the 119 stale snapshot references, stays an
  owner contract-authority decision and is not touched here.
- Deployment, version release and product delivery remain separate, unauthorized steps.
