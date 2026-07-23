# Delivery context switch log v1

This log records current product-repository implementation context only. Historical
customer delivery evidence belongs in private customer or payload repositories.

## 2026-07-23 — v1.0.0-rc.2 version lock

- Branch: `release/v1.0.0-rc.2`
- Starting product commit: `adfd725eda45b8f2c8c41e8b30571dfa43d7e633`
- Formal Product Layer: P4 operations delivery tooling
- Layer Target: candidate release version authority
- Module: `VERSION` and isolated production-contract image acceptance
- Reason: assign the next candidate version only after RELEASE-CANDIDATE-02R merged and ensure snapshot acceptance consumes the same version authority
- Standard vs User-Specific: generic release identity; no business or customer semantics
- Why Here / Why Not Elsewhere: `VERSION` is the formal product release source; image tags, manifests, and snapshot acceptance consume it rather than duplicating a stale literal
- Blast Radius: next candidate image tag and release manifest version only; no production connection, database, runtime, baseline, rc.1 artifact, or application behavior change
- Validation: product release version tests, shell syntax, generated-report guard, and PR required checks

## 2026-07-23 — RELEASE-CANDIDATE-02R

- Branch: `fix/release-candidate-02r-contract`
- Starting product commit: `2554617a7a31b07e02cba5d9278213d9ac0d8acf`
- Formal Product Layer: P4 operations delivery tooling
- Layer Target: formal scan observation, release manifest identity, production Git authority diagnosis, and digest-addressed Compose admission
- Module: `scripts/release`, `scripts/verify`, production candidate Compose, release schema/tests, and production remediation documentation
- Reason: fail closed when scan observations or artifact identity are incomplete, reject stale Git authority evidence, and prevent tag-only or legacy-target production admission
- Standard vs User-Specific: generic release safety; no construction-industry or customer business semantics
- Why Here: repository-owned P4 tooling is the authority for build evidence, release admission, and non-mutating production diagnostics
- Why Not Elsewhere: application modules must not own deployment identity, frontend cannot validate server artifacts, and production runtime configuration cannot repair a missing source contract
- Blast Radius: the next candidate scan/manifest, release identity preflight, Git diagnostic evidence, and production candidate Compose inputs; no business model, baseline content, rc.1 artifact, production connection, database, container, or runtime mutation
- Validation: unit matrices for scan, manifest, authority and Compose contracts; release-contract suite; repository lint/type/unit gates; one standard `make ci`

## 2026-07-22 — PRODUCTION-DEPLOYMENT-11-R10E Colocated Platform Core

- Branch: `fix/r10e-colocated-platform-core-release-contract`
- Starting product commit: `8caaaa63e105a3cc280b80e397c466a61860234e`
- Formal Product Layer: P0 platform database-selection mechanism plus P4 release, backup, restore, and verification tooling
- Layer Target: `smart_core` server-owned platform database contract and production release orchestration
- Module: `smart_core`, production candidate contract, release scripts, deployment templates, ADR, and runbook
- Reason: make `sc_production` the explicit source of truth for both business and currently enabled platform data, removing the unsafe mismatch between a single-database deployment and an implicit `sc_platform_core` code fallback
- Standard vs User-Specific: generic current-production architecture and release safety; no construction-industry or customer-specific business semantics
- Why Here: P0 owns generic platform registry selection and release-gate behavior; P4 owns deterministic initialization, paired recovery, and release admission
- Why Not Elsewhere: frontend/Nginx client input cannot choose databases, industry/customer modules cannot redefine platform topology, and ops scripts cannot become platform data authority
- Blast Radius: platform policy/snapshot reads, production preflight, candidate configuration, snapshot initialization, and paired database/filestore recovery; no ACL, record rule, formal database, formal config, Nginx, attachment, deployment, traffic, or production service mutation
- Validation: 103/103 `smart_core` HttpCases completed (102 passed, one approved missing-demo-data skip), 45 client database/trust override requests safely served or rejected with zero HTTP 500 and zero invalid-database connections, colocated configuration and snapshot idempotency on an isolated production clone, paired backup validation and isolated restore equality for platform/business tables and filestore, production release-contract tests, and full `make ci`

## 2026-07-18 — TENANT-SEC-01

- Branch: `feature/security-product-history-customer-payload-closure`
- Starting product commit: `28d453420371b1a92f3401551834f32866955540`
- Formal Product Layer: P4 operations delivery governance
- Layer Target: product payload boundary, build/release defaults, and CI gates
- Module: repository-wide delivery tooling; no customer module is embedded
- Reason: remove customer payload from the public product tree and prevent reintroduction
- Standard vs User-Specific: generic product guard only; customer facts remain external
- Why Here: the public product repository owns its build and release boundary
- Why Not Elsewhere: a private customer module cannot enforce the public repository boundary
- Blast Radius: tracked payload paths, product/demo defaults, Docker context, release defaults, and CI

## 2026-07-18 — TENANT-PRO-03

- Branch: `feature/tenant-demo-seed-fixture-boundary`
- Starting product commit: `6b296068d6062c5f5f537a6ca813a6fe0c3c02ce`
- Formal Product Layer: P1 industry product reference baseline plus P4 initialization, demo, and acceptance tooling
- Layer Target: `smart_construction_seed`, `smart_construction_demo`, acceptance fixture carriers, and authoritative module sets
- Module: product seed/demo modules and repository delivery verification; no customer payload module
- Reason: separate production reference data, explicit demo data, and disposable acceptance fixtures
- Standard vs User-Specific: generic product and non-production test responsibilities only; customer baselines remain external P2 modules
- Why Here: these carriers own install triggers, environment guards, idempotency, and uninstall scope
- Why Not Elsewhere: P0 must not gain construction data, P2 remains private, and P3 is not an initialization carrier
- Blast Radius: manifests, data files, hooks, seed migration, Compose/Make/release module sets, and acceptance runners

