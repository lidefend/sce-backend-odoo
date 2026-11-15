# ODOO-NATIVE-CAPABILITY-EXPLORER-03

## Candidate

- Baseline: `d176e2fd67fec87257114b207cec655ec8fa6e9d`
- Branch: `audit/platform-capability-studio-01-20261115`
- Stage: implementation and local runtime validation complete; strict 282
  reconciliation remains environment-specific

## Product Boundary

- P0 `smart_core`: generic read-only projection, catalog token, pagination,
  diagnosis, handler registration and entry authorization.
- P1 `smart_construction_core`: existing scene binding and product publication
  facts supplied through a generic extension hook.
- P4: focused tests, runtime read-only evidence, registry and documentation.

No parallel capability registry, capability ORM, scene mutation, frontend page,
product business-logic change, deployment or merge is in scope.

## Required Contract

- `catalog_token` covers language, installed modules and dependencies, native
  Menu/Action identities and hierarchy, model/action targets, views, ACL, record
  rules, scene bindings and active release snapshots.
- List and Detail accept `expected_catalog_token`; mismatch returns
  `CATALOG_STALE`.
- `draft_selectable`, `scene_assignable`, `preview_qualified` and
  `standard_qualified` are separate facts.
- Business-domain classification comes only from existing scene bindings.
- Native centers never become inferred business domains.
- Ordinary business users are denied before sudo metadata reads.

## Verification

- `verify.platform.capability_explorer.unit`: PASS, 17 tests.
- `verify.runtime_capability_catalog.unit`: PASS, 19 tests.
- `verify.capability.identity_boundary.unit`: PASS, 6 tests.
- `verify.frontend.dev.incremental.unit`: PASS, 145 tests.
- `verify.guard.registry`: PASS, 24 tests.
- `verify.agent.ledger.unit`: PASS, 18 tests.
- `verify.agent.resume.unit`: PASS, 57 tests.
- `verify.daily.permission_truth.capability.orm`: PASS, 65 ORM tests.
- `verify.local.dev.runtime.performance.unit`: PASS, 9 tests.
- `verify.page.finalize.authority.orm`: PASS, 1 ORM test.
- `verify.page.project_finalize.authority.orm`: PASS, 1 ORM test.
- `verify.verification.lane_coverage`: PASS, 74 tests.
- `make ci.local.iteration`: PASS with 12 affected targets.

The verification-surface baseline was deliberately rewritten from 669 to 670
zero-reference targets because the new on-demand
`audit.platform_capability_explorer.demo` runtime probe was registered as
`diagnostic_cli`. The disposition has an owner and review date; it is not a
functional acceptance claim.

## Local Persistent Database Upgrade

- Target: `sc-local-dev` / `sc_dev_demo`, precise filter `^sc_dev_demo$`.
- Role: persistent local development demo, not platform control, customer tenant
  or production.
- Upgraded modules: `smart_construction_bootstrap`,
  `smart_construction_bundle`, `smart_construction_core`,
  `smart_construction_demo`, `smart_construction_portal`,
  `smart_construction_scene`, `smart_construction_seed`, `smart_core`,
  `smart_license_core`, `smart_scene`.
- The Odoo registry loaded normally; entry identity and demo authority readback passed.
- Odoo was restarted after upgrade; `local.dev.health` passed.
- Pre-upgrade database and filestore snapshot:
  `artifacts/local-dev/snapshots/20261115T082948Z/`.
- Snapshot manifest SHA256:
  `bf9db35d4715f656521f9e5964fcdfdb905b3b7820958f5648d561769d08d316`.
- Database dump SHA256:
  `0f416a23009a1e0678fa5e0a71eb19972854112bd112f2525bf03e6a790544b4`.
- Filestore SHA256:
  `90ae7b1ce8bdb3829ca08e84ff0a370862eaf7662bed1221a2acc70f0e539686`.
- Upgrade log SHA256:
  `3d4cdf13960a4ea6724d83962f28d06c87cb8e6b057b747c1187da28d6b021cb`.

## Runtime Result

The current `sc_dev_demo` data snapshot exposes three leaf entries under the
declared construction root after the complete upgrade:

- 3 stable native entry identities.
- 1 `center_only`.
- 2 `unclassified`.
- 0 authoritative scene bindings.
- 0 active release snapshots on this local development database.

The reduced-carrier runtime probe passed:

- List, Detail and Diagnose handler registration passed.
- Public-user denial passed; tenant-config and patched platform-control permission
  decisions passed.
- Stale token rejection passed.
- Concurrent `zh_CN`/`en_US` queries stayed database-scoped, produced stable
  same-language tokens and distinct cross-language tokens.
- List returned no technical detail payload.
- Full projection: 61 SQL queries, 255 ms.
- List: 27 SQL queries, 112 ms.
- Handler: 212 ms projection, serialization under 1 ms.

