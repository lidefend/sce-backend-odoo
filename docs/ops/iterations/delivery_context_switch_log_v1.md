# Delivery context switch log v1

This log records current product-repository implementation context only. Historical
customer delivery evidence belongs in private customer or payload repositories.

## 2026-08-01 — Isolated restore filestore permission repair

- Branch: `fix/restore-rehearsal-volume-permissions`
- Starting product commit: `3fb17948feacb34c2574668eaba7ddb2ad4bef26`
- Formal Product Layer: P4 ops delivery tool
- Layer Target: governed production backup restore rehearsal
- Module: `scripts/release/production_backup_restore.py` and its contract tests
- Reason: immutable RC images run as the unprivileged `odoo` user, which cannot
  initialize the root-owned filesystem of a newly created rehearsal volume
- Standard vs User-Specific: repository-wide recovery safety; no customer data,
  application behavior, database semantics, or production runtime policy
- Why Here / Why Not Elsewhere: P4 owns isolated recovery resource preparation;
  application images must retain their non-root runtime identity and product
  modules must not compensate for host volume ownership
- Blast Radius: only the network-disabled filestore extraction container runs as
  uid/gid 0; the Odoo health container remains on the image's unprivileged user,
  and production database, network, volumes, backup artifacts, and cleanup
  authorization remain unchanged
- Validation: 42 backup/restore contract tests, extraction-user assertion,
  unprivileged Odoo health-container assertion, Python compilation, and diff checks

## 2026-07-31 — CONTROLLED-MAIN-CUTOVER-01 governance capability

- Formal Product Layer: P4 ops delivery tool
- Layer Target: governed dual-remote main history cutover and external recovery bundle
- Module: `make/codex.mk`, `scripts/ops`, `scripts/verify`, SCM governance documentation
- Reason: the frozen clean-history candidate cannot replace divergent GitHub/Gitee
  `main` safely through the existing fast-forward-only mirror target
- Standard vs User-Specific: repository-wide SCM governance; no customer data,
  application behavior, database, filestore, runtime configuration, or production deployment
- Why Here / Why Not Elsewhere: P4 owns publication state, exact leases, protection
  snapshots, paired rollback and recovery evidence; P0-P2 product modules must not
  own or invoke repository history mutation
- Blast Radius: one explicit Make target, one fail-closed operation script, focused
  tests and governance documentation; default mode performs zero writes and apply
  requires exact live SHAs, four successful checks, a private Gitee token and an
  external immutable bundle

## 2026-07-30 — Standard product field publication cleanup

- Branch: `fix/field-arch-p0-02-formal-contracts`
- Starting product commit: `48e4f359c22f3d6ebdca1b4704a429bd8514712c`
- Formal Product Layer: P1 construction product contracts, with P0 generic renderer cleanup
- Layer Target: formal model fields, views, list profiles, search/export contracts, and clean product bootstrap
- Module: `smart_construction_core`, generic `smart_core` contract handlers, Web field-label consumer, upgrade migration, and purity guard
- Reason: the product is newly developed and has no legacy customer compatibility obligation; hashed migration aliases must not become product fields or runtime contract identities
- Standard vs User-Specific: product modules contain only stable formal fields; historical business data and its source mapping belong to the separate private P2 user-data carrier
- Why Here / Why Not Elsewhere: P1 owns construction field semantics and formal views; P0 only removes construction-specific alias interpretation. Customer payload modules, product UI, and runtime contracts must not register or publish each other's fields
- Blast Radius: removes non-stored alias declarations, alias-only views, dynamic contract injection, customer backfill scripts, and stale registry metadata on product upgrade; does not delete business records, physical business columns, `x_custom_field*`, permissions, workflows, or customer data modules
- Validation: product-source purity, formal list profiles, Odoo view/contract tests, fresh install, upgrade cleanup, frontend strict/lint/build, semantic regression, and diff checks

## 2026-07-24 — Immutable resumable RC publication contract

- Branch: `fix/atomic-release-publication-contract`
- Starting product commit: `378b1c49543b08e95a5f4007ada481360fd3822a`
- Formal Product Layer: P4 operations delivery tooling
- Layer Target: externally visible RC publication transaction admission and evidence custody
- Module: release Make entry, publication orchestrator/state machine, report/plan schemas, mock contract tests, and bilingual runbook
- Reason: replace the legacy manifest-mutating image push with a recoverable registry/tag/Release workflow that never invalidates accepted candidate evidence
- Standard vs User-Specific: repository-wide release safety; no application, customer, runtime, or database semantics
- Why Here / Why Not Elsewhere: P4 owns registry/SCM publication and cross-system recovery; candidate evidence, application modules, production configuration, and deployment tooling must not absorb or emulate publication state
- Blast Radius: publication preflight, registry digest verification, GitHub/Gitee annotated tags, GitHub prerelease creation, per-version publication locking, and publication-only evidence; no real publication, deployment, production access, candidate mutation, main push, or mirror
- Validation: candidate immutability, full preflight no-side-effect, state transitions, partial-stage resume, digest/tag/Release identity, concurrency, atomic report/index, schema, path/shell/secret safety, formal Release Contract, CI, and diff checks

## 2026-07-24 — Atomic candidate retry attempt evidence isolation

- Branch: `fix/release-candidate-attempt-evidence-isolation`
- Starting product commit: `530d40bf701adf1d9e1c3fa4cd2eac96ce901871`
- Formal Product Layer: P4 operations delivery tooling
- Layer Target: immutable retry attempt identity, evidence custody, and resume admission
- Module: atomic release candidate orchestrator, report schema, contract tests, and bilingual runbook
- Reason: prevent a legal same-version retry with a new tool contract from appending to or overwriting the first failed candidate report and stage logs
- Standard vs User-Specific: repository-wide release safety; no application, customer, or runtime business semantics
- Why Here / Why Not Elsewhere: P4 owns release attempt lifecycle and evidence paths; Git history cleanup, application modules, and production configuration cannot safely implement retry custody
- Blast Radius: local pre-publication candidate attempt directories, reports, logs, source repositories, outputs, latest index, resume and locking only; no candidate execution, registry push, tag, publication, deployment, production access, gc, or prune
- Validation: legacy evidence hash preservation, unique attempt identity, retry/resume distinction, tool/source/tree mismatch rejection, ready-version guard, atomic report/index, log/path isolation, concurrency, schema, release contract, and formal CI

## 2026-07-24 — Atomic candidate clean source repository

- Branch: `fix/release-candidate-clean-source-repository`
- Starting product commit: `6dc2601460137759d4bb1dc1ef204e67a1f2abf9`
- Formal Product Layer: P4 operations delivery tooling
- Layer Target: isolated candidate source preparation and pre-build RH010 admission
- Module: atomic release candidate orchestrator, tests, and runbook
- Reason: prevent unreachable objects and stale refs from a long-lived caller clone from contaminating candidate history hygiene
- Standard vs User-Specific: repository-wide release safety; no application or customer semantics
- Why Here / Why Not Elsewhere: P4 owns source custody and build admission; RH010 remains unchanged and application modules must not manage Git object isolation
- Blast Radius: pre-publication source preparation, identity, RH010, build and scan working directory only; no push, tag, publication, deployment, production access, gc or prune
- Validation: independent main-only clone, no alternates, SHA/tree/main binding, RH010 isolation/failure, resume drift, concurrency, release contract and formal CI

## 2026-07-24 — Controlled PR merge expected-head guard

- Branch: `fix/controlled-merge-expected-head-guard`
- Starting product commit: `99953f4964f2ead1f8f69fa56f1cbef3680216ce`
- Formal Product Layer: P4 operations delivery tooling
- Layer Target: race-safe protected-main PR merge admission
- Module: `make pr.merge` and branch-governance contract tests
- Reason: bind every approved merge write to the independently reviewed full PR head SHA and close the check-to-merge race window
- Standard vs User-Specific: repository-wide governance control; no application, customer, release-candidate, runtime, or database semantics
- Why Here / Why Not Elsewhere: the approved Make entry owns GitHub merge mutation admission; callers, release automation, and production tooling must not reproduce or bypass it
- Blast Radius: one required `EXPECTED_HEAD` input, one live head comparison, and one `--match-head-commit` propagation; merge methods, protected-main checks, review policy, auto-merge, main push, mirroring, and release actions remain unchanged
- Validation: missing/short/non-hex/shell input rejection, live-head mismatch zero-merge, exact matched-head argv propagation, governance tests, formal CI, and diff checks

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

## 2026-07-23 — First Fresh Production Formal Module Closure Tool

- Branch: `fix/formal-module-install-tool`
- Starting commit: `a3ab1b5349d6a7d97fcd7dfbfe72a7d2723b19b3`
- Formal Product Layer: P4 operations delivery tooling
- Layer Target: exact production backup, three-module installation, and post-install acceptance orchestration for the first fresh `sc_production` database
- Module: release Make target, formal-module state probe, fixed installation orchestrator, production command policy, and focused contract tests
- Reason: the existing generic single-module entry cannot bind one approval to the exact missing formal set, dependency topology, paired recovery point, zero-business-data boundary, and 10/10 postcondition
- Standard vs User-Specific: one first-production delivery control; no customer preference, application behavior, runtime configuration, or long-term business fact
- Why Here / Why Not Elsewhere: P4 owns production mutation authorization and recovery sequencing; rc.4, P0/P1 modules, Nginx, credentials, and database schema remain immutable
- Blast Radius: one new production Make target that accepts no caller module selection and makes at most one Odoo install invocation after a validated backup; negative preflight performs zero production writes
- Validation: exact environment/confirmation/allowlist, manifest topology and data boundary, safe retry, pending/history/business/seed/demo drift rejection, backup-failure zero-install, 10/10 postcondition, Nginx fingerprint preservation, release contracts, security/generated gates, and PR required checks

## 2026-07-23 — Production Backup Configuration Loading Guard

- Branch: `fix/backup-config-loading`
- Starting commit: `8d17b82241422c096d31790cf47e057a4ff045f4`
- Formal Product Layer: P4 operations delivery tooling
- Layer Target: fixed production backup configuration admission for the guarded three-module closure
- Module: formal-module installation orchestrator, versioned production-backup environment template, focused release-contract tests, and production command policy
- Reason: the versioned installation tool required process-level `BACKUP_*` values but did not load the approved `/etc/scems/production-backup.env`, making a persistent audited backup configuration unusable without a forbidden command-line override
- Standard vs User-Specific: repository-wide production safety mechanism; no application behavior, business semantics, tenant preference, runtime data, or image content
- Why Here / Why Not Elsewhere: P4 owns backup identity admission and production mutation sequencing; neither rc.4 nor the Odoo modules should read host configuration
- Blast Radius: the existing formal-module target now admits exactly six root-owned `0600` backup identity fields from one fixed non-symlink file and rejects process overrides; no backup, module installation, database write, or Nginx operation occurs during deployment of the tool
- Validation: missing/unsafe/symlink/unknown/duplicate/incomplete/identity-drift configuration rejection, process-override rejection, exact backup identity propagation, existing backup-before-install and zero-install-on-failure tests, release contracts, and standard CI

## 2026-07-23 — Formal Module Pre-Install Backup Artifact Guard

- Branch: `fix/formal-module-backup-artifact-guard`
- Starting commit: `47c50401c0edc21ecdbd831f4f34a27027734891`
- Formal Product Layer: P4 operations delivery tooling
- Layer Target: atomic paired recovery-point acceptance before the guarded first-production module installation
- Module: `production_colocated_backup.py`, its direct formal-module caller, focused backup tests, and release-contract evidence
- Reason: the existing backup produced a validated dump, filestore archive, and manifest but relied on the caller for restrictive umask, final permissions, and an external `SHA256SUMS`; the formal installation contract must complete those controls before its sole module-install call
- Standard vs User-Specific: repository-wide production recovery safety; no application behavior, business semantics, tenant preference, database data, runtime configuration, Compose, Nginx, or image change
- Why Here / Why Not Elsewhere: the paired backup implementation owns artifact creation, integrity, permissions, and atomic publication; installation orchestration only consumes a strictly accepted recovery point and must not repair it afterward
- Blast Radius: new recovery points use an in-root `0700` incomplete directory, four `0600` artifacts, relative three-file SHA-256 inventory, structure validation, additive schema-v1 manifest evidence, fsync and atomic rename; legacy manifest validation remains readable
- Validation: caller umask `0022`/`0000`, exact modes/owners, checksum inventory and tampering, missing/empty/symlink artifacts, dump/filestore/manifest/structure/permission/checksum failure cleanup, path escape and time ordering, old-manifest compatibility, backup-before-single-install order, release contracts, and standard CI

## 2026-07-23 — First Fresh Production Administrator Identity Baseline Tool

- Branch: `fix/production-admin-identity-baseline`
- Starting commit: `19e1c3766c56641adac9a911eb53709a618a0e13`
- Formal Product Layer: P4 operations delivery tooling
- Layer Target: guarded, versioned repair of the sole first-production administrator's missing authoritative role relation
- Module: production release Make entry, identity-baseline runner, focused contract tests, and production command policy
- Reason: the fresh `sc_production` administrator is an active internal user but resolves to `restricted/no_authoritative_role`, so the unchanged security policy correctly denies all navigation
- Standard vs User-Specific: one first-production control-plane repair; no customer preference, company initialization, application behavior, menu definition, demo data, or historical data
- Why Here / Why Not Elsewhere: P4 owns explicit production mutation authorization and evidence; the P1 identity resolver and P2 role policy remain the facts consumed by the tool and are not weakened or duplicated
- Blast Radius: at apply time only the missing `smart_core.group_smart_core_admin` relation may be appended to the unique active internal `admin`; password, login, company, allowed companies, products, menus, modules, and business data are immutable
- Validation: dry-run zero writes, exact database/user/current-role/XML-ID guards, 10/10 modules and zero pending operations, conflicting-role rejection, explicit apply confirmation, transactional postcondition, idempotent NOOP, redacted atomic evidence, nonempty navigation projection, and release contract tests

## 2026-07-23 — Administrator Identity Dry-Run Evidence Guard