## 2026-07-19 — TENANT-PRO-04

- Branch: `feature/tenant-historical-payload-import-v1`
- Starting product commit: `6b7ec6a667f297cca4d3788f0fd3b0633097b94e`
- Formal Product Layer: P4 operations delivery mechanism with a P2 private customer adapter
- Layer Target: generic payload schema, offline validation, database plan/import/verify, audit checkpoints, and filestore integrity
- Module: `smart_core` generic protocol plus repository delivery tooling; no customer facts or payload bytes are embedded
- Reason: separate customer configuration from signed, encrypted, repeatable historical data delivery
- Standard vs User-Specific: product-neutral mechanism in the product repository; field mappings and source compatibility in the private customer module
- Why Here: the product owns the fail-closed import protocol, audit state, stable external identity, and CI boundary
- Why Not Elsewhere: customer adapters cannot redefine product security or filestore semantics, and real payloads cannot enter Git or public CI
- Blast Radius: one platform audit model, external identity mapping, Make operations, synthetic customer fixture, private adapter declaration, and Gitee main mirroring guard
- System-bound verification: offline tamper matrix, read-only conflict plans,
  four checkpoint interruption stages, dedicated-role denial, paired
  database/filestore recovery, pure-product installation, and a second
  anonymous synthetic tenant using the same engine
- Containment decision: monetary precision normalization and implied-role
  expansion require explicit adapter policies; defaults remain exact and
  fail-closed

## 2026-07-19 — TENANT-BOUNDARY-06

