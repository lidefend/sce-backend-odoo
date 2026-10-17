# Post-#671 local runtime experience observation — 2026-10-17

Scope: `sc-local-dev` / `sc_dev_demo` only. This is a local development
observation, not target-environment acceptance, not a capacity measurement and
not a delivery baseline. No product code, schema, fixture or ACL was changed.
No deployment was performed.

## Identity actually observed

- Observed source: `f7765c52ee1283cc8fdeccec6782b046df33f292`, tree
  `5ffd4802aa23e7cdd6eb05683814705855bab6e8`.
- `origin/main` after PR #671 is `5dbf503d514040fbfddaddd056cecda7ae460876`
  with the same tree, so the observed tree is the merged mainline tree.
- Backend container `6582e34f6fbba8428f5b94a39f522bafc9afbea8fc6c260baada79fb64302f8b`,
  odoo process started `2026-10-17T10:53:14.088036316Z`.
- `app_config_engine/models/app_nav_config.py` is blob
  `e1aec0b9e34593c0b5f7eabe1bf718289191a016`, sha256
  `864954628a4e05363de6ae800318a523c074cf0121c2392aa9099daac900ece9`, matching
  the `origin/main` tree.

The instance that was running before this observation started its odoo process
at `2026-10-17T09:01:04Z`, while the final source change to
`app_nav_config.py` landed at `10:07:30Z`. With `workers = 0` and no
`--dev=reload`, that process still held the pre-#671 module in memory, so it
could not be used as the identity for this observation. The instance was
reloaded through the governed entry `make local.dev.restart` and the identity
above was re-read afterwards. Observing with the stale process would have
measured the previous implementation and could not be attributed to #671.

Gap: the browser probe records `backend.revision = "unknown"`, so the running
identity is established by process start time plus per-file hashes, not by an
image revision label.

## Backend startup segment (`system.init`, web_startup)

Principal `smart_construction_demo.user_demo_role_finance`, company 1, one
process-first sample plus five subsequent samples in the same process.

| sample | elapsed ms | SQL | build_nav ms | finalize_startup_surface ms | execute_scene_runtime ms |
| --- | --- | --- | --- | --- | --- |
| process-first | 1813.33 | 2646 | 1327 | 242 | 77 |
| 1 | 505.28 | 602 | 229 | 153 | 50 |
| 2 | 387.77 | 602 | 117 | 147 | 54 |
| 3 | 378.32 | 602 | 109 | 149 | 51 |
| 4 | 491.51 | 602 | 113 | 262 | 49 |
| 5 | 376.61 | 602 | 107 | 148 | 52 |

- Subsequent median: 387.77 ms at 602 SQL; `build_nav` settles near 107-117 ms.
- `navigation_sha256` is identical in all six samples
  (`487a12322f48d507a3b52401d3136814592dc516933f81d816f2622c119da72f`), so the
  cold and warm responses are the same payload.
- The probe declares `no_true_cold_cache_claim`: the first sample is a
  fresh-process first request, not a measured cold filesystem/database state.

## Record-bound form request (`ui.contract.v2`, action 878, `payment.request`)

Uninstrumented probe, no monkey patches.

- First request: 2724.31 ms, `cache_reason = asset_not_found`, response
  1,137,769 bytes.
- Hot window n=6: 429.74 / 438.28 / 445.32 / 475.73 / 595.87 / 639.68 ms,
  median 460.52 ms. `p95` is the window maximum (639.68 ms) and is reported as
  an observation only, not a tail claim.

## Browser observations (Playwright 147.0.7727.15)

| journey | wall ms | server segments |
| --- | --- | --- |
| login -> workbench (median of 5 samples, 2 warmups) | 1453 | login 300.56, `system.init` 442.21, `my.work.summary` 179.08, `global.message.conversations` 8.49 |
| list first open | 2219 | `ui.contract.v2 action_open` 1151.20 (permission 179.00), `user.view.preference.get` 25.26, `api.data list` 38.77 |
| list re-query | 582 | `ui.contract.v2 action_open` 29.19, `api.data list` 132.33 |
| record open | 2702 | `ui.contract.v2 action_open` (form) 1759.31 |

Login samples: 1453 / 1388 / 1501 / 1662 / 1414 ms.

Two observations worth a follow-up, neither concluded here:

- The first list contract costs 1151 ms and reports 179 ms of permission time,
  while the same contract on re-query costs 29 ms. The first-open cost is
  therefore assembly/permission bound, not data bound (`api.data` is 38.77 ms).
- The record form and its backend probe disagree in size (2724 ms first /
  460 ms hot vs 1759 ms first open in the browser). The browser value is one
  window, so it does not establish a distribution.

## Explicitly not claimed

- No true cold-cache number, no p95 or capacity claim, no SLO statement.
- No target-environment result. `daily_experience` and capacity acceptance stay
  open.
- No attribution of any change to #671 beyond identity: this run produced a
  single-window baseline on the merged tree, it did not A/B the fix.

## Raw evidence

- `artifacts/main-scheduled-ci-closeout-20261016/local-browser-login-performance.json`
  sha256 `2d51c6511b8755821a73beebecbb5807d552e0070a935bca11df757f30940007`
- `artifacts/main-scheduled-ci-closeout-20261016/local-browser-chain-performance.json`
  sha256 `dee9573798086c2343a9cb7e0cafdde2c85f41d03952319e3a437a3ca04749f3`
- `artifacts/main-scheduled-ci-closeout-20261016/local-browser-record-performance.json`
  sha256 `2d8768210ec311a1851994e4df64d7f192a21d690e415b964ecb8e577cadc89a`
- Backend probe output is console-only (`RUNTIME_PERFORMANCE_OBSERVATION=` and
  `CONTRACT_RECORD_FORM_PROBE_REPORT=`) and is reproduced above; it was not
  persisted to a file, so no hash is asserted for it.