- Branch: `fix/admin-identity-dry-run-evidence-guard`
- Starting commit: `cfbfd872bd888a807d95dddb718efb9b2109e671`
- Formal Product Layer: P4 operations delivery tooling
- Layer Target: database-enforced dry-run safety and reviewable production identity evidence
- Module: administrator identity baseline runner, focused tests, release static contract, and production command policy
- Reason: the first version relied on rollback, copied observed current identity into the planned-after fields, and omitted exact relation-plan, write-audit, and stable state-fingerprint evidence
- Standard vs User-Specific: one repository-wide production mutation admission control; no customer preference, company initialization, application behavior, menu policy, demo data, or historical data
- Why Here / Why Not Elsewhere: P4 owns production mutation authorization and evidence; the installed P1/P2 identity resolver remains the only role-policy authority and is consumed through its side-effect-free resolution methods
- Blast Radius: dry-run now enables and verifies PostgreSQL transaction read-only before target queries, computes the proposed role from an in-memory XML-ID set, records one allowed relation append or NOOP, and atomically emits redacted observed/planned evidence; apply semantics and rc.4 are unchanged
- Validation: read-only ordering and failure closure, database write rejection in tests, current/planned/observed separation, shared-policy role projection, zero write counters, stable user/module/menu/product fingerprints, atomic evidence failure, redaction, apply confirmation/rollback/idempotency regression, release contracts, and standard CI

## 2026-07-23 — Administrator Identity Evidence Execution Binding Guard

- Branch: `fix/admin-identity-evidence-binding-guard`
- Starting commit: `0c957786f2bd1d9f617dd477e4da3ad9e85cad9d`
- Formal Product Layer: P4 operations delivery tooling
- Layer Target: immutable execution-to-tool-to-evidence identity binding before production database access
- Module: administrator identity baseline runner, production Make entry, focused tests, release static contract, and production command policy
- Reason: v2 evidence proved database read-only behavior and exact planned state but did not internally bind its unique execution ID, merged tool source, deployed directory, or deployed file digests
- Standard vs User-Specific: repository-wide production evidence custody; no customer preference, application behavior, company initialization, menu policy, demo data, historical data, or production database mutation
- Why Here / Why Not Elsewhere: P4 owns deployed-tool provenance and operational evidence; rc.4 and the P1/P2 identity policy remain immutable inputs and cannot establish host-tool custody
- Blast Radius: each dry-run/apply now fails before database queries unless its safe UTC run ID, evidence filename, 40-character source SHA, versioned path, deployment marker, metadata, script digest, and release Make digest agree; v3 JSON binds execution/tool/target identity and a non-self-referential canonical payload digest
- Validation: missing/invalid/mismatched run ID and source identity, metadata and file-digest drift, pre-query failure ordering, path traversal/symlink/existing-file rejection, exact 0600 atomic output, canonical digest recomputation and tamper detection, v2 read-only/plan/fingerprint regressions, apply confirmation/rollback/idempotency, release contracts, and standard CI

## 2026-07-23 — Atomic RC candidate workflow

- Branch: `refactor/atomic-release-candidate`
- Starting product commit: `99953f4964f2ead1f8f69fa56f1cbef3680216ce`
- Formal Product Layer: P4 operations delivery tooling
- Layer Target: atomic RC candidate orchestration, local immutable scan identity, and machine-readable readiness evidence
- Module: `make/release.mk`, `scripts/release`, and the paired atomic-flow runbook
- Reason: replace repeated conversational build/scan/SBOM approvals with one fail-closed repository entry while retaining separate publication and production approvals
- Standard vs User-Specific: generic repository release automation; no business or customer semantics
- Why Here / Why Not Elsewhere: P4 owns build and release evidence; application modules, frontend, and runtime configuration must not own delivery-state orchestration
- Blast Radius: pre-publication candidate build, scan, SBOM, retry, and reporting only; no registry push, Git tag, Release publication, deployment, production connection, or database write
- Validation: local/published scan identity tests, schema positive/negative cases, failure injection and preserved evidence, resume identity/tool-contract mismatch, per-version concurrency lock, report integrity, release contract, shell/static checks, and formal CI

## 2026-07-24 — Expected-head PR ready guard

- Branch: `fix/atomic-release-publication-contract`
- Starting commit: `54adfef911aff51b12b1a8b0b2383d62d5bb6c74`
- Formal Product Layer: P4 operations delivery tooling
- Layer Target / Module: `make pr.ready`, execution allowlist, and focused governance contracts
- Reason: the approved PR creation workflow can create a draft, while direct `gh pr ready` is forbidden and no governed transition existed
- Standard vs User-Specific: repository-wide PR governance; no product, candidate, runtime, or customer semantics
- Why Here / Why Not Elsewhere: P4 owns remote PR mutations; publication state and application modules must not own review-state transitions
- Blast Radius: one expected-head-bound draft-to-ready mutation; no base, code, merge policy, auto-merge, main, release, registry, tag, or deployment mutation
- Validation: missing/invalid/mismatched head rejection, non-draft rejection, exact ready invocation, release contract, standard CI, and static diff checks

## 2026-07-24 — Frozen Candidate Publication Source Contract

- Branch: `fix/publication-candidate-source-preflight`
- Starting commit: `1f0cc1e7e950fce37a63957dcdac6fbeb350837c`
- Formal Product Layer: P4 operations delivery tooling
- Layer Target / Module: release publication preflight, identity schemas, contract tests, and bilingual runbook
- Reason: merging the publication workflow advanced main after the immutable RC candidate was accepted, while the first publication preflight incorrectly required live main to remain the candidate source
- Standard vs User-Specific: repository-wide release identity governance; no application, customer, runtime, image, or candidate-content change
- Why Here / Why Not Elsewhere: P4 owns publication provenance and remote-state admission; the frozen candidate and application layers must not absorb later delivery-tool commits
- Blast Radius: publication preflight/reporting only; candidate evidence remains immutable and tag/image/Release remain bound to candidate source
- Validation: candidate creation evidence, first-parent ancestry, live dual-remote and tool identity, pre-write drift checks, tag/Release bindings, resume/idempotency, schemas, release contract, standard CI, and evidence hash/size/mtime custody
## 2026-07-24 — Governed Production Backup Install and Isolated Restore Contract

- Branch: `fix/production-backup-restore-contract`
- Starting commit: `c62ce848defee501a4de99e758a5d8286a2f1348`
- Formal Product Layer: P4 operations delivery tooling
- Layer Target: controlled backup-tool installation, atomic triple recovery point, and fully isolated restore rehearsal
- Module: release Make targets, atomic installer, backup/rehearsal runner, systemd templates, schemas, tests, production command policy, and bilingual runbook
- Reason: the production timer still targeted legacy container/database identities, while the repository had no approved installation entry, no deployment-metadata member in the recovery set, no operation lock, and no tool-owned isolated Odoo rehearsal
- Standard vs User-Specific: repository-wide production recovery governance; no application behavior, business semantics, customer preference, candidate evidence, publication evidence, or production data mutation
- Why Here / Why Not Elsewhere: P4 owns host installation, backup custody, rehearsal isolation, and timer sequencing; P0–P3 modules and frozen release evidence must remain immutable
- Blast Radius: five default-deny Make entries; two versioned operations tools; database/filestore/sanitized-metadata backup schema; isolated internal Docker rehearsal namespace; timer remains stopped until backup and rehearsal evidence pass
- Validation: identity and drift rejection, install rollback, triple-set atomicity, independent locks, checksum/resume rejection, sanitized metadata, internal-network restore, zero cron/egress, Odoo stop-after-init, table/attachment/filestore comparison, timer evidence gate, release contracts, standard CI, and static diff checks

## 2026-07-24 — RC5 production acceptance harness repair

- Branch: `fix/rc5-production-acceptance-harness-v2`
- Starting commit: `3c79fa2f9e05286dc9a147afb7ba5927058f664b`
- Formal Product Layer: P4 operations delivery tooling
- Layer Target: immutable real-HTTP production acceptance package and governed local worktree cleanup
- Module: `scripts/ops`, focused CI tests, Make entrypoints, and deployment acceptance evidence
- Reason: the production deployment helper called request-bound token generation from a bare Odoo shell, while stale historical worktrees obscured the authoritative local development surface
- Standard vs User-Specific: repository-wide delivery verification; no product behavior, customer preference, production data, role, or permission change
- Why Here / Why Not Elsewhere: P4 owns acceptance orchestration and workspace lifecycle; application authentication semantics and P0-P3 business modules remain unchanged
- Blast Radius: read-only HTTP login/system initialization/navigation/role/permission checks, clean-session evidence, immutable package verification, and clean merged linked-worktree removal only
- Validation: no-request regression, credential redaction, two independent HTTP sessions, exact-command digest parity, daily-development server execution, dirty/unmerged worktree rejection, quick gate, and one full CI run

## 2026-07-24 — RC5 production promotion configuration readiness

- Branch: `fix/rc5-promotion-config-readiness`
- Starting commit: `096f5d90e68f27ad616d97521500519b4347c4d8`
- Formal Product Layer: P4 operations delivery tooling
- Layer Target: fail-closed production promotion configuration admission before application-container replacement
- Module: `scripts/ops`, release Make entry, production command policy, deployment runbook, and focused regression tests
- Reason: the RC5 short promotion replaced the healthy application before discovering that the formal acceptance login was empty
- Standard vs User-Specific: repository-wide production promotion safety; no product behavior, customer preference, account permission, production data, image content, or database migration
- Why Here / Why Not Elsewhere: P4 owns promotion configuration provenance and deployment sequencing; Odoo modules, frontend, acceptance product semantics, and runtime business configuration must remain unchanged
- Blast Radius: read-only validation of the governed promotion config/secret sources, fixed image, immutable acceptance package, current-production HTTP login/system initialization/core reads, and redacted readiness evidence only
- Validation: undefined/empty/whitespace/placeholder login, missing secret, wrong URL/database/digest/role, complete-config pass, clean-session HTTP parity, exact local image identity, atomic `0600` evidence, daily server execution, production read-only preflight, release contracts, and full CI
# Daily candidate data continuity baseline — 2026-07-24

- Branch / anchor: `audit/daily-data-continuity-baseline` at `7a57a47c`
- Formal Product Layer: P4 ops delivery tool
- Layer Target / Module / Reason: versioned daily candidate continuity contract,
  paired database/filestore backup, isolated restore drill and aggregate data
  sentinels under `scripts/ops`; the daily server carries persistent candidate
  user data and must not be governed as a disposable product sandbox.
- Standard vs User-Specific: environment delivery governance for the confirmed
  daily candidate state pair; no P0–P3 product or customer business semantics.
- Why Here / Why Not Elsewhere: backup, restore and upgrade safety belong to P4;
  they must not alter Odoo modules, frontend rendering, runtime business
  configuration or make ops scripts a business-data source of truth.
- Blast Radius / Validation: new opt-in Make targets only; exact environment,
  database, container, volume and backup-root guards; the four shared
  destructive reset/demo targets now refuse the exact daily candidate state
  pair; unit regression, paired backup validation, isolated restore equality
  and standard CI prove containment.
# Daily candidate historical data sentinel baseline — 2026-07-24

- Branch / anchor: `audit/daily-data-sentinel-baseline` at `207334b`
- Formal Product Layer: P4 ops delivery tool
- Layer Target / Module / Reason: versioned read-only historical data sentinel
  contract, repeatable-read capture, deterministic samples, attachment/
  relationship assertions, compare semantics and isolated clone verification
  under `scripts/ops`; a restorable backup alone cannot detect silent data
  damage during an upgrade.
- Standard vs User-Specific: generic stateful candidate-environment governance
  bound to the approved daily database identity; no customer record content or
  product business rule becomes repository source.
- Why Here / Why Not Elsewhere: observation, migration acceptance and recovery
  proof belong to P4. No P0–P3 module, frontend, runtime configuration, running
  repository, user data or filestore is modified.
- Blast Radius / Validation: new opt-in Make targets and read-only scripts only;
  UUID/backup/filestore guards, sensitive-output denylist, targeted comparison
  regressions, repeated primary captures, isolated restore equality and full CI
  prove containment.
# RC6 daily candidate clone upgrade rehearsal admission — 2026-07-24

- Branch / anchor: `audit/rc6-daily-clone-upgrade-rehearsal` at `8962c8e`
- Formal Product Layer: P4 ops delivery tool
- Layer Target / Module / Reason: immutable RC6 candidate admission, isolated
  clone specification, deterministic migration plan, sentinel preservation,
  upgrade idempotency, rollback-mode and redacted evidence contracts under
  `scripts/ops`; an advancing main branch cannot be treated as a reproducible
  upgrade candidate.
- Standard vs User-Specific: generic stateful candidate-environment upgrade
  governance; no customer business facts, product behavior or runtime
  configuration are introduced.
- Why Here / Why Not Elsewhere: clone recovery, migration orchestration and
  promotion evidence belong to P4. They must not enter P0–P3 modules, frontend
  rendering or the running daily repository.
- Blast Radius / Validation: opt-in fail-closed Make admission only; immutable
  SHA/digest/CI ancestry checks, source identity checks, isolation and
  no-egress guards, destructive-path rejection, deterministic plans, sentinel
  and idempotency regressions, mode-0600 evidence and full CI prove
  containment. No clone restore or source operation occurs without a formally
  frozen candidate.

# RC6 candidate identity freeze — 2026-07-24

- Branch / anchor: `release/tenant-rc-rc6-identity-freeze` at `fb1f2b5`
- Formal Product Layer: P4 ops delivery tool
- Layer Target / Module / Reason: exact-source build workspace, single-write
  registry publication, manifest-to-config identity verification and a
  versioned RC6 candidate declaration under `scripts/ops`, `make/release.mk`
  and `config/releases`; clone rehearsal requires one immutable candidate
  rather than an advancing `main`.
- Standard vs User-Specific: repository-wide release identity governance; no
  product behavior, customer preference, runtime configuration, database or
  filestore change.
- Why Here / Why Not Elsewhere: source/image provenance and supersession policy
  belong to P4. They must not enter P0–P3 modules, frontend rendering, runtime
  configuration or alter the frozen product source commit.
- Blast Radius / Validation: one fixed source tag was pushed to GHCR; no
  movable or product-version tag was published. Clean SHA-bound build, SBOM
  and vulnerability scan, independent manifest/config inspection, OCI
  revision check, required PR ancestry and CI checks, declaration regressions,
  release contract and full CI prove containment. Daily and production
  environments were not accessed.