- Branch: `refactor/product-customer-legacy-boundary`
- Starting product commit: `fc948924c31cb5b9184ef465d718433ad42914da`
- Formal Product Layer: P1 standard construction product plus external P2 customer legacy extension
- Layer Target: `smart_construction_core` ownership inventory and generic history-count evidence tooling
- Module: product audit tooling; the concrete legacy bridge remains in the private customer repository
- Reason: move customer historical facts, views, ACL, navigation, and source metadata out of the standard product without rebuilding historical tables
- Standard vs User-Specific: generic migration protocol remains product-owned; legacy carriers are external customer-owned
- Why Here: the product repository must prove that its own runtime and install closure are customer-neutral
- Why Not Elsewhere: customer code cannot enforce the product repository boundary, while concrete customer module names and rules must not enter product code
- Blast Radius: model registration, standard-model legacy fields, XML records, ACL/rules, navigation, seeds, reports, migrations, and historical upgrade compatibility
- First checkpoint: 64 direct carrier models counted on an isolated frozen history copy; private Bridge V1 installed with zero copied schema or records and zero pending modules
- Second ownership batch checkpoint: move four self-contained P2 history facts (`business.fact.residual`, `finance.auxiliary.fact`, `payment.adjustment.fact`, and `workflow.detail.fact`) with their views and ACL into the private legacy carrier; retain exact model/table/field names and use the neutral handoff namespace during upgrade.
- Formal Product Layer: P2 customer legacy carrier with a P4 ownership-transfer migration; no customer fact implementation remains in the P1 module for this batch.
- Why Here / Why Not Elsewhere: the facts encode old-source tables and audit payloads that are not construction standards; only the product migration stages existing XML identities so the private module can claim them without copying tables or records.
- Blast Radius: four model registrations, five customer view files, eleven ACL entries, related actions/menus, and their Odoo metadata identities; containment is proven by pure-product static checks and isolated history-copy double upgrade fingerprints.
- Third ownership batch checkpoint: move the customer-only old-source staging fact and user-priority menu-plan model, views, ACL, and navigation into the private P2 legacy carrier.
- Formal Product Layer / Layer Target: P2 customer history configuration with P4 in-place XML-ID handoff; P1 no longer registers these two models.
- Blast Radius: two model/table identities, their dedicated UI carriers, three ACL entries, and one audit-list inheritance; product migration `17.0.0.64` transfers metadata ownership without record writes.
- Fourth ownership batch checkpoint: move the customer migration inventory and historical income-invoice fact into the private P2 legacy carrier while retaining their existing tables and technical identities.
- Formal Product Layer / Layer Target: P2 customer migration evidence and historical finance fact; the P1 product keeps neither implementation nor navigation for these carriers.
- Blast Radius: two model/table identities, three dedicated view files, ten ACL entries, actions/menus, and inventory seed XML identities; product migration `17.0.0.65` stages metadata ownership only and performs no business-record writes.
- Fifth ownership batch checkpoint: remove the historical financing fact and its legacy ledger navigation while retaining the canonical product `sc.financing.loan` capability.
- Formal Product Layer / Layer Target: P1 keeps the standard financing workflow; P2 owns the customer historical financing table, read-only views, and compatibility actions.
- Blast Radius: one model/table identity, two dedicated view carriers, three ACL entries, legacy actions/menus, and audit-list metadata; product migration `17.0.0.66` transfers ownership without copying records.
- Frozen-history correction: `sc.legacy.legacy_source.fact.staging` has no physical table and no customer-adapter consumer, so it is `DEAD_OR_UNUSED`, not an owned historical carrier. Product migration `17.0.0.67` retires only its metadata and fails closed if any target database actually contains the table.
- Sixth ownership batch checkpoint: move both historical invoice report facts and their two SQL-ID-specific summary projections to the private customer carrier.
- Formal Product Layer / Layer Target: these projections encode old-source SQL identities and read only customer history tables, so they are P2 reports rather than P1 canonical analytics.
- Blast Radius: four model/view identities, three XML view carriers, eighteen ACL entries, and four compatibility actions; product migration `17.0.0.68` performs an in-place metadata handoff without record copies.
- Seventh ownership batch checkpoint: move the two old-source tender facts and their customer-history guarantee summary out of P1 while retaining canonical `tender.bid` and `tender.guarantee` product workflows.
- Formal Product Layer / Layer Target: P2 owns old tender source codes, raw-fact administration, and the history-only projection; raw history navigation is restricted to customer configuration administrators.
- Blast Radius: three model/view identities, three dedicated XML carriers, customer-scoped ACLs, one legacy menu, and compatibility actions; product migration `17.0.0.69` stages metadata only.
- Overnight Q10 correction: an older Odoo registry pass may materialize the already classified dead material-map table with zero rows. Migration `17.0.0.70` therefore fails closed on records, not mere empty-table existence, and deliberately performs no table or column drop.
- Formal Product Layer / Layer Target: P4 isolated upgrade guard for the P1-to-P2 ownership handoff.
- Why Here / Why Not Elsewhere: zero-row registry residue is upgrade orchestration state, not a customer business fact; the private adapter must not delete product-era schema and the product must not reinterpret any non-empty history.
- Blast Radius: one fixed legacy table existence/count probe; containment is proven by the frozen carrier fingerprint, schema-copy/record-copy counters, and two isolated upgrades.
- Q10 registry ordering correction: the product-owned `sc.optional.customer.projection` protocol is registered before all P1 projections that inherit it; no projection formula, SQL body, or customer adapter behavior changes.
- The package root also loads the projection package before importing any support submodule, because importing a support child executes the support package initializer and its projection consumers.
- Final placement: the abstract protocol lives at the `models` package root and is imported before `core`; this avoids Python package-initializer side effects while keeping all concrete reports in their existing P1 packages.
- Mixed partner split correction: the canonical product extension explicitly retains `_name = "res.partner"` while adding the generic delete-guard mixin, preventing Odoo from registering an accidental parallel `ResPartner` model and duplicate inherited many-to-many fields.
- Projection handoff guard: an explicit isolated-upgrade environment flag preserves existing non-view projection relations until the external P2 module takes ownership. Outside that audited handoff, the P1 empty-projection mechanism fails closed on relation-type conflicts.
- Contract mixed-file closure: automatic category text now uses canonical `subject`, `name`, and `note` only. The module-init legacy amount fallback writer is removed rather than recalculating frozen historical amounts, so P1 no longer reads P2 evidence fields and Q10 can prove zero amount drift.
- Settlement formal identity closure: record-name search and display dependencies use canonical project, partner, settlement unit, contract subject/name, and formal amounts only; customer history text is no longer a P1 fallback.
- Formal form-contract closure: remove 51 `legacy_*` field entries from the P1 view-orchestration seed. Standard sections and canonical fields remain; P2 history fields are available only through the private audit surface.
- Product XML surface closure: remove 319 customer-history field widgets across 40 P1 view files, including two inline project audit labels; model/table columns and historical records are untouched.
- Partner view split: remove private history-derived `sc_business_role_label` and `sc_business_fact_basis` widgets/groupings from P1 customer and supplier views. Canonical Odoo ranks and P1 supplier types remain the standard product identity surface.
- Expense-claim form closure: remove the customer migration-source notebook page after its P2-owned identity field left the product view. Canonical responsibility and attachment pages remain unchanged.
- Receipt-income form closure: retain the canonical treasury-ledger page while removing its customer migration-source visibility dependency and label.
- Remaining P1 source-surface closure: remove four migration-only notebook pages and stop loading the customer-confirmed historical form extensions from the standard product manifest; canonical business pages remain loaded.
- Mixed seed split correction: restore P1 approval-policy seeds and canonical contract tier callbacks for fresh installs; only the retired historical purchase policy and callbacks remain in the private legacy carrier.
- Reference-closure split correction: return the standard material-outbound category and canonical contract callback group restrictions to P1; the P2 closure no longer owns or references those product identities.
- Partner-import review closure: remove its ACL and generated form-orchestration record from P1; both belong to the private customer legacy carrier with the unchanged model and XML identities.
- Q11 released-navigation closure: My Work and financial relationship links now use the P1 canonical payment semantic route or a record-authoritative route instead of coupling to removed raw menu/action entries. P4 browser fixtures resolve their targets from the released navigation contract.
- Formal Product Layer / Layer Target: P1 construction navigation contract with P4 acceptance adapters; module `smart_construction_core` and generic verification scripts.
- Standard vs User-Specific / Why Here: every standard construction deployment consumes the same released navigation and ORM authorization result; no customer identity, path, or preference is introduced.
- Why Not Elsewhere / Blast Radius: P0 does not own payment semantics and P2 must not repair standard navigation. The change is limited to payment quick links, financial relationship links, and acceptance target resolution; released-navigation, page-identity, finance, My Work, boundary, build, and role-journey gates contain it.
- Q11 role-semantics correction: J12 contract editing now uses an acceptance-only contract operator carrying the existing P1 `group_sc_role_operation_user`; PM remains contract-read-only as required by the authoritative role matrix. No ACL, record rule, production seed, or customer role changes.
- Q11 low-code acceptance closure: two acceptance-only users carry the existing P1 business-configuration administrator role so change-set preview, atomic publish, isolation, rollback, and ordinary-user denial are exercised without legacy accounts or fixed production credentials. Runtime targets are the current canonical contract action/menu resolved from product XML-IDs.

## 2026-07-20 — CLEAN-REPO-01G Gitee WebHook CI

