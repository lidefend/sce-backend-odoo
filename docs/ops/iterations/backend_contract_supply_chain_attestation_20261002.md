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

## Results at the frozen candidate `f4280c850`

Candidate: `f4280c8508e8b106cb922d774797497284941c91` (`fix/contract-supply-chain-attestation`,
clean tree, 22 paths). `make ci.local.iteration` PASS; the regenerated tracked reports were
confirmed current by `make ci.generated_reports.guard` after the merge, not copied from either
side (only `view_orchestrator.py` 1301 -> 1305 lines and +6 scanned files versus `main`, which
is exactly this topic's footprint).

| Layer | Entry | Result |
| --- | --- | --- |
| L2 offline | `verify.backend.contract_supply_chain.unit` | 19 tests PASS |
| L2 offline | `verify.backend.contract_supply_chain.compatibility.unit` | 31 tests PASS |
| L2 offline | `verify.backend.contract_lifecycle.authority` | 35 tests PASS, score 100/100 L4, p0Count 0 |
| L2 offline | `verify.contract.catalog` | 16 tests PASS |
| L3 runtime | `verify.backend.contract_supply_chain.runtime` | probe 14/14 PASS + host Ed25519 guard 12 tests OK |
| L3 runtime | `verify.backend.contract_slo_telemetry.runtime` | probe 43/43 PASS + host guard 11 tests OK |

The runtime lanes ran after `make local.contract-lifecycle.prepare` refreshed
`SC_SOURCE_REVISION` from the old branch tip `2ad47f83f` to this candidate and
`make local.contract-lifecycle.up` recreated the odoo container through the governed entry; no
module upgrade was needed because the `addons/` tree is byte-identical to the topic branch that
produced the original evidence, and the probe runs in a fresh `odoo shell` process that imports
from this worktree's mount.

The SLO telemetry runtime lane is in scope here because it is the check that locks the carried
`view_orchestrator.py` carrier fix (topic b's published-version attribution). The L4
`verify.backend.contract_lifecycle.runtime` lane was not re-run: it asserts nothing about the
carrier and its declared inputs are unchanged, so its integration-head receipt in the closed
`BACKEND-CONTRACT-L4-CLOSURE` goal stands for its own scope.

One owning-layer fix was made while verifying: the standalone
`verify.backend.contract_supply_chain.runtime.schema.guard` target silently read an implicit
`/tmp` report. It now binds the governed `artifacts/` report explicitly and fails closed with a
clear message when none exists, so a stray file from another revision cannot be consumed.

Still open and owner-gated: independent review of this carried delta, the Gitee candidate
dispatch (after the `gitee-mirror/main` sync), publication, the external trust root, and topic
(e).

## Closure outcome (2026-10-03, after PR #535)

This carried topic merged into `main` as PR #535, squash commit
`08759706b32743bce251473ff2fa1e85a36661b0` (head
`e18fe9dc49594403f84e1a4ef20f6f78602b8616`, merged 2026-10-02T11:07:14Z). The PR head
advanced the frozen candidate `f4280c850` to `e18fe9dc` by merge-base reconciliation.

Carry integrity was re-checked against `main` at `7ed180d8b` (the closeout baseline): a
`git diff` over the declared code scope — `contract_supply_chain_attestation.py`,
`contract_version_compatibility.py`, `view_orchestrator.py`, `scripts/verify/**`,
`scripts/dev/local_contract_lifecycle_env_prepare.sh`, `make/dev.mk`, `make/dev_test.mk` and
`docs/architecture/backend_contract_lifecycle_authority_v1*.md` — is empty. Only this record
document gained its results section. The offline locks (19 / 31 / 35 / 16 tests) and the two
runtime lanes (14/14 + 12 and 43/43 + 11) recorded at `f4280c850` are therefore carried forward
unchanged, not re-run for reassurance; the runtime receipts remain head-bound and stale by
design, as the reuse evaluator intends.

The closeout itself is a record-only change under `.agent/`. Its owning-layer check
`make verify.agent.resume.unit` (30 tests) passed, recorded as the governed receipt
`.runtime/agent-runs/BACKEND-CONTRACT-SUPPLY-CHAIN-ATTESTATION/agent_record_guard.json`; the L1
entry `make ci.local.iteration` passed on the active-run state. `main` and the Gitee mirror
`main` both read `7ed180d8b`, and the merged branch `fix/contract-supply-chain-attestation` is
deleted on both remotes.

Still open and owner-gated, unchanged by this closeout: the external trust root (the
attestation stays self-signed, so L5 is not declared), the topic (e) re-baseline decision for
the 119 stale snapshot references, and publication. None of them blocks mainline stability, so
the run and goal are recorded complete with these items explicitly deferred.