# RC6 daily candidate clone upgrade execution — 2026-07-24

- Branch / anchor: `audit/rc6-daily-clone-upgrade-rehearsal-03` at `e1f258a`
- Formal Product Layer: P4 ops delivery tool
- Layer Target / Module / Reason: fixed-image offline import, isolated paired
  restore, versioned module upgrade, historical-data comparison, real-HTTP
  acceptance, idempotency and paired rollback execution under `scripts/ops`
  and `make/daily_candidate.mk`; PR #43 supplied admission contracts but no
  state-changing rehearsal executor.
- Standard vs User-Specific: generic stateful candidate-environment delivery
  governance. The existing P2 customer add-on is copied from its fixed DAILY
  Git identity into an isolated read-only volume and is not promoted into the
  product image or repository.
- Why Here / Why Not Elsewhere: backup consumption, clone lifecycle, migration
  sequencing, external-side-effect blocking and evidence custody belong to P4.
  No P0–P3 product behavior, frontend contract, DAILY runtime configuration or
  business data source is changed.
- Blast Radius / Validation: explicit-confirmation Make targets only; one
  tagless offline image import, exact manifest-to-config/OCI chain, independent
  internal networks and volumes, no source mounts, fixed paired backup and
  sentinel checks, two identical upgrade entries, real-HTTP role checks,
  independent old-version rollback proof, exact labeled cleanup, targeted
  regressions and full CI prove containment. Production access is forbidden.

# Customer-tenant database architecture freeze — 2026-07-24

- Branch / anchor: `feature/user-module-personal-data-visibility` at `790e8bc`
- Formal Product Layer: P0 platform kernel product governance
- Layer Target / Module / Reason: `docs/governance/database_architecture_policy.md`;
  freeze the platform control plane, versioned construction-industry capability
  layer, database-per-customer-tenant data plane, and supporting ops/analytics
  store boundaries before UM-P1 ownership work begins.
- Standard vs User-Specific: platform-wide tenancy and data-governance baseline;
  no customer-specific business semantics or customer data.
- Why Here / Why Not Elsewhere: tenant/database boundaries govern P1 product
  ownership and P2 installation rehearsal, so they belong in the single
  authoritative governance policy and root agent entry; they must not be
  inferred from Odoo multi-company rules, frontend behavior, runtime low-code
  configuration, or an individual customer module.
- Blast Radius / Validation: documentation and execution policy only; exact
  frozen-key scan, ownership-matrix review, policy-reference check,
  `git diff --check`, and changed-path review prove containment. No database,
  filestore, container, service, remote branch, product source file, or
  customer data is modified. The earlier P0 artifact's quarantined-draft
  identity is not reasserted here because those draft paths were already absent
  or different from the recorded hashes at this audit's starting state.

## Quarantined draft disposition

After the read-only provenance and scope audit, the user authorized acceptance
of the current HEAD state. This disposition does not establish who changed the
drafts, how they were changed, or that their proposed product behavior is
complete.

```text
QUARANTINED_DRAFT_COUNT=5
QUARANTINED_DRAFT_DISPOSITION=AUTHORIZED_REMOVAL_AND_ACCEPT_CURRENT_HEAD_STATE
TRACKED_DRAFT_FILES_ACCEPTED_AT_HEAD=2
UNTRACKED_DRAFT_FILES_AUTHORIZED_ABSENT=3
DRAFT_CONTENT_RESTORED=false
DRAFT_CONTENT_MIGRATED=false
DRAFT_CONTENT_USED_FOR_P1=false
P1_MUST_START_FROM_COMMITTED_GOVERNANCE_BASELINE=true
DRAFT_DRIFT_ACTOR=UNKNOWN
DRAFT_DRIFT_EXACT_OPERATION=INSUFFICIENT_EVIDENCE
USER_DISPOSITION_AUTHORIZED_AFTER_READ_ONLY_AUDIT=true
```

# Administrator visibility/data-access decoupling — 2026-07-24

- Branch / anchor: `feature/user-module-personal-data-visibility` at `bd8d460`
- Formal Product Layer: P0 platform identity and navigation security mechanism,
  with the P1 construction-industry role projection as its policy consumer.
- Layer Target / Module / Reason: `smart_core` now distinguishes installed
  capability and configuration discovery from strict platform-operator
  privilege; `smart_construction_core` projects both `base.group_system` and
  `smart_core.group_smart_core_admin` through the system-admin discovery
  surface instead of an empty business-function menu.
- Standard vs User-Specific: product-wide administrator semantics. No customer
  role, project membership, company scope, business record, fixture or
  customer-specific navigation is introduced.
- Why Here / Why Not Elsewhere: capability discovery belongs to identity and
  navigation metadata projection. Customer business access remains owned by
  model ACLs, record rules, company scope and explicit business membership;
  dangerous platform actions retain their strict backend authorization.
- Blast Radius / Validation: identity predicates, navigation/config metadata
  projection, construction role policy and direct regression tests only. No
  ACL, record rule, business model, migration, database, filestore, runtime
  environment or customer data is changed.

# Ephemeral registry audit environment — 2026-07-25

- Branch / anchor: `feature/user-module-personal-data-visibility` at `d2038e92`
- Formal Product Layer: P4 operations and audit-delivery tooling.
- Layer Target / Module / Reason: repository-governed Make, Compose, exporter,
  exact-cleanup tooling and infrastructure tests provide a disposable registry
  metadata export without reusing an existing database or runtime.
- Standard vs User-Specific: generic security-audit infrastructure; no customer
  business semantics, fixture, demo data or customer data is introduced.
- Why Here / Why Not Elsewhere: registry discovery and resource lifecycle
  controls are operational governance concerns. They do not belong in product
  handlers, services, models, ACLs, record rules or project-ID authorization.
- Blast Radius / Validation: a random Compose project uses dedicated labeled
  containers, an internal network and three explicit volumes, publishes no
  ports, runs Odoo as the image's non-root user, exports deterministic metadata
  to a run-specific temporary directory, and deletes only exact manifest
  resources after label verification. Unit, real-container, failure-cleanup,
  foreign-label refusal and second-cleanup tests prove containment.
- Resource isolation hardening: image-declared volume paths are reconciled
  against the rendered Compose configuration before initialization. A
  two-phase manifest predeclares names, then records exact Docker IDs; cleanup
  verifies names, IDs and labels. The one anonymous volume created by the
  pre-hardening `/mnt/extra-addons` gap was attributed from preserved pre/post
  snapshots and removed once by its full ID under explicit user authorization.

# Effective generic API policy registry export — 2026-07-25

- Branch / anchor: `feature/user-module-personal-data-visibility` at `0197ae2`
- Formal Product Layer: P4 operations and audit-delivery tooling.
- Layer Target / Module / Reason: the dedicated registry exporter reconstructs
  effective generic API model, operation, field, method, domain, context and
  project-scope policy metadata without invoking policy predicates, handlers
  or business model methods.
- Standard vs User-Specific: generic audit evidence only. No product policy,
  customer setting, business record or authorization behavior is changed.
- Why Here / Why Not Elsewhere: policy inspection belongs to the governed
  exporter. Product handlers and construction extension policy providers
  remain authoritative and unmodified.
- Blast Radius / Validation: exporter metadata projection, strict schema
  validation, dedicated unit tests and this brief documentation entry only.
  Full ephemeral registry initialization, secret scanning, exact cleanup and
  pre/post Docker resource-set equality prove containment.

# Effective route policy registry export — 2026-07-25

- Branch / anchor: `feature/user-module-personal-data-visibility` at `cf9b399`
- Formal Product Layer: P4 operations and audit-delivery tooling.
- Layer Target / Module / Reason: the dedicated registry exporter projects
  loaded controller decorator policy, inheritance and collision metadata
  without executing controller methods or issuing requests.
- Standard vs User-Specific: generic audit metadata only; route behavior and
  product controllers remain unchanged.
- Why Here / Why Not Elsewhere: runtime route inventory is audit evidence, not
  product routing policy. The exporter observes existing controller metadata
  and does not become a competing route registry.
- Blast Radius / Validation: one pure metadata helper, exporter/schema
  integration, dedicated tests and documentation. The governed ephemeral run
  and exact cleanup remain the system-bound proof.

# Route-surface conflict gate and effective winner proof — 2026-07-25

- Branch / anchor: `feature/user-module-personal-data-visibility` at `0b24eb6`
- Formal Product Layer: P4 operations and audit-delivery tooling.
- Layer Target / Module / Reason: route-surface taxonomy, final routing-map
  identity, complete Rule/dispatch/security dimensions, false-conflict gate
  and current-framework-only order proof under `scripts/ops/registry_audit`;
  path plus method alone overstates controller inheritance as runtime conflict.
- Standard vs User-Specific: generic audit evidence only. No controller,
  product route, customer policy, business data or runtime configuration is
  modified.
- Why Here / Why Not Elsewhere: final route registration and framework source
  inspection belong to the governed exporter. Product controllers, frontend
  code and public RPC classification are outside this iteration.
- Blast Radius / Validation: schema v4 marks inheritance-collapsed candidates
  `FALSE_CONFLICT`, admits only same-map overlapping Rules to winner analysis,
  hashes the source actually installed in the isolated container, and records
  compiled patterns plus ordering keys. Unit tests, schema checks, the
  governed ephemeral lifecycle and exact cleanup prove that no `match()`, HTTP
  request, endpoint or business method executed.

# Isolated project record-rule ORM acceptance entrypoint — 2026-07-26

- Branch / anchor: `feature/user-module-personal-data-visibility` at `9322f50`
- Formal Product Layer: P4 operations and test-delivery tooling.
- Layer Target / Module / Reason: one focused Odoo `TransactionCase`, a
  single-purpose test launcher, a healthcheck-disabled Compose overlay and a
  Make wrapper exercise `business_scope_meta()` with the installed project ACL
  and record rules in a unique disposable database.
- Standard vs User-Specific: generic security acceptance with synthetic users
  and projects only. No customer data, product authorization logic, ACL,
  record rule or generic entrypoint is changed.
- Why Here / Why Not Elsewhere: database lifecycle and repeatable acceptance
  belong to repository test operations; the already-patched product helper
  remains unchanged.
- Blast Radius / Validation: the launcher rejects database overrides, enforces
  a fixed random database prefix and denylist, drops only the database created
  by the current run, and removes only its uniquely named Compose resources.
  Two valid executions passed the focused real-ORM assertions and restored the
  pre-run database, container, network and volume inventories exactly. Seven
  ADMIN_VIS_P3 boundaries remain open pending the independent patch re-test.

# Generic business-scope real-ORM closure review — 2026-07-26

- Branch / anchor: `feature/user-module-personal-data-visibility` at `0696fed`
- Formal Product Layer: P4 audit and security-verification records.
- Layer Target / Module / Reason: the verified disposable ORM entrypoint was
  rerun and bound to each of the seven fixed ADMIN_VIS_P3 call chains. Six
  caller-environment chains are closed with real ACL and record-rule evidence.
- Remaining boundary: `ADMIN_VIS_P3_GENERIC_API_DATA` stays open because its
  internal `account.tax` quick-create policy can elevate `env_model` before
  scope metadata is built; the helper then derives the project model from that
  elevated environment.
- Blast Radius / Validation: no product, ACL, record-rule, generic entrypoint,
  ORM test or infrastructure file changed. The focused ORM run passed and
  restored all resource inventories; unit, AST, compile, JSON and three-point
  quality-gate comparisons also passed without new or worsened failures.

# API data caller-scope isolation before account-tax sudo — 2026-07-26

- Branch / anchor: `feature/user-module-personal-data-visibility` at `ff45aab`
- Formal Product Layer: P2 generic API authorization boundary.
- Layer Target / Module / Reason: `ApiDataHandler._op_create` now captures the
  original caller-scoped `account.tax` model and authorizes project scope
  before the existing quick-create policy can select an elevated operation
  model.
- Standard vs User-Specific: platform-generic authorization sequencing; no
  customer policy, project domain, ACL, record rule or account-tax business
  rule is introduced.
- Why Here / Why Not Elsewhere: the environment propagation defect originates
  in the single `api.data` create branch. The shared scope helper and the six
  already-safe generic entrypoints remain unchanged.
- Blast Radius / Validation: one handler, one focused AST boundary test, the
  existing real-ORM acceptance test and audit records. Real ACL/record-rule
  tests prove unauthorized and nonexistent projects stop before policy sudo,
  while authorized contract-tax policy still returns its original
  `allowed=true, sudo=true` decision. All temporary resources were removed and
  the seven ADMIN_VIS_P3 boundaries are closed.

# UM-P1 S01 ownership and visibility contract baseline — 2026-07-26

- Branch / anchor: `feature/user-module-personal-data-visibility` at `01820d7`
- Formal Product Layer: P1 construction-industry standard product governance
  and verification.
- Layer Target / Module / Reason: the six document-ordered business entries
  are recorded in one machine-readable ownership and visibility contract,
  backed by the committed `smart_construction_core` model fields, ACLs, record
  rules and a real-registry acceptance test.
- Standard vs User-Specific: construction-product authorization evidence only.
  Full user-management productization remains deferred, and no customer
  preference or customer data is introduced.
- Why Here / Why Not Elsewhere: P1 owns the standard business models and their
  authorization boundaries. P0 mechanisms, P2 customer modules, P3 runtime
  configuration, frontend filtering and P4 repair scripts cannot invent the
  missing personal-visibility policy.
- Current contract result: payment request/execution and contract settlement
  have committed allowed-company plus project-responsible/follower rules.
  Project receipt, invoice/deduction and cost ledger have ACLs but no model
  record rules; interfund transfer has a company rule but no common personal
  ownership rule. Missing behavior is preserved as a product gap, not reported
  as a passing personal-visibility contract.
- Next document-order entry: `UM-P1-S02-PROJECT-RECEIPT`. Its product
  implementation can reuse the existing `project_id` relationship and the
  committed project responsible-user/follower semantics. The minimal product
  gap is the absence of the corresponding project/company record rules on
  `sc.receipt.income`; no new field or migration is required.
- Blast Radius / Validation: one JSON contract, one static guard and test, one
  real-registry test import, and this iteration record. Product models,
  handlers, ACLs, record rules, generic entrypoints and business data remain
  unchanged.