- Branch: `fix/clean-repository-ci-governance`
- Starting product commit: `f01710c926188c4f7b482068bc491880c57a628d`
- Formal Product Layer: P4 operations delivery tool
- Layer Target: Gitee WebHook authentication, normalized CI queue, exact-SHA checkout, and server service isolation
- Module: `scripts/ci`, `scripts/verify`, `deploy/gitee-ci`, and Make governance entry points
- Reason: run repository guards on the existing Huawei CI node without GitHub billing or Gitee Go build minutes
- Standard vs User-Specific: product-neutral repository governance; no customer code, payload, credential, or business semantic is introduced
- Why Here: repository CI owns event admission, source identity, immutable checkout, cleanup, and evidence retention
- Why Not Elsewhere: Gitee must not execute builds, product modules must not own delivery orchestration, and production hosts must not accept ordinary Push events
- Blast Radius: one loopback service on `1.95.2.123` exposed only through an exact-path Nginx HTTPS proxy, a dedicated unprivileged account/deploy key, SQLite idempotency state, lightweight clean-history gates, and no RC/attachment/production entry point
- System-bound verification: 11 signed WebHook positive/negative tests covering header and query transport, server systemd activation, loopback and trusted public HTTPS health probes, unsigned public request denial, fixed repository/sender allowlist, replay denial, fork denial, SHA injection denial, secret environment isolation, and pre-write Gitee scope validation
- External state: Nginx 1.24 and Certbot 5.7 are active; Let's Encrypt issued the short-lived IP certificate and the renewal timer is enabled. Gitee Deploy Key `5932346`, signed WebHook `2106026`, protected `main`, and governance PR `#1` are configured. The built-in Gitee test payload is intentionally denied by the repository allowlist; a real same-repository Push is the authoritative end-to-end probe.
- End-to-end result: the real PR event for `736a310ab4f5a0844797d8178a34e3b92cc3320a` passed with exact-SHA checkout, release scan 12/12, exit code 0, workspace cleanup, and zero credential markers in retained CI logs.

## 2026-07-20 — CLEAN-REPO-01G Gitee-to-GitHub Mirror

- Branch: `fix/gitee-github-mirror-governance`
- Starting product commit: `a8b490da148b6926cb51a88be6131d0a9c7d5fea`
- Formal Product Layer: P4 operations delivery tool
- Layer Target: Gitee-authoritative, exact-SHA, fast-forward-only GitHub main mirroring
- Module: `scripts/ci`, `scripts/ops`, `scripts/verify`, `deploy/gitee-mirror`, Make governance, and ops documentation
- Reason: keep GitHub and Gitee on one commit history without permitting GitHub-side PR merges or ordinary direct pushes
- Standard vs User-Specific: repository governance only; no product function, customer module, attachment, RC image, or production deployment
- Why Here: the CI worker proves the Gitee main candidate, a credential-free bare repository hands it off, and a separate service exclusively owns the GitHub write key
- Why Not Elsewhere: the receiver must not hold repository credentials, build code must not read the GitHub key, and GitHub must not become an independent write path
- Blast Radius: one repository Ruleset, one write Deploy Key, one unprivileged mirror account, one oneshot/timer, the Gitee-only PR push guard, and fixed fresh-clone validation
- System-bound verification: exact repository allowlist, exact SHA push, ancestor check, force-free negative tests, active Ruleset readback, unique write Deploy Key, worker-key denial, mirror-key access, idempotent timer execution, dual fresh clones, identical SHA/tree/branches/tags, and 12/12 release scans

## 2026-07-20 — TENANT-RC-01 Pure Product Candidate

- Branch: `release/tenant-rc-01-product-image`
- Starting product commit: `db31271c286e3a898d8882242cac5c3940484a66`
- Formal Product Layer: P4 release delivery tooling assembling the P0/P1 product set
- Layer Target: immutable product image, formal lifecycle entry points, external customer package admission, isolated profile acceptance, and recovery evidence
- Module: `make/release.mk`, `scripts/release`, `scripts/verify`, candidate Dockerfiles, and the frozen product module-set configuration
- Reason: produce one customer-neutral image that can be installed and upgraded without hand-built module lists, while admitting customer modules and payloads only through a fail-closed external protocol
- Standard vs User-Specific: the repository owns only the generic product and delivery protocol; synthetic payloads are test-only and `<PRIVATE_CUSTOMER_MODULE>` code/data remain in authorized private storage
- Why Here / Why Not Elsewhere: image assembly and admission checks are P4 responsibilities; P0/P1 modules remain the product facts, and no customer semantics enter platform, industry, frontend, or low-code layers
- Blast Radius: product module closure, production static assets, candidate container contents, isolated databases, external read-only mounts, release reports, and no production or 175GB attachment writes

## 2026-07-20 — NAV-PRO-01 Product Navigation Exposure

