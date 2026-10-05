# Daily runtime detached-candidate return to main (2026-10-05)

Formal Product Layer: P4 (ops delivery tool / mainline deployment entry).
Layer Target: `scripts/ops/daily_runtime_bundle_sync.py`, `make daily.runtime.main.bundle_sync`,
`make verify.daily.runtime.main.bundle_sync`.
Standard vs User-Specific: platform ops mechanism, not product semantics.
Why Here: the exact-SHA bundle-sync entry is the only governed way to move an approved main SHA
onto the daily runtime host, so returning a previously deployed detached candidate runtime to
`main` is lifecycle behavior owned by that same entry.
Why Not Elsewhere: no product module, frontend renderer, P3 runtime configuration, database
fixture, migration or release snapshot is touched.
Blast Radius: one P4 ops script plus its unit test and Make wiring; no product runtime behavior
changes, no audit or assertion is relaxed.

## Trigger

The daily runtime host (`sc-root`, `/opt/projects/repos/sce-product-odoo`) was left detached at a
recorded accepted daily candidate `d004bbf2…`, recorded under
`refs/daily-candidates/codex/daily-dev-user-acceptance-closeout-20261005`, while the entry requires
an attached `main` at the expected old SHA. The governed mainline entry therefore failed closed:

```
make daily.runtime.main.bundle_sync DAILY_RUNTIME_EXPECTED_SHA=e44f9c3a… \
  DAILY_RUNTIME_EXPECTED_OLD_SHA=3f424993…
-> BLOCKED git rev-parse: fatal: HEAD does not point to a branch
```

There is no managed entry to return a detached recorded candidate to `main`; a manual
`git checkout` on the host would bypass the governed identity checks.

## Change (minimal P4 extension)

The remote program embedded in `daily_runtime_bundle_sync.py` now accepts a fifth identity,
`expected_candidate_sha`, and normalizes an attached-detached runtime only when **all** of the
following hold:

1. `git branch --show-current` is empty (detached HEAD);
2. `expected_candidate_sha` is a full SHA and equals the current detached HEAD;
3. `git status --porcelain` is empty (clean worktree);
4. `refs/heads/main` equals `expected_old_sha`;
5. `refs/remotes/origin/main` equals `expected_old_sha`;
6. `expected_candidate_sha` is present in `refs/daily-candidates/`.

Only then does it run `git checkout main` and continue with the unchanged exact bundle sync. The
previous attached-`main` path is unchanged. Any other state fails closed with
`BLOCKED remote branch or old SHA differs`. The evidence JSON records
`normalized_from_candidate`.

Local wiring adds the optional `--expected-candidate-sha` argument and the
`DAILY_RUNTIME_EXPECTED_CANDIDATE_SHA` Make variable. An absent candidate SHA preserves the
original behavior exactly.

## Verification

- `make verify.daily.runtime.main.bundle_sync` (L2, offline, non-zero unit tests) — see run record.
- Negative coverage: detached-but-unrecorded HEAD, dirty detached worktree, mismatched
  `refs/heads/main`, and absent candidate SHA all fail closed.

## Results

- `make verify.daily.runtime.main.bundle_sync` — L2, offline, **9/9 passed** (receipt
  `.runtime/agent-runs/DAILY-RUNTIME-CANDIDATE-RETURN/bundle_sync_unit.json`, reusable). Coverage:
  attached-main fast-forward, detached clean recorded-candidate normalization (`normalized_from_candidate`
  `true`), and four fail-closed negatives (unrecorded candidate, dirty candidate, `refs/heads/main`
  mismatch, detached HEAD with no declared candidate identity).
- `make ci.local.iteration` — passed (L1 advisory entry; run resolved, no out-of-scope paths).
- `make ci.delivery.freeze.prepare` — passed with no generated-report drift.
- `make ci.local.quick` — passed on frozen `bbee7981`.
- PR #576 — merged (`e9e381d455edf4b598e5d6af2a823885311f295e`); required gates `public_guard`,
  `merge_policy_gate`, `professional_quality_gate`, `frontend_release_gate` all success.

## Deployment and daily acceptance

Executed against the daily runtime repository (`sc-root:/opt/projects/repos/sce-product-odoo`,
`ENV=dev`, `.env.dev`, `sc_demo`):

| Step | Result |
| --- | --- |
| `make daily.runtime.main.bundle_sync` (`DAILY_RUNTIME_EXPECTED_CANDIDATE_SHA=d004bbf2…`) | PASS, `normalized_from_candidate=true`, `old_sha=3f424993`, `source_sha=e9e381d4`, `bundle_sha256=633b5d27…` |
| `make verify.frontend.build` | PASS (`dist-dev` rebuilt) |
| `make mod.upgrade MODULE=smart_core` | PASS (only `smart_core` differed from the previous runtime SHA) |
| `make restart` | PASS |
| `make verify.daily_dev.runtime_repo.clean` | PASS (`head=e9e381d4`, clean, customer addons read-only) |
| `make daily.runtime.source_revision.align` | PASS (`previous_revision=d004bbf2` → served `e9e381d4`) |
| `make daily.dev.acceptance_fixture.ensure` | PASS (`fixture_role_finance` uid 210) |
| `make daily.dev.acceptance_contract.resolve` | PASS (`artifacts/backend/acceptance_record_identity.json`) |
| `make verify.daily_dev.acceptance.readonly.probe` | PASS (`sc_demo`, served `e9e381d4`) |

The readonly probe reported: runtime identity `served_sha = expected_sha = e9e381d4`; `wutao`
(uid 16) login navigation 90 leaf actions with no forbidden labels and no required-path misses;
contract account `fixture_role_finance` (uid 210, company `FE Company A`) resolving the unique
payment target `smart_construction_acceptance_fixture.fe_delivery_hardening_payment_request_a`.

Daily dev credential: owner-directed fixed password `123456` for `wutao` and `fixture_role_finance`
in `sc_demo`. The daily profile still refused the weak password until a bound
`daily-readonly-credential-confirmation.v1` envelope (5-minute expiry, binding
`tool/baseUrl/apiUrl/database/login/expectedSha/runId`) was supplied; no daily login default and no
other environment was changed.

### Final identity alignment

The record close-out itself added a docs-only commit, so `main` advanced from the code-bearing
`e9e381d4` to `a438d69d`. The daily runtime was re-synced to that exact SHA
(`normalized_from_candidate=false`, bundle `a3ab2e02…`) and its source revision re-aligned, so
`/api/runtime-version` serves `a438d69d`. No addon or frontend source changed in that delta, so the
frontend rebuild and `smart_core` upgrade were not rerun; the daily readonly acceptance probe was
re-executed at `a438d69d` and passed with the same identity, navigation and contract results.

Live run/deployment status is tracked in `.agent/runs/DAILY-RUNTIME-CANDIDATE-RETURN/run.json`.