# UM-P1 S02 project receipt visibility — 2026-07-26

- Branch / anchor: `feature/user-module-personal-data-visibility` after
  `e26dde3`.
- Formal Product Layer: P1 construction-industry standard product.
- Layer Target / Module / Reason: the first document-order business entry,
  `sc.receipt.income`, now applies the S01 allowed-company plus project
  responsible-user/follower visibility contract to business initiator,
  finance-read and finance-user roles. Finance managers retain full CRUD
  within allowed companies.
- Standard vs User-Specific: one standard server-side record-rule boundary;
  no customer-specific policy, frontend filter or user-management
  productization is introduced.
- Why Here / Why Not Elsewhere: the product gap was the absence of rules on
  the receipt model itself. The existing `project_id` relation supplies the
  approved ownership anchor, so no new field, ACL, handler, migration or
  generic API change is required.
- Blast Radius / Validation: four receipt rules, one static topology test, an
  extension of the existing isolated real-ORM contract test, and current
  contract evidence. Ordinary users are limited to allowed-company projects
  they own or follow; finance managers remain company-scoped. Unauthorized,
  cross-company and nonexistent searches are indistinguishable at the ORM
  boundary, and no-scope searches retain the rule domain.
- Next document-order entry:
  `UM-P1-S03-PAYMENT-REQUEST-EXECUTION`.

# UM-P1 S03 payment visibility verification — 2026-07-26

- Branch / anchor: `feature/user-module-personal-data-visibility` at
  `429db7c`.
- Formal Product Layer: P1 construction-industry standard product
  verification.
- Layer Target / Module / Reason: the second document-order entry already has
  committed project-member plus allowed-company rules for `payment.request`
  and `sc.payment.execution`; S03 closes the remaining identifier
  nondisclosure evidence gap without changing product behavior.
- Existing contract confirmed: ordinary business and finance roles see only
  projects they own or follow in allowed companies. Finance managers and
  executives remain company-scoped; the payment-request business-config
  administrator retains its explicit all-record contract.
- Real-ORM evidence: caller-scoped searches and direct reads were exercised for
  authorized, cross-user, cross-company and nonexistent IDs on both models.
  Unauthorized and nonexistent searches return the same empty observation;
  direct unauthorized reads raise `AccessError`; no-scope searches retain the
  rules.
- Resource safety: an initial synthetic-fixture error was corrected after its
  unique database and resources were fully removed. The final 20-test run
  passed with zero failures/errors and restored database, container, network
  and volume inventories exactly.
- Product blast radius: none. Only focused tests, current contract evidence,
  validators and this iteration record change.
- Next document-order entry: `UM-P1-S04-INVOICE-DEDUCTION`. The S01 matrix
  records `OWNERSHIP_ANCHOR_MISSING`, so implementation requires an explicit
  ownership-contract decision before product rules can be changed.

# UM-P1 S04 company-finance invoice visibility — 2026-07-26

- Branch / anchor: `feature/user-module-personal-data-visibility` at
  `0712242`.
- Formal Product Layer: P1 construction-industry standard product.
- Layer Target / Module / Reason: `sc.invoice.registration` and
  `sc.tax.deduction.registration` are company finance shared ledgers. Their
  server-side rules now intersect every ACL holder with allowed companies,
  admit the existing finance capabilities within that boundary, and prevent
  business-initiation capability alone from opening the ledgers.
- Approved ownership contract: no personal ownership field is required.
  `applicant_name`, `source_created_by` and `creator_name` remain audit text,
  and project responsibility/followership is not used as ledger visibility
  authority. No ACL, field or migration is added.
- Create/write boundary: both models resolve a supplied project through a
  caller-scoped `project.project.search` constrained to allowed companies
  before business-category lookup or persistence. Unauthorized and nonexistent
  projects therefore share the same `AccessError` path; no sudo, browse or
  exists probe is used.
- Real-ORM evidence: the final 29-test isolated run proves company-shared
  finance search/read, caller-visible project create/write, cross-company
  denial, business-initiator denial, manager delete scope, superuser framework
  behavior, nonexistent equivalence and no-scope company intersection for both
  models. The initial test-baseline adaptation run and final passing run both
  removed their unique databases and restored database, container, network and
  volume inventories exactly.
- Blast Radius: two model authorization guards, one record-rule file, focused
  static/ORM tests, the existing S01 contract validator and this iteration
  record. Business calculations, ACLs, generic APIs, frontend and existing
  business data are unchanged.
- Next document-order entry: `UM-P1-S05-INTERFUND-TRANSFER`.

# UM-P1 S05 company-finance interfund visibility — 2026-07-26

- Branch / anchor: `feature/user-module-personal-data-visibility` at
  `eb6fb5a`.
- Formal Product Layer: P1 construction-industry standard product.
- Approved contract: `sc.fund.account.operation` and `sc.financing.loan` are
  company-finance shared ledgers. `company_id` is their common security
  anchor; project links are business attribution and never personal ownership.
- Product boundary: both models now have a mandatory global allowed-company
  intersection and exact finance-capability rules. Business-initiation ACL
  alone cannot open either ledger. No ACL, group, ownership field or migration
  was added.
- Mutation boundary: fund operations accept an omitted project while retaining
  their required caller company, and validate any supplied project against the
  same company. Financing loans validate their required project in the caller
  environment before create or project reassignment. No sudo, browse or exists
  pre-probe participates in either check.
- Real-ORM evidence: the final isolated run passed 38 post tests with zero
  failures/errors, including nine S05 tests over both models. It covers
  company-shared finance read/search, caller-scoped create/write, optional
  project handling, cross-company and non-finance denial, manager delete,
  direct read denial, nonexistent equivalence, no-scope behavior and superuser
  framework behavior.
- Resource safety: the initial test-expectation adaptation and final passing
  run each removed their unique databases and exactly restored database,
  container, network and volume inventories.
- Next document-order entry: `UM-P1-S06-CONTRACT-SETTLEMENT`.

# UM-P1 S06 contract-settlement visibility verification — 2026-07-26

- Branch / anchor: `feature/user-module-personal-data-visibility` at
  `5a5e9e8`.
- Formal Product Layer: P1 construction-industry standard product.
- Existing contract verified: settlement read/user roles are limited to
  allowed companies and projects for which the caller is responsible or a
  follower. Settlement/finance managers share within allowed companies, while
  the business-config administrator retains its explicit all-record rule.
- Audit-field boundary: `entry_user_id` remains metadata only. A synthetic
  record naming the ordinary user as entry user but belonging to an unrelated
  project stayed invisible.
- Real-ORM evidence: the final isolated run passed 46 post tests with zero
  failures/errors, including eight S06 tests for owner/follower access,
  cross-user and cross-company denial, manager/config-admin behavior, direct
  read denial, nonexistent equivalence and no-scope behavior.
- Resource safety: the initial fixture-adaptation run and final passing run
  each removed their unique database and exactly restored database, container,
  network and volume inventories.
- Product changes: none. Existing ACLs, record rules, groups, model behavior
  and entrypoints were not modified.
- Next document-order entry: `UM-P1-S07-COST-LEDGER`; its ownership contract
  remains an explicit decision gate because no committed ownership authority
  or model record rule exists.

# UM-P1 S07 cost-ledger project visibility — 2026-07-26

- Branch / anchor: `feature/user-module-personal-data-visibility` from
  `8666bbe`.
- Approved contract: cost-model ACL capability AND allowed company AND project
  responsibility/followership. The canonical responsibility field is
  `project.project.user_id`; explicit followership uses
  `message_is_follower`, backed by `mail.followers` and the formal
  `sc.project.member.assignment` contract.
- Excluded authority: `project.project.manager_id` remains a frontend filter
  input only for this slice and does not independently grant backend access.
- Product implementation: added a global allowed-company rule, matching
  project responsible/follower rules for the three cost capabilities, and a
  caller-scoped project guard before period helper sudo work on create/write.
- Real-ORM evidence: final isolated run
  `sc_test_admin_vis_p3_20260726001330_f59483df` passed 56 post tests with zero
  failures/errors, including ten cost-ledger tests for responsible/follower
  visibility, unrelated and cross-company denial, ACL non-expansion,
  create/write/unlink, direct-read denial, identifier equivalence,
  manager-field exclusion and no-scope behavior.
- Resource safety: all adaptation and final runs removed their unique
  databases and restored database, container, network and volume inventories
  exactly.
- Document-order status: all six approved P1 business-entry families are now
  implemented or verified; there is no additional P1 entry after S07 in the
  approved source order.

# UM-P2 S01 receipt relation aggregation — 2026-07-26

- Branch / anchor: `feature/user-module-personal-data-visibility` from
  `f4dbbdc`.
- Approved authority chain: `sc.receipt.income.payment_request_id` is the
  primary anchor, its single income contract is authoritative, and
  `construction.contract.partner_id` is the required receipt counterparty.
  An explicit contract or partner may confirm this chain but cannot override
  it.
- Product implementation: receipt create/write now resolve every supplied
  application, contract and authoritative partner in the caller environment
  before persistence. Missing consistency fields are derived from the strong
  relation; conflicting values are rejected. A contract without an
  application remains a valid secondary anchor, while records with neither
  anchor remain unaggregated.
- Excluded behavior: no name, amount, date, note or first-result matching; no
  historical inference or migration; no ACL, record-rule or public API
  change; no sudo/browse/exists pre-probe.
- Real-ORM evidence: isolated database
  `sc_test_admin_vis_p3_20260726002723_6f9f79bf` passed 63 post tests with zero
  failures/errors. The seven S01 tests cover primary/secondary derivation,
  contract and counterparty conflicts, write revalidation, unlinked records,
  and unauthorized/nonexistent equivalence.
- Resource safety: the temporary database and all test resources were removed;
  database, container, network and volume inventories exactly match their
  pre-run digests.
- Next formal P2 order entry:
  `UM-P2-S02-PAYMENT-RELATION-AGGREGATION`.

# UM-P2 S02 payment relation aggregation — 2026-07-26

- Branch / anchor: `feature/user-module-personal-data-visibility` from
  `8fafca0`.
- Approved authority chain: `payment.request` is the execution anchor. Its
  maintained detail set is authoritative; otherwise exactly one standard or
  material settlement header is the source. Contracts are aggregated from the
  complete valid source set and copied to the execution scalar only when that
  set contains one contract.
- Multi-contract behavior: existing `payment.request.line` relations preserve
  every settlement. Different source contracts leave the execution
  `contract_id` empty; no first, latest or amount-based source is selected.
- Payee boundary: the application partner remains the business counterparty,
  while the execution partner is the actual funds recipient. Equal and
  different payees are both valid and neither path rewrites the application,
  settlement or contract basis.
- Product implementation: caller-scoped source resolution and create/write
  normalization were added to payment execution, with request and detail
  mutation constraints that revalidate linked executions. No sudo,
  browse/exists pre-probe, ACL, record-rule, migration or heuristic matching
  was added.
- Real-ORM evidence and exact resource cleanup are recorded in
  `docs/audit/um_p2/um_p2_s02_payment_relation_aggregation_v1.json`.
- Next formal P2 order entry:
  `UM-P2-S03-INTERFUND-RELATION-AGGREGATION`.

# UM-P2 S03 interfund relation aggregation — 2026-07-26

- Branch / anchor: `feature/user-module-personal-data-visibility` from
  `f65243d`.
- Formal relation contract: source and target fund accounts are the two
  transfer authorities. Each endpoint project derives only from its account;
  the operation's optional `project_id` remains business attribution and does
  not override either endpoint.
- Counterparty projection: for a project perspective, the opposite endpoint
  is another project, the company, or the same project's internal account.
  Account transfers do not invent a partner relation and do not match names,
  account numbers, amounts or notes.
- Product implementation: transfer account IDs are resolved with caller
  permissions and constrained to the operation company; an account whose
  project belongs to another company is rejected. Create and endpoint-changing
  writes revalidate the same relation without sudo or browse/exists probing.
- Real-ORM evidence: isolated database
  `sc_test_admin_vis_p3_20260726005614_bda64e74` passed 77 post tests with zero
  failures/errors. Five S03 tests cover project/project, project/company and
  internal endpoints, cross-company/nonexistent equivalence, project/company
  mismatch and write revalidation.
- Resource safety: the temporary database and all test resources were removed;
  database, container, network and volume inventories exactly match their
  pre-run digests.
- Next formal P2 order entry:
  `UM-P2-S04-INVOICE-RELATION-AGGREGATION`.

# UM-P2 S04 invoice relation aggregation — 2026-07-26

- Branch / anchor: `feature/user-module-personal-data-visibility` from
  `b647855`.
- Formal relation contract: `sc.invoice.registration` dispatches its relation
  policy by the repository's exact `source_kind` values. Input and output
  invoice contracts derive only from caller-visible formal settlement or
  contract relations; prepaid tax keeps project/counterparty authority and
  permits an empty contract.
- Receipt invoice lines follow the strong receive-application -> contract ->
  counterparty chain. Explicit project, contract and counterparty values are
  consistency checks and cannot override that chain.
- Tax deduction remains outside contract aggregation. No relationship field
  was added, and its textual invoice number is never used to match an invoice
  registration or contract.
- Product implementation performs caller-scoped relation searches and
  revalidates create and write operations without sudo, browse/exists probing,
  heuristic matching or historical inference.
- Real-ORM evidence: isolated database
  `sc_test_admin_vis_p3_20260726011941_c8c8996b` passed 85 post tests with zero
  failures/errors. The temporary database was removed and database, container,
  network and volume inventories exactly match their pre-run digests.
- Next formal P2 order entry:
  `UM-P2-S05-SETTLEMENT-RELATION-AGGREGATION`.
- S05 decision boundary: `sc.settlement.order.contract_id` is optional while
  new settlement lines require a contract, and current server validation only
  requires every line contract to belong to the header project. It does not
  require line contracts to be identical to each other or to the optional
  header contract. Choosing header authority versus a multi-contract
  line-authority contract therefore requires one explicit cardinality decision.

# UM-P2 S05 settlement relation aggregation — 2026-07-26

- Branch / anchor: `feature/user-module-personal-data-visibility` from
  `5ea03fa`.
- Formal authority contract: the complete valid
  `sc.settlement.order.line.contract_id` set is authoritative. The optional
  `sc.settlement.order.contract_id` is projected only when that set contains
  one unique contract; distinct contracts remain on their lines and force the
  scalar header projection empty.