- Branch: `release/tenant-rc-01-product-image`
- Starting product commit: `43a30985a4eb`
- Formal Product Layer: P1 construction-product exposure policy, P0 generic authorization projection, P4 verification
- Layer Target: matrix-derived primary navigation, contextual route authority, and fail-closed native-menu intersection
- Module: `smart_construction_core`, `smart_core` delivery/identity services, shared frontend router/session, and NAV-PRO-01 audit/verification tooling
- Reason: replace historical 70/80 menu-count assumptions with the 324-row authoritative role/menu matrix and expose only task- or journey-backed primary entries
- Standard vs User-Specific: standard construction role policy; no customer identity, preference, payload, production data, or low-code override
- Why Here: P1 owns role/menu product decisions, P0 owns identifier-only projection and contract transport, the frontend consumes the delivered authority without inferring business semantics, and P4 proves the result
- Why Not Elsewhere: platform code must not encode construction roles or XML-ID sets, the frontend must not infer authorization from labels/models, customer modules must not repair the standard product, and ops scripts must not become runtime policy
- Blast Radius: four formal roles, 138 authorized role/menu assignments, 31 primary/home assignments, 100 contextual assignments, 7 explicit denials, two stale legacy action domains, shared route admission, and no ACL or record-rule expansion
- Validation: deterministic matrix regeneration, Python syntax, frontend lint/strict typecheck, Odoo role-surface tests, native visibility, HTTP contract/data probes, browser primary/contextual navigation smoke, and zero HTTP 5xx
- Browser closure: contextual authorities carry native action metadata and seed `currentAction` before route rendering, preventing an async metadata transition from trapping hidden contextual actions in a blank-page render loop while keeping those menus out of the primary tree.
- RC gate closure: replace the stale 70/80-leaf page-audit constants with the NAV-PRO-01 primary/home denominator (finance 10, project member 7, PM 10, owner 4; total 31). The audit accepts both demo and fixture login prefixes but fails closed on unknown roles, while the tenant RC verifier requires the exact four fixture-role counts and 31/31 identity/reachability evidence.
- RC journey closure: J02 proves the released payment entry by exact database-exported action/menu IDs because the wire navigation does not carry action XML-IDs. RC page-identity evidence remains external under `CANDIDATE_ARTIFACTS`; the runner no longer rewrites the repository's versioned demo inventory.
- J03 scope closure: the project-member journey opens the released project-ledger action resolved from `menu_sc_project_project`, rather than bypassing the primary navigation contract through the legacy `/s/projects.list` scene route.
- Shared acceptance closure: page identity, financial workspace, My Work, delivery hardening, and core-form journeys resolve released targets by stable menu XML-ID and consume the delivered action/menu IDs. Runtime target exporters use the menu's formal action directly instead of substituting the retired generic payment action.
### 2026-07-21 — RC runtime mutable-fixture isolation

- Continued the tenant RC runtime gate after navigation-target alignment.
- Root cause for the J07 failure: J06 submitted the same `FE-JOURNEY-PAYMENT-001` row that J07 subsequently expected to remain in draft.
- Added a dedicated J06 settlement/payment-request pair and kept J07 on its original deterministic row. This is acceptance-fixture isolation only; no production domain, permission, or workflow semantics changed.
- J07 then passed and exposed a separate J08 navigation-contract defect: the settlement entry action carried the payment action with the settlement menu context, which the released navigation authority correctly denied.
- Corrected the projected entry route to use the released payment menu and that menu's own action. This changes P1 navigation context only; it does not change create ACLs, finance capability checks, defaults, or payment workflow semantics.
- Updated the FE-B05 static guard from the retired native-dialog ref marker to the current shared `ScDialog` open-state marker; the guard continues to assert confirmation behavior without pinning an obsolete implementation detail.
- On the rebuilt candidate, J08 reached the authorized create form and exposed duplicate native field projections. Scoped the browser assertions to the first rendered project/contract/settlement field instance; no form values or production rendering behavior changed.
- The next rebuilt-candidate J08 run confirmed that the payment request form consistently projects multiple amount inputs as well. Scoped the post-refresh amount assertion to the first rendered projection so Playwright strict mode does not reject equivalent field instances.
- The following J08 run completed create/save/refresh/submit, then exposed that the shell's empty-menu guard hid `/my-work` from the executive approval role even though My Work is a shell-native route. Allowed the My Work route and its scene alias to render with an empty menu tree; backend approval capabilities, record rules, and menu authority remain unchanged.
- With the shell route fixed, J08 reached the executive decision and exposed a split authority check: the intent handler and approval policy admitted executive/finance-approver roles while `payment.request` admitted only the finance-manager capability. Aligned the model guard to the same three explicit approval authorities and added negative coverage for ordinary internal users; record scope and workflow prerequisites remain unchanged.
- After J07/J08 passed, J10 exposed a fixture sequencing collision: J07 had already submitted the draft record that J10 expected in the todo section. Added a dedicated draft payment request for delivery-hardening journeys and made the browser assertions consume its exported display identity, isolating J09-J11 from prior workflow mutations.
- The isolated J09-J11 record passed the prior collision point; the responsive matrix then hit the same repeated amount-field projection already observed in J08. Scoped every delivery-hardening amount readiness probe to the first equivalent projection, including the optional accessibility and performance paths.
- The rebuilt candidate passed J09-J11 with all 72 responsive checks and zero blocking accessibility findings, then exposed that J12 pinned the retired merged contract menu XML-ID. The contract operator's released tree still exposes the same authoritative contract action through its role-projected entry, so J12 now resolves that delivered action/menu pair by action XML-ID; payment journeys retain exact menu XML-ID selection where multiple payment entries share an action.
- The action-based probe then confirmed that release-navigation wire nodes intentionally omit action XML-IDs. J12 now selects the contract operator's actual primary `menu_sc_contract_center` node by menu XML-ID and consumes its delivered numeric action/menu pair; it no longer depends on either the retired child menu or absent wire action metadata.
- J12 then passed its dirty guard, save, and authoritative reload checks. J13 exposed one final fixture collision: the existing-record conflict scenario reused the J06 payment request after J06 had submitted it, leaving no editable amount input. Added a dedicated draft core-form request and exported it separately so J13 conflict recovery is isolated from financial-workspace and approval mutations.

## 2026-07-21 — NAV-PRO-01R Explicit Route Authority