This carrier does not contain the prior 282-entry business snapshot, so the
strict 282/75/207 check correctly fails rather than substituting reduced data.
The strict failure is recorded; no scene or menu data was fabricated or copied.

An all-menu performance probe, explicitly marked non-authoritative for business
classification, projected 498 stable native entries with 91 SQL queries and
53 native-stage queries in 467 ms. This is shape evidence that query count no
longer scales one-for-one with entries; it is not a 282 product reconciliation.

Runtime logs:

- Unit:
  `.runtime/agent-runs/ODOO-NATIVE-CAPABILITY-EXPLORER-03/platform-capability-explorer-unit.log`,
  SHA256 `d5b36dee2797b9c4b01f25d6679cda843908f64d15beef88321aece9f32edf1f`.
- Post-upgrade reduced runtime:
  `.runtime/agent-runs/ODOO-NATIVE-CAPABILITY-EXPLORER-03/platform-capability-explorer-runtime-post-upgrade-reduced.log`,
  SHA256 `f9c3e8d3bdaa54ee952a8aa86a3617b63a7d127e17e859a141679857820438d9`.
- Strict 282 rejection:
  `.runtime/agent-runs/ODOO-NATIVE-CAPABILITY-EXPLORER-03/platform-capability-explorer-runtime-strict.log`,
  SHA256 `0a12a137782f5587908632b0a2c8b749ff695d362f60617432a8ce0b674a69fa`.
- All-menu stress:
  `.runtime/agent-runs/ODOO-NATIVE-CAPABILITY-EXPLORER-03/platform-capability-explorer-all-menu-stress.log`,
  SHA256 `85290803325476003ccfd31efc93208aae067732a620bf36a5ec77f912bade01`.

## R03-R1 Independent Review Repair

The independent review returned `REQUEST_CHANGES` with two S1 and three S2
findings. The repair is intentionally scoped to the Explorer:

- Tenant Explorer requests now use an Explorer-specific release projection.
  When the declared release database differs from the current registry, no
  second `Registry` is opened and no cross-database superuser environment is
  created. Authority is explicitly unavailable with
  `PLATFORM_RELEASE_DB_ISOLATED`, and release states remain unknown.
- `catalog_token` now includes scene/release authority availability, provider
  success/failure, root/fallback diagnostics, provider conflicts, XMLID
  ambiguities and candidate-menu diagnostic facts. Runtime request time and
  metrics remain outside the token.
- Release Center source is carried from the P1
  `construction.product_menu_source.v1` declaration and consumed verbatim by P0.
- P1 and cross-provider Release Center conflicts are merged, never resolved by
  first-wins; the ambiguous center is omitted and
  `RELEASE_CENTER_AMBIGUOUS` becomes an explicit diagnostic blocker.
- Diagnose now accepts `menu_xmlid` and can report `ACTION_NOT_FOUND`,
  `ACTION_TYPE_UNSUPPORTED`, `MENU_ACTION_MISMATCH`, `MODEL_NOT_FOUND`,
  `MODULE_NOT_INSTALLED`, `XMLID_INVALID`, `XMLID_NOT_FOUND` and
  `XMLID_AMBIGUOUS`. The main draftable catalog remains stable-identity only.
- XMLID aliases are dereferenced only when unique. Multiple aliases are
  fail-closed and included in the token.

R1 verification:

- `verify.platform.capability_explorer.unit`: PASS, 27 tests.
- `verify.runtime_capability_catalog.unit`: PASS, 19 tests.
- `make ci.local.iteration`: PASS with 12 affected targets.
- Reduced `sc_dev_demo` runtime probe: PASS, including actionless Menu,
  Menu/Action mismatch, missing Menu XMLID and isolated-release authority.
- Full projection: 63 SQL / 260 ms; List: 29 SQL / 119 ms.
- 498-entry all-menu stress remains non-authoritative business classification:
  93 SQL / 526 ms, no entry-linear N+1.
- Strict 282/75/207 remains a separate acceptance condition on a compatible
  business snapshot.
- R1 runtime log:
  `.runtime/agent-runs/ODOO-NATIVE-CAPABILITY-EXPLORER-03/platform-capability-explorer-r03-r1-runtime.log`,
  SHA256 `5647268b8aaa7a0a59dd524b63370122d34d41b0b4ea6b20b47ffbff8417ff7e`.
- R1 all-menu stress log:
  `.runtime/agent-runs/ODOO-NATIVE-CAPABILITY-EXPLORER-03/platform-capability-explorer-r03-r1-all-menu-stress.log`,
  SHA256 `030457b7a7b0a0393c71f827f5c0f66923c76ca3f0e2f7e468b5c5c6110ae4af`.

## Result

The read-only backend implementation and R03-R1 review repairs are complete and
locally verified. It has no persistent discovery model, no write endpoint and no
frontend. Strict 282/75/207 and active-release validation must run on a
compatible business data carrier; the registered persistent development carrier
truthfully reports three entries after full upgrade.