- Mutation coverage: header create/write, nested One2many commands, and direct
  line create/write/unlink all re-evaluate the final detail state. An explicit
  conflicting header contract is rejected and never rewrites line contracts.
- Relation boundary: caller-visible contracts must match the settlement
  project, company, direction and counterparty. No sudo, browse/exists probe,
  heuristic matching, historical inference, ACL or record-rule change was
  added.
- Material settlement remains purchase-order/supplier based and has no
  contract-bearing header or detail field, so S05 does not add or infer one.
- Real-ORM evidence: isolated database
  `sc_test_admin_vis_p3_20260726014607_95c5133e` passed 93 post tests with zero
  failures/errors. The temporary database was removed and database, container,
  network and volume inventories exactly match their pre-run digests.
- Formal P2 sequence status: the five relationship entries in
  `user_business_data_portrait_productization_plan_2026-06-10.md` are now
  implemented and verified. The next documented phase is P3 business closure;
  its first slice authority and acceptance contract is not yet formally
  approved, so no P3 behavior is inferred here.

# UM-P3 S01 core-domain authority baseline — 2026-07-26

- Branch / anchor: `feature/user-module-personal-data-visibility` from the
  accepted S05 commit `3af4f0e`.
- Formal Product Layer: P4 audit and machine-verifiable governance evidence;
  this P3 phase slice does not change P1 industry business models.
- Authority baseline: 31 relations across 22 project, contract, procurement,
  subcontract, settlement, receipt/payment, fund, invoice, counterparty and
  company models. The matrix freezes all five P2 authorities without
  redesigning them.
- Closure result: six chains are closed, three are partial, one is blocked by
  schema and authority, and tax-deduction relation modeling remains formally
  out of scope. No heuristic matching, historical inference, ACL, record
  rule, migration or business behavior was added.
- Highest-priority gap: `FUND_PLAN_TO_ACTUAL_FUND_EVENT` is critical but not
  safe to implement. The repository has no formal relation carrier identifying
  which historical `project.funding.baseline` version authorizes a request or
  actual fund event, and neither its authority side nor cardinality has been
  approved.
- Next formal task:
  `FORMALLY_DECIDE_FUNDING_BASELINE_EVENT_AUTHORITY_CARDINALITY_AND_SCHEMA`.

# UM-P3 S02 fund-plan actual-event allocation — 2026-07-26

- Branch / anchor: `feature/user-module-personal-data-visibility` from the
  accepted P3-S01 commit `f7a1201`.
- Formal authority: `project.funding.baseline` is an approved budget baseline,
  each `project.funding.baseline.line` is one planned budget bucket, and
  `payment.ledger` is the occurred payment fact in this slice. A request
  remains workflow intent and is not an allocation authority.
- Relation carrier:
  `project.funding.actual.event.allocation` records the explicit positive
  amount between a plan line and an actual payment event. The carrier preserves
  many-to-many facts; unallocated events remain valid.
- Boundary: allocation endpoints must share project, company and currency;
  event allocations cannot exceed the event amount. Plan capacity is exposed
  as a non-blocking projection because no stricter budget policy exists.
- No current-active-plan, shared-project or request relation creates an
  allocation. No historical relation was inferred or backfilled.
- Real-ORM evidence: isolated database
  `sc_test_admin_vis_p3_20260726082509_9f8c7ab6` passed 107 post tests with
  zero failures/errors. The temporary database was removed and database,
  container, network and volume inventories exactly match their pre-run
  digests.
- Matrix result: 32 relations and seven closed chains. The next uniquely safe
  gap is `PROJECT_TO_FUND_PLAN` caller-visible project and company validation:
  `IMPLEMENT_UM_P3_S03_FUNDING_BASELINE_PROJECT_VISIBILITY`.

# UM-P3 S03 funding-baseline project visibility — 2026-07-26

- Branch / anchor: `feature/user-module-personal-data-visibility` after the
  P3-S02 audit commit `9a60edd`.
- Formal relation remains `project.funding.baseline.project_id`; S03 adds no
  field or new authority. Create and write resolve the target project through
  caller-visible search without sudo, browse/exists probing, or inference.
- Funding baseline headers now reuse the same project-responsible/follower and
  allowed-company boundary as their lines and allocations. Finance managers
  share records only inside allowed companies.
- Real-ORM evidence: isolated database
  `sc_test_admin_vis_p3_20260726083348_97ef6eec` passed 112 post tests with
  zero failures/errors. The temporary database and all resources were removed,
  and database/container/network/volume inventory hashes were restored.
- Matrix result: eight chains are closed. The next highest-priority gap is
  blocked on the authority precedence among material settlement
  `purchase_order_id`, explicit project and explicit supplier:
  `FORMALLY_DECIDE_MATERIAL_SETTLEMENT_PURCHASE_AUTHORITY`.

# UM-P3 S05 subcontract register-settlement authority — 2026-07-26

- Branch / anchor: `feature/user-module-personal-data-visibility` from the
  accepted P3-S04 commit `43466d78`.
- Formal authority: `construction.contract` owns project and counterparty
  scope, `sc.subcontract.register.line` owns occurred performance facts, and
  `sc.subcontract.settlement.line` owns settled quantity and amount facts.
- Relation carrier: `sc.subcontract.settlement.line.register_line_id` is the
  explicit strong relation. One settlement may preserve multiple registers
  within one contract, and one register line may be split across settlements.
  The settlement header is projection only.
- Boundary: complete relation sets converge on one contract, project,
  counterparty and company; caller-visible resolution uses no sudo or
  heuristic matching. Direct line CRUD, nested commands and contract/register
  mutations revalidate the final relation state.
- Real-ORM evidence: isolated database
  `sc_test_admin_vis_p3_20260726094713_09b5ce98` passed 134 post tests with
  zero failures/errors. The temporary database and resources were removed,
  and all database/container/network/volume inventory hashes were restored.
- The repository has no unique cumulative policy connecting register-line
  `contract_qty` or `registered_amount` to settlement-line `qty` or
  tax-inclusive `amount_total`, nor a formal included-state or
  cancellation/reversal rule. The explicit relation gap is closed, while
  `CORE-033-SUBCONTRACT-REGISTER-CUMULATIVE-SETTLEMENT-POLICY` remains the
  next blocked decision:
  `FORMALLY_DECIDE_SUBCONTRACT_CUMULATIVE_SETTLEMENT_POLICY`.

# UM-P3 S06 subcontract cumulative settlement quantity policy — 2026-07-26

- Branch / anchor: `feature/user-module-personal-data-visibility` from the
  accepted P3-S05 commit `5536de19`.
- Formal policy: register-line `contract_qty` is the hard quantity/workload
  cap for all explicitly related settlement-line `qty` values whose parent
  settlement is `confirmed`. Draft, submitted and cancelled documents do not
  consume the cap.
- Unit and precision boundary: both models expose free-text `unit_name` rather
  than a formal UoM relation. Effective settlement therefore requires identical
  nonempty unit values and uses the repository `Product Unit of Measure`
  precision; no conversion is inferred.
- Transaction boundary: cumulative validation locks the affected register
  lines, forces row-version conflict detection under repeatable-read isolation,
  and converts concurrent serialization conflicts into a clear validation
  error. Direct CRUD/import, nested commands, state transitions, relation
  changes, quantity changes and register-cap changes all revalidate final
  database facts.
- Amount boundary:
  `AMOUNT_CUMULATIVE_CONTROL=DEFERRED_PENDING_COMMON_VALUATION_BASIS`.
  Register `registered_amount` and tax-inclusive settlement `amount_total` are
  not treated as a hard-limit pair, and no false remaining-amount field exists.
- Real-ORM evidence: isolated database
  `sc_test_admin_vis_p3_20260726101100_ed88bff4` passed 167 tests with zero
  failures/errors, including a real two-transaction over-settlement race. The
  temporary database and resources were removed, and all
  database/container/network/volume inventory hashes were restored.
- Matrix result: CORE-033 is closed within comparable quantity scope.
  Source-proven historical relation remediation remains explicit and is not
  inferred during upgrade. The next highest-priority gap is
  `CORE-035-SUBCONTRACT-HISTORICAL-REGISTER-RELATION-REMEDIATION`, blocked on
  migration approval:
  `FORMALLY_APPROVE_SOURCE_PROVEN_SUBCONTRACT_REGISTER_RELATION_MIGRATION`.

# UM-P3 post-S07A external-blocker execution rerank — 2026-07-27

- Branch / anchor: `feature/user-module-personal-data-visibility` at the
  accepted S06 commit `0aeb3e4b`.
- S07A disposition: the accepted read-only discovery stop remains local to
  CORE-035. Its policy stays open and its high priority is unchanged, while
  execution waits for authorized LEGACY_SOURCE_A/LEGACY_SOURCE_B sources and an isolated
  S05/S06-ready target:
  `CORE_035_EXECUTION_STATE=BLOCKED_WAITING_FOR_ENVIRONMENT_OPERATOR`.
  S07B is not approved and no migration ran.
- Execution rerank: after excluding only the external blocker, CORE-020
  (`payment.ledger.payment_request_id`) is the highest remaining relation.
  Its authority, one-request-to-zero-or-one-ledger cardinality, approved-state
  requirement, uniqueness, positive-amount and overpayment rules are already
  explicit.
- Permission evidence: the finance-manager `payment.request` rule is limited
  to `company_id in company_ids`, while the finance-manager
  `payment.ledger` rule is unconditional `[(1, '=', 1)]`. Dedicated
  caller-visibility proof cannot close until that model-specific record rule
  is aligned with the authoritative request company boundary.
- Current execution result: zero candidates satisfy every safe-selection
  gate. No product, ACL, record-rule, schema, migration or business-data
  change was made. The unique next decision is
  `FORMALLY_APPROVE_PAYMENT_LEDGER_ALLOWED_COMPANY_RECORD_RULE_CHANGE`.
- CORE-034 remains lower priority and blocked on a common tax, currency,
  valuation and adjustment basis; its amount hard limit remains deferred.

# UM-P3 CORE-020 payment-ledger request-company permission closure — 2026-07-27

- Branch / anchor: `feature/user-module-personal-data-visibility` from
  `f8e567485bc1cfe30da15fd8bcf23d6e36dc5da6`.
- Formal approval:
  `UM_P3_CORE_020_PAYMENT_LEDGER_ALLOWED_COMPANY_RECORD_RULE`, limited to the
  finance-manager-specific `payment.ledger` record rule.
- Authority: required, SQL-unique `payment.ledger.payment_request_id`; the
  ledger rule now follows `payment_request_id.company_id in company_ids`.
  The previous unconditional `[(1, '=', 1)]` domain was removed.
- Permission proof: isolated database
  `sc_test_admin_vis_p3_20260727022903_52bb15f2` passed 211 tests with zero
  failures/errors, covering A-only, B-only, A+B, search, search_count,
  direct-ID access, mixed batches, context switching and create/write/unlink.
  The temporary database was removed and database/container/network/volume
  inventory hashes were unchanged.
- Scope: no ACL, user group, other record rule, public permission framework,
  schema, migration, payment logic or business data changed.
- CORE-035 remains
  `CORE_035_EXECUTION_STATE=BLOCKED_WAITING_FOR_ENVIRONMENT_OPERATOR`, open
  and priority-preserved; S07B remains unapproved.
- Matrix rerank: zero further safe candidates. CORE-034 remains
  `AMOUNT_CUMULATIVE_CONTROL=DEFERRED_PENDING_COMMON_VALUATION_BASIS`; the
  unique next decision is
  `FORMALLY_DECIDE_SUBCONTRACT_CUMULATIVE_AMOUNT_VALUATION_BASIS`.
# UM-P3 CORE-034 subcontract cumulative amount policy — 2026-07-27

- Baseline: `b52a17cef1f8fae329872d6307859e4eca1e2c8f`.
- Formal authority:
  `UM_P3_CORE_034_SUBCONTRACT_CUMULATIVE_AMOUNT_VALUATION_BASIS`.
- Existing anchors proved: `construction.contract.amount_total/currency_id`,
  `sc.subcontract.register.registered_amount/currency_id/state`,
  `sc.subcontract.settlement.amount_total/currency_id/state`, and explicit
  `sc.subcontract.settlement.line.register_line_id`.
- Effective register tax-included totals (`active`, `closed`) and confirmed
  settlement tax-included totals are bounded by contract `amount_total` in exact
  contract currency. Explicit settlement-line totals are additionally bounded
  by the related register-line `registered_amount`.
- No implicit FX, tax inference, absolute-value normalization, schema change,
  migration, ACL, or record-rule change was introduced. Currency comparison
  reuses authoritative currency rounding.
- Ordered contract-row database locks serialize competing effective writes;
  final-state ORM aggregation is repeated after create/write/state transition
  and contract-line amount mutations.
- Isolated real ORM acceptance:
  `sc_test_admin_vis_p3_20260727030941_8bc331bc`, 259 tests, 0 failures,
  0 errors. The temporary database was removed, residue is zero, and database,
  container, network, and volume inventories are unchanged.
- CORE-035 remains
  `BLOCKED_WAITING_FOR_ENVIRONMENT_OPERATOR`; no source scan or historical
  inference was performed. After excluding that external blocker, no further
  safe candidate exists. The unique next input is
  `PROVIDE_AUTHORIZED_LEGACY_SOURCE_A_LEGACY_SOURCE_B_SOURCE_AND_ISOLATED_TARGET`.

# UM-P3 CORE-035 S07A source profiling — 2026-07-27

- Authorization:
  `OWNER_APPROVAL_CORE035_S07A_SERVER_DISCOVERY_20260726`.
- The source was found in the `sc-root` user-module custody artifacts, not on
  `sc-prod`: the LEGACY_SOURCE_A and LEGACY_SOURCE_B strict parity captures share the
  `20260601T130457Z` evidence point and are Git-tracked with recorded SHA-256.
- LEGACY_SOURCE_A has no subcontract-register or subcontract-settlement surface.
  LEGACY_SOURCE_B contains 86 contract rows, 721 register-line capture rows, and 88
  settlement rows.
- Source classification is 0 exact authoritative keys, 0 immutable composite
  keys, 76 ambiguous attribute-only candidates, and 12 conflicting false
  `pid`/`RowIndex` matches. Every false match crosses project; 11 also cross
  counterparty.