- Branch: `release/tenant-rc-01-product-image`
- Starting product commit: `2d9d187d391cfe2c1c6e085a0a96ba6d27f20793`
- Formal Product Layer: P0 generic route-authority transport/runtime enforcement, P1 construction role policy, shared frontend consumer, and P4 verification
- Layer Target: one fail-closed `route_authority.v1` contract separating `PRIMARY_NAV`, `ROLE_HOME_ACTION`, `CONTEXTUAL_ROUTE`, `ADMIN_ROUTE`, and `DENIED`
- Module: `smart_core` identity/delivery/intent handlers, `smart_construction_core` policy declarations, frontend session/router/shell, and NAV-PRO-01R verification tooling
- Reason: backend execution permission alone does not authorize a frontend page; administrator-only and context-only pages require explicit, stable route authority without entering the business menu tree
- Standard vs User-Specific: generic product mechanism plus standard construction role declarations; no customer model, payload, login identity, production record, attachment, or private module enters the contract
- Why Here: P1 declares role/action XML-IDs and context requirements, P0 intersects declarations with native visibility and model ACLs and validates record scope, and the frontend consumes only the delivered principal-scoped authority
- Why Not Elsewhere: the frontend must not infer authorization from numeric IDs, labels, models, usernames, roles, menus, or successful data requests; test tooling must not become runtime policy
- Blast Radius: system/configuration administrator access to the existing user-and-role page, PM access to the existing contract-income-execution relation route, session/context/policy-refresh cache invalidation, and no ACL, record-rule, workflow, amount, status, or primary-navigation expansion
- Validation: route-authority unit and policy split guards, 13 Odoo post-tests, 31/31 primary browser regression, 100/100 contextual contract checks, administrator and context direct-route browser probes, four-role administrator denial, cross-company/project/contract denial, zero unauthorized page-data requests, zero HTTP 500, production frontend build, and repository diff checks
- New-image runtime correction: J08 proved that the valid shell-only `executive` role received an empty principal scope when it intentionally declared no action exposure. The contract now binds an empty action/menu set to the authenticated user, company, and role, allowing session bootstrap without granting any implicit route; backend and frontend regressions reject every mismatched principal.

## 2026-07-21 — TENANT-RC-01B1 Product Payload Boundary

- Branch: `release/tenant-rc-01-product-image`
- Starting product commit: `2d9d187d391cfe2c1c6e085a0a96ba6d27f20793`
- Formal Product Layer: P4 generic external tenant-package admission and RC profile execution
- Layer Target: remove fixed tenant identity while retaining fail-closed, signed, manifest-declared external add-on and payload admission
- Module: product lifecycle, authorized payload exporter, generic RC profile runner, package preflight, repository boundary Guard, and their negative tests
- Reason: a product repository and candidate image must understand only the external tenant-package protocol, never a named tenant, fixed archive, fixed snapshot, or module inferred from a local prefix scan
- Standard vs User-Specific: only generic schema, signature, compatibility, checksum, module-set, extraction, and zero-write admission behavior remain; every tenant value and private profile stays outside the product repository
- Why Here / Why Not Elsewhere: P4 owns package admission and release orchestration; customer identities and execution profiles belong to signed external manifests or private delivery storage, not product code or public history
- Blast Radius: five existing boundary findings, one narrowly scoped negative-test allowance, lifecycle module counting from the signed declaration, and no product ACL, business data, production database, attachment, or customer payload mutation
- Validation: fixed module/tenant/archive rejection, signed arbitrary module admission, tampered signature rejection, missing-manifest pre-I/O failure, redacted logs, generic-prefix placeholder allowance, release tooling tests, and product payload boundary Guard

## 2026-07-21 — REL-VERSION-01M Product Release Baseline

- Branch: `release/tenant-rc-01-product-image`
- Formal Product Layer: P4 release identity, immutable image metadata, external customer-package compatibility admission, and runtime information projection
- Layer Target: one repository `VERSION` source feeding release configuration, OCI labels/tags, runtime identity, customer compatibility, SBOM-linked release manifest, and lightweight release gates
- Scope Boundary: no database release ledger, schema field, workflow/state change, customer identity, private package content, production write, attachment mutation, or deployment
- Runtime Contract: `system.init` exposes only `product_version` and `source_revision`; the frontend system HUD reads both without exposing internal paths or environment variables
- Build Contract: one versioned source SHA produces the human version tag and short-SHA tag in one Docker build; deployment remains digest-addressed and save/remove/load must preserve both tags and the image ID
- Customer Compatibility: the signed external manifest declares an inclusive minimum, exclusive maximum, and required generic contracts; incompatibility fails before archive extraction or database access

## 2026-07-21 — USER-MODULE-PRODUCT-CLOSURE-01

- Branch: `release/tenant-rc-01-product-image`
- Starting product commit: `a322a85fa76ada9879c5fc6ee9ff08083d564515`
- Formal Product Layer: P1 construction-product user, personnel, organization, project-membership, and profile-document capability
- Layer Target: close the standard product capability gaps without importing legacy profile, scope, staging, customer identity, or cross-database identifiers into runtime models
- Module: `smart_construction_core`
- Standard vs User-Specific: generic construction deployment capabilities only; historical identity selection and mappings remain external P4 evidence/data-owner inputs
- Why Here / Why Not Elsewhere: every construction deployment needs governed personnel and project membership; these are not P0 platform semantics, customer preferences, frontend inference, or low-code configuration
- Blast Radius: controlled `res.users`/`hr.employee` linkage, company-scoped employee maintenance, auditable project-member assignments backed by existing followers, scoped profile documents, runtime user views, and targeted permission/regression tests
- Migration boundary: `sc.project.member.staging` and its 23,190 rows, 7,860 references, and 6,803 locators are archive-only; approved formal identity mappings never use old database auto-increment IDs

## 2026-07-21 — REPO-GOVERNANCE-GITHUB-AUTHORITY-02

- Branch: `fix/github-authority-governance`
- Starting commit: `aaad9e06d5e0d70d92041b65b8a4ae9003fb7cda`
- Formal Product Layer: P4 repository and continuous-integration governance only
- Layer Target: make `lidefend/sce-backend-odoo` the explicit GitHub authority while keeping authorization fail-closed and actor-independent
- Module: GitHub Actions workflows, repository security guard and tests, safe-push/mirror tooling, CODEOWNERS, and repository governance documentation
- Reason: the authoritative repository moved from `Leedefend/sce-product-odoo`; the former fixed repository and actor identities prevented required checks from running under the new authority
- Standard vs User-Specific: repository governance constants and auditable trust rules only; no user-module product behavior, tenant payload, production data, or customer-specific policy changes
- Why Here / Why Not Elsewhere: P4 owns repository identity, CI admission, push direction, and mirror policy; product modules must not encode source-host ownership or CI actors
- Blast Radius: workflow admission and checkout, public governance verification, GitHub branch-push safety, GitHub-to-Gitee fast-forward mirroring, and documentation; no runtime, database, deployment, image, or migration impact
- Validation: workflow YAML parsing, authorization positive/negative tests, public guard, generated-report guard, safe-push self-tests, shell syntax, sensitive-data scan, and product-diff isolation

