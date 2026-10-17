# Menu cache invalidation closeout — 2026-10-17

## Purpose

The 2026-10-17 incremental review of PR #669 reported that the menu projection
cache could still serve stale navigation after an edit that the timestamp
watermark cannot see:

- an edit made in the same transaction after generation shares the transaction
  clock, so `write_date > last_generated` is false;
- a transaction that began before generation but commits after it stamps rows
  with an earlier clock, also below the watermark;
- the cache has no TTL, so such a stale projection can persist indefinitely.

This batch replaces timestamp-only invalidation with a content digest of the
projection inputs and closes the evidence gaps reported with it.

## Layer declaration

- Formal Product Layer: P0 platform kernel product (menu projection cache),
  with P4 changes to the governed performance-evidence tooling.
- Layer Target: `addons/smart_core/app_config_engine/models/app_nav_config.py`,
  `scripts/verify/`, `make/dev.mk`.
- Standard vs User-Specific: platform mechanism; no industry or customer
  semantics.
- Why Here: `app.menu.config` owns the persisted menu projection consumed by
  `system.init`.
- Why Not Elsewhere: the rule cannot live in the frontend, low-code runtime or
  a customer module without making two sources of truth.
- Blast Radius: menu cache freshness checks and the startup observation
  identity; no contract payload, schema or product semantics change.

## Work log

### Root cause

`app.menu.config` invalidated its persisted projection by comparing
`ir.ui.menu`/`ir.actions.*` `write_date`/`create_date` with `last_generated`.
Those columns carry the *writing transaction's* clock, so two legal edits were
invisible:

- an edit made later in the same transaction equals the watermark, and
  `write_date > last_generated` is false;
- a transaction that began before generation but commits afterwards stamps an
  earlier clock, also below the watermark.

The cache has no TTL, so an invisible edit could be served indefinitely.

### Change

- Staleness is now decided by a deterministic content digest of every source
  row the projection persists: `ir.ui.menu` (id/name/sequence/parent/action/
  active/groups/web_icon), `ir.actions.actions`, `ir.actions.act_window`,
  `ir.actions.act_window.view`, the `ir.ui.view` rows referenced by those
  act_window views (id/type, because the projection persists
  `(view_id, view_id.type)` and picks a default view by type), and the
  `ir.model.data` rows that supply menu `xml_id`/`module`. No timestamp takes
  part in the comparison.
- `_generate_from_menus` takes the digest before reading any source row and
  stores it in `meta_info.source_digest`. An edit that lands between digest and
  tree read only causes one extra rebuild; it cannot be served as fresh.
- A legacy row without a digest is stale once, rebuilt, and then stable.
- When the projection is unchanged, `last_generated` and `meta_info` are
  refreshed so the same source edit does not trigger a rebuild on every lookup;
  the concurrent-create path refreshes them the same way.

### Evidence identity and impact analysis

Changed product input: `addons/smart_core/app_config_engine/models/app_nav_config.py`.
The only product entry point that reaches the changed code is
`app.menu.config.get_menu_contract -> _get_or_generate_from_menus ->
_menu_metadata_changed_since/_menu_source_digest`.

Derived affected set (declared consumers x runtime entrypoints):

| unit | reaches changed code | action |
| --- | --- | --- |
| `observe` (`system.init` handler) | yes | re-captured |
| `sla` (HTTP `system.init`) | yes | re-captured |
| `permission` (`MenuService.build_nav` sample) | yes | re-captured |
| `contract-request` (`check_intent_permission -> _published_menu_decision -> build_nav`) | yes | re-captured |
| `role-matrix` (`published_route_authority` with `menu_id` carrier) | yes | re-captured |
| `contract-profile` (`ui.contract` action_open) | no | reused |
| `cache-identity` (`ui.contract.v2`) | no | reused |

The two `ui.contract.v2` probes were initially reused on the assumption that
they never reach the menu cache. Independent review traced both probes through
`Policy.published_route_authority()` and `check_intent_permission()` into
`MenuService.build_nav`, so that assumption was wrong. Their identity blocks
now declare `delivery/menu_service.py` and
`app_config_engine/models/app_nav_config.py`, and both units were re-captured.

Identity binding added for the affected units:

- `observe` reports `menu_config_sha256`; the normalizer binds it to
  `app_nav_config.py` (mismatch is `stale`, not a silent pass).
- `platform_sla_guard.py` emits an `identity` block for `system_init.py` and
  `app_nav_config.py`; `platform-sla-guard/v1` now resolves those hashes.
- the permission probe's identity includes `app_config_engine/models/app_nav_config.py`.
- the contract-request and role-matrix probes now declare
  `delivery/menu_service.py` and `app_config_engine/models/app_nav_config.py`;
  omitting them had made a stale reuse look like `identity_match=match`.
- the runtime probe resolves the model implementation through
  `_menu_metadata_changed_since`; Odoo's dynamic model class otherwise points
  at `odoo/api.py` and would compare the wrong file.

`cache-identity` still reports `identity_match=unknown` with no declared
product hashes. That is an unbound entry, not a match: `identity_gaps=0` counts
only complete-identity gaps, so "7 entries, 0 gaps" must not be read as "7
entries fully bound".

Environment prerequisite: the governed `local.dev` Odoo process was restarted
at `2026-10-17T08:57:43Z`, after the candidate file mtime
`2026-10-17T08:52:52Z`, so the HTTP `system.init` unit runs the changed code.
The first SLA capture after restart reported `system.init` p95 `1702.02 ms`,
dominated by the process-first request; it is retained as
`sla-guard.cold-after-restart.json` and is not compared with the warm baseline.
The comparable warm-state unit was re-captured under the same candidate:
`system.init` p95 `644.95 ms` (previous baseline `630.90 ms`).

Stage identity of these captures: the governed `sc-local-dev` runtime mounted
the candidate working tree, so the inputs were captured against
`base 95919c2a + dirty candidate content (pre-commit)`. They are not clean-HEAD
measurements; the clean identity is established by the frozen fingerprint and
the exact-head Quick receipt that follow the commit.

### Checks

| layer | command | result |
| --- | --- | --- |
| L1 | `make verify.local.dev.runtime.performance.unit` | 20 + 9 tests, 0 failed |
| L1 | `make verify.system.performance.baseline.unit` | 72 tests, 0 failed |
| L1 | `python3 -m unittest scripts.verify.test_local_dev_runtime_permission_probe` | 9 tests, 0 failed |
| L2 | `make local.dev.test MODULE=smart_construction_bundle TEST_TAGS=/smart_construction_bundle:TestStartupPerformanceContract` | 13 tests, 0 failed |
| L3 | `local.dev.runtime.performance.baseline` with `SOURCES=contract_request,role_matrix` + `SOURCES=sla,observe,permission`, `REUSE_UNCHANGED=1` | 7 entries, 0 gaps; 6 units `match`, `cache-identity` `unknown` |

### Independent review (three parallel roles)

Final-candidate review ran as three concurrent read-only roles over the same
exact identity (`HEAD 9f02b158`, `tree 0df86460`, base `95919c2a`):

| role | scope | finding |
| --- | --- | --- |
| A | menu invalidation mechanism and counter-examples | S2: `ir.ui.view.type` was not in the digest while the projection persists it; fixed in this batch |
| B | performance evidence identity and impact set | S1: contract-request/role-matrix reuse basis invalid; fixed and re-captured |
| C | run index, archive and fingerprint integrity | S1: stale `run.json` index and missing complete fingerprint; fixed in this batch |

Recorded follow-ups, not fixed here and not claimed as closed:

- `head.permissions` is an ACL snapshot persisted with `menu_tree`; ACL changes
  do not move the digest. Pre-existing derived-field gap, unchanged by this fix.
- A theoretical ABA race between digest capture and tree read can store a
  mid-state tree with a restored digest; a single edit cannot trigger it.
- The cold path computes the full digest twice (freshness check and generation);
  correctness is unaffected, cost is not optimized further in this batch.

### Status boundaries

- This record closes the reported menu-invalidation defect and rebinds the
  affected performance evidence. It does not close the performance topic:
  first-open, daily experience and capacity acceptance remain open, and no
  deployment is performed.
- PR #669 was merged without a completed independent-review record. That gap
  cannot be backdated; this follow-up PR requires its own recorded independent
  review before merge.