- Dedicated target
  `sc_migration_core035_s07a_20260727035410_acab0f53` contains current S05/S06
  models and zero initial subcontract business rows. Only a sanitized aggregate
  profile was stored in `core035_analysis`; the second identical run changed
  zero rows.
- No source, existing database, product code, ACL, record rule, schema, or
  historical relation was modified. S07B remains unapproved.
- CORE-035 remains open and priority-preserved, now with
  `CORE_035_EXECUTION_STATE=BLOCKED_SOURCE_PROVEN_RELATION_EVIDENCE_REQUIRED`.
  The unique next input is
  `PROVIDE_AUTHORIZED_AUDITED_SETTLEMENT_LINE_TO_REGISTER_LINE_MAPPING_OR_DOCUMENT_CONFIRMATION_SET`.

# UM-P3 CORE-035 S07A-C manual confirmation set — 2026-07-27

- Baseline: `da25c8afc903b0358b8a3e5ef59b77c4646848ad`.
- Prepared 88 stable, content-derived review items from the verified LEGACY_SOURCE_B
  capture: 76 attribute-only candidates remain `PENDING`; 12 false-link
  conflicts remain `ESCALATED/REQUIRE_SOURCE_DOCUMENT`.
- The package preserves all finite candidates as hashed references and records
  consistency outcomes only. It does not rank, recommend, pre-confirm, or emit
  a migration mapping.
- `pid -> RowIndex` remains explicitly prohibited. All 12 superficial matches
  cross project and 11 also cross counterparty.
- The authorization template is unsigned. Authorized-final count is zero;
  S07B remains unapproved and no migration or relation remediation ran.
- The retained S07A target was restored after ORM verification and now contains
  zero subcontract business rows, zero `register_line_id` relations, and one
  sanitized aggregate profile. The independent regression run passed 259 tests
  with zero failures and zero errors.
- Current state:
  `CORE_035_EXECUTION_STATE=S07AC_CONFIRMATION_SET_READY`.
- Unique next decision:
  `ASSIGN_AUTHORIZED_BUSINESS_OWNER_DATA_STEWARD_AND_SECOND_REVIEWER`.

# CORE-035 UAT role context and shell stability — 2026-07-28

- Branch / anchor: `feature/user-module-personal-data-visibility` from
  `ad99156a40e46a84c93d5a6ed3f049f9bc901227`.
- Formal Product Layer: P1 construction-industry role contract plus the
  generic frontend shell renderer. No customer data or permission semantics
  moved into the shared frontend.
- The standard `executive` role now publishes the customer-facing label
  `管理层`. `AppShell` consumes that contract and exposes an operative account
  context panel with the current role, user, company and existing logout
  action; the shell does not contain a role-code translation dictionary.
- The UAT shell now removes the browser's default document margin, includes
  sidebar padding inside the viewport height, reserves the shared 52px toolbar
  height, keeps a stable scrollbar gutter and reserves the full routed-page
  height during async loading.
- Public UAT browser proof covered both CORE-035 accounts and all 94 business
  routes. No raw `executive` label, denied page, horizontal overflow or browser
  error remained. Before/after geometry reduced maximum routed-page loading
  expansion from `728.19px` to `71px`; shell, sidebar, content, topbar and
  router-host geometry stayed identical across all 94 routes.
- The same viewport contract passed at `1280x800`, `1440x1000` and
  `1920x1080`. UAT business data, permissions, historical relations and
  financial guards were not modified.

# Shared list and kanban loading continuity — 2026-07-28

- Branch / anchor: `feature/user-module-personal-data-visibility` from
  `7c2481e2e80e5c6dc3702a4095ae8c2b9db68577`.
- Formal Product Layer: P0 generic frontend runtime; Layer Target:
  `frontend renderer`; Module: `frontend/apps/web`.
- Reason / Why Here: the shared list and kanban renderers owned a generic
  loading lifecycle that cleared the resolved native-view structure and
  records before every request. The fix contains no construction-industry,
  role, customer or record semantics.
- Why Not Elsewhere: backend contracts already provide the authoritative view
  and data. A customer module, low-code configuration or runtime data repair
  cannot provide consistent first-load and refresh feedback across actions.
- First load now renders a stable, structure-matched list or kanban skeleton
  instead of stretching a small status alert over the workspace. Subsequent
  pagination, filter and refresh requests retain the previously rendered
  records and expose a non-layout-shifting progress indicator.
- Delayed-request geometry is identical before and after resolution:
  list `toolbar=42px/main=790px/page=952px`; kanban
  `toolbar=47px/main=939px/page=1175px`. Route-selected kanban mode is applied
  before the first request so the page never flashes a list-shaped placeholder.
- Blast Radius: shared action list and kanban surfaces only. Delayed-request
  browser proof covers initial loading and retained-content refresh; typecheck,
  production build, route regression and `git diff --check` verify containment.
- UAT data, permissions, historical relations and financial guards remain
  unchanged.

# Business workspace inline-gutter consolidation — 2026-07-28

- Branch / anchor: `feature/user-module-personal-data-visibility` from
  `66df2695dbd8cb1959ec933b03fdc151c2117a8f`.
- Formal Product Layer: P0 generic frontend shell; Layer Target:
  `frontend renderer/AppShell`; Module: `frontend/apps/web`.
- Reason / Why Here: the desktop routed workspace accumulated AppShell's
  14px inline inset and the shared page frame's 32px inset. This generic
  double gutter placed the first business surface 46px from the sidebar
  divider. Neither customer configuration nor backend data owns that visual
  geometry.
- The business router now extends to the sidebar divider and the routed page
  owns one 20px desktop inline gutter. Configuration routes keep their
  existing shell geometry; mobile business routes retain a 16px safe gutter.
- Public UAT browser measurements at 1440px changed
  `divider -> page frame` from 14px to 0 and
  `divider -> business surface` from 46px to 20px. The sampled table width
  increased from 1097px to 1149px without horizontal overflow.
- The same 20px contract passed at 1280px and 1920px. The 900px responsive
  shell passed with a 16px content gutter. Sequential route regression
  passed 50/50 and 44/44 routes with no access denial, loading residue,
  browser error or horizontal overflow.
- Blast Radius: shared non-configuration business workspace geometry only.
  UAT data, permissions, historical relations and financial guards remain
  unchanged.

# Business configuration frontend type-contract closure — 2026-07-28

- Branch / anchor: `feature/user-module-personal-data-visibility` from
  `dd77b3383db1dc388d008b3ed2d8309d07e3ce89`.
- Formal Product Layer: P0 generic frontend business-configuration contract;
  Layer Target: `frontend API/runtime consumer`; Module: `frontend/apps/web`.
- The staged change-set request type now includes the backend-supported
  optional `contract_name` lookup key. No new transport or backend field was
  introduced.
- Form configuration reads precheck warnings only from responses that
  actually carry a precheck object. Staged change-set responses remain typed
  as change sets instead of being falsely widened with a standalone-save
  response field.
- Menu configuration now derives its target key from the company returned by
  the authoritative configuration panel. Missing company context blocks the
  save explicitly rather than relying on the nonexistent `session.companyId`
  property or emitting a `menu.config.company.0` target.
- Standard typecheck, strict typecheck, affected-source ESLint and production
  build all pass. The change does not alter UAT data, permissions, published
  configuration, historical relations or financial guards.

# Single-divider business workspace boundary — 2026-07-28

- Branch / anchor: `feature/user-module-personal-data-visibility` from
  `306a598aa486beb3f96e214aa01b2dd91ea99b58`.
- Formal Product Layer: P0 generic frontend shell and list renderer; Layer
  Target: `frontend presentation`; Module: `frontend/apps/web`.
- Browser inspection proved that the previous seam contained three vertical
  strokes: the nested navigation card at x=221, the formal sidebar boundary
  at x=236, and the primary table shell at x=256.
- The navigation region is now a flat, transparent surface without an outer
  card border. The primary list table retains horizontal structure and row
  separators but removes inline borders and panel shadow. The 20px business
  content gutter remains unchanged.
- Initial list loading uses the same flat boundary contract as the resolved
  table: both inline borders and shadow compute to none. Loading and resolved
  geometry remain identical at `toolbar=42px`, `main=790px`,
  `page=952px`.
- Public UAT proof leaves exactly one shell separator: the sidebar's 1px
  inline-end border. Sequential navigation regression passed 50/50 and 44/44
  routes with no denied page, residual loading state, browser error or
  horizontal overflow.
- Blast Radius: generic sidebar navigation presentation and primary list
  surfaces only. Form panels, dialogs, cards, UAT data, permissions,
  historical relations and financial guards remain unchanged.

# List-to-form loading continuity — 2026-07-28

- Branch / anchor: `feature/user-module-personal-data-visibility` from
  `24c7f57c1891a1ad5c9b0f53e9abca223c0924b7`.
- Formal Product Layer: P0 generic record-form renderer; Layer Target:
  `frontend presentation/runtime continuity`; Module: `frontend/apps/web`.
- Delayed-request browser inspection proved that the old transition rendered
  an incomplete real form header at `323.6px` high and a second `449px`
  status card. The resolved header was only `38px`, so the route visibly
  changed structure while loading.
- Initial record loading now renders one structure-matched form skeleton.
  Its header and body use the resolved form's exact horizontal frame, with a
  `38px` header and the body starting at `y=193px`. The generic status card
  is no longer part of a successful form load.
- A refresh after the form contract is available retains the existing form,
  disables transient interaction and shows a reduced-motion-aware progress
  edge instead of replacing the page.
- A 2.2-second delayed public-UAT click from customer list to record form
  passed with `statusPanel=false`, loading and resolved width `1149px`,
  identical header geometry, identical body start, and zero browser or
  console errors.
- Blast Radius: shared record-form initial loading and refresh feedback only.
  UAT data, permissions, historical relations and financial guards remain
  unchanged.

# Personal-data hash-boundary scan correction — 2026-07-28

- Branch / anchor: `feature/user-module-personal-data-visibility` from
  `78168407a105de5ba800fadc1ac49a4e23fb765b`.
- Formal Product Layer: P4 delivery security tooling; Layer Target:
  `repository personal-data gate`; Module: `scripts/ci`.
- Pre-merge scanning identified an 11-digit sequence embedded inside a
  40-character anonymized candidate reference. The sequence was not an
  independently delimited phone number and no matched value was printed.
- The mobile-phone rule now requires an alphanumeric boundary on both sides,
  preserving rejection of standalone mobile numbers while avoiding false
  classification of hash-internal digit runs. A focused regression locks both
  behaviors.
- Blast Radius: repository personal-data scanning only. No audit record,
  business data, product runtime, UAT permission or financial behavior changed.

# Tenant-neutral P3 governance projection — 2026-07-28

- Branch / anchor: `feature/user-module-personal-data-visibility` from
  `771510bc4ae8b7526177b75f4f302878fa88c565`.
- Formal Product Layer: P0/P1 product governance with P4 delivery evidence;
  Layer Target: `tenant-neutral product repository boundary`; Modules:
  `docs/audit/um_p3`, `scripts/verify`, `scripts/ops`, and frontend guard tests.
- Pre-merge product-boundary validation found legacy tenant source names in
  otherwise anonymized governance references. Those names are delivery
  identities, not platform or construction-standard semantics.
- The product-tree projection now uses `LEGACY_SOURCE_A` and
  `LEGACY_SOURCE_B`. The 88 review-item identifiers remain content-derived and
  stable, while their evidence digests, package hash and authorization-template
  hashes were rebuilt deterministically.
- Validation preserves all governance counts and prohibitions:
  `88=76+12`, zero authorized mappings, no migration, and no S07B approval.
  The tenant payload boundary reports zero fixed customer identifiers and zero
  customer payload files.
- Blast Radius: names and derived digests in anonymized governance evidence and
  related guard fixtures only. Product runtime, UAT data, permissions,
  financial controls and historical relation decisions are unchanged.

# RELEASE-P0-01R qualification fail-closed repair — 2026-07-28

- Branch / anchor: `fix/release-p0-01r-qualification-fail-closed` from
  `e948e760c09f1f3be25f3844149932925de2e6aa`.
- Formal Product Layer: P4 release governance and P0 platform authorization
  verification; Layer Target: GitHub required checks, immutable release
  candidate qualification, and generic chatter timeline authorization tests;
  Modules: `.github/workflows`, `scripts/ops`, and `addons/smart_core/tests`.
- Reason: the merged `main` SHA must receive its own required-check evidence,
  superseded candidates must fail before any database rehearsal, and timeline
  content/existence boundaries require real ORM negative proof.
- Why Here / Why Not Elsewhere: release eligibility belongs to delivery
  governance, while timeline authorization verification belongs beside the
  platform handler. No construction-domain policy, customer data, frontend
  behavior, or runtime permission configuration is changed.
- Blast Radius: CI event/checkout qualification, RC6 release-tool entrypoints,
  and isolated authorization tests only. DAILY and production databases,
  candidate images, business models, ACLs, record rules, and frontend
  experience remain untouched.

# FE-R2-P1-01 business-list productization — 2026-07-29

- Branch / anchor: `feat/frontend-business-list-productization` from
  `b4c8bfd9870f558e27324066a7c3cd07420d5652`.
- Formal Product Layer: P0 generic contract renderer; Layer Target:
  `shared frontend business-list presentation`; Module: `frontend/apps/web`.
- Reason: payment, contract, and project list surfaces exposed the same weak
  title/action hierarchy, fragmented query feedback, indistinct filtered-empty
  state, and heavy table framing. These are generic rendering concerns rather
  than construction policy or customer data semantics.
- The shared list header, action toolbar, list state, and table presentation now
  provide a clear business title and result count, visible/removable active
  conditions, distinct filtered-empty recovery, restrained table boundaries,
  stronger primary cells, localized standard audit columns, and accessible row
  numbering.
- Why Here / Why Not Elsewhere: all three real pages consume the same contract
  renderer, so the change belongs in the shared frontend surface. No backend
  field, role, ACL, record rule, navigation identity, low-code customer
  preference, or fixture business meaning is changed.
- Blast Radius: generic list rendering and its isolated browser acceptance only.
  Targeted payment, contract, and project journeys cover 1440x900, 1280x800,
  and 960x768 with zero serious/critical axe findings and zero console,
  pageerror, blocking HTTP, or document-overflow findings.