## 2026-07-21 — PRODUCTION-RELEASE-CONTRACT-HARDENING-06

- Branch: `fix/production-release-contract-hardening`
- Starting commit: `fd7ac52b7ee2d8d5588804a69cdaf68bc7c82312`
- Formal Product Layer: P4 operations delivery tooling and release contract only
- Layer Target: immutable production image inputs, fail-closed runtime database admission, explicit database lifecycle entrypoints, and isolated persistent volumes
- Module: production candidate Dockerfile/Compose, Odoo entrypoint/config, release Make targets, contract tests, and bilingual operations documentation
- Reason: remove nondeterministic image upgrades and implicit database bootstrap while making `sc_migration_rehearsal`, `sc_production`, and archived `sc_prod` boundaries mechanically auditable
- Standard vs User-Specific: repository-wide production delivery safety mechanism; no platform, construction-domain, customer preference, low-code, or business-data semantics
- Why Here: P4 owns build, startup, release orchestration, database lifecycle gating, and verification without becoming a product fact authority
- Why Not Elsewhere: no Odoo product module or frontend layer should decide image provenance, create databases, or encode operator release approval
- Blast Radius: production candidate image and future explicit lifecycle commands only; no existing server, database, attachment, TLS, Nginx, business model, ACL, record rule, or frontend behavior
- Validation: registry digest verification, static and negative contract tests, Compose parsing, repository CI, isolated image build, fail-closed missing-database probe, explicit temporary-database lifecycle, precise local resource cleanup, and a fail-closed `PR_DRAFT=0/1` option on the existing governed PR creation target

## 2026-07-21 — PRODUCTION-RELEASE-CONTRACT-HARDENING-06R1

- Branch: `fix/production-release-contract-hardening`
- Starting commit: `a2b68823bc01e88bb1f8bcadfebafc5f2f05a30c`
- Formal Product Layer: P4 operations delivery tooling only
- Layer Target: invocation-owned database initialization compensation and safe retry
- Module: explicit production database manager, isolated image acceptance, release contract tests, and bilingual operations documentation
- Reason: an Odoo `base` initialization failure after `CREATE DATABASE` must not leave a half-initialized database that blocks a guarded retry
- Standard vs User-Specific: generic release safety; no product, tenant, business-data, server, or environment-specific semantics
- Why Here / Why Not Elsewhere: P4 owns explicit lifecycle compensation; normal runtime, product modules, frontend, and database schema must not expose or infer destructive cleanup authority
- Blast Radius: only a database proven to have been created by the current `init` invocation; pre-existing and reserved databases remain immutable to this path
- Validation: pre-existing preservation, no cleanup before successful creation, injected Odoo failure cleanup, retry success, cleanup-failure fail-closed behavior, production confirmation revalidation, full CI, and isolated image lifecycle cleanup

## 2026-07-22 — R11F0S Independent Permission Test Gates

- Branch: `fix/preexisting-permission-test-gates`
- Starting commit: `e276e93745c2f8788c74350953ab58e4a2888ebb`
- Formal Product Layer: P4 governance validation and P1 permission/record-rule test contracts
- Layer Target: remove a migration-only model from the formal ACL matrix and align record-rule fixtures with existing company and settlement-direction constraints
- Module: `smart_construction_core` tests only
- Standard vs User-Specific: repository-wide security gates; no customer data, runtime configuration, or new business capability
- Why Here / Why Not Elsewhere: tests must describe the registered formal runtime and valid business fixtures without changing production ACLs, record rules, or domain constraints
- Blast Radius: ACL and record-rule tests only; no model, security definition, locked baseline, production data, snapshot, runtime, or image mutation
- Validation: ACL matrix and real-model drift probe, settlement multi-company visibility, invalid-direction rejection, `sc_perm`, release contracts, baseline integrity, and full CI

### R11C locked-menu transfer record

- Original files: `addons/smart_construction_core/services/locked_menu_policy_contract.py`, `addons/smart_construction_core/models/support/product_policy_sync.py`, and `scripts/release/test_locked_menu_policy_contract.py`
- Original failure: the R11C-only initialization specification treated the unresolved “外经证登记” entry as the runtime model `sc.legacy.payment.residual.fact`
- Root cause: an unapproved legacy/menu-contract entry was duplicated as a resolvable runtime action specification
- Required R11C repair: remove the invented runtime model specification, retain the stable menu/action identity as `BUSINESS_DECISION_REQUIRED`, and reject it before resolving any historical database action
- Target branch: the future clean R11C branch recreated from the then-current `main`; this replacement branch intentionally contains no locked-menu code
- Fixed boundaries: do not create `sc.legacy.payment.residual.fact`, do not bind `sc.invoice.registration`, do not alter the 97-entry baseline, and keep formal initialization fail-closed until the business disposition is approved

## 2026-07-23 — R11C Locked Menu Policy Initialization Repair

- Branch: `fix/r11c-locked-menu-policy-repair`
- Starting commit: `84db202b4732d3509cab7b796feec7d5ee0a18f3`
- Formal Product Layer: P1 construction industry menu baseline plus P4 release initialization and immutable image packaging
- Layer Target: one versioned, checksummed locked-menu contract shared by formal policy synchronization, snapshot initialization, and the production menu release guard
- Module: `smart_construction_core`, production candidate Dockerfile, colocated snapshot initializer, and isolated release-contract acceptance
- Reason: first deployment silently lost the locked baseline inside the production image, generated a 214-entry catalog fallback policy, and froze that candidate policy before comparing it with the 97-entry repository release contract
- Standard vs User-Specific: construction standard/preview release policy only; no customer preference, low-code override, production data baseline, or frontend behavior
- Why Here: P1 owns the construction menu contract and its stable XML-ID identity; P4 packages and applies that authority transactionally during first deployment
- Why Not Elsewhere: P0 snapshot infrastructure remains generic, the frontend cannot choose product menus, runtime configuration cannot replace a versioned release contract, and production data is not a policy authority
- Blast Radius: formal initialization of `construction.standard` and `construction.preview`, candidate image contract contents, and guard normalization; catalog fallback remains available only to explicitly non-formal development flows
- Validation: locked baseline missing/invalid/product/normalization negatives, numeric-ID independence, pre-resolution `BUSINESS_DECISION_REQUIRED`, transactional rollback without policy/action/model/snapshot mutation, standard/preview isolation, repeatable fail-closed initialization, candidate-image contract acceptance, release-contract tests, and full CI

## 2026-07-23 — R11F1 Fund Legacy Read-Only Archives

- Branch: `fix/r11f1-fund-legacy-readonly-archive`
- Starting commit: `66e9e663f7b754dca56765eea11d4c25e1ede91c`
- Formal Product Layer: P1 construction industry standard
- Layer Target: L2 finance-domain historical archive model boundary plus native Odoo XML entry surfaces
- Module: `smart_construction_core`
- Reason: oil-card registration and recharge registration are approved historical archives, not new fund-processing workflows; each needs a stable, source-isolated and server-enforced read-only entry
- Standard vs User-Specific: construction product standard; no tenant preference, production data mutation, frontend-only policy, or platform-core behavior
- Why Here: the owning finance-domain model must enforce immutable archive identity, while its module-owned XML defines the stable actions, menus and dedicated read-only views
- Why Not Elsewhere: P0 snapshot governance cannot enforce record mutation safety, frontend context is not a security boundary, and P4 release tooling is not a business-model authority
- Blast Radius: only the exact `online_old_legacy_direct:direct_acceptance` oil-card and recharge source pairs, their finance-read entry surfaces, and company-scoped access; ordinary `sc.fund.account.operation` workflows remain writable under their existing roles
- Validation: stable XML identity, fixed distinct domains, server-side create/write/unlink/workflow denial, finance-read access, non-finance exclusion, multi-company isolation, ordinary fund workflow regression, clean-database module loading, release contract tests, and full CI

## 2026-07-23 — REL-SHA-01 Formal Release Source Identity Binding

- Branch: `fix/rel-sha-source-identity-binding`
- Starting commit: `2b4b3fea350a0835600fb4c3f16a079add4544ec`
- Formal Product Layer: P4 operations delivery tooling
- Layer Target: formal repository admission, immutable candidate source identity, release manifests, and deployment-time artifact identity
- Module: release Make targets, candidate build/scan scripts, production candidate Compose, and production database lifecycle contract
- Reason: remove the stale candidate SHA default and require the approved repository, clean HEAD, authoritative remote main, explicit source SHA, OCI revision, container revision, image manifest, release manifest, image digest, and deployment input to resolve to one identity
- Standard vs User-Specific: repository-wide formal release safety mechanism; no platform runtime behavior, construction business semantics, customer preference, low-code configuration, or production data
- Why Here: P4 owns source admission, artifact generation, manifest custody, and deployment guards
- Why Not Elsewhere: product modules and frontend code must not infer repository identity or authorize deployment artifacts
- Blast Radius: formal candidate build/scan and guarded database lifecycle commands only; no image is built, no database is created, and no environment is deployed by this change
- Validation: explicit/full SHA, exact repository remote, clean worktree, HEAD/remote-main equality, old-SHA rejection, OCI/container/manifest/digest equality, manifest checksum, missing-input negatives, release contract tests, and one standard pre-PR CI run

## 2026-07-23 — R11F2 Formal Tax Certificate Registration

- Branch: `fix/r11f2-tax-certificate-registration`
- Starting commit: `5ee305a060767f4039d7b3c54b90990b43116ca6`
- Formal Product Layer: P1 construction industry tax-center product capability with P4 initialization contract alignment
- Layer Target: independent formal registration and inquiry lifecycle for cross-region tax certificates
- Module: `smart_construction_core` model, views, stable action/menu identity, role ACLs, multi-company/project record rules, locked product baseline, and focused verification contracts
- Reason: the approved business decision requires “外经证登记” to be an independent tax matter rather than an invoice-registration variant, a legacy runtime model, or a historical read-only downgrade
- Standard vs User-Specific: construction standard/preview formal product capability; no tenant preference, customer data, historical migration, or production initialization
- Why Here: P1 owns the formal tax business model and stable entry identity; P4 consumes the same locked 97-entry product contract during formal initialization
- Why Not Elsewhere: `sc.invoice.registration` has a different lifecycle, `sc.legacy.payment.residual.fact` is forbidden, and release-source identity plus existing `ci.full` reason-code debt remain independent workstreams
- Blast Radius: one approved tax-center entry in each locked 97-row baseline, its independent records, views, roles, company/project visibility, and transactional initialization expectations; no release SHA tooling, production database, image, runtime, or historical data
- Validation: static model/action/menu/ACL/rule/baseline/checksum contracts, locked-menu policy tests, legacy-carrier and baseline-integrity guards, targeted module initialization attempt, standard pre-PR CI, and PR-bound required checks