# FE-R2-P1-02 business detail/form productization — 2026-07-29

- Branch / anchor: `feature/frontend-detail-form-productization` from
  `96aa5d7368ef5f6383a1c98f57e9400b3d8c1c8f`.
- Formal Product Layer: P0 generic contract renderer; Layer Target:
  `shared frontend business detail/form presentation`; Module:
  `frontend/apps/web`.
- Reason: payment request, contract, and project routes shared four product
  defects: composite technical-looking record headings, edit routes fronted by
  a read-only financial workspace, duplicate native/header actions, and
  relation identifiers shown without their authorized business labels.
- The explicit route now owns the page mode (`/r` is detail and `/f` is
  edit/create). Contract-declared primary fields produce concise identity,
  edit routes enter the native form directly, the header exposes one direct
  business action plus overflow, and required/read-only/dirty states use
  visible text. The debug HUD is opt-in even in development.
- Why Here / Why Not Elsewhere: all three real domains consume the same
  contract-driven form renderer. The change preserves native view order and
  grouping, uses only relation labels already readable by the caller, and does
  not add frontend model-specific semantics or alter backend authorization.
- Blast Radius: shared detail/form identity, presentation and isolated browser
  verification only. Eighteen targeted screenshots cover three domains, two
  modes and three work viewports with zero serious/critical axe findings,
  runtime errors, raw relation identifiers or horizontal overflow. No customer,
  DAILY or production database was accessed.

# FE-R0-CLEAN frontend product baseline reconstruction — 2026-07-29

- Branch / anchor: `fix/fe-r0-clean` from
  `8e4b7512e56a5f8db034f1f731b6702a70f04547`, followed only by the two
  approved multi-role union commits `a1d83d154975f3161f6b20a67cefde0ab6e62da6`
  and `a1a416699cc8a526e5658520a7a9829dd983bb62`.
- Formal Product Layer: P0 generic frontend runtime; Layer Target:
  `shared page renderer and route assembly guards`; Module:
  `frontend/apps/web`.
- Reason: establish a traceable frontend product baseline before the separate
  FE-R1 scrolling iteration. The clean branch restores product-surface markers,
  keeps the shared form container within its governed size limit, and teaches
  the route guard to verify the existing `ContractFormRoute` compatibility
  wrapper instead of requiring a direct page import.
- Why Here / Why Not Elsewhere: the changes close generic renderer and static
  verification gaps only. They do not introduce construction-domain semantics,
  modify role projection, or change backend authorization.
- Blast Radius: frontend semantic marker classes and their fail-closed static
  guards. The excluded single-scroll and sticky-header experiments are not
  present; no overflow, scroll-container, sticky-position, database, ACL,
  record-rule, navigation, or business-data behavior is changed.

# Full-list field semantic integrity convergence — 2026-07-30

- Branch / anchor: `fix/fe-r1-single-vertical-scroll` from
  `779db55b3c119c0c45cd9618fcad2408326e22d3`.
- Formal Product Layer: P0 platform contract mechanism plus P1 construction
  industry field semantics; Layer Target: native list semantic normalization,
  authoritative aggregation, and generic frontend contract consumption;
  Modules: `addons/smart_core`, `addons/smart_construction_core`,
  `frontend/apps/web`, and `scripts/verify`.
- Reason: historical compatibility projection fields preserve visible values
  but can erase monetary, numeric, date, selection, and relation semantics
  between the native model and the list contract. The first confirmed symptom
  is a missing page/filtered total for `tender.doc.purchase`.
- Standard vs User-Specific: the contract protocol, aggregation execution, and
  frontend rendering rules are platform mechanisms. Construction models own
  their explicit projection-to-formal-field mapping. No customer identifier,
  tenant data, or page-specific frontend dictionary is allowed.
- Why Here / Why Not Elsewhere: `smart_core` must transport and enforce generic
  semantic declarations without knowing construction fields;
  `smart_construction_core` must declare its formal value and aggregation
  sources. The frontend only renders the declared result and must not infer
  numeric meaning from Chinese labels or formatted strings. P2 customer data,
  P3 runtime preferences, and P4 repair scripts are not semantic authorities.
- Blast Radius: all published native list contracts and their sort, filter,
  aggregate, and export field identities. List visual structure, scrolling,
  ACLs, record rules, company/project scopes, business data, and production
  runtime are excluded. Validation must reconcile page and filtered totals
  under the same authorized domain and fail closed on undeclared lossy
  projections.

# FIELD-ARCH-P0-01 product field purity audit — 2026-07-30

- Branch / anchor: `audit/field-arch-p0-01` from
  `2b68039cfc5410b22c54ded596140ef2470ad5d4`.
- Formal Product Layer: P4 ops audit; Layer Target: read-only field inventory,
  dependency classification, and cross-company discovery evidence; Module:
  `scripts/verify` plus `docs/audit/field_arch_p0_01`.
- Reason: determine whether legacy compatibility aliases and runtime custom
  fields are product-standard fields, tenant-owned extensions, isolated
  migration metadata, or globally discoverable model/schema pollution.
- Standard vs User-Specific: this task changes no P0/P1/P2/P3 runtime fact. It
  audits P1 product declarations, P2/P3 extension ownership, and P4 migration
  compatibility without deleting fields or changing records.
- Why Here / Why Not Elsewhere: evidence generation and classification belong
  to P4. Moving or deleting fields would require separate P1/P2/P3 migration
  tasks with rollback plans and is explicitly excluded.
- Blast Radius: repository source analysis, sanitized metadata snapshots, and
  rollback-only probes in an isolated customer UAT database. No business value,
  production database, DAILY database, 18093 deployment, ACL, record rule, or
  product contract is modified.
## 2026-07-31 — CANDIDATE-GATE-CLOSURE-01

- Branch: `fix/candidate-gate-closure-01`
- Starting product commit: `733b61647495e0c0264204fdf65dbbcdc1b4b3ae`
- Formal Product Layer: P1 construction industry product navigation plus generic frontend runtime organization
- Layer Target: finance release navigation projection and frontend complexity locks
- Module: `smart_construction_core` finance surface, contract form route shell, and session store
- Reason: publish the already-authorized historical payment read-only entry to finance and restore the candidate line-count gates without changing behavior
- Standard vs User-Specific: generic product behavior; no customer identifier, payload, or customer-specific branch
- Why Here / Why Not Elsewhere: the role projection belongs to the industry product policy; type and pure query helpers belong beside their generic frontend domains rather than customer modules or release exceptions
- Blast Radius: finance navigation adds one existing read-only menu identity; contract form and session changes only move pure helpers/types; no ACL, workflow, payload, database, `main`, protection, or production mutation
- Validation: finance projection unit guard, role/authorization regression, frontend lint/strict/build/unit gates, complexity locks, four required checks on the new SHA, and dual-remote candidate parity

## 2026-07-31 — RELEASE-TOOLING-P0-RC11-RUNTIME-FIX-05

- Branch: `fix/rc11-runtime-plan`
- Starting product commit: `0750d928ca7049eb7cc368d3988f158f6ad17f67`
- Formal Product Layer: P0 platform kernel plus P4 release delivery tooling
- Layer Target: signed tenant-payload maintenance capability comparison and immutable candidate publication gate
- Module: `smart_core` tenant payload boundary and `scripts/release` publication evidence
- Reason: replace the invalid runtime comparison call and require the final candidate image to complete the real payload plan path against an isolated equivalent database before publication
- Standard vs User-Specific: generic signed-import and release safety mechanism; no customer semantics or payload contents are encoded
- Why Here / Why Not Elsewhere: capability authorization belongs to the platform import boundary, while pre-publication execution evidence belongs to release tooling; neither belongs in customer modules, frontend code, or production data
- Blast Radius: maintenance capability matching, focused release tests, candidate publication preflight, and version identity only; production data, ACL design, customer package, v4 payload, and runtime services remain unchanged
- Validation: behavioral equality/mismatch tests, repository API audit, publication negative tests, HIGH_RISK required checks, and final rc.11 image execution of the production-equivalent v4 plan with zero database writes

## 2026-08-01 — CI-SURFACE-AWARE-ORCHESTRATION-01

- Branch: `fix/ci-surface-aware-orchestration`
- Starting product commit: `3fb17948feacb34c2574668eaba7ddb2ad4bef26`
- Formal Product Layer: P4 delivery and CI orchestration
- Layer Target: risk-tier routing and required-check execution ownership
- Module: `config/ci`, `scripts/ci`, GitHub Actions workflows, and `make/ci.mk`
- Reason: high-risk release or operations changes currently trigger the complete frontend release suite even when no frontend surface changed, while the professional gate independently reinstalls and rebuilds the frontend. Route validation by affected surface and retain one authoritative frontend executor.
- Standard vs User-Specific: generic repository delivery policy; no customer, tenant, role, navigation, or business semantics are encoded.
- Why Here / Why Not Elsewhere: CI classification owns lane selection, the frontend workflow owns frontend validation, and the professional workflow owns backend/static validation. Product modules and production runtime are outside this change.
- Blast Radius: required-check orchestration and CI duration only. Check names, fail-closed risk classification, release-event full validation, frontend dependency/config full validation, application code, databases, and production services remain unchanged.

## 2026-08-01 — GOVERNED-PRODUCTION-IMAGE-SYNC-01

- Branch / anchor: `fix/governed-production-image-sync` from `a0c706ba8709c8ccf2c00e76647d6c340d7b93a4`.
- Formal Product Layer: P4 ops delivery tool.
- Layer Target / Module: governed immutable candidate transfer in `scripts/ops` and `make/release.mk`.
- Reason: preload an already-published candidate image when the production registry path is too slow, without weakening release identity checks or touching runtime state.
- Standard vs User-Specific: generic release delivery mechanism; no tenant, customer, role, navigation, or business semantics.
- Why Here / Why Not Elsewhere: verified artifact transfer belongs to P4 release operations, not platform, industry, customer, low-code, frontend, or database layers.
- Blast Radius: the fixed `sc-prod` Docker image cache only. The target creates no remote staging file and does not modify services, containers, volumes, systemd, databases, or application source.
- Validation: clean dual-remote-approved main, archive path and SHA-256, restricted image ref, local and remote image content ID equality, fixed SSH target, and focused unit/contract tests.

## 2026-08-01 — GOVERNED-PRODUCTION-IMAGE-SYNC-IDENTITY-02

- Branch / anchor: `fix/governed-production-image-sync-id` from `7519cee5ca62a84c69922fad887366d0f5e2f760`.
- Formal Product Layer / Target: P4 ops delivery tool; Docker-backend-portable immutable image identity verification.
- Module / Reason: `scripts/ops/production_candidate_image_sync.py`; distinguish the OCI manifest ID reported by a containerd image store from the archive config ID reported by classic Docker while proving both belong to the same SHA-verified archive.
- Standard vs User-Specific / Why Here: generic artifact transport compatibility belongs to P4 release operations and carries no product or customer semantics.
- Why Not Elsewhere / Blast Radius: no P0-P3, frontend, runtime configuration, container, volume, database, service, or systemd behavior changes; only verification and cached-image transfer skipping are affected.
- Validation: synthetic archive manifest/config digest tests, remote cached-ID skip test, focused backup/restore contract, and required PR checks.

## 2026-08-01 — GOVERNED-RESTORE-CANCEL-01

- Branch / anchor: `fix/governed-restore-cancel` from `866177db69135738ae266d7bf8b9b64ebbc1ee36`.
- Formal Product Layer / Target / Module: P4 ops delivery tool; scoped isolated-restore cancellation in `scripts/ops` and `make/release.mk`.
- Reason: a disconnected SSH client can leave an isolated restore waiting on a registry pull; cancellation needs an auditable fail-closed Make entry before cleanup.
- Standard vs User-Specific / Why Here: generic production rehearsal lifecycle control belongs to P4 and carries no customer or product semantics.
- Why Not Elsewhere / Blast Radius: no runtime application, P0-P3, systemd, production container, volume, database, or service behavior; SIGTERM is limited to one exact report/restore-ID process tree and cleanup remains separately authorized.
- Validation: report-root and identity guards, exact process-argument matching, SIGTERM-only static contract, focused backup/restore suite, and required PR checks.

## 2026-08-01 — RESTORE-HEALTH-CONFIG-PERMISSION-01

- Branch / anchor: `fix/restore-health-config-permission` from `7db6264a636c1cd79b68ed95b3dc87e4e424fbe9`.
- Formal Product Layer / Target / Module: P4 ops delivery tool; isolated restore health container in `scripts/release/production_backup_restore.py`.
- Reason: the root-owned `0600` temporary Odoo config bind mount is unreadable by the RC12 image's default unprivileged `odoo` user.
- Standard vs User-Specific / Why Here: generic restore rehearsal execution compatibility belongs to P4 and contains no customer or product semantics.
- Why Not Elsewhere / Blast Radius: no image, P0-P3, frontend, production service, production database, systemd, or runtime-compose change; only the network-isolated health container receives supplemental group `0`, and the temporary config remains non-world-readable and is unlinked in `finally`.
- Validation: health-container command contract, observed temporary mode `0640`, continued absence of `--user`, focused backup/restore tests, and required PR checks.

## 2026-08-01 — GOVERNED-CANDIDATE-MANIFEST-SYNC-01

- Branch / anchor: `fix/governed-candidate-manifest-sync` from `03cb579f24e53a3b9a669745388f2f7e06274855`.
- Formal Product Layer / Target / Module: P4 ops delivery tool; immutable production candidate manifest synchronization in `scripts/ops` and `make/release.mk`.
- Reason: RC11 and RC12 production orchestration files are byte-identical, so production needs only the RC12 formal identity files rather than another source bundle.
- Standard vs User-Specific / Why Here: generic release identity delivery belongs to P4 and carries no customer or business semantics.
- Why Not Elsewhere / Blast Radius: no source, image, container, volume, service, systemd, database, P0-P3, or frontend mutation; the only remote write is a new atomic `/opt/sce/candidates/v1.0.0-rc.12` directory.
- Validation: secure-root containment, exact source/version/GHCR digest identity, release checksum, three-file inventory, immutable-existing-target fail-closed behavior, focused contract tests, and required PR checks.

## 2026-08-01 — PRODUCTION-PROMOTION-CONFIG-FLOW-01

- Branch / anchor: `fix/production-promotion-config-flow` from `407dea2efa964ff4e2dcab36f0f46d34dc7ebe94`.
- Formal Product Layer / Target / Module: P4 ops delivery; production deployment tooling sync, runtime identity promotion, and pre-replacement readiness configuration.
- Reason: the readiness contract hard-coded an obsolete image ID while production config carried a stale product key/image ID; immutable RC12 deployment needs dynamic exact-ID validation plus durable atomic identity promotion.
- Standard vs User-Specific / Why Here: generic production release lifecycle control belongs to P4 and carries no business or customer semantics.
- Why Not Elsewhere / Blast Radius: no P0-P3, frontend, image build, container replacement, service, systemd, volume, or database mutation; remote writes are a new immutable tool directory and two fixed configuration files with paired rollback copies.
- Validation: SHA-only deployment image IDs, exact Docker inspect equality, current-running/next-manifest identity checks, root-owned mode guards, paired rollback, clean dual-remote main, focused tests, and required PR checks.

## 2026-08-01 — RC12-PRODUCTION-DEPLOYMENT-RECORD-01

- Branch / anchor: `release/rc12-production-deployment-record` from `915067ba5d282bfcc03d276d49cd61c5f169a0fd`.
- Formal Product Layer / Target / Module: P4 ops delivery; production deployment evidence in `docs/ops/releases/current`.
- Reason: close the completed RC12 immutable-image upgrade with a repository-governed, reviewable deployment record.
- Standard vs User-Specific / Why Here: release evidence is generic P4 operational governance; tenant identity is recorded as deployment context only and no customer behavior is encoded.
- Why Not Elsewhere / Blast Radius: no P0-P3, frontend, application source, image, runtime configuration, container, service, volume, or database change; only documentation and audit evidence are added.
- Validation: production deployment record guard, production release flow guard, diff integrity, required PR checks, and dual-remote main parity after merge.

## 2026-08-01 — PRODUCTION-USER-ACTIVATION-READINESS-01

- Branch / anchor: `feature/production-user-activation-readiness` from `3de566fdbfc2b699155ce91800cc1601124e12b9`.
- Formal Product Layer / Target / Module: P4 ops delivery tool reading the P0 `smart_core` enterprise activation model.
- Reason: begin the real-user usage closure with a governed production readiness probe before any activation administrator grant, pilot selection, credential issuance, or password change.
- Standard vs User-Specific / Why Here: aggregate activation readiness is generic release operations evidence; it contains no customer identity, preference, roster, or business semantics.
- Why Not Elsewhere / Blast Radius: no frontend, P1-P3, runtime configuration, user, permission, credential, service, volume, or database mutation; the only output is a root-only aggregate evidence file.
- Validation: strict production/database/read-only controls, PostgreSQL read-only transaction before ORM access, privacy-negative tests, production release contract tests, and required PR checks.

## 2026-08-01 — PRODUCTION-USER-ACTIVATION-03-PREDEPLOY

- Branch / anchor: `release/production-user-activation-03-predeploy` from `966082fe8258cdf38e8fe3899b69fa5f48e2729c`.
- Formal Product Layer / Layer Target / Module: P4 ops delivery tool in `scripts/release` and `make/release.mk`, invoking the installed P0 `smart_core` activation mechanism.
- Reason: establish the production activation runtime baseline after the completed RC12 immutable-image release without redeploying RC12 or issuing any user credential.
- Standard vs User-Specific: generic governed production activation setup; the tenant key and approved user population remain runtime evidence and are not encoded as product semantics.
- Why Here / Why Not Elsewhere: plan/apply/verify orchestration and evidence belong to P4; token, binding, and permission behavior remain in P0; no P1 industry, P2 customer module, P3 low-code, frontend, or product-image change is needed.
- Blast Radius: at most two `ir.config_parameter` rows and one activation-administrator group relation for the unique active internal `admin`. Ordinary users, logins, passwords, roles, companies, credentials, business data, modules, images, services, and public registration remain unchanged.
- Validation: frozen RC12 and immutable tool identity, database-enforced read-only plan/verify, exact 62/76/14 roster assertion, isolated minimal-permission TransactionCase, plan-digest drift guard, exact write counters, and write-after read-only verification.

## 2026-08-01 — PRODUCTION-DEPLOYMENT-TOOL-DIRECTORY-PERMISSION-01

- Branch / anchor: `fix/production-tool-directory-permission` from `0bae81fc1d420db4febda68acd52d0edf05fe7b4`.
- Formal Product Layer / Layer Target / Module: P4 ops delivery tool in `scripts/ops/production_deployment_tool_sync.py`.
- Reason: `mkdtemp` left a synchronized immutable tool root at `0700`, so the production image's unprivileged `odoo` user could not read the mounted tool marker before a read-only activation plan.
- Standard vs User-Specific / Why Here: generic immutable tool transport permissions belong to P4; no tenant, customer, activation, product, or business semantics change.
- Why Not Elsewhere / Blast Radius: no P0-P3, frontend, image, module, service, container, database, volume, or existing immutable target mutation. New tool roots are explicitly `0755`; file modes and root ownership remain preserved.
- Validation: exact directory-mode assertion, existing-target mode guard, idempotent archive drain, remote-error precedence over local SIGPIPE, focused sync tests, and production release contract tests.

## 2026-08-01 — PRODUCTION-ACTIVATION-CAPABILITY-DIAGNOSTICS-01

- Branch / anchor: `fix/activation-predeploy-capability-diagnostics` from `884a36cd7e9c09951e31f25643e1af83b966f54a`.
- Formal Product Layer / Layer Target / Module: P4 activation predeploy diagnostics in `scripts/release`.
- Reason: the first database-enforced read-only production plan correctly blocked a capability/policy mismatch but collapsed all checks into one code, preventing the required per-check decision record.
- Standard vs User-Specific / Why Here: non-secret fail-closed diagnostics belong to the P4 verifier; no product or tenant behavior is changed.
- Why Not Elsewhere / Blast Radius: no P0-P3, frontend, image, module, service, user, group, parameter, credential, business data, or database mutation. Only the blocked terminal message gains the required boolean/TTL/XMLID/parameter-name diagnostics.
- Validation: complete diagnostic-key contract, secret/identity-negative assertion, focused predeploy tests, and production release contract tests.
## 2026-08-01 — wutao single-user production activation governance

- Branch: `release/wutao-single-user-activation-01r`
- Start SHA: `ee9a098`
- Formal Product Layer: P4 ops delivery tool
- Layer Target: governed production activation plan/apply/verify
- Module: `scripts/release`, `make/release.mk`
- Standard vs User-Specific: one-off explicitly approved production operation
- Why Here: production writes require an allowlisted Make target with immutable
  tool identity, reviewed plan digest, exact write ceilings, and redacted evidence.
- Why Not Elsewhere: the existing P0 activation model already owns credential
  semantics; no product image, frontend, role policy, or customer data baseline
  change is needed.
- Blast Radius: two runtime parameters, one `admin` activation-group relation,
  optional `wutao.active`, one activation batch/credential and non-secret audit;
  all other user, role, company, login, and business records are fingerprinted.

## 2026-08-01 — PRODUCTION-GOVERNED-PASSWORD-RESET-01

- Branch / anchor: `codex/governed-user-password-reset` from `6bee5e63821db2838db729b35b7459f20c3195e2`.
- Formal Product Layer / Layer Target / Module: P4 ops delivery tool in `scripts/ops` and `make/release.mk`.
- Reason: provide a reusable, governed single-user production password-reset entry that does not depend on activation credentials, email delivery, or a batch user roster.
- Standard vs User-Specific / Why Here: the mechanism is generic and accepts one exact login; the separately approved `wutao` execution remains runtime scope and is not encoded in the tool.
- Why Not Elsewhere: password maintenance is an operational delivery action, not P0 authentication product behavior, P1 industry semantics, P2 customer configuration, P3 low-code data, or frontend behavior.
- Blast Radius: one Odoo ORM `res.users.password` write for the unique active internal target. Login, role, job, company and menu scope, other users, business data, RC12 image, modules, services, and runtime configuration remain unchanged.
- Validation: immutable synchronized-tool identity, production/database/danger guards, real TTY enforcement, `/dev/tty` `getpass` double entry, password transport negative assertions, ORM-only static contract, before/after scope fingerprints, other-user fingerprint, real HTTP login, `system.init`, and authorized-menu contract access.

### Production terminal preflight correction

- Follow-up branch / anchor: `fix/password-reset-target-db-binding` from `1355bd47c1bb82978983f8d7bfa6370d88dbefaa`.
- The first no-password terminal preflight stopped before container creation because Compose requires explicit `TARGET_DB` even when the public entry receives the equivalent `DB` alias.
- The P4 Make recipe now binds both `TARGET_DB` and `DB_NAME` to the already validated `sc_production` value before Compose interpolation. No database, container, service, image, user, or password write occurred during the blocked preflight.

### Current-runtime Compose context reconstruction

- Follow-up branch / anchor: `fix/password-reset-runtime-context` from `d90836c4761d2b3cf87ea880fbb6036608114eee`.
- The second no-password terminal preflight showed that `.env.prod` intentionally lacks the complete immutable-release Compose identity. The launcher now reads only the four running `sc_production` service identities, digest image refs, exact database/environment/source values, and named mounts, then reconstructs the one-off context without printing or copying secret values.
- The customer-addons overlay and current manifest mounts are preserved for registry compatibility. Both blocked preflights ended before container creation and produced zero database writes.

### Redacted execution-stage diagnostics

- Follow-up branch / anchor: `fix/password-reset-stage-diagnostics` from `e54a2f42a04cb6f00f16fb4f2ce6b1ba19e93f85`.
- The third no-password terminal preflight passed production database-contract and config rendering, created and removed only the governed one-off container, then stopped before the password prompt with a redacted `OperationalError`.
- The tool now reports only a fixed non-secret execution stage and exception class for unexpected failures. Exception text, connection strings, credentials, passwords, hashes, and payloads remain excluded; the failed preflight performed zero database writes.

### Live infrastructure-secret context

- Follow-up branch / anchor: `fix/password-reset-live-secret-context` from `8af2cbf89aa5f4ccd4f02977d81bb09c7344c81c`.
- Redacted stage diagnostics localized the fourth no-password preflight to Odoo bootstrap. A digest-only equality check proved that disk `.env.prod` retained stale database, JWT, and Odoo master secrets while the current production container held the active values.
- The launcher now inherits `DB_USER`, `DB_PASSWORD`, `JWT_SECRET`, and `ADMIN_PASSWD` in memory from the already verified running Odoo container. Values are never printed, persisted, copied into evidence, or used as the target user's password; the failed preflight performed zero database writes.

### Native getpass TTY handling

- Follow-up branch / anchor: `fix/password-reset-getpass-tty` from `a41673b8e5b181caed95273eafd3d342ec927d3b`.
- The fifth no-password preflight passed database contract, configuration rendering, Odoo bootstrap, and live secret inheritance, then proved that Python text `r+` wrapping is unsupported for this container's TTY device.
- The tool now lets standard-library `getpass` open and control `/dev/tty` natively while retaining the outer real-TTY guard. No stream override, stdin pipe, environment value, argument, or file can carry the new user password; the failed preflight performed zero database writes.

### Activation-independent immutable identity resolution

- Follow-up branch / anchor: `fix/password-reset-identity-resolution` from `4d8ee50fc221dd3a6f70b472eed056e525cfc562`.
- The sixth no-password preflight passed database contract, Odoo bootstrap, live secret inheritance, and TTY handling, then exposed an invalid dependency on the unset activation tenant parameter.
- Direct password maintenance now resolves exactly one external identity by the already unique `res.users` target record. It does not read or require activation runtime parameters, activation administrators, delivery channels, or the 62/76 roster; the failed preflight performed zero database writes.

### Activation-independent target-record binding

- Follow-up branch / anchor: `fix/password-reset-target-record-identity` from `993bc1f658c60d5683fb5803da6728e0408a9e11`.
- The seventh no-password preflight proved that the production registry does not expose the optional activation external-identity model. Direct password maintenance now binds the already unique active internal `res.users` target to a non-secret database/model/record digest and has no activation-model dependency.
- This matches the authorized stop conditions: missing, duplicate, inactive, or non-internal target users still fail closed; activation parameters, activation administrators, delivery channels, and 62/76 roster artifacts cannot block a direct ORM password reset. The failed preflight performed zero database writes.

### Post-write HTTP verification correction

- Branch / anchor: `fix/password-reset-http-verification` from `3f71c47f83012af5b50f2b76184b63477ecace8c`.
- The first operator-entered password reset committed the single authorized ORM password write, then the post-write menu probe incorrectly sent `op=get`; production `ui.contract` requires `op=menu` with `menu_id`. The resulting failure did not roll back the already committed password.
- The probe now uses the supported operation, post-commit failures explicitly report that the password write committed, and a governed `ops.user.password-verify` recovery entry accepts the already assigned password once through `getpass` and performs HTTP reads only. It does not repeat the password reset or write any production record.
## 2026-08-02 — WUTAO-ROLE-NAVIGATION-COMPOSITION-01

- Branch / anchor: `fix/wutao-role-navigation-composition` from `57e456c`.
- Formal Product Layer: P1 construction industry standard product; Layer
  Target: construction role-surface provider registration and formal capability
  composition; Module: `smart_construction_core`.
- Reason: the P0 provider selector received no construction provider, and the
  business configuration administrator surface did not compose the user's
  existing ACL-visible business capabilities into the frozen product policy.
- Standard vs User-Specific: construction-standard navigation behavior. No
  user ID, login, tenant data, customer preference, or production data is
  encoded.
- Why Here / Why Not Elsewhere: P1 owns the construction provider and role
  policy; existing P0 code already owns generic provider selection, product
  whitelist intersection, ACL enforcement, and route-authority projection.
  Frontend, P2, P3, and P4 are not navigation authority.
- Blast Radius: `business_config_admin` navigation projection only. User groups,
  roles, company scope, system-admin status, native menus, historical tables,
  business data, and frontend rendering remain unchanged. Validation proves a
  selected construction provider, formal-policy intersection, and no technical
  or historical acceptance exposure.
