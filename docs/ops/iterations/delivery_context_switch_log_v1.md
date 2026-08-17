# Delivery context switch log v1

This log records current product-repository implementation context only. Historical
customer delivery evidence belongs in private customer or payload repositories.

## 2026-08-04 — DAILY-DEV-ADDON-ROOT-AUDIT-COMPAT-01

- Branch / anchor: `fix/daily-dev-addon-root-audit` from merged `main` at `95313b73be47107e09daa955e5e9f12ba23d7622`.
- Formal Product Layer: P4 verification governance; Layer Target: daily-development formal-field boundary audit runtime-path compatibility.
- Reason: the daily Compose topology mounts platform/industry addons at `/mnt/source-addons` and the private customer module at `/mnt/customer-addons`, while the audit only recognized the retired single-root `/mnt/extra-addons` layout and therefore blocked the governed daily publication before its real-login probe.
- Standard vs User-Specific: generic verification infrastructure only; no customer data, business fields, module ownership, route, permission, interface, or application behavior changes.
- Why Here / Why Not Elsewhere: the audit owns discovery of its static source inputs and must support the canonical split source/customer Compose mounts; changing container mounts or copying a private customer addon into the public repository would violate the product boundary.
- Blast Radius: split core/custom audit-root resolution plus one static regression test; no database write, module upgrade, frontend behavior, deployment topology, or production mutation.
- Validation: unit regression, Python compile, local audit, generated-report refresh/guard, PR checks, and the daily-development `release.daily_dev.acceptance.publish` entrypoint.

## 2026-08-04 — FRONTEND-ACCESSIBLE-INTERACTIVE-TOKEN-07

- Branch / anchor: `feature/frontend-experience-upgrade` from `b18b71c31b2bac895ef63c65752e6fb6e3ac2f11`.
- Formal Product Layer: P0 platform product; Layer Target: shared light-theme semantic design-token accessibility.
- Reason: the experience branch mapped interactive surfaces and white button text to `cyan_500`, producing 2.3:1 contrast, while cyan link text on subtle backgrounds produced 4.07–4.29:1; the authoritative WCAG AA browser scan therefore found five serious blocking groups.
- Standard vs User-Specific: generic accessible presentation semantics only; no customer identity, business data, workflow, route, permission, interface, or runtime configuration changes.
- Why Here / Why Not Elsewhere: semantic tokens own cross-component foreground/background contrast. Component-specific overrides would duplicate color policy across login, buttons, navigation, forms, dialogs, and error states.
- Blast Radius: light-theme interactive, hover, link, and information semantic mappings reuse existing `blue_500/600` base tokens; spacing, typography, layout, dark theme, APIs, backend modules, and performance policy remain unchanged.
- Validation: token build/verify/tests, no-hardcoded-color guard, strict typecheck, production frontend build, WCAG browser scan with zero blocking findings, visual audits, and full-product browser coverage.

## 2026-08-04 — FRONTEND-PR-MAIN-SYNC-AUDIT-SELECTOR-06

- Branch / anchor: `feature/frontend-experience-upgrade` from `acfdf29154db0eda0ac51214300ca83b6fb5be1d` after synchronizing `origin/main`.
- Formal Product Layer: P4 verification governance; Layer Target: frontend release browser audit selector alignment.
- Reason: the enterprise form upgrade renamed the generic header overflow-action class from the model-prefixed `contract-header-more-actions` to `form-header-more-actions`, while two release-audit locators still referenced the retired selector and falsely reported that the visible “更多操作” control was missing.
- Standard vs User-Specific: generic verification wiring only; no customer data, product behavior, route, permission, interface, visual style, performance threshold, or business workflow changes.
- Why Here / Why Not Elsewhere: the browser audit owns DOM interaction selectors and must follow the already accepted generic component class; changing the product component or restoring a model-specific compatibility class would regress the shared semantic boundary.
- Blast Radius: two Playwright locators in the delivery-hardening audit and this audit record; no backend, database, runtime configuration, deployment, or production mutation.
- Validation: static selector search, strict typecheck, frontend release units/build, delivery-hardening production browser gate, full-product browser audit, generated-report guard, and exact-SHA GitHub checks.

## 2026-08-04 — FRONTEND-PR-RELEASE-GATE-CONVERGENCE-05

- Branch / anchor: `feature/frontend-experience-upgrade` from `0087d7b3e36c8dc7d7bed3ebdd25335473d33849`.
- Formal Product Layer: P0 platform product; Layer Target: shared frontend semantic boundaries and release-safe presentation selectors.
- Reason: the authoritative frontend release workflow detected industry literals in shared list/home rendering and model-prefixed CSS introduced by the experience-upgrade branch.
- Standard vs User-Specific: generic presentation semantics only. Runtime titles remain contract-provided, list priority uses field metadata, and renamed selectors express UI roles rather than a customer or construction model.
- Why Here / Why Not Elsewhere: shared renderers own generic field ranking and presentation classes; P1/P2 modules, runtime configuration, backend contracts, permissions, routes, and business data do not require changes.
- Blast Radius: one role-home label binding, generic list default-column ranking, and mechanical CSS selector renames across the existing form/home components; no visual behavior, API, workflow, database, deployment, or production mutation.
- Validation: shared-surface semantic boundary and delivery-hardening guards, strict TypeScript, release units, workspace alignment, production build, browser audits, and exact-SHA GitHub release checks.

## 2026-08-04 — FRONTEND-FULL-PRODUCT-AUDIT-04

- Branch / anchor: `feature/frontend-experience-upgrade` from `b7678cb0000944afd069017da618f79fa60adc76`.
- Formal Product Layer: P4 ops delivery tool; Layer Target: read-only full-product browser coverage and acceptance evidence.
- Reason: extend the contract-specific evidence with authoritative-navigation discovery, all-leaf desktop/mobile smoke coverage, and five-viewport representative business coverage before final PR review.
- Standard vs User-Specific: generic product verification only; no customer data, permission, route, interface, visual component, or business rule is changed.
- Why Here / Why Not Elsewhere: browser verification belongs in `scripts/verify`; it must observe P0/P1 runtime output without adding audit semantics to the frontend renderer, platform kernel, industry module, or runtime configuration.
- Blast Radius: one read-only browser auditor and local acceptance reports; no database write, external PUMA access, deployment, production mutation, or main-branch merge.
- Validation: 100% authorized menu-route coverage at 1440/390, 100% template coverage, 100% representative-module coverage at five viewports, zero P0/P1 issues, full frontend gates, production build, and browser report review.

## 2026-08-04 — FORM-BOSS-REFERENCE-CORRECTION-03

- Branch / anchor: `feature/frontend-experience-upgrade` from `cf4d412563e9b152ccdee3745bedf42201d506dd`.
- Formal Product Layer: P0 verification evidence; Layer Target: target-system provenance, privacy-safe screenshots, dimension mapping, and separated maturity conclusions.
- Reason: correct the prior audit's inaccurate classification of Weaver Jincenda as the BOSS target, then compare the accepted form system against the authenticated PUMA/BOSS361 contract workflow.
- Standard vs User-Specific: audit metadata and local acceptance evidence only; no customer-specific identity, record value, credential, cookie, route behavior, permission, or business rule is committed.
- Why Here / Why Not Elsewhere: the form-system audit owns reference provenance and comparison claims. The actual PUMA sample showed no regression requiring product code changes, so frontend components remain untouched.
- Blast Radius: one audit generator and acceptance artifacts; no application code change, database write, deployment, production mutation, or main-branch merge.
- Validation: authenticated target-system source hosts, BOSS/Weaver hash separation, eight complete comparison dimensions, privacy masking, UTF-8 delivery, full frontend gates, production build, and all browser audits.

## 2026-08-04 — FORM-SYSTEM-VISUAL-CONVERGENCE-02

- Branch / anchor: `feature/frontend-experience-upgrade` from `53507132fc7fe2eec95af8b91c3e9f1f499041df`.
- Formal Product Layer: P0 shared frontend renderer; Layer Target: mobile visibility, workflow/section discoverability, compact relationship selection, x2many action reachability, and trustworthy browser evidence.
- Reason: close independent visual-review findings that document-width checks missed, especially ancestor-clipped helper text, off-screen workflow stages, overlapping mobile section navigation, oversized relation results, and UTF-8 audit delivery.
- Standard vs User-Specific: generic responsive presentation and audit semantics only; no field values, permissions, routes, interfaces, or workflow rules change.
- Why Here / Why Not Elsewhere: shared form components own layout, focus, scroll discovery, and responsive degradation; the acceptance script owns element-level clipping, reachability, external-reference provenance, and UTF-8 round-trip evidence.
- Blast Radius: frontend presentation, local acceptance serving, and browser audit artifacts; no backend mutation, database migration, production deployment, or main-branch merge.
- Validation: five viewports, 95 real-browser assertions, explicit text-clipping and sticky-anchor checks, official external enterprise contract-product references, UTF-8 HTTP headers, all existing frontend gates, production build, and legacy visual audits.

## 2026-08-03 — FORM-SYSTEM-PROFESSIONALIZATION-01

- Branch / anchor: `feature/frontend-experience-upgrade` from `e5f0e03021b179e07c31c9e6a0e96f8dd9ad0309`.
- Formal Product Layer: P0 shared frontend renderer; Layer Target: generic record-form presentation, interaction states, and browser audit; Modules: `ContractFormPage`, native form canvas, reusable form fields, relation dialog, x2many renderer, and the form-system Playwright audit.
- Reason: extend the accepted readonly detail treatment into a complete, verifiable enterprise form lifecycle covering create, edit, validation, saving, failure, relationships, detail rows, collaboration, long-form navigation, and form design.
- Standard vs User-Specific: contract-driven generic presentation only; no construction/customer field names, permissions, route identities, record data, or model-specific workflow semantics are introduced.
- Why Here / Why Not Elsewhere: P0 owns rendering, responsive degradation, focus behavior, and reusable interaction feedback. P1 business modules, backend APIs, ACLs, and runtime configuration remain unchanged because the contract already exposes the required semantics.
- Blast Radius: frontend presentation and a read-only/mocked-write acceptance probe; no production deployment, database mutation, API change, route change, permission change, business workflow change, or main-branch merge.
- Validation: strict typecheck, style-token guard, release unit tests, workspace/content alignment guards, production frontend build, legacy visual/form audits, and a five-viewport form matrix with 70 assertions and zero errors.
## 2026-08-04 — FRONTEND-COMPANY-SWITCH-BASELINE-GOVERNANCE-01

- Branch / anchor: `fix/frontend-company-switch-performance-baseline` from `2eb4dfaf108d2b2c8ea181a86043dbd48cebcb6c` (`origin/main`).
- Formal Product Layer: P4 verification governance; Layer Target: frontend release performance capture and the governed mainline baseline asset.
- Reason: the baseline capture path returned before measuring `company_switch`, leaving the configured scenario absent and forcing otherwise valid relative performance evaluation to fail closed.
- Standard vs User-Specific: generic release evidence only; no customer data, product behavior, interface, route, permission, threshold, or regression tolerance changes.
- Why Here / Why Not Elsewhere: the browser performance harness owns sampling order and the release guard owns baseline completeness; frontend rendering and backend business modules do not own benchmark governance.
- Blast Radius: isolated `sc_frontend_acceptance` fixture, one capture-order correction, one baseline-integrity guard, and one full mainline baseline refresh; no UAT, production, customer tenant, external system, or PR #110 candidate measurement.
- Validation: five samples for every configured scenario, eight company-switch warm-ups, exact measured source SHA, captured environment metadata, release-unit/static guards, and the authoritative frontend release audit.

## 2026-08-02 — DAILY-DEV-MISSING-ADDONS-PATH-RUNTIME-01

- Branch / anchor: `fix/dev-missing-addons-path-runtime` from `968b942`.
- Formal Product Layer: P4 runtime configuration rendering; Layer Target:
  non-production Odoo addon-path admission; Module: `render_odoo_conf.py`.
- Reason: the daily source-mounted container declared three immutable-image
  addon roots that were absent in its older development image, causing Odoo to
  raise `FileNotFoundError` before every intent request, including login.
- Standard vs User-Specific: generic non-production runtime compatibility; no
  login, password, user identity, tenant data, or navigation policy is encoded.
- Why Here / Why Not Elsewhere: configuration rendering owns the effective
  runtime addon search path. Product modules, frontend code, ACLs, and database
  records cannot repair a missing container filesystem root.
- Blast Radius: only unavailable addon roots are omitted for explicit dev,
  daily, test, or UAT environments, and the repository `VERSION` authority is
  mounted read-only at the immutable image's standard path. Production
  rendering remains byte-for-byte unchanged and fails neither open nor over to
  source mounts.

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

## 2026-08-02 — FE-NAVIGATION-INITIALIZATION-RACE-01

- Branch / anchor: `fix/navigation-initialization-race` from `f191c34`.
- Formal Product Layer / Layer Target / Module: P0 platform kernel; frontend
  session/navigation state machine, product shell, and generic router guard.
- Reason: a menu click during `system.init` could combine menu, action, scene,
  and authority values from different navigation snapshots. The backend
  authority gate rejected the resulting route, but the frontend had already
  attempted an unrelated business navigation.
- Standard vs User-Specific: generic session and navigation consistency. No
  construction role, login, tenant, customer preference, database value, or
  business menu is encoded in the fix.
- Why Here / Why Not Elsewhere: P0 owns authentication-adjacent bootstrap,
  route authority, session invalidation, and atomic navigation publication.
  P1 navigation manifests and business permissions remain authoritative and
  unchanged; P2, P3, P4, database migrations, and backend ACLs are unaffected.
- Blast Radius: frontend-only fail-closed initialization and navigation. An
  authoritative bootstrap clears the prior menu/action/scene/activity snapshot;
  navigation becomes interactive only after `route_authority_v1` is ready; one
  click freezes and validates one immutable menu/action/scene/route/authority
  tuple. No user, role, company, password, module, schema, or business-data
  write is introduced.
- Validation: unit contract, release unit gate, ESLint, strict TypeScript, Vite
  development build, and browser fault injection covering delayed init, refresh,
  reload, failed init/retry, and role switching against `sc_demo`.

## 2026-08-03 — FRONTEND-EXPERIENCE-UPGRADE-01

- Branch / anchor: `feature/frontend-experience-upgrade` from `084e60d`.
- Formal Product Layer: P0 platform kernel product.
- Layer Target: generic frontend design system, application shell, list and
  record presentation.
- Module: `frontend/packages/design-tokens`, `frontend/apps/web`.
- Standard vs User-Specific: platform-wide visual and interaction mechanism;
  no construction-industry or tenant-specific semantics are introduced.
- Why Here / Why Not Elsewhere: the frontend renderer owns reusable visual
  density, navigation presentation, list scanning and form hierarchy. Backend
  contracts, P1 business defaults, P2 customer preferences, P3 runtime
  configuration and P4 delivery tooling remain authoritative and unchanged.
- Blast Radius: semantic tokens, application chrome and reusable list/form
  presentation only. Menu authority, routes, permissions, API payloads,
  business workflows and database records are outside scope.
- Validation: design-token generation, token verification and unit tests;
  frontend release unit suite; strict TypeScript; source ESLint; workspace
  alignment, list-scroll and form-canvas guards; and Vite development build
  to an isolated temporary output directory all pass. The aggregate style
  guard remains blocked by the pre-existing 1815-line `ContractFormPage.vue`
  limit violation, and the aggregate quick gate reaches a pre-existing Node
  24 CommonJS harness incompatibility in `frontend_page_identity_smoke.js`.

## 2026-08-03 — FRONTEND-EXPERIENCE-UPGRADE-ROUND-09

- Branch / anchor: `feature/frontend-experience-upgrade` from `2e61ade`.
- Formal Product Layer / Layer Target / Module: P0 platform product; generic
  frontend shell navigation and responsive layout; `frontend/apps/web`.
- Reason: the activity rail exposed a hard-coded configuration route based on a
  frontend administrator flag, bypassing the backend-published menu node and
  its frozen route-authority selection path. The related static guard also
  continued scanning the Vue SFC after layout CSS moved to `AppShell.css`.
- Standard vs User-Specific / Why Here: this is generic rendering and
  navigation behavior shared by all products. The frontend interprets only an
  explicit backend `sc_web_route`; it does not add construction or customer
  semantics.
- Why Not Elsewhere: backend menu, action, ACL, and route authority already own
  visibility and access. No P1 policy, P2 preference, P3 runtime configuration,
  P4 data repair, or database change is required.
- Blast Radius: AppShell configuration shortcut visibility and selection plus
  the corresponding static guard. All business routes continue through the
  existing immutable menu/action/authority snapshot; backend contracts and
  business data are unchanged.

## 2026-08-03 — FRONTEND-EXPERIENCE-UPGRADE-STAGE-01

- Branch / anchor: `feature/frontend-experience-upgrade` at `5b47663`.
- Formal Product Layer / Layer Target / Module: P0 platform product; generic
  navigation shell and governed list/form presentation; `frontend/apps/web`.
- Stage outcome: delivered a visually distinct dark enterprise navigation
  frame and a dense, continuous contract ledger surface with integrated query
  tools, table and pagination. The isolated acceptance fixture now includes
  deterministic `sc.general.contract` rows so the released menu, list and
  record-detail routes can be verified end to end without production data.
- Boundary: presentation tokens and acceptance-only synthetic fixture data;
  no customer policy, route authority, permission or production database
  semantics changed.
- Validation: acceptance login, released contract menu, populated list and
  record-detail journey pass at 1440x900; Python compilation and Vite build
  pass. Strict TypeScript remains blocked by pre-existing query typing errors
  in unmodified `AppShell.vue` and `ContractFormPage.vue`.

## 2026-08-03 — FRONTEND-EXPERIENCE-UPGRADE-BOSS-ALIGNMENT

- Branch / anchor: `feature/frontend-experience-upgrade` at `a87aea7`.
- Formal Product Layer / Layer Target / Module: P0 platform product; generic
  shell, list and form presentation; `frontend/apps/web`.
- Outcome: removed the unsupported dark-navigation direction and aligned the
  shell to the sampled BOSS visual system: one light 220px navigation column,
  light-gray workspace, white continuous business surfaces, blue local active
  states, compact query actions, dense ledger rows and low-decoration form
  sections.
- Boundary: generic presentation only. Published navigation, route authority,
  permissions and business semantics remain unchanged.
- Validation: isolated acceptance login, populated contract list, record
  detail journey and Vite build pass at 1440x900.

## 2026-08-03 — FRONTEND-EXPERIENCE-UPGRADE-GLOBAL-STAGE

- Branch / anchor: `feature/frontend-experience-upgrade` at `1070936`.
- Formal Product Layer / Layer Target / Module: P0 platform product; global
  application shell, role home, governed lists and contract forms.
- Outcome: completed the BOSS-aligned stage across the shared frontend system:
  single light navigation, compact role home, continuous dense ledgers,
  restrained form sections and responsive business-card presentation.
- Boundary: generic renderer and acceptance-only synthetic data. No customer
  policy, permission, route authority or production data was changed.
- Validation: real acceptance login/list/detail journeys pass at 1440x900,
  1280x800, 768x1024 and 390x844 with zero browser errors and zero document
  overflow. Strict TypeScript, ESLint, release units, style-system guard,
  standard-list scroll guard, workspace alignment, wide-form guard and Vite
  build pass.

## 2026-08-03 — FRONTEND-EXPERIENCE-UPGRADE-ACTIVITY-TABS

- Branch / anchor: `feature/frontend-experience-upgrade` at `c98aa84`.
- Formal Product Layer / Layer Target / Module: P0 platform product; global
  application-shell activity navigation; `frontend/apps/web`.
- Outcome: replaced browser-like bordered activity cards with a flat business
  tab bar. Inactive pages are neutral, the current page uses one blue bottom
  rule, and close actions appear only for hover, focus, or the active page.
- Boundary: generic navigation presentation only. Page lifecycle, route
  authority, permissions and business semantics remain unchanged.
- Validation: real acceptance login/list/detail journeys pass at 1440x900,
  768x1024 and 390x844 with zero browser errors and zero document overflow;
  mobile activity tabs remain hidden. ESLint, strict TypeScript, release units,
  style-system guard and Vite production build pass.

## 2026-08-03 — FRONTEND-EXPERIENCE-UPGRADE-MENU-STATE

- Branch / anchor: `feature/frontend-experience-upgrade` at `4fef3df`.
- Formal Product Layer / Layer Target / Module: P0 platform product; global
  navigation state and menu-tree presentation; `frontend/apps/web`.
- Outcome: aligned navigation with the BOSS-style business hierarchy. Route
  selection now expands every active ancestor and presents one visible active
  leaf; ancestors retain hierarchy without competing backgrounds. Menu-count
  badges were removed, indentation and arrows were tightened, shortcut entries
  became neutral rows, and the search label is visually hidden but accessible.
- Boundary: generic navigation rendering and state only. Backend menu authority,
  permissions, route contracts and business semantics remain unchanged.
- Validation: the real acceptance contract route resolves one visible active
  `一般合同（公司）` leaf beneath `合同中心 / 合同管理`, with zero count badges,
  browser errors or horizontal overflow. Mobile keeps navigation closed by
  default. ESLint, strict TypeScript, release units, style-system guard and Vite
  production build pass.

## 2026-08-03 — FRONTEND-EXPERIENCE-UPGRADE-SURFACE-RHYTHM

- Branch / anchor: `feature/frontend-experience-upgrade` at `2da04b7`.
- Formal Product Layer / Layer Target / Module: P0 platform product; shared
  business surfaces and action-toolbar presentation; `frontend/apps/web`.
- Outcome: removed the legacy three-pixel accent bands from list, form and role
  home surfaces so activity navigation and page content no longer compete for
  emphasis. List query controls now use one toolbar surface instead of nested
  borders; a single available view no longer renders a redundant view switch.
  Sidebar footer actions were reduced to the same neutral row language as the
  navigation.
- Boundary: generic presentation and conditional rendering only. Search,
  multi-view switching, route authority, permissions and business behavior are
  unchanged; multi-view pages retain their switcher.
- Validation: real home, contract list and contract detail journeys pass at
  1440x900, 768x1024 and 390x844. Query surfaces have no decorative top border,
  the single-list view has no redundant switch, and all sizes have zero browser
  errors or document overflow. ESLint, strict TypeScript, release units,
  style-system guard and Vite production build pass.

## 2026-08-03 — FRONTEND-EXPERIENCE-UPGRADE-BRANCH-ACCEPTANCE

- Branch / anchor: `feature/frontend-experience-upgrade` at `8ee7f78`.
- Formal Product Layer / Layer Target / Module: P0 platform product; completed
  frontend experience system across shell, navigation, list, record and role
  home surfaces; `frontend/apps/web`.
- Outcome: completed the branch-level BOSS-style alignment. The mobile contract
  workflow status is now one horizontally scrollable business-state row instead
  of wrapped button fragments, while desktop and tablet show the complete row.
  Mobile header actions stay compact and no longer stretch across the canvas.
- Boundary: generic responsive rendering only. Workflow states, action
  availability, permissions, menu authority and backend business behavior are
  unchanged.
- Validation: real login, role home, contract menu, populated list, internal
  table horizontal navigation, record detail, activity-tab switching and tab
  closing pass at 1440x900, 1280x800, 768x1024 and 390x844. The matrix reports
  zero browser errors and zero document overflow. ESLint, strict TypeScript,
  release units, style-system guard, standard-list scroll contract, workspace
  alignment, wide-form grid guard and Vite production build all pass.

## 2026-08-03 — FRONTEND-EXPERIENCE-UPGRADE-VISUAL-IDENTITY

- Branch / anchor: `feature/frontend-experience-upgrade` at `43fc97d`.
- Formal Product Layer / Layer Target / Module: P0 platform product; shared
  visual identity across shell, role home, navigation, list and contract form;
  `frontend/apps/web`.
- Outcome: responded to visual acceptance feedback with a deliberately visible
  identity pass rather than another structural refinement. The shell now has a
  236px branded navigation column and a distinct white application header;
  current navigation, table headers, role-home KPIs and contract section bands
  share one governed blue hierarchy. Query controls are tighter and flatter.
- Boundary: generic presentation only. Navigation authority, workflow states,
  permissions, data contracts and backend business behavior are unchanged.
- Validation: real home, list and detail journeys pass at 1440x900, 1280x800,
  768x1024 and 390x844 with zero browser errors and zero document overflow.
  ESLint, strict TypeScript, release units, style-system guard, standard-list
  scroll contract, workspace alignment and Vite production build pass.

## 2026-08-03 — FRONTEND-EXPERIENCE-UPGRADE-LIST-FIRST-SCREEN-BUDGET

- Branch / anchor: `feature/frontend-experience-upgrade` at `2e6b2b8`.
- Formal Product Layer / Layer Target / Module: P0 platform product; standard
  business ledger first-screen density; `frontend/apps/web`.
- Outcome: replaced the unbounded default ledger projection with a governed
  12-column first-screen budget. Identity, state, date, numeric and relational
  fields are prioritised before remaining model-order fields. All 33 available
  fields remain accessible through column configuration and saved user choices
  continue to override the default. The column configuration cell now uses the
  same sticky-edge treatment as governed table navigation.
- Boundary: default presentation only. Model fields, export data, filters,
  sorting, permissions, backend contracts and explicit user column preferences
  are unchanged.
- Validation: the populated contract ledger now renders 12 business columns by
  default instead of 33, reducing the measured table width from 5414px to
  2113px while retaining 33 configuration choices. Real home, list and detail
  journeys pass at 1440x900, 1280x800, 768x1024 and 390x844 with zero browser
  errors. Strict TypeScript, release units, style-system guard, standard-list
  scroll contract, workspace alignment and Vite production build pass.

## 2026-08-03 — FRONTEND-EXPERIENCE-UPGRADE-BOSS-CYAN-IDENTITY

- Branch / anchor: `feature/frontend-experience-upgrade` at `dbe6eae`.
- Formal Product Layer / Layer Target / Module: P0 platform product; shared
  visual identity, role home, application header and responsive surfaces;
  `frontend/packages/design-tokens` and `frontend/apps/web`.
- Outcome: corrected the remaining visual-identity mismatch by replacing the
  prior conventional blue accent with the BOSS-aligned cyan identity family
  anchored at `#00b6fe`. Interactive, hover, focus, link, navigation-active and
  informational states now derive from one governed cyan scale in both light
  and dark themes. The role home now has a visibly branded cyan identity band,
  governed KPI cards and stronger section rhythm; the application header uses
  the same cyan anchor line across home, list and record journeys.
- Boundary: design tokens and presentation only. Navigation authority,
  workflows, data contracts, permissions and backend behavior are unchanged.
- Validation: real role-home, populated contract ledger and contract detail
  journeys pass at 1440x900, 1280x800, 768x1024 and 390x844 with zero browser
  errors and zero document overflow. Design-token build/verification, strict
  TypeScript, release units, style-system guard, standard-list scroll contract,
  workspace alignment and Vite production build pass.

## 2026-08-03 — FRONTEND-EXPERIENCE-UPGRADE-LEDGER-COLUMN-DISCOVERY

- Branch / anchor: `feature/frontend-experience-upgrade` at `5b842aa`.
- Formal Product Layer / Layer Target / Module: P0 platform product; standard
  ledger first-screen controls and responsive column discovery;
  `frontend/apps/web/src/pages/ListPage.vue`.
- Outcome: moved column management out of the horizontally scrolled table edge
  into a permanent first-screen utility row. Users now see `12 / 33` column
  context and a visible column-settings action before scrolling; the settings
  menu retains all 33 fields while the governed 12-column default remains.
  Desktop table width falls from 2113px to 2033px by removing the obsolete
  trailing management cell. The same control remains discoverable above mobile
  record cards.
- Boundary: list presentation and column-discovery placement only. Field
  availability, saved preferences, sorting, filtering, export and backend
  contracts are unchanged.
- Validation: populated desktop and mobile ledgers show the settings entry on
  first render; the settings menu opens with 33 visible choices, 12 selected,
  zero document overflow and zero browser errors. Strict TypeScript, release
  units, style-system guard, standard-list scroll contract, workspace alignment
  and Vite production build pass.

## 2026-08-03 — FRONTEND-EXPERIENCE-UPGRADE-READONLY-FORM-HIERARCHY

- Branch / anchor: `feature/frontend-experience-upgrade` at `932834b`.
- Formal Product Layer / Layer Target / Module: P0 platform product; shared form
  information hierarchy and responsive record presentation;
  `frontend/apps/web/src/components/template/FormSection.vue`.
- Outcome: removed repeated per-field readonly pills when an entire form group
  is readonly, allowing section titles, field labels and values to carry the
  hierarchy without status noise. Readonly values now use a denser 28px rhythm,
  stronger primary text and reduced row gaps. Mixed edit groups still retain
  readonly markers on individually locked fields.
- Boundary: form presentation only. Field mutability, validation, permissions,
  workflow state and persistence behavior are unchanged.
- Validation: populated contract detail journeys pass at 1440x900, 1280x800,
  768x1024 and 390x844 with zero browser errors and zero document overflow.
  Desktop and mobile screenshots show zero repeated readonly pills while the
  grouped record structure remains intact. Strict TypeScript, release units,
  style-system guard, workspace alignment and Vite production build pass.

## 2026-08-03 — FRONTEND-EXPERIENCE-UPGRADE-FORM-ACTION-STATUS-SPLIT

- Branch / anchor: `feature/frontend-experience-upgrade` at `98e1ae7`.
- Formal Product Layer / Layer Target / Module: P0 platform product; record
  action toolbar and workflow-status presentation;
  `frontend/apps/web/src/pages/contractForm`.
- Outcome: separated page navigation from workflow state in the record header.
  Desktop now anchors the back action on the left and keeps mode plus workflow
  status on the right, eliminating the former empty-left/right-only composition.
  Mobile intentionally keeps the horizontally scrollable status row first and
  places the back action beneath it. The action wrapper is now a neutral toolbar
  rather than a nested bordered capsule.
- Boundary: header order and presentation only. Back navigation, workflow
  state transitions, action availability and permissions are unchanged.
- Validation: real desktop geometry places the back action at x=251 and the
  status row at x=967; mobile places the back action below the status row. Both
  viewports report zero document overflow and zero browser errors. Strict
  TypeScript, release units, style-system guard, workspace alignment and Vite
  production build pass.

## 2026-08-03 — FRONTEND-EXPERIENCE-UPGRADE-NAVIGATION-BRAND-CONTEXT

- Branch / anchor: `feature/frontend-experience-upgrade` at `13af40e`.
- Formal Product Layer / Layer Target / Module: P0 platform product; navigation
  product identity and business-context presentation;
  `frontend/apps/web/src/layouts/AppShell.vue`.
- Outcome: removed raw account and fixture names from the permanent product
  brand area. The sidebar subtitle now presents governed business context as
  `company · role`, producing `FE Company A · 项目成员` in the acceptance
  journey. The actual account name remains available inside the account/role
  panel for traceability without visually contaminating product identity.
- Boundary: shell identity presentation only. Session identity, company scope,
  role authority, audit context and permissions are unchanged.
- Validation: real home, ledger and record screenshots show business context in
  the sidebar with no fixture account label. All four viewport journeys report
  zero browser errors and zero document overflow. Strict TypeScript, release
  units, style-system guard, workspace alignment and Vite production build pass.

## 2026-08-03 — FRONTEND-EXPERIENCE-UPGRADE-LAYERED-WORKSPACE

- Branch / anchor: `feature/frontend-experience-upgrade` at `c14aa65`.
- Formal Product Layer / Layer Target / Module: P0 platform product; shell,
  navigation, ledger and record workspace visual hierarchy;
  `frontend/apps/web/src/layouts`, `components/product-list`,
  `components/template`, `pages/ListPage` and `pages/contractForm`.
- Outcome: replaced the edge-to-edge flat canvas with a visibly layered light
  workspace. Restored the left activity rail, retained a light navigation
  panel, introduced separated query/data/record surfaces, stronger active-tab
  identity and governed semantic shadows. Removed the redundant search wrapper
  border, tightened content-sampled column widths by business field role, and
  surfaced the shared icon system on column configuration.
- Responsive outcome: desktop uses activity rail plus navigation panel;
  tablet and mobile retain the drawer model and compact record cards. Record
  sections become single-column business cards without document overflow.
- Boundary: presentation and default width derivation only. User-resized width
  persistence, column visibility, search semantics, workflow state, permission
  checks and record data are unchanged.
- Validation: real desktop, compact, tablet and mobile home/list/detail journeys
  report zero browser errors and zero document overflow. Strict TypeScript,
  style-system guard, release units, workspace alignment and Vite production
  build pass.

## 2026-08-03 — FRONTEND-EXPERIENCE-UPGRADE-ICON-SEMANTICS

- Branch / anchor: `feature/frontend-experience-upgrade` at `91c1d1b`.
- Outcome: expanded the governed `ScIcon` vocabulary and applied it to home,
  work, menu search, menu disclosure, ledger search, record creation and column
  configuration. Text labels remain present, while icon size, spacing and state
  rotation are normalized for faster recognition and accessibility.
- Boundary: visual semantics only. Navigation routes, search behavior, create
  authorization and menu expansion persistence are unchanged.
- Validation: real four-viewport browser journeys report zero errors and zero
  document overflow. Strict TypeScript and style-system guards pass.

## 2026-08-03 — FRONTEND-EXPERIENCE-UPGRADE-MOBILE-WORKFLOW-GRID

- Branch / anchor: `feature/frontend-experience-upgrade` at `ba25e2d`.
- Outcome: replaced the clipped horizontal mobile workflow strip with a complete
  three-column, two-row status grid. All six workflow states remain visible,
  with active and completed semantics preserved and the back action positioned
  beneath the grid.
- Boundary: layout only. Workflow ordering, transition availability and record
  state are unchanged.
- Validation: mobile geometry reports a 313px grid with three approximately
  100px columns and all six states contained within x=31..344; document overflow
  and browser errors remain zero.

## 2026-08-03 — FRONTEND-EXPERIENCE-UPGRADE-ENTERPRISE-RESPONSIVE-POLISH

- Branch / anchor: `feature/frontend-experience-upgrade` at `5e05545`.
- Formal Product Layer / Layer Target / Module: P0 platform product; shared
  shell, role-home, list and record presentation;
  `frontend/apps/web/src/components`, `layouts` and `pages`.
- Outcome: aligned the light shell, role home, navigation utilities, responsive
  ledger and record canvas into one restrained enterprise hierarchy. The ledger
  now ranks primary business fields and packs them using the container's actual
  pixel budget, distributes readable widths without right-edge clipping, and
  switches narrow tablet and mobile surfaces to complete record cards. Mobile
  cards omit desktop column-count language while retaining column settings and
  present registration number, contract number and name, state, date, amount
  and related project. The record view removes the intermediate tinted sheet,
  keeps one continuous document surface and uses separated section headings.
  Header, role, notification, panel and theme tools use the governed `ScIcon`
  vocabulary; the light navigation rail and leftmost application shortcut are
  retained.
- Boundary: responsive presentation, visual hierarchy, default first-screen
  field selection and icon semantics only. User data, backend contracts,
  permissions, workflow transitions, search, sorting and persisted column
  configuration remain unchanged.
- Validation: real 1440px desktop, 768px tablet and 390px mobile home/list/detail
  journeys report zero browser errors and zero document overflow. Desktop table
  headings, amounts and rightmost related-project values remain fully visible;
  tablet cards form a two-column ledger and mobile cards form a single-column
  ledger. Strict TypeScript, release units, style-system guard, workspace
  alignment, production build and both browser audits pass.

## 2026-08-03 — FRONTEND-EXPERIENCE-UPGRADE-MATURITY-CONVERGENCE

- Branch / anchor: `feature/frontend-experience-upgrade` at `8e5f880`.
- Formal Product Layer / Layer Target / Module: P0 platform product; responsive
  shell density, list query/pagination presentation, role-home balance and
  record document continuity; `frontend/apps/web/src/components`, `layouts`
  and `pages/contractForm`.
- Outcome: compressed the mobile shell from three visual rows to at most two,
  replacing message, work and navigation text controls with accessible
  `ScIcon` tools. Removed the standalone mobile query-card treatment and joined
  search and list controls into a lighter continuous workspace. Narrow tablet
  pagination now forms a compact control cluster instead of distributing every
  item across the full row. Record sections no longer render nested cards;
  headings, dividers and spacing carry hierarchy inside one document canvas.
  The role home uses a shorter, less saturated banner, content-height empty
  tasks and two lightweight status metrics, eliminating the previous visual
  imbalance.
- Boundary: presentation and responsive density only. Business data, API
  contracts, workflow, permissions, navigation targets, list field selection
  and column-width behavior are unchanged.
- Validation: Playwright journeys at 1440px, 768px and 390px show the mobile
  business surface entering roughly 50px earlier, complete list actions, a
  single record canvas and compact tablet pagination. Strict TypeScript,
  release units, style-system guard with zero hardcoded colors, workspace
  alignment, production build and both browser audits pass with zero errors
  and zero document overflow.

## 2026-08-04 — LONG-RUNNING-AGENT-CONTROL-MVP

- Branch / anchor: `feature/long-running-agent-control` at `40243b1`.
- Formal Product Layer / Layer Target / Module: P4 operations delivery tool;
  local autonomous task control, GitHub Issue command polling, Codex checkpoint
  execution and Feishu notification; `scripts/ops`, `deploy/agent-controller`
  and `make/codex.mk`.
- Reason / Why Here: long-running engineering coordination is an operations
  concern and must reuse repository execution policy without entering platform,
  construction-industry, customer, low-code or frontend product layers.
- Why Not Elsewhere: no business semantics, runtime UI contracts or customer
  preferences are introduced. GitHub remains the audited control plane and
  Feishu remains notification-only.
- Blast Radius: one explicitly configured local checkout, one trusted GitHub
  sender, one control Issue, one worker lease and one Feishu custom bot. There
  is no production command and daily deployment requires an exact full SHA.
- Validation: Python unit tests cover strict command parsing, Feishu signing,
  UTF-8 notification payloads, state round trips, GitHub GET-only polling and
  closed structured output. The service unit and installer receive shell and
  policy guards before local enablement.

## 2026-08-04 — LONG-RUNNING-AGENT-SYSTEMD-RUNTIME-RECOVERY

- Branch / anchor: `fix/agent-controller-systemd-node-path` at `12c95a4`.
- Formal Product Layer / Layer Target / Module: P4 operations delivery tool;
  deterministic systemd worker runtime and bounded startup recovery;
  `scripts/ops/codex_agent_controller.py` and its unit tests.
- Outcome: prepend the configured Codex and GitHub CLI runtime directories to
  the child PATH without resolving away the configured executable symlink, so
  an NVM-installed Codex can resolve its adjacent `node` under systemd. A task
  that fails before obtaining a session id receives one bounded restart recovery
  attempt per controller recovery generation; an explicit trusted
  `/agent continue` can also relaunch that pre-session task. Codex CLI 0.146
  approval behavior is supplied through strict recognized configuration rather
  than the removed `--ask-for-approval` argument. The user service permits
  `AF_NETLINK` and PTY devices required by Codex's own bubblewrap sandbox while
  retaining `ProtectSystem=strict`, explicit writable paths and the Codex
  `workspace-write` boundary.
- Boundary: local development controller only. No product, database, GitHub
  authorization, deployment, production or notification-channel semantics
  change.
- Validation: unit coverage proves deterministic PATH construction, secret
  stripping and exactly-once pre-session recovery; the live failed task is
  resumed only after the patched service is reinstalled.

## 2026-08-04 — FEISHU-DIRECT-AGENT-CONTROL

- Branch / anchor: `feature/feishu-direct-agent-control` at `c42eb16`.
- Formal Product Layer / Layer Target / Module: P4 operations delivery tool;
  trusted Feishu app-bot command ingress and GitHub audit bridging;
  `scripts/ops`, `deploy/agent-controller` and `make/codex.mk`.
- Outcome: receive direct app-bot text through the official WebSocket SDK,
  require an exact local user/chat binding, deduplicate message ids, translate
  a small Chinese command vocabulary and submit the equivalent strict `/agent`
  command through a governed Make target to the existing control Issue.
- Boundary: no chat text is evaluated as shell, unbound users and chats are
  rejected, secrets are stripped from child processes, production remains
  unsupported and daily deployment still requires a full SHA.
- Validation: translation, mention normalization, decision ids, full-SHA
  deployment and fail-closed command validation are covered by unit tests;
  live acceptance uses the already published Feishu enterprise app.

## 2026-08-04 — LONG-RUNNING-AGENT-OBSERVABILITY

- Branch / anchor: `codex/long-running-workspace` at `c7b29e7`.
- Formal Product Layer / Layer Target / Module: P4 operations delivery tool;
  local worker progress observation and Feishu status delivery; `scripts/ops`,
  `deploy/agent-controller`, `make/codex.mk` and paired operations docs.
- Reason / Why Here: a background worker must expose a consistent local and
  mobile-readable execution state without changing task authority or product
  behavior. One read-only progress parser now owns event counts, elapsed time,
  recent activity, recoverable failures and the latest safe stage summary.
- Why Not Elsewhere: this is not a platform, construction product, customer,
  low-code, frontend or database concern. Read-only `状态` and `进度` queries bypass
  GitHub latency, while every state-changing command remains GitHub-audited.
- Blast Radius: the configured local controller, its bound Feishu conversation
  and the `sce-agent-watch` terminal command. Heartbeats start after two minutes,
  repeat every five minutes and warn after ten minutes without an event; no raw
  command output, credential, production action or business-data write is added.
- Validation: shared snapshot tests cover direct Feishu replies without GitHub
  mutation and initial heartbeat emission; controller/bridge compilation, unit
  tests, installer shell checks and systemd unit verification run through
  `make verify.codex.agent_controller`.
## 2026-08-05 — ISOLATED-ACCEPTANCE-GATE-PORTABILITY

- Branch / starting anchor: `codex/long-running-business-iteration` at `c924d9f`.
- Formal Product Layer / Layer Target / Module: P4 operations delivery tool;
  isolated acceptance profile parsing and source-ownership guards;
  `scripts/verify` and its verification documentation.
- Outcome: restricted validation now accepts explicit isolated company profiles
  without changing baseline thresholds or product data, removes profile secrets
  from child environments and reports, and checks capability delivery tokens at
  their post-split implementation owner. Targeted tests and independent A/B
  review pass; the final restricted gate passes against the isolated acceptance
  database with company evidence for IDs 2 and 3.
- Boundary: no frontend, addon runtime, contract/schema, permission, fixture,
  business-data, deployment or merge change.
# 2026-08-05 — Custom frontend professional product convergence

- Branch: `codex/long-running-business-iteration`
- Starting product commit: `2ae5dd9ff99f54db66e80bf1e9855a3d59ee090e`
- Formal Product Layer: P0 platform kernel product
- Layer Target: generic frontend renderer, AppShell geometry, design-system interaction, and acceptance tooling
- Module: `frontend/apps/web` and read-only browser acceptance scripts under `scripts/verify`
- Reason: converge shared enterprise pages on one viewport-aware geometry, scroll, responsive, focus, and feedback contract without changing business semantics
- Standard vs User-Specific: platform-wide rendering and interaction mechanism; no construction-specific or customer-specific rules
- Why Here / Why Not Elsewhere: geometry, accessibility, generic native-view presentation, and runtime-discovered browser verification belong to the shared frontend; P1/P2/P3/P4 must not carry renderer fixes or database-ID exceptions
- Blast Radius: AppShell, role home, generic list/form/dialog/relation/x2many/designer/config surfaces and acceptance evidence; excludes permissions, API semantics, business data, production, and main-branch integration
- Validation: strict typecheck, unit and design guards, production build, runtime-discovered five-viewport geometry/form/full-route audits, visual screenshots, daily-development re-verification, and `git diff --check`

## 2026-08-06 — FRONTEND-FORM-AUDIT-RUNTIME-EDITABILITY-RF1

- Branch / anchor: `codex/form-audit-runtime-editability` from `a2848368730a2c283f276d875d4c18b84caa2855`.
- Formal Product Layer / Layer Target / Module: P4 operations delivery tool; runtime form editability and save-action verification; `scripts/verify`.
- Outcome: replace the first-twelve-record UI scan with action-contract-driven candidate discovery and form-contract `pageAuth=edit` proof, accept the authoritative runtime save label, and use rendered form semantics instead of global network idleness.
- Boundary: no frontend product behavior, permission, workflow, API, contract/schema, route authority, module, or business-data change. Daily verification is read-only and does not click save.
- Validation: negative fixture and acceptance environment guard PASS; daily browser discovery finds 30 enabled controls and “保存修改” with zero console errors; frontend lint/typecheck/build PASS. Restricted remains blocked by the isolated secondary-company snapshot (1/2 profiles), while the full form audit truthfully retains 11 product visual/state failures for the next P0 batch.

## 2026-08-06 — FORMAL-ACTION-RUNTIME-DRIFT-ROOTFIX

- Branch / anchor: `fix/daily-formal-action-runtime-drift` from `4420ca4`.
- Formal Product Layer / Layer Target / Module: P1 construction industry standard
  product; L2 native action and list-view release definitions;
  `smart_construction_core`. The controlled daily upgrade and verification are
  P4 delivery operations only.
- Reason / Why Here: seven formal actions were either overwritten by later XML,
  bound to incomplete columns, filtered with a field absent from their model, or
  checked against fixture presence instead of their historical source facts.
  The industry module owns the reproducible action/view defaults and the runtime
  audit owns source-to-projection validation.
- Why Not Elsewhere: no frontend workaround, low-code override, customer module,
  permission change, or business-record repair can make these P1 definitions
  correct for a fresh install and a repeatable module upgrade.
- Blast Radius: the construction-contract, engineering-progress receipt,
  input-tax report, material inbound/rental acceptance, and tender-guarantee
  formal list actions. Login, `system.init`, `ui.contract`, public routes,
  workflow semantics, ACLs, and customer data remain unchanged.
- Upgrade / rollback: upgrade `smart_construction_core` from `17.0.0.77` to
  `17.0.0.78` through the governed `make mod.upgrade` target. Roll back the
  source commit and run the same module upgrade; no schema or data migration is
  introduced.

## 2026-08-06 — DAILY-RUNTIME-EXACT-BUNDLE-SYNC

- Branch / anchor: `fix/daily-runtime-bundle-sync` from `2a6759f`.
- Formal Product Layer / Layer Target / Module: P4 operations delivery tool;
  exact daily-development runtime repository synchronization;
  `scripts/ops` and `make/codex.mk`.
- Reason / Why Here: the daily server can reach ordinary GitHub HTTP but its Git
  smart-HTTP transfer repeatedly times out. A governed incremental bundle keeps
  iteration independent of that external transport without weakening source
  identity or repository isolation.
- Why Not Elsewhere: this is not product, frontend, module, database, tenant,
  low-code, or production behavior. It must not be implemented as ad hoc server
  edits, a Git configuration override, or a database patch.
- Blast Radius: one configured SSH host and the fixed clean runtime repository
  `/opt/projects/repos/sce-product-odoo`. Exact local/remote SHAs, bundle digest,
  upstream identity, ancestry, clean worktrees, and post-sync equality are all
  fail-closed; only a fast-forward of `main` is possible.
- Validation / rollback: unit tests execute the embedded remote program against
  temporary repositories and prove main/upstream alignment. A failed preflight
  performs no repository update; the previous commit remains an ancestor for an
  explicitly governed rollback task.

## 2026-08-06 — FORMAL-CONTRACT-VIEW-FIELD-CONTRACT-ROOTFIX

- Branch / anchor: `fix/daily-runtime-deploy-a514e0c` from `a514e0c`.
- Formal Product Layer / Layer Target / Module: P1 construction industry
  standard product; native formal list field and ordering contract;
  `smart_construction_core`.
- Root cause: the previous action-drift repair referenced two aliases that the
  governed field-architecture cleanup had removed, and retained a legacy sort
  field absent from `construction.contract.income`. Odoo rejected the view and
  rolled the daily upgrade back.
- Resolution: expose the single governed `name` identifier once as `单据编号`,
  use `date_contract desc, id desc`, remove the stale legacy-number test
  contract, add negative source regression, and advance the module to
  `17.0.0.81`.
- Post-deploy root extension: the formal-action gate found three material
  actions filtering an invented generic source identity while all 13,387
  projected rows carried their real customer lineage. The P1 actions now use
  the generic `legacy_acceptance_label` semantic field; the gate locks both the
  domain and action-to-projection count without importing a private carrier.
- Full-surface closure: label the engineering-progress receipt relationship as
  `施工管理合同` instead of the ambiguous `合同编号`, matching the locked runtime
  audit without changing the underlying relationship field or data.
- Boundary: no frontend, API, ACL, workflow, route, customer override, database
  patch, or business-record repair. Daily application remains a P4 governed
  upgrade protected by the paired backup and successful isolated restore drill.

## 2026-08-06 — FORMAL-ENTRY-METADATA-ORPHAN-HANDOFF-ROOTFIX

- Branch / anchor: `codex/daily-runtime-sync-6387` from `6387c30`.
- Formal Product Layer / Layer Target / Module: P1 construction industry
  standard product; L2 native model/view contract plus versioned upgrade
  migration; `smart_construction_core` and its formal-surface verification.
- Reason / Why Here: five supported business models lacked a truthful visible
  entry-source pair, while three active menus targeted customer-handoff models
  absent from the runtime registry. The industry module owns reproducible native
  views and fail-closed menu usability; the migration owns a precise,
  replay-safe UI metadata retirement.
- Why Not Elsewhere: no frontend fallback, low-code override, customer-module
  reconstruction, audit exclusion, `create_uid/create_date` substitution, or
  business-data repair can correct this product/runtime split.
- Blast Radius: five formal metadata surfaces and the menu/action/view/XMLID
  records for exactly three orphan models. Six legacy summary/fact relations,
  attachments, permissions, public contracts, workflow, and production remain
  untouched.
- Validation / rollback: real `.81 -> .82` isolated upgrade and repeated
  migration, Odoo TransactionCase negative fixtures, formal P1 gates and exact
  count assertions. Daily application remains protected by the verified paired
  backup and exact bundle synchronization; rollback restores the paired backup
  and preceding exact source SHA rather than attempting a module downgrade.
## 2026-08-06 — FRONTEND-RUNTIME-VIEW-CONTRACT-PRODUCT-CLOSURE

- Branch / anchor: `fix/runtime-view-contract-product-closure` from `6250dc6`.
- Formal Product Layer / Layer Target / Module: P0 generic contract assembly and
  frontend renderer plus P1 construction standard list defaults;
  `smart_core`, `smart_construction_core`, `frontend/apps/web` and design tokens.
- Reason / Why Here: native optional-column semantics, action-specific labels,
  cross-device critical columns and compact list surfaces must stay consistent
  across Windows and Harmony clients without frontend model-name branches.
- Why Not Elsewhere: customer preferences remain in governed runtime preference
  storage; migrations only retire stale configuration metadata. No permission,
  route, workflow or business-record semantics are changed to mask UI defects.
- Blast Radius / validation: dynamic list/form headers, project and partner list
  contracts, responsive list selection, Shell spacing and semantic color tokens.
  Strict typecheck, release unit, style guard, production build, isolated module
  upgrade, multi-viewport browser evidence and independent QA are required before
  daily-development deployment.

## 2026-08-06 — GOVERNED-WORKTREE-CREATE-ENTRY

- Branch / anchor: `fix/worktree-create-governance` from `6250dc6`.
- Formal Product Layer / Layer Target / Module: P4 operations delivery tool;
  local parallel-workspace lifecycle governance; `scripts/ops`,
  `make/codex.mk`, and Codex execution policy.
- Reason / Why Here: the policy correctly prohibited ungoverned `git worktree`
  mutation but exposed only a cleanup target, leaving no compliant creation
  path for isolated parallel tasks. The new Make entry keeps raw Git mutation
  prohibited while validating an exact reachable base, eligible new branch,
  controlled sibling path, nonexistence, explicit apply confirmation, and the
  created worktree's branch, HEAD, and cleanliness.
- Why Not Elsewhere: this is not a product, frontend, database, permission,
  menu, or deployment concern. It must not be implemented as an agent-specific
  shell exception or by weakening the raw Git command ban.
- Blast Radius / validation: local linked worktree creation only; no remote,
  database, service, or product state changes. Fourteen isolated create and
  cleanup tests cover successful creation plus confirmation, path, branch,
  commit identity, reachability, dirty, unmerged, and primary-worktree denials.
## 2026-08-06 — FRONTEND-ACCEPTANCE-ENVIRONMENT-PORTABILITY

- Branch / anchor: `feature/frontend-acceptance-environment-portability` from
  `b7bb5565c82d784ac96c5f64f54a7e36106ead6a`.
- Formal Product Layer / Layer Target / Module: P4 operations delivery tool;
  frontend acceptance environment policy, target safety, process lifecycle and
  evidence isolation; `config/frontend`, `scripts/verify`, release probe and
  Make verification entrypoints.
- Reason / Why Here: browser and release audits had divergent URL, database,
  credential, artifact, browser and lifecycle assumptions. P4 owns execution
  safety and portable evidence; the frontend renderer and construction modules
  do not own runner or deployment topology.
- Why Not Elsewhere: no business permission, route, API, field, customer
  preference or database record changes are needed. Environment differences
  must not be encoded as UI branches or customer-module overrides.
- Blast Radius: the versioned acceptance profiles and tool matrix, canonical
  resolver and cross-worktree lease, daily release identity probe, report
  server, and the full-product/form/geometry formal audit entrypoints. The
  remaining historical browser scripts are deliberately outside this batch.
- Validation / rollback: fail-closed tests cover alias conflicts, unsafe target
  management, daily/production write denial, weak credentials, identity drift,
  path escape and numeric routes before network launch; concurrency tests cover
  shared reads, exclusive writes, independent artifacts, dynamic ports and
  owned-process cleanup. Generated-report consistency passes. The optional
  documentation link check still reports the repository's existing 69 legacy
  absolute-path references; neither document changed in this batch contributes
  a missing link. Reverting this commit restores the previous tools and does
  not change any runtime or database state.

## 2026-08-06 — FRONTEND-RUNTIME-LABEL-AND-GEOMETRY-CLOSURE

- Branch / anchor: `fix/runtime-view-contract-product-closure` from `74a6766`.
- Formal Product Layer / Layer Target / Module: P0 native view contract assembly,
  responsive list rendering and P4 acceptance assertions; `smart_core`,
  `smart_construction_core`, `frontend/apps/web` and `scripts/verify`.
- Reason / Why Here: isolated browser evidence found native Chinese tree labels
  being replaced by generic English field metadata and business amounts/names
  clipping at 1280px and browser zoom. Native view strings now remain the
  display authority, critical contract columns participate in the same
  cross-device policy, and semantic width floors force secondary columns out
  before key facts are truncated.
- Why Not Elsewhere: no customer configuration, user preference, permission,
  route, workflow or business record is changed to hide the defect. Runtime
  action/menu identifiers are discovered from authenticated navigation instead
  of copied from one database.
- Blast Radius / validation: customer, supplier, project and contract list
  labels, column choice/default semantics and geometry audit thresholds. The
  isolated acceptance database is upgraded/restarted and tested at five
  viewports plus zoom before any daily-development deployment.

## 2026-08-07 — DAILY-CANDIDATE-BEFORE-MAIN-ACCEPTANCE-FLOW

- Branch / anchor: `feature/daily-candidate-acceptance-flow` from
  `e081c5494e95cfdf33ab0f34548e11f810ab51b1` (`origin/main`).
- Formal Product Layer / Layer Target / Module: P4 operations delivery tool;
  daily-development candidate source identity, exact Git bundle transport,
  runtime repository guard, controller command grammar and release runbooks.
- Reason / Why Here: daily development is the owner's acceptance environment,
  so a clean locally validated governed branch must be deployable at an exact
  SHA before the PR merges. Requiring `main` first inverted acceptance and
  integration order.
- Why Not Elsewhere: no platform, construction, customer, low-code, permission,
  route, API or business-data semantics change. Production remains restricted
  to `main` or a frozen release package.
- Blast Radius / validation: only `/opt/projects/repos/sce-product-odoo` in
  `ENV=dev`, `.env.dev`, `DB_NAME=sc_demo`. Candidate transport leaves
  `main`/`origin/main` untouched, records a `refs/daily-candidates/*` evidence
  ref and runs detached at the exact SHA. Unit and negative tests cover source
  branch syntax, full SHA identity, clean worktrees, bundle digest/base,
  detached runtime identity and missing/mismatched evidence refs.
- Documentation link check: the repository-wide guard still reports the 69
  pre-existing legacy absolute-path references; none originate from the files
  changed by this batch.

## 2026-08-07 — PRODUCT-MENU-GOVERNANCE-CURRENT-MAIN-CANDIDATE

- Branch / anchor: `feature/product-menu-governance-current` from
  `de8bbcaeb382147e7224d1df0db5addbb073d14a` (`origin/main`).
- Formal Product Layer / Layer Target / Module: P1 construction product menu
  defaults plus P4 deterministic governance evidence;
  `smart_construction_core`, `scripts/verify`, and
  `docs/engineering_convergence/menu_governance`.
- Reason / Why Here: the completed menu-governance branch was based on
  `6250dc64` and conflicted with the accepted frontend and daily-candidate
  infrastructure already in main. This candidate reapplies only the reviewed
  menu declaration changes and their evidence to current main without merging,
  rebasing, or deploying the stale branch tree.
- Why Not Elsewhere: no P0 frontend/model/action/role special case and no P2/P3
  customer preference or runtime menu mutation is introduced. Existing XMLIDs,
  actions, groups, names, sequences, and role/company visibility remain the
  compatibility boundary.
- Blast Radius / validation: `smart_construction_core` menu XML and module
  version, source-revision acceptance plumbing, deterministic menu inventory,
  runtime/browser audit tooling, and generated engineering reports. Local
  static/unit/build gates and a fresh isolated module/browser acceptance run
  must pass before exact-SHA daily deployment.

## 2026-08-07 — MENU-AND-COLLECTION-RUNTIME-CONVERGENCE

- Branch / anchor: `feature/menu-collection-convergence` from the exact daily
  menu candidate `0193b5b23f799bdb8475f94fdd21daf12ad49199`.
- Formal Product Layer / Layer Target / Module: P0 generic collection contract,
  dispatcher and renderer semantics; P1 project table/card/workflow bindings;
  P4 deterministic menu and browser acceptance evidence.
- Reason / Why Here: a full module upgrade for the menu candidate reloaded
  action/view metadata and exposed an existing divergence between requested
  view mode, user column preferences and responsive presentation. Windows and
  Harmony must resolve the same action facts while retaining intentional table,
  explicit card and grouped workflow semantics.
- Why Not Elsewhere: the frontend contains no device, model, action or role
  special case. Project-specific view declarations remain in the P1 product
  module; generic selection, route continuity and fail-safe semantics remain in
  P0 platform code.
- Blast Radius / validation: `smart_core`, project collection views, generic SPA
  action navigation and collection rendering, plus focused unit/guard/browser
  audits. Daily acceptance must bind the combined exact SHA and prove Windows
  table, Harmony responsive cards, explicit cards and grouped workflow all
  preserve the same record set without technical-field leakage or overflow.

## 2026-08-08 — FRONTEND-PRODUCT-STABLE-BASELINE-FINAL-CLOSURE

- Branch / anchor: `feature/frontend-product-stable-baseline` from
  `901e97af54e3bc288a008cfb183485fd55aa0d65`.
- Formal Product Layer / Layer Target / Module: P0 platform kernel product;
  shared frontend contract consumption, renderer and form lifecycle;
  `frontend/apps/web`.
- Reason / Why Here: the candidate's source lint gate exposed three stale
  dependency declarations after the frontend stopped owning the related
  product semantics. The generic frontend layer owns removal of those unused
  inputs while preserving existing compatibility call shapes.
- Why Not Elsewhere: no construction or customer semantics, permission, API,
  route, database record, native view definition or low-code configuration is
  changed. No frontend fallback or model/scene-specific branch is introduced.
- Blast Radius / validation: section presentation compatibility and generic
  record-form action/lifecycle dependency extraction only. Source lint, strict
  type checking, release units, deterministic build and exact-SHA browser
  release gates must pass after integrating the current authoritative main.
- First full-gate correction: `7ff409a` removed the project-intake-specific
  frontend route but also added its menu to the P1 project-manager primary
  surface without adding it to the locked formal product menu. Exact runtime
  evidence proved the released authority remains PM 14 and aggregate 71. The
  unconfirmed primary-menu expansion is removed; generic `/s/:sceneKey`
  rendering continues to own the scene entry. The browser identity audit now
  reads the platform-neutral app title used by the runtime instead of freezing
  the retired construction-specific brand suffix.
- Delivery-hardening correction: the release browser still waited for the
  retired finance-specific workspace after the production renderer converged
  on the generic record surface. Its readiness checks now bind to the shared
  record container. Read-only forms no longer preload edit-time relation
  candidate lists; selected relation identities remain contract/record driven,
  avoiding both unnecessary enumeration requests and permission-noise 403s.
  Four orphan product-record components left behind by the retired workspace
  are removed, and the full source typecheck joins lint, strict typecheck,
  release units, build and exact-SHA browser evidence in the final gate set.
- Generic entry-action correction: the retired workspace component had also
  been the only renderer of settlement `entry_actions`. The P1 provider now
  projects those authorized entries into the existing generic V2
  `businessActions` protocol as same-tab open actions; the shared P0 form
  remains model-neutral. The V2 runtime probe asserts the URL, visibility and
  settlement default binding before browser acceptance.

## 2026-08-08 — PRODUCT-MENU-VISIBLE-CONVERGENCE-V2

- Branch / anchor: `feature/product-menu-visible-convergence` from the exact
  daily frontend candidate `ca1ee11165ec1ea7f7be527ba05fab999b417f09`.
- Formal Product Layer / Layer Target / Module: P1 construction standard
  product navigation and truthful release maturity; native menu XML, released
  product-policy projection and release guards in `smart_construction_core`.
- Reason / Why Here: the native cost center and its actions existed, but the
  locked released policy omitted them, so the frontend correctly filtered the
  center out. The product menu also mixed centers, process groups and leaves at
  the same visual level. This batch restores cost as an independent center,
  keeps construction delivery and resource/subcontract supply as peer centers,
  keeps tax as an independent compliance center, names the cross-domain
  analytics surface “报表中心”, and converges organization/admin branches.
- Why Not Elsewhere: XMLIDs, actions, ACLs, record rules and P3 user runtime
  configuration remain unchanged. The P0 frontend receives the released
  policy without construction-specific navigation branches. The locked user
  baseline remains page-identity authority; only explicit navigation-v2 group
  aliases, six allowlisted cost entries and two allowlisted management reports
  may extend it.
- Blast Radius / validation: `smart_construction_core` menu parentage and
  product-policy grouping, frontend acceptance paths, menu release evidence and
  guards. WBS remains internal-only. Static manifest/XML checks, locked-contract
  unit tests, module upgrade, product menu runtime audit, release snapshot and
  real `wutao` daily navigation acceptance must pass before handoff.
- Daily release operation: the acceptance-fixture snapshot tool remains denied
  for `sc_demo`. `release.daily_product_navigation.snapshot` is the only V2
  daily write entry; it is fixed to dev/sc_demo, requires an explicit
  confirmation, derives the exact HEAD version and reuses the formal snapshot
  service plus locked-contract assertions.

## 2026-08-09 — ISOLATED-PRODUCTION-ACCEPTANCE-PAYLOAD-CLOSURE

- Branch / anchor: governed `release/tenant-rc-<tenant-key>-v1` branch from
  `c3806823ae07c5b23b9d2dde0508382a0287d81b`.
- Formal Product Layer / Layer Target / Module: P2 signed customer
  history baseline executed by a P4 delivery tool; `scripts/ops`,
  `scripts/tenant_payload`, and `make/release.mk`.
- Reason / Why Here: the isolated production restore and immutable P2 module
  were activated on the daily server, but the signed supplemental fuel payload
  had no governed plan/import/verify entry for that persistent clone. The P4
  tool owns the one-time replay and audit boundary while the signed P2 payload
  remains the customer-data authority.
- Why Not Elsewhere: no customer records enter P0/P1 source, no platform or
  industry default is changed, and no P3 runtime configuration is used as a
  data carrier. The tool refuses production-connected resources and binds the
  exact restore, database filter, internal network, filestore, tenant addon,
  signature key, payload checksum, operator XMLID, and importer group.
- Blast Radius / validation: only the explicitly named isolated tenant acceptance clone
  may receive writes. Unit/compile guards, immutable remote-tool installation,
  signed payload plan, explicit-confirmation import, post-import verification,
  exact 8/32/501 archive counts, identity consistency, read-only behavior,
  frontend contract/data probes, and zero production connections prove
  containment and closure.
- Runtime correction: supplemental archives may retain a relationship to an
  inactive historical project. The P2 customer adapter admits that lookup only
  inside the signed narrow-import context, still requires importer authority
  and an allowed company, and never uses `sudo`. A distinct confirmed P4
  refresh replaces only the isolated clone's Odoo container and immutable
  tenant mount; it preserves the exact database, internal network and
  filestore, and restores the previous tenant mount if startup fails.
  Retrying a failed batch is enabled only by the same explicitly confirmed
  import action; plan and verify remain non-resuming read paths.
- Product-boundary correction: the P4 runtime now requires the tenant key as an
  explicit invocation parameter and compares it with the signed manifest. Public
  product code, tests, and audit prose retain no fixed customer identity.
  Immutable tool reinstall remains idempotent while consuming the complete
  archive stream before validating the existing SHA, preventing a false
  `SIGPIPE` failure on repeated verify calls.

  Clone activation and tenant refresh create or reuse a private stable runtime
  JWT secret and inject it without printing the value; the image's weak
  missing-secret fallback is therefore not exercised by this acceptance clone.
  The immutable candidate edge exposes an exact JSON `/healthz` liveness
  contract ahead of the SPA fallback, and the nginx container healthcheck
  validates its status and body rather than checking configuration syntax only.
  The tenant-RC boundary build now passes an explicit `boundary_head` source
  authority to repository preflight. It still requires a clean allowlisted
  release branch and exact `SOURCE_SHA == HEAD`; ordinary candidates continue
  to require the same SHA at `origin/main`.
  Candidate builds isolate workspace manifests and the frozen pnpm install
  ahead of frontend source, and use named BuildKit caches for pnpm, apt and
  pip downloads. Incremental source changes therefore rebuild application
  output without reinstalling 623 frontend packages or refetching package
  indexes; dependency changes remain locked by `pnpm-lock.yaml`.

## 2026-08-09 — NORM-ENGINE-ENTRY-TARGET-CLOSURE

- Branch / anchor: governed `release/tenant-rc-<tenant-key>-v1` at `78d10d0`.
- Formal Product Layer / Layer Target / Module: P1 industry capability entry in
  `sc_norm_engine`; P0 generic explicit-parent target projection in `smart_core`.
- Reason / Why Here: the installed norm module exposed all four authorized child
  actions, but its root had no action and the delivery projection rebuilt that
  root as a targetless synthetic group. The root now explicitly opens the norm
  item list. When native discovery and policy paths emit the same menu once as
  an action and once as a directory, the platform merges them by exact native
  menu identity, preserving both the declared target and directory children.
- Why Not Elsewhere: no frontend label special case, low-code override, database
  repair, or customer-module behavior is introduced.
- Blast Radius / validation: explicit-action native groups can open their declared
  target; ordinary targetless groups retain expand/collapse behavior. Static XML,
  delivery-menu regression, module upgrade, runtime system-init projection, and
  real browser navigation must pass.
- P4 acceptance orchestration: the persistent isolated restore gains an exact,
  confirmation-gated `sc_norm_engine` upgrade entry. It validates restore,
  database filter, image revision, tenant mount, network and container labels,
  stops only the clone Odoo process, runs `--stop-after-init`, and restarts the
  same clone; production resources and arbitrary modules remain inadmissible.

## 2026-08-09 — FINAL-NAVIGATION-AUTHORITY-SOURCE-CLOSURE

- Branch / anchor: governed `release/tenant-rc-<tenant-key>-v1` at `6a09245`.
- Formal Product Layer / Layer Target / Module: P0 platform kernel; final
  `system.init` navigation and route-authority assembly in `smart_core`.
- Reason / Why Here: the SPA consumes `release_navigation_v1.nav` before the
  delivery and legacy carriers, but final route authority was rebuilt from the
  legacy `data.nav`. A late, valid directory/action merge could therefore be
  visible yet fail closed on click. The platform assembler now uses the same
  release/delivery/legacy priority as its consumer.
- Why Not Elsewhere: no construction or customer semantics belong in this
  rule, and neither frontend fallback nor low-code configuration may infer or
  weaken route authority.
- Blast Radius / validation: only menu/action pairs emitted by the authoritative
  final navigation projection can be admitted. Static source-order regression,
  focused backend tests, final `system.init` pair consistency, and a real
  `wutao` browser click on the isolated rehearsal clone prove containment.
## 2026-08-09 — ACTION-SURFACE-RENDERER-REGISTRY

- Branch / anchor: governed `release/tenant-rc-<tenant-key>-v1` at `eef94ed`.
- Formal Product Layer / Layer Target / Module: P0 platform kernel; generic
  frontend contract consumption through the Action Surface Renderer Registry.
- Reason / Why Here: every collection presentation, including planned pivot,
  graph, calendar, gantt, activity, and dashboard views, needs one governed
  dispatch boundary instead of page-local component branches.
- Why Not Elsewhere: no construction, quota, tenant, low-code, or operations
  semantics belong in renderer selection; the frontend consumes only the
  backend presentation semantic.
- Blast Radius / validation: ActionView surface dispatch, registered collection
  semantics, explicit readable fallbacks, and unsupported fail-closed behavior.
  Registry unit tests, architecture guards, existing collection semantics,
  frontend build, and real hierarchy-browser acceptance prove containment.
## 2026-08-09 — DESIGN-TOKEN-CONTROL-VISUAL-CLOSURE

- Branch / anchor: governed `release/tenant-rc-<tenant-key>-v1` at `eef94ed`.
- Formal Product Layer / Layer Target / Module: P0 platform design system;
  design-token CSS compilation and shared button/query-toolbar primitives.
- Reason / Why Here: numeric radius tokens were emitted without CSS length
  units, so browsers discarded the shared radii and controls rendered square.
  Shared button hierarchy also needed one consistent hover, border, focus,
  alignment, and motion policy.
- Why Not Elsewhere: quota, construction, customer, and page-local styles must
  not compensate for a platform token compiler defect.
- Blast Radius / validation: all consumers of component radius tokens and
  `.sc-btn`, plus search-toolbar button height. Token unit tests, token verify,
  strict typecheck, frontend build, computed-style browser assertions, and the
  real hierarchy workbench screenshot prove containment.

## 2026-08-09 — VERSIONED-BOQ-IMPORT-TO-COST-WBS-CLOSURE

- Branch / anchor: `feature/boq-versioned-import-wbs` at `86d6ee8`.
- Formal Product Layer / Layer Target / Module: P1 construction standard product;
  L2 domain models and Odoo native model/view/security system in
  `smart_construction_core`.
- Reason / Why Here: BOQ source, version, publication state, import evidence,
  amount conservation, and cost-WBS ownership are construction cost facts. The
  contract must remain stable while file-specific parsing evolves incrementally.
- Why Not Elsewhere: `smart_core` owns only generic runtime mechanisms; the SPA
  renders backend contracts and must not invent BOQ state. Low-code and customer
  modules cannot own statutory cost facts. P4 is limited to isolated fixtures,
  real-file probes, browser acceptance, and release evidence.
- Blast Radius / validation: `project.boq.line`, new version and import-batch
  facts, `construction.work.breakdown`, project BOQ entry, downstream cost and
  progress references, native views/security, and import wizard. Static guards,
  focused ORM tests, isolated `sc_clean` install/upgrade, real XLS import with
  row/amount reconciliation, WBS idempotency, and authenticated `sc_demo`
  browser acceptance must pass before product-baseline closure resumes.

## 2026-08-09 — SOURCE-ORDER-BOQ-RECONCILIATION-CLOSURE

- Branch / source evidence: `feature/boq-versioned-import-wbs`; real XLS SHA-256
  `08c05ba9a357453d95e552b0cdfc2f7a83b749d1d8b2d479a2a8250c5eae35a3`.
- Formal Product Layer / Layer Target / Module: P0 generic contract-driven
  `hierarchical_worksheet` source-order presentation in `smart_core` and the
  SPA; P1 BOQ source facts, independent calculations, summary scopes, and
  reconciliation rules in `smart_construction_core`.
- Preserved source structure: the published `V1-20260809` snapshot (version id
  21, project id 4) contains 135 source-order rows: 108 BOQ items, 13 structural
  headings, and 14 source subtotal/total rows. Only 4 blank or semantically empty
  helper rows are ignored. Source amount remains `3,478,851.81`; WBS remains 203
  nodes and no `Units` alias survives.
- Independent calculation evidence: every item freezes quantity × unit price;
  each subtotal/total freezes its item scope, source amount, calculated amount,
  variance, scope count, and boundary sequences. Real source differences include
  `114,896.48 - 114,896.49 = -0.01` and
  `3,031,841.76 - 3,031,841.74 = 0.02`.
- Browser evidence: authenticated `wutao` acceptance at
  `http://127.0.0.1:18083` passed with 108 items, 13 headings, 14 summaries,
  exact nine-column standard contract with side-by-side source/system amounts,
  audit variance kept outside the ordinary worksheet, resizable panes, real XLS
  preflight, and 203-node WBS. Evidence is under
  `artifacts/boq-baseline-browser/`, including
  `boq-source-calculation-comparison.png`,
  `boq-import-preflight-verified.png`, and `result.json`.
- Gates: BOQ ORM tag passed 8 tests / 0 failures; isolated page assembler passed
  7 tests; strict Vue typecheck, local incremental frontend build, XML/Python
  syntax, `git diff --check`, browser runtime errors, HTTP errors, console errors,
  and captured OLE warning-log checks all passed.

## 2026-08-09 — FULL-BOQ-ANALYSIS-AND-TARGET-COST-PLAN-BASELINE

- Branch / anchor: `feature/boq-versioned-import-wbs` at `aa0c208`.
- Formal Product Layer / Layer Target / Module: P1 construction industry
  standard product; L2 cost-domain facts, import service, native views, and
  permissions in `smart_construction_core`.
- Reason / Why Here: statutory BOQ workbooks contain BOQ facts, unit-price
  analyses, norm composition, resource consumption, measures, fees, and taxes.
  A target cost plan must be generated from an immutable published snapshot of
  those facts and remain a separate management baseline.
- Why Not Elsewhere: generic contract infrastructure stays in `smart_core`;
  frontend renders the backend contract and performs no cost calculations;
  WBS remains a management dimension rather than the owner of BOQ or target
  cost facts; sample-specific probes remain P4 evidence only.
- Blast Radius / validation: BOQ import parsing and preview, BOQ version and
  analysis records, target cost plan lifecycle, cost permissions/actions/views,
  and existing WBS/BOQ consumers. Both supplied real workbooks, component and
  amount conservation tests, isolated `sc_clean` module rehearsal, contract
  guards, and authenticated browser acceptance must pass before baseline
  closure.
- Final real-data evidence: published `V6-FULL-20260810` preserves 1,658 BOQ
  rows, 1,414 priced items, 1,138 unit-price analyses, 1,622 norm composition
  rows, and 225 unit-project summary facts. `CN-SC-2015-BUDGET` resolves 1,541
  norm rows (95.01%); 81 source-specific or supplemental rows remain explicit
  unmatched facts rather than being guessed. The generated `V5-20260810`
  target plan contains 7,441 lines and a `29,922,323.10` budget baseline.
- Scale closure: the plan form no longer embeds and hydrates all 7,441
  one-to-many lines. A native contextual action opens the separately secured
  target-cost ledger at 20 rows per page (373 pages), while the plan form owns
  summary, version, validation, publication, adjustment, and archive state.
  The project-manager delivery contract explicitly exposes BOQ analysis and
  cost plan menus and binds the ledger action to the cost-plan context; no SPA
  business rule or client action is introduced.

## 2026-08-10 — FINAL-IMAGE-REAL-PLAN-EVIDENCE-PRODUCER

- Branch / anchor: `release/rc16-final-plan-producer` from `bd97bd0`.
- Formal Product Layer / Layer Target: P4 governed release delivery tooling.
- Reason: candidate publication required `final-image-real-plan.json`, but the
  repository only validated that evidence and had no governed producer; RC12
  therefore depended on a repository-external one-off script.
- Boundary: the new Make entry runs the existing read-only signed-payload plan
  only against a production-disconnected restore namespace, fingerprints the
  isolated database before and after, binds manifest relationship totals, and
  atomically emits the exact candidate evidence contract. It does not import
  payload data, connect to production, change frontend/business contracts, or
  relax the zero-write publication gate.
- Validation: runtime and evidence unit tests, governed restore-ID acceptance,
  publication contract regression, Python compilation, and `git diff --check`.

## 2026-08-10 — PRODUCTION-CANDIDATE-INCREMENTAL-DIGEST-SYNC

- Branch / anchor: `fix/production-candidate-digest-reference` from `1f5fc43`.
- Formal Product Layer / Layer Target / Module: P4 governed release delivery
  tooling in `scripts/ops/production_candidate_image_sync.py` and
  `make/release.mk`.
- Reason / Why Here: the production archive importer created only a version-tag
  cache entry while configuration promotion required the published registry
  digest reference. It also retransmitted the full OCI archive even when most
  layers already existed remotely.
- Why Not Elsewhere: product images, P0/P1 modules, frontend contracts, tenant
  payloads, and production data do not own transport or registry identity.
- Blast Radius / validation: only the explicitly confirmed production image
  cache sync changes. Every OCI blob is hash-verified, unchanged blobs are
  reused through a digest-addressed `rsync --link-dest` cache, the published
  digest is resolved after import, and both tag and digest must map to the
  archive config ID. Focused tests, the complete backup/restore tooling
  contract, Python compilation, and a real idempotent production sync prove
  containment; no service, container, volume, or database is changed.

## 2026-08-10 — CUSTOMER-HISTORY-ATTACHMENT-DELIVERY

- Branch / anchor: `fix/customer-history-attachment-delivery` from `60c3693`.
- Formal Product Layer / Layer Target / Module: P0 tenant delivery manifest
  admission and P4 governed production release tooling; customer facts remain
  in the external P2 `sce_customer_<tenant>_legacy` carrier.
- Reason / Why Here: the product baseline must contain no customer history,
  while a signed customer package may install a declared same-tenant history
  carrier and resolve its binaries from a tenant-owned read-only root.
- Why Not Elsewhere: no customer record, attachment index, binary, path, or
  business meaning enters the product image, P1 industry module, or frontend.
- Blast Radius / validation: signed customer-package admission, short-lived
  maintenance module sets, and the explicitly confirmed production Odoo/nginx
  runtime overlay. The external binary root is mounted read-only; release
  tooling tests, manifest tests, isolated signed-payload verification, product
  zero-history verification, authorized byte comparison, and unauthorized 403
  prove containment.

## 2026-08-10 — PRODUCTION-TENANT-ARTIFACT-CUSTODY-SYNC

- Branch / anchor: `fix/production-tenant-artifact-sync` from `0da2ecf`.
- Formal Product Layer / Layer Target / Module: P4 governed tenant-delivery
  transport in `scripts/ops/production_tenant_delivery_artifact_sync.py` and
  `make/release.mk`.
- Reason / Why Here: production already had fail-closed package preparation,
  module install, payload import, and verification, but no governed route from
  signed external artifacts into production custody; direct `scp` is forbidden.
- Why Not Elsewhere: P0/P1 modules, the product image, frontend, product
  filestore, and the P2 module must not own customer payload transport.
- Blast Radius / validation: only an exact-confirmation production filesystem
  target is added. It checks local and remote checksums, forbids symlinks,
  incrementally resumes into one scoped staging root, atomically freezes one
  delivery directory, and generates a bound release-set lock. It performs zero
  database, service, container, product-image, filestore, or legacy-binary
  writes. Focused inventory tests and the release-tooling suite prove scope.

## 2026-08-10 — PRODUCTION-MAINTENANCE-CONFIG-OVERRIDE

- Branch / anchor: `fix/production-maintenance-config-override` from `f0f82e0`.
- Formal Product Layer / Layer Target / Module: P4 short-lived production
  tenant-payload maintenance runtime.
- Reason: the locked rc.17 product runtime remains valid, but its embedded
  maintenance validator predates the generic same-tenant history-extension
  protocol. Rebuilding the whole product image is unnecessary for one
  short-lived validation script.
- Boundary: only tenant-payload maintenance containers may mount the validator
  from an immutable `/opt/sce/deployment-tools/<sha>` root, read-only and bound
  to `DEPLOYMENT_TOOL_SHA`. Normal Odoo/nginx runtime, product code, customer
  payloads, databases, filestore, and historical binaries are unchanged.

## 2026-08-10 — PRODUCTION-TENANT-ARTIFACT-READER-MODES

- Branch / anchor: `fix/production-tenant-artifact-modes` from `c04a283`.
- Formal Product Layer / Layer Target: P4 production custody permissions.
- Reason / Boundary: signed payloads remain root-owned, but the short-lived
  non-root maintenance container must read the bind-mounted payload and public
  key. The governed sync now normalizes only that payload subtree to `0750`
  directories and `0640` files, verifies all checksums first, and reports the
  metadata changes. Customer packages, databases, services, product filestore,
  and 70GB historical binary custody remain untouched.

## 2026-08-11 — CUSTOMER-HISTORY-DUAL-ATTACHMENT-ROOTS

- Branch / anchor: `fix/legacy-attachment-dual-roots-v2` from `990e9d8`.
- Formal Product Layer / Layer Target / Module: P0/P4 generic customer runtime
  delivery mechanism in `docker-compose.production-customer.yml` and the
  governed activation target in `make/release.mk`; customer attachment facts
  and bindings remain in the external P2 customer package.
- Reason / Why Here: the frozen tenant attachment corpus spans the authoritative
  `raw_files` root and its prepared `online_mirror`, while the production
  customer overlay exposed only the first root to the generic file resolver.
- Why Not Elsewhere: the P1 product, frontend, product filestore, and customer
  data module cannot provide host filesystem mounts; no business or rendering
  contract changes are required.
- Blast Radius / validation: only the explicitly confirmed production Odoo and
  nginx runtime activation receives a second required read-only mount. Compose
  rendering, maintenance contract tests, exact-root guards, customer payload
  replay, authorized byte comparison, and anonymous 403 prove containment.

## 2026-08-11 — SIGNED-CUSTOMER-MODULE-UPGRADE

- Branch / anchor: `fix/production-customer-module-upgrade` from `6fc02ae`.
- Formal Product Layer / Layer Target / Module: P4 governed production customer
  delivery tooling in `make/release.mk`.
- Reason / Boundary: a signed P2 customer module already installed in production
  needs an explicit upgrade path; the existing target covered first install
  only. The new target admits only a module named by the signed release set and
  delegates to the immutable production DB contract's existing `upgrade`
  action. It does not broaden product, frontend, image, or tenant scope.
- Validation: maintenance contract tests, release-set allowlist checks,
  production DB contract tests, and `git diff --check`.

## 2026-08-11 — PRODUCTION-ATTACHMENT-PREVIEW-CSP

- Branch / anchor: `fix/production-attachment-preview-csp` from `14641e9`.
- Formal Product Layer / Layer Target / Module: P4 governed production edge
  policy in `scripts/ops/production_attachment_preview_csp.py`.
- Reason / Boundary: authenticated historical attachment bytes download
  correctly, but the edge CSP inherits `default-src 'self'` for frames and
  blocks the frontend's in-memory image/PDF preview URL. The change adds only
  `frame-src 'self' blob:`; script, connect, object, origin, and frame-ancestor
  policies remain unchanged.
- Blast Radius / validation: one exact nginx snippet and one nginx reload. The
  tool is immutable-SHA bound, captures a rollback copy, fails closed on policy
  drift, validates nginx before reload, verifies the public header, and rolls
  back on failure. Unit tests and real wutao browser preview/download prove it.

## 2026-08-11 — PRODUCTION-CSP-RELOAD-CONVERGENCE

- Branch / anchor: `fix/production-csp-reload-convergence` from `311ea03`.
- Formal Product Layer / Layer Target / Module: P4 production edge verification
  in `scripts/ops/production_attachment_preview_csp.py`.
- Reason / Boundary: nginx graceful reload may serve one in-flight request from
  an old worker immediately after `systemctl reload`; a single public-header
  read caused a correct candidate to roll back. Verification now polls the same
  exact public CSP condition for at most five seconds. Mutation scope and
  rollback behavior are unchanged.

## 2026-08-11 — P1-PRODUCT-CENTER-BASELINE-INTEGRATED-CLOSEOUT

- Branch / anchor: `feature/product-center-baseline-v1-integrated` from current
  `main` at `c1edcf8`; source task branch ended at `63a2159`.
- Formal Product Layer / Layer Target / Module: P1 / L2 native navigation /
  `smart_construction_core`; generic navigation delivery remains in
  `smart_core`.
- Reason / Why Here: the locked construction-product centers, released menu
  actions, ACL-visible native tree and product configuration entry are standard
  industry defaults. The task branch was replayed on current main to preserve
  completed production attachment tooling without using a divergent merge or
  rebase.
- Why Not Elsewhere: P0 owns only the generic navigation contract and delivery
  mechanism; customer naming and stable customer differences remain P2;
  administrator runtime adjustments remain P3; verification scripts are P4
  evidence rather than runtime authority.
- Blast Radius / validation: ten canonical primary-center identities and order,
  51 delivered menu leaves, product/low-code boundary guards and customer-field
  extraction guards. The isolated `sc_product_center` runtime and `wutao`
  browser acceptance are rerun on the integrated candidate before publication.

## 2026-08-11 — P1-PRODUCT-CENTER-CLEAN-INSTALL-CLOSEOUT

- Branch / anchor: `feature/product-center-baseline-v1-integrated` at the PR #169
  candidate derived from `c1edcf8`.
- Formal Product Layer / Layer Target / Module: P1 / deterministic native view
  loading / `smart_construction_core`; generic boundary enforcement remains P0
  and customer identity remains outside the product repository.
- Reason / Why Here: the candidate's formal list alignment file was loaded
  before the tree views it binds, while a duplicated salary action introduced a
  reverse cross-file dependency. Existing upgraded databases masked both
  forward references; a clean product install failed closed.
- Boundary / validation: load the base formal views before final alignment,
  keep the salary action override only in the alignment authority, and make the
  runtime drift audit follow manifest order. A static regression rejects future
  cross-file forward references. Fixed customer identifiers are removed from
  the P1 menu documentation and guard description. The tenant payload boundary,
  19 focused tests, fresh install plus upgrade, five authorization ORM tests,
  resource cleanup proof, and the product-menu release-ready aggregate pass.

## 2026-08-11 — P1-FULL-MENU-RESTORE-CONTRACT-CONVERGENCE

- Branch / anchor: `feature/product-center-baseline-v1-integrated` at `020cc32`.
- Formal Product Layer / Layer Target / Module: P1 / L2 locked product-menu
  projection / `smart_construction_core`; the repair is confined to its P4
  restore consumer and release regression test.
- Reason / Why Here: the locked 159-page product policy explicitly includes
  stable action-only page identities, while the older restore utility required
  every identity to resolve as `ir.ui.menu`. The canonical runtime
  synchronizer already supports both native-menu and action-only targets.
- Why Not Elsewhere / Blast Radius: no frontend fallback, customer override,
  low-code mutation, menu renaming, or baseline rewrite is introduced. The
  restore utility now consumes the same action-only mapping, validates the
  resolved action XMLID, preserves `menu_id=0`, and emits an action route. Unit
  tests plus a direct-source `sc_demo` restore and full runtime/browser menu
  audit prove containment.

## 2026-08-11 — P4-DAILY-CANDIDATE-INCREMENTAL-SOURCE-PRESEED

- Branch / anchor: `feature/product-center-baseline-v1-integrated` after
  `e244e01`.
- Formal Product Layer / Layer Target / Module: P4 daily delivery tooling /
  `scripts/ops/daily_candidate_bundle_sync.py`.
- Reason / Boundary: direct-source iteration may safely preload a small set of
  candidate files before the exact candidate bundle arrives. The governed sync
  now accepts only tracked, unstaged modified paths whose Git blob hashes equal
  the exact candidate commit; all unknown, staged, deleted, renamed, or
  different bytes remain fail-closed.
- Blast Radius / validation: daily candidate synchronization only; production,
  origin main, database and filestore behavior are unchanged. The integration
  test exercises an exact preseed plus remaining bundle delta and still proves
  detached exact SHA, clean worktree and untouched origin/main.

## 2026-08-11 — P4-FULL-MENU-RUNTIME-AUDIT-CONTRACT-CONVERGENCE

- Branch / anchor: `feature/product-center-baseline-v1-integrated` after
  `662323b`.
- Formal Product Layer / Layer Target / Module: P4 release verification for the
  P1 locked menu contract / `construction_product_menu_release_audit.py`.
- Reason / Boundary: the runtime audit still assumed every locked page identity
  was a native menu and rejected the contract's explicit action-only targets.
  Native targets continue to require visible `ir.ui.menu`; action-only targets
  now require the exact mapped action XMLID, installed model, action-group
  access and model read ACL for a verification user.
- Blast Radius / validation: verification semantics only; no runtime policy,
  frontend, customer module or business data is changed. Unit coverage and the
  daily `sc_demo` release audit prove the gate accepts only the two canonical
  delivery forms.

## 2026-08-11 — P4-CONTRACT-CENTER-AUDIT-AUTHORITY-CONVERGENCE

- Branch / anchor: `feature/product-center-baseline-v1-integrated` after
  `9742275`.
- Formal Product Layer / Layer Target / Module: P4 contract-center release
  verification consuming the P1 locked menu contract.
- Reason / Boundary: the contract-specific audit retained a second hardcoded
  list of superseded contract and settlement menus. It now derives the exact
  contract-center set from the checksum-locked product contract, requires
  standard/preview parity, validates native group ownership, and checks the
  non-roadmap pages for both real verification users.
- Blast Radius / validation: audit authority only; no menu, action, frontend or
  database fact is changed. The full 159-page audit remains the aggregate gate,
  while this focused gate proves the current contract center's permission and
  user visibility semantics.

## 2026-08-11 — P0-CONTRACT-GOVERNANCE-CLOSURE-V1

- Branch / anchor: `codex/contract-governance-closure-v1` from `63a2159`.
- Formal Product Layer / Layer Target / Module: P0 / L0-L1 contract and release
  governance / `smart_core`, generic frontend contract consumers, verification
  scripts and Make release topology.
- Standard vs User-Specific: platform mechanism shared by every industry and
  tenant; no construction or customer semantics are introduced.
- Reason / Why Here: release certification, Scene-ready authority, contract
  projection, entitlement consumption and runtime probes are platform
  mechanisms. Their evidence must fail closed and remain synchronized with
  refactored runtime code.
- Why Not Elsewhere: P1 owns construction defaults, P2 customer baselines and
  P3 administrator configuration. None may define or bypass the common
  contract protocol or its release gate.
- Blast Radius / validation: product release dependencies, generic web
  Home/Action/Form consumers, contract verification scripts and isolated test
  runtime only. Validation requires the full frontend product gate, Unified
  Page Contract v2 gate, contract-mode runtime probes, Scene source evidence
  minimums, production-chain guard and two-viewport browser acceptance.
- Closure Evidence: `verify.product.release.ready` passed end to end; the
  isolated `sc_contract_governance_v1` database was rebuilt without demo or
  customer data and passed exact project/database/dbfilter health checks.
  Contract-mode and strict Scene live probes passed with canonical token and
  explicit database routing; strict Scene gaps and fallback gaps were both
  zero. Frontend strict typecheck, release units, style-system guard and a
  667-module isolated static build passed. The zero-data browser check reached the
  database-locked login shell with zero console warnings/errors; authenticated
  customer UX evidence is intentionally outside this platform-mechanism
  closure because no customer principal is seeded into the isolated database.

## 2026-08-11 — P0-RELEASE-GATE-ACTION-PARENT-PRESERVATION

- Branch / anchor: `feature/product-center-baseline-v1-integrated` after the
  selective integration of contract-governance commit `74a44e4`.
- Formal Product Layer / Layer Target / Module: P0 / L0-L1 released navigation
  projection / `smart_core`; no construction label, model or customer identity
  is introduced into the platform mechanism.
- Reason / Boundary: a released navigation node may own both an executable
  target and child nodes. The release gate previously treated every such node
  as a pure directory and deleted its released target when all children were
  filtered. The gate now preserves only an independently authorized executable
  parent as a leaf; pure directories, unreleased targets and user-acceptance
  surfaces remain fail-closed.
- Blast Radius / validation: `system.init` navigation filtering and its focused
  transaction tests only. The exact candidate is replayed on `sc_demo`, then
  the 159-page release audit, contract-open matrix and authenticated browser
  navigation acceptance are rerun before baseline promotion.

## 2026-08-11 — P1-FULL-MENU-POLICY-AUTHORITY-CONVERGENCE

- Branch / anchor: `feature/product-center-baseline-v1-integrated` after
  `6e20d0e` daily-source diagnostics.
- Formal Product Layer / Layer Target / Module: P1 / construction product
  navigation authority / `smart_construction_core`; the P0 generic extension
  point remains available for products that explicitly require a native tree.
- Reason / Boundary: construction still exported an unconditional native-tree
  authority hook from the earlier primary-center experiment. It bypassed the
  locked 159-page release policy, delivered 94 database-native actions including
  42 descendants of the retired user-acceptance root, and left only 36 actions
  after the release gate. The construction product now uses the standard
  delivery-policy projection: the release snapshot selects product pages while
  Odoo menu visibility, action identity, model ACL and record rules remain the
  execution authority.
- Read-only counterfactual evidence: disabling only the stale hook on `sc_demo`
  projected 135 executable actions, zero release-gate removals and nine product
  groups for `wutao`; route authority retained 131 primary, 14 contextual and
  five administrator action facts. The committed change is accepted only after
  exact-source replay and authenticated browser/contract verification reproduce
  those bounds.

## 2026-08-11 — P0-SINGLE-NAVIGATION-AUTHORITY-CLOSURE

- Formal Product Layer / Layer Target / Module: P0 / L0-L1 navigation authority
  / `smart_core`, generic overlay and runtime verification.
- Decision: the early experimental native-tree short circuit is removed from
  the platform, not merely disabled in construction. Every product follows one
  route: released product policy selects pages, native Odoo menu/action facts
  intersect authorization, the release gate enforces the active snapshot, and
  the frontend renders the final contract.
- Compatibility: Odoo models, views, actions, ACL and record rules remain
  authoritative execution facts. P2/P3 overlays may rename, order or hide only
  allowed stable menu identities; lack of a customer configuration row cannot
  delete a released P1 page. No client action or frontend business fallback is
  introduced.
- Governance: focused tests and static guards now reject reintroduction of the
  native-tree hook, helper builders or source marker. The runtime probe always
  verifies that a non-admin policy projection cannot exceed its supplied native
  authorization facts.
## 2026-08-11 — P0-BACKEND-CONTRACT-LIFECYCLE-AUTHORITY-V1

- Branch / anchor: `codex/backend-contract-lifecycle-authority-v1` from
  `74a44e4e486d22ad97b52cba5215f947fe7a8958`.
- Formal Product Layer / Layer Target / Module: P0 / L0-L1 contract lifecycle
  authority / `smart_core`, typed generic frontend consumer and P4 release
  verification.
- Standard vs User-Specific: common platform mechanism. No construction or
  customer semantics and no customer data are introduced.
- Reason / Why Here: schema identity, generation provenance, append-only
  publication, runtime resealing, traceability and compatibility are one
  indivisible platform contract lifecycle.
- Why Not Elsewhere: P1/P2/P3 may provide industry, customer and tenant
  definitions but may not redefine the public protocol or bypass publication
  authority.
- Blast Radius / validation: UPC v2.2 metadata and typed consumer, business
  configuration contract lifecycle fields and migration, centralized rollback,
  backend boundary detection and release topology. The isolated
  `sc_contract_lifecycle` database contains no demo/customer data and passed
  exact environment health, a controlled 17.0.1.1.8 migration rehearsal and
  14/14 lifecycle runtime assertions.

## 2026-08-13 — P4-ACCEPTANCE-CLONE-DATABASE-AUTHORITY-CLOSURE

- Branch / anchor: `fix/acceptance-clone-db-authority-v2` from `af117b4`.
- Formal Product Layer / Layer Target / Module: P4 / isolated production-restore
  acceptance orchestration / `scripts/ops/production_acceptance_clone_runtime.py`.
- Standard vs User-Specific: generic delivery safety mechanism; no platform,
  construction-industry, customer preference or business-data semantics change.
- Reason / Why Here: a renamed isolated restore retains its source
  `smart_core.platform_release_db` value, while the locked snapshot initializer
  correctly requires that authority to equal the exact current database. The
  acceptance orchestrator owns the explicit, fail-closed rebind immediately
  before refreshing the snapshot.
- Why Not Elsewhere: P0-P3 must not silently rewrite database identity during
  normal runtime, installation or configuration; the frontend has no database
  authority. This is an isolated restore transition owned by P4.
- Blast Radius / validation: only the exact
  `r10e_sc_restore_<timestamp>_<suffix>` database inside the verified restore
  namespace and its single release-database parameter row. The replacement path
  also admits the legacy clone label only on the exact isolated network and
  combines product and installed-tenant module names into one Odoo `-u` value
  because repeated options overwrite. Unit tests lock identity rejection,
  validated SQL identity, idempotence, missing/duplicate-row failure and upgrade
  ordering. The production clone rehearsal upgraded `smart_construction_core`
  from `17.0.0.127` to `17.0.0.129`, retained the P2 module at `17.0.3.1.7`,
  preserved protected business-data counts, and passed the RC20 acceptance
  package twice without connecting to the production database.

## 2026-08-11 — P1-PROJECT-SALARY-FACT-OWNERSHIP-CLOSURE

- Branch / anchor: `fix/product-ten-center-runtime-closure` at `74e28e7`.
- Formal Product Layer / Layer Target / Module: P1 / L2 construction business
  fact and governed-entry authority / `smart_construction_core`.
- Standard vs User-Specific: construction-industry standard. No customer data,
  customer wording, tenant preference or frontend business rule is introduced.
- Reason / Why Here: salary calculation recognizes project salary cost and the
  payable amount, while salary payment records confirmed payment evidence. The
  previous two menu entries shared one fact model because the locked menu and
  model-family registries had no machine-checked connection.
- Why Not Elsewhere: P0 only transports and renders the contract; P2/P3 may
  configure permitted presentation but cannot replace the fact owner; P4 may
  migrate historical values but cannot own the ongoing workflow.
- Blast Radius / validation: two project-salary menus, their actions and
  action-scoped form contracts, payroll/payment models, ACL and record rules,
  salary/cost projections, and the formal menu baseline. The ownership registry
  now declares exact entry bindings and conservation invariants; the release
  aggregate fails closed on shared-model drift or frontend fact authority.
  `sc_ten_center_clean` passed module upgrade, project salary lifecycle tests,
  ACL/record-rule gates, and the full 10-center/89-page/245-contract release gate.

## 2026-08-12 — P1-VARIATION-VIEW-LOAD-ORDER-CLOSURE

- Branch / anchor: `fix/product-ten-center-runtime-closure` at `6cf86f7`.
- Formal Product Layer / Layer Target / Module: P1 / L2 native view dependency
  order / `smart_construction_core`.
- Standard vs User-Specific: construction-industry standard; no customer data,
  preference, low-code state or frontend behavior is involved.
- Reason / Boundary: the variation lineage form inherits the standard settlement
  adjustment form, so its XML must load only after the base form external ID is
  registered. The manifest now expresses that dependency directly and a static
  regression test locks the order.
- Blast Radius / validation: module installation order for the inherited
  settlement view and the accounting-center parent identity. The navigation
  baseline now creates that parent before accounting children, while the final
  primary-center overlay remains the naming/sequence authority. Acceptance
  requires the fresh-database chatter authorization ORM gate, focused
  manifest-order test, product menu release gate and protected PR checks.

## 2026-08-12 — P1-DEMO-TENANT-LIFECYCLE-AND-COVERAGE

- Branch / anchor: `feature/demo-tenant-lifecycle` from
  `af117b49615e83b64b33927c1d76a2aa7050188d`.
- Formal Product Layer / Layer Target / Module: P1 / construction product Demo
  dataset / `smart_construction_demo`; P4 / isolated reset and verification /
  `scripts/demo`, `deploy/demo-tenant`, and Make targets.
- Standard vs User-Specific: platform-owned construction Demo only. It contains
  no customer module, customer data, historical migration carrier or customer
  path, and runs in its own exact-filtered `sc_demo_*` tenant database.
- Reason / Why Here: the Demo module had drifted behind the governed BOQ, WBS,
  execution-scope, cost-plan and formal ten-center surfaces. Current product
  sample facts belong to the Demo module; destructive reset, purge, scheduling
  and evidence generation remain delivery/runtime tooling.
- Why Not Elsewhere: neither product core nor frontend may carry fake business
  records; a customer module must not be required for the product Demo; P3
  configuration is not a substitute for reproducible Demo data.
- Blast Radius / validation: 89 locked formal capabilities, 65 unique page
  models, 11 governed BOQ/WBS/cost backbone models, 390 Demo XMLIDs, scheduled
  tenant reset and CI drift guard. A fresh exact-filtered database must resolve
  all 89 entries, seed all mandatory business surfaces, classify only four safe
  empty surfaces, install zero customer modules, and leave zero pending module
  operations.

## 2026-08-12 — P4-PERSONAL-DATA-HISTORY-FALSE-POSITIVE-GOVERNANCE

- Branch / anchor: `feature/demo-tenant-lifecycle` after `66bff58`.
- Formal Product Layer / Layer Target / Module: P4 / release security
  verification / `scripts/ci`.
- Standard vs User-Specific: product release governance only. No customer data,
  tenant configuration or runtime product behavior is introduced.
- Reason / Boundary: the all-history personal-data gate found a synthetic Demo
  placeholder in an already-pushed immutable Git blob. The current source removes
  the phone-shaped placeholder, while the scanner may suppress only an exact
  rule, repository path, full blob SHA-1 and classification tuple recorded with
  an auditable reason.
- Why Not Elsewhere: rewriting published history would violate protected-branch
  workflow, and weakening the phone detector or excluding the Demo directory
  would create an uncontrolled security blind spot.
- Blast Radius / validation: one historical synthetic blob only. Registry schema
  validation rejects short blob identities and unsafe paths; an exact-match unit
  test proves that a different path remains reportable. The full all-history
  personal-data scan and PR public guard must pass without recording matched
  personal-data values.

## 2026-08-13 — P4-CLEAN-HISTORY-EXACT-FALSE-POSITIVE-CLOSURE

- Branch / anchor: `feature/demo-tenant-lifecycle` after `26658a7`.
- Formal Product Layer / Layer Target / Module: P4 / release security history
  verification / `scripts/verify/repository_clean_history_guard.py`.
- Standard vs User-Specific: generic repository security governance. The
  registered object is a synthetic product Demo fixture, not customer data.
- Reason / Boundary: the worktree/history personal-data scanner already bound
  its exception to an exact rule, path, full blob SHA-1 and classification, but
  the repository clean-history guard independently reclassified the same blob
  without consuming that registry. Both public CI gates therefore rejected the
  governed immutable object.
- Why Here / Why Not Elsewhere: the clean-history guard owns reachable-object
  admission. Rewriting published history, excluding the Demo tree or weakening
  the global detector would widen the security boundary and is forbidden.
- Blast Radius / validation: one existing registry and the RH018 classifier.
  Exact path/blob/classification matching suppresses only `PD002`; wrong paths,
  wrong blob identities and a `PD001` match in the same object remain reportable.
  Unit tests and the real `make verify.repository.clean_history` gate pass.

## 2026-08-13 — P1-DEMO-TENDER-STANDARD-DOCUMENT-NUMBER-CLOSURE

- Branch / anchor: `feature/demo-tenant-lifecycle` after `e880dd5`.
- Formal Product Layer / Layer Target / Module: P1 / construction tender
  guarantee visible-field semantics / `smart_construction_core`.
- Standard vs User-Specific: construction product standard. The visible
  document number falls back to the governed tender bid number, never to a
  customer-history compatibility field.
- Reason / Boundary: the Demo branch's guarantee fallback read
  `legacy_visible_document_no` before `tender.bid.name`, leaking historical
  compatibility semantics into the product runtime and failing the tenant
  product legacy boundary gate.
- Why Here / Why Not Elsewhere: the P1 tender model owns the standard fallback;
  Demo fixtures, frontend rendering and customer modules must not redefine it.
- Blast Radius / validation: only the computed guarantee document number when
  no payload value exists. A focused ORM test supplies a conflicting legacy
  value and requires the standard bid number; the tenant legacy boundary and
  local quick CI gates prove containment.

## 2026-08-13 — P4-HOOK-FACTS-GUARD-CURRENT-LABEL-CLOSURE

- Branch / anchor: `feature/demo-tenant-lifecycle` after `e880dd5`.
- Formal Product Layer / Layer Target / Module: P4 / static architecture
  verification / `construction_core_extension_hook_facts_split_guard.py`.
- Standard vs User-Specific: generic product CI governance.
- Reason / Boundary: the guard still required the legacy `开票申请` rename
  removed by merged PR #179, while the current P1 policy deliberately prevents
  legacy aliases from overriding locked product labels.
- Why Here / Why Not Elsewhere: the stale expectation belongs to its P4 static
  guard; restoring the removed alias in P1 runtime would reverse the product
  navigation boundary.
- Blast Radius / validation: one static assertion now locks the retained
  `开票登记` to `销项发票登记` mapping. The focused hook-facts guard and
  full local quick CI gate prove containment.

## 2026-08-13 — P4-RC20-CUSTOMER-INDEPENDENT-RELEASE

- Branch / anchor: `release/rc20-version-v2` at `e8555f4`.
- Formal Product Layer / Layer Target / Module: P4 / immutable standard-product
  release identity / `VERSION` and release tooling.
- Standard vs User-Specific: standard product release only. Customer projection
  carriers, history data and tenant-specific migrations remain in the private
  P2 package and are not consulted by the product runtime.
- Reason / Why Here: merged PR #188 already enforces product/P2 projection
  decoupling. RC20 freezes that customer-independent product state for a new
  candidate build after RC19 was superseded operationally.
- Why Not Elsewhere: no P0/P1 business mechanism changes are needed; P2 repairs
  its own historical carriers independently; P3 and frontend are unaffected.
- Blast Radius / validation: version identity, immutable candidate manifests,
  release-contract guards and candidate image build. The customer package is
  validated and versioned in its separate private repository.

## 2026-08-13 — P4-PRODUCT-PUBLICATION-CUSTOMER-DECOUPLING

- Branch / anchor: `fix/product-publication-customer-decoupling` from
  `bd5a6e6`.
- Formal Product Layer / Layer Target / Module: P4 / immutable standard-product
  publication transaction / `scripts/release/release_publication.py`.
- Standard vs User-Specific: standard product release governance only.
- Reason / Boundary: the publication preflight still required a tenant payload
  real-plan artifact, making standard-product publication depend on P2 customer
  data despite the runtime boundary already being decoupled by PR #188.
- Why Here / Why Not Elsewhere: product publication must prove its own source,
  image, scan, SBOM, remote and check identities. Customer-module repair and
  customer-data acceptance remain independent P2/P4 delivery workflows and do
  not belong in the product publication transaction.
- Blast Radius / validation: removes only the customer real-plan read from
  publication identity. Candidate readiness, artifact hashes, image identity,
  security policy, dual-remote authority, required checks and zero-write
  preflight ordering remain fail-closed and are covered by the complete
  publication and production release-contract suites.

## 2026-08-13 — P4-PRODUCTION-READONLY-CLOSEOUT-CONTRACT

- Branch / anchor: `fix/production-readonly-closeout-contract` from
  `0b37864e`.
- Formal Product Layer / Layer Target / Module: P4 / production read-only
  verification transport / `p0_base.sh` and `odoo_shell_exec.sh`.
- Standard vs User-Specific: generic product and delivery verification; no
  customer identity, preference, module or business-data rule is introduced.
- Reason / Boundary: the RC20 runtime renders its Odoo config at
  `/opt/sce-runtime/config/odoo.conf`, while the legacy shell helper fixed the
  retired `/var/lib/odoo/odoo.conf` path. The P0 probe also required physical
  parameter rows even where the product runtime deliberately supplies stable
  defaults.
- Why Here / Why Not Elsewhere: read-only verification must observe the same
  effective semantics and runtime config as the product. Writing redundant
  parameters into production or changing P2 data would mask verifier drift.
- Blast Radius / validation: production selects only the rendered config path;
  non-production keeps its prior default and explicit overrides remain
  available. P0 uses the exact defaults already declared by product views and
  seed policy while still rejecting conflicting stored values.

## 2026-08-13 — LOCAL-WORKTREE-BASELINE-CONSOLIDATION

- Branch / anchor: `fix/worktree-consolidation-v2` from stable product main
  `7ba2d73`.
- Formal Product Layer / Layer Target / Module: P4 / local workspace lifecycle /
  governed worktree cleanup tool and Make entry.
- Standard vs User-Specific: generic engineering operations; no product,
  tenant, database or production-runtime behavior is involved.
- Reason / boundary: post-release operation needs one canonical product
  directory without deleting unfinished branch history. Detach removes only a
  clean non-primary worktree at an exact SHA and proves its branch ref remains.
- Blast radius / validation: local linked-worktree metadata and directories.
  Tests cover unmerged and release branch retention, dirty refusal, SHA drift,
  confirmation failure, and primary-worktree protection.
# Frontend acceptance managed-runtime profile closeout (2026-08-13)

- Branch / SHA: `fix/frontend-acceptance-profile-closeout-v1` / `9e2d2cb`.
- Formal Product Layer: P4 ops delivery tool.
- Layer Target: managed acceptance profile resolution, Make entrypoints, and
  fail-closed topology preflight.
- Module: `config/frontend`, `make`, `scripts/dev`, `scripts/common`, and P4
  verification/runbook assets.
- Reason: the former entrypoints locked the frontend database and ports but
  still inherited Compose project, volume, filter, and credentials from an
  arbitrary `.env.dev`, allowing an acceptance operation to attach development
  volumes before Odoo started.
- Boundary: no P0/P1/P2/P3 product semantics, model, action, view, permission,
  frontend renderer, customer data, or production policy change.
- Database identity: isolated `sc_frontend_acceptance`, exact filter
  `^sc_frontend_acceptance$`, fixture allowed, customer business data forbidden,
  and filestore locked to `sc_fe_r2_p1_01_odoo`.
- Validation: resolver unit tests cover complete identity plus database-filter,
  shared-volume, frontend-port, and unmanaged-profile rejection; shell
  regression proves explicit topology overrides survive base environment
  loading; live preflight proves DB/Redis/Odoo volume identity; managed backend
  and frontend entries pass on ports 18082/5175 with the database lock. The
  first governed upgrade exposed a separate historical product-baseline
  migration gap; that repair is isolated in the P1 baseline-recovery topic and
  is not implemented in this P4 environment layer.
- Independent gate correction: a healthy response alone no longer permits
  backend reuse. Reuse and health now require the current worktree source mount,
  exact source SHA, database/filter/list policy, host port and filestore volume.
  Frontend health requires its governed PID, worktree and locked database/proxy
  environment. PostgreSQL credentials must match the credential authority.

# Product baseline 17.0.0.75 upgrade recovery (2026-08-13)

- Branch / base SHA: `fix/product-baseline-upgrade-075-current-v1` /
  `9e2d2cb2e57d0465734cbc5900857a935fb88c51`.
- Formal Product Layer: P1 product-baseline migration.
- Layer Target: historical metadata compatibility for an in-place
  `smart_construction_core` upgrade from `17.0.0.75`.
- Boundary: no payment-request capability, frontend component, environment
  topology, customer data, action, menu, permission, or model-field change.
- Repair: retire the removed `view_p1_daily_business_visible_*` inherited-view
  namespace by XML ID before registry validation; archive invalid historical
  runtime contracts without invoking the current payload validator.
- Runtime evidence: governed `sc_frontend_acceptance` upgraded to
  `smart_core=17.0.1.1.9` and `smart_construction_core=17.0.0.130`; retired XML
  IDs, stale view `1976`, and null `ir_model_inherit.parent_id` rows are all
  zero. The focused runtime-contract migration test completed with
  `0 failed / 0 errors`.

## 2026-08-14 — P0-RELATION-READ-CLOSURE

- Branch / anchor: `fix/p0-relation-read-closure-v1` from `d7ae51b`.
- Formal Product Layer / Layer Target / Module: P0 platform kernel / generic
  relation-access projection and frontend runtime / `smart_core`, the contract
  form relation runtime, and its verification entry.
- Standard vs User-Specific: platform-wide access enforcement only; no
  construction-industry, customer, low-code, or environment semantics.
- Reason / Boundary: the existing runtime already fails closed before relation
  query and record-fetch I/O, but the static guard still required an obsolete
  inline implementation shape and omitted the shared runtime. The guard now
  follows the actual responsibility boundary and a bundled behavior test proves
  both denied paths issue zero requests while an allowed fetch remains usable.
- Why Here / Why Not Elsewhere: `relation_entry.can_read` is a backend-owned
  permission fact consumed by the generic frontend runtime. It must not be
  inferred by P1 business code, page-specific rendering, customer config, or
  P4 environment tooling.
- Blast Radius / validation: only the generic relation-read verification path
  and its Make target change. The focused query/fetch behavior test, static
  closure guard, strict typecheck, static build, and complete frontend quick
  gate pass; no database, container, service, or acceptance fixture is touched.

## 2026-08-14 — P4-CI-CREDENTIAL-ENTRY

- Branch / anchor: `fix/p4-ci-credential-entry-v1` from `d7ae51b`.
- Formal Product Layer / Layer Target / Module: P4 ops delivery / isolated
  GitHub frontend-release credential and operation routing / workflow, Make
  acceptance entries, and CI identity validator.
- Standard vs User-Specific: generic release validation only; no customer,
  construction-business, authentication, page, or product-model semantics.
- Reason / Boundary: the workflow generates a run-scoped test credential file,
  but the shared acceptance runtime required the local primary-worktree
  `.env.dev` profile before it could create the isolated CI resources. The CI
  route now treats the generated file as inert data, validates every allowed
  key and the checkout/project/database/volume identity, and only then permits
  the first Compose operation. Local acceptance continues through the existing
  managed profile without rebuilding or changing its topology.
- Database identity: role is an isolated internal acceptance tenant; tenant and
  environment identity are the GitHub run-scoped `sc-fe-release-<run_id>`;
  database is exactly `sc_frontend_acceptance`, filter is
  `^sc_frontend_acceptance$`, fixture is allowed, customer business data is
  forbidden, and DB/Redis/filestore volumes are three exact run-scoped names.
- Blast Radius / validation: only the frontend release CI lane and the thin
  local/CI routing boundary change. Tests cover exact identity, duplicate or
  executable env content, SHA/project/volume drift, route overrides, Make
  pre-parse zero side effects, and invalid-operation zero side effects. The
  final authority is a full release workflow on the frozen candidate SHA.

# P0 form and action assembler closeout (2026-08-14)

- Branch / base SHA: `fix/p0-form-action-assembler-v2` /
  `319a7d2f31f734b41ea45a04b383a7dc0f2ff4c0`.
- Formal Product Layer / Layer Target / Module: P0 platform kernel / normalized
  page and action assembly / `smart_core`.
- Standard vs User-Specific: generic contract mechanism only; no construction,
  payment, customer, role-specific presentation, or runtime configuration is
  introduced.
- Reason / boundary: a published `entry_semantic_surface` must remain the only
  primary form structure across repeated composition, while native modifiers,
  relations, notebook capabilities and chatter remain subordinate. Actions are
  canonicalized by stable backend identity only after every source is retained;
  constraints merge fail-closed and product presentation has explicit priority.
- Why Here / Why Not Elsewhere: source arbitration and canonical identity are
  platform assembly responsibilities. Industry modules, payment-specific pages,
  frontend inference and P4 runtime tooling must not duplicate these rules.
- Blast radius / validation: all normalized form/action consumers. Pure-Python
  tests cover semantic-plus-template precedence, native fallback, notebook and
  relation preservation, object/server/window/URL identity, permission denial,
  presentation priority and three generic Odoo page samples loaded from the
  repository native XML fixtures through the existing Tree/Form parser. Exact
  new-baseline static, runtime and Full Release gates remain required.

# P0 authentication credential framework (2026-08-14)

- Branch / base SHA: `fix/p0-auth-credential-framework-v1` /
  `c61b6c4363b9b0c2d6580773898625f1b7d25057`.
- Formal Product Layer / Layer Target / Module: P0 / authentication and
  principal orchestration / `smart_core` plus the generic account integration
  surface.
- Standard vs User-Specific: standard platform capability only; no customer,
  construction-domain or business-document behavior is introduced.
- Reason / Boundary: password-only JWT issuance could not represent long-lived
  machine integrations without implicitly treating an API key as a password.
  This topic keeps `res.users` and Odoo `res.users.apikeys` authoritative,
  adds only policy/audit projections, and makes `password` and `api_key`
  explicit non-fallback credential types. P4 may inject and redact credentials
  but does not implement authentication; P1/PFL consume only the resulting
  principal and existing permission decisions.
- Security contract: machine keys exchange for 15-minute scoped JWTs; company
  and scope may only narrow the user's existing authority; native key removal
  plus credential epoch revokes existing tokens; raw keys and key hashes are
  absent from policy, audit, logs and evidence; JWT signing has no default and
  rejects secrets shorter than 32 bytes.
- Validation scope: native one-time key creation, HTTP create/list/rotate/revoke,
  explicit password and API-key paths, wrong/revoked/expired keys, inactive
  users, database and company boundaries, scope non-expansion, rate limiting,
  audit projection, immediate token invalidation, and denial of credential
  management from machine sessions. The post-review suite additionally covers
  all registered handler machine metadata, `chatter.post`, `global.message.send`,
  `global.message.read`, dynamic `api.data` operations, duplicate native indexes,
  concurrent creation, expiry projection and single-event expiry audit. The
  current focused suite completes `27 tests / 0 failed / 0 errors`; password
  compatibility completed `4 tests / 0 failed / 0 errors`, and evidence-bundle
  tests completed `10 tests / 0 failed / 0 errors`. These results must be rerun
  on the exact frozen candidate SHA before publication.

# Baseline-backed iteration execution lock (2026-08-15)

- Branch / base SHA: `fix/baseline-iteration-rules-v1` /
  `9524263a4fd3b03bb8855d527e81941d3dc82dd1`.
- Formal Product Layer / Layer Target / Module: P4 repository governance /
  baseline-backed iteration execution policy / root instructions, ops rules,
  CI governance guard and tests.
- Standard vs User-Specific: repository-wide engineering governance. No P0
  platform behavior, P1 construction semantics, P2 user preference, database,
  fixture, runtime profile or frontend product behavior changes.
- Reason / boundary: the repository already owns governed worktree, test,
  incremental upgrade, acceptance profile, fixture, release snapshot, evidence
  and PR publication tools. Business topics must inventory and consume those
  authorities instead of assembling credentials or deriving projects,
  databases, networks, ports or volumes.
- Locked sequence: inventory -> exact baseline/worktree -> layer and scope ->
  complete tracked+staged+untracked fingerprint -> Quick -> non-zero Targeted
  tests -> governed incremental upgrade -> fixture -> release snapshot ->
  governed runtime -> user journey -> independent review -> generated reports
  -> `make pr.push`.
- Failure contract: `0 tests` is failure; identity-domain mixing is failure;
  full browser reruns are blocked while an earlier static/backend/identity/
  normalized-contract gate remains red. Shared acceptance writes are serial,
  and each report/review must bind one frozen full fingerprint.
- Validation: the new policy guard checks one canonical policy marker across
  the three authority documents, locks the required rule fragments and proves
  the eight existing Make authorities remain declared. Its behavior suite
  covers complete policy, missing locked rule and missing Make target.

# P0 readonly route profile propagation (2026-08-15)

- Branch / base SHA: `fix/p0-readonly-route-profile-v1` /
  `da1b02d99915174733bc36aa3934d609fcf3af7b`.
- Formal Product Layer / Layer Target / Module: P0 platform frontend / shared
  contract-form route profile resolution / generic web contract consumer.
- Standard vs User-Specific: generic platform behavior only; no payment,
  construction, customer, fixture, environment or database rule is added.
- Reason / boundary: `/r/:model/:id` rendered as readonly only after its
  action contract had already been requested with the edit profile. A shared
  route/profile resolver now drives both the initial action-contract request,
  its model fallback and the final renderer. `/r` resolves readonly,
  existing `/f` resolves edit and new `/f` resolves create.
- Why Here / Why Not Elsewhere: route mode is frontend platform context. P1
  field matrices and product contracts remain authoritative inputs and the P0
  normalized assembler remains unchanged; no industry-field exception is
  introduced.
- Blast radius / validation: all generic contract-form routes. The existing
  readonly coverage unit now checks the three routes, contract-profile
  precedence and both request call sites. Frontend Quick, strict typecheck,
  static build and release-unit collections pass before runtime verification.

# P0 create default hydration closure (2026-08-15)

- Branch / base SHA: `fix/p0-create-default-hydration-v1` /
  `55c950d84ed1d0fb3f9d228b22448ddb3a3823a1`.
- Formal Product Layer / Layer Target / Module: P0 platform frontend / generic
  contract-form create initialization / `frontend/apps/web`.
- Standard vs User-Specific: platform mechanism only. No payment, construction,
  customer, fixture, database, credential or environment rule is introduced.
- Reason / boundary: a create route could carry complete `default_*` identities
  while relation labels remained dependent on later asynchronous reads, and
  changes to most defaults were absent from the retained route identity. The
  shared create hydration plan now fills only empty contract values, binds
  labels to the exact route-supplied identity and fingerprints every create
  default. Explicit contract values remain authoritative; edit and readonly
  records never consume create defaults.
- Blast radius / validation: all generic create forms. A generic `x.document`
  behavior suite covers explicit contract precedence, multiple relation
  defaults, context fallback, immediate labels, deterministic route identity,
  changed-default invalidation and create/edit/readonly separation. It is wired
  into both Frontend Quick and release-unit collections.

# P0 api.data operation-context authority (2026-08-15)

- Branch / base SHA: `fix/p0-api-data-operation-context-v1` /
  `9ac2aa15181579f8a69c321912ef9647f4b44b21`.
- Formal Product Layer / Layer Target / Module: P0 platform kernel / generic
  `api.data` request-context composition / `smart_core`.
- Standard vs User-Specific: platform mechanism only. No construction,
  payment, customer, fixture, credential or environment semantics are added.
- Reason / boundary: the intent envelope may carry current-record context while
  an operation such as `default_get` carries more specific `default_*` values.
  The generic handler previously flattened both carriers and allowed the
  envelope context to replace the operation context. The operation params are
  now the final authority while authenticated Odoo context and envelope context
  remain inherited defaults.
- Why Here / Why Not Elsewhere: request-context precedence belongs to the P0
  ORM proxy. P1 must not duplicate source facts, and the frontend continues to
  send both contexts without model-specific merging rules.
- Blast radius / validation: all `api.data` operations that consume context.
  Generic unit coverage includes the real dispatcher payload shape and
  conflicting envelope/operation defaults. A governed acceptance HTTP probe
  proves `default_get` receives the operation value under a conflicting
  envelope without exposing credentials.

# P0 create attachment presentation closure (2026-08-15)

- Branch / base SHA: `fix/p0-create-attachment-render-v1` /
  `f8d1db0afcf4bd1a9e3a7afacbea811ba34eaffa`.
- Formal Product Layer / Layer Target / Module: P0 platform frontend / generic
  contract-form collaboration presentation / `frontend/apps/web`.
- Standard vs User-Specific: platform mechanism only. No payment, construction,
  customer, fixture, database, credential or environment semantics are added.
- Reason / boundary: intake create mode hid the complete collaboration panel,
  even when the normalized contract declared attachment capability and the
  attachment runtime supported pending uploads before the first save. The
  shared presentation rule now keeps pending attachment upload available while
  record-bound chatter alone remains hidden until a record exists.
- Why Here / Why Not Elsewhere: create-mode rendering of normalized attachment
  capability belongs to the shared contract-form frontend. P1 continues to
  declare whether attachments exist and does not receive a model-specific UI
  exception.
- Blast radius / validation: generic create/edit/readonly forms with native
  collaboration contracts. The behavior test covers saved records, intake
  attachment upload, record-bound chatter suppression and empty contracts; it
  is wired into Frontend Quick and release-unit collections. Strict typecheck,
  static build and the complete frontend release-unit collection pass.

# P0 cross-model action context authority (2026-08-15)

- Branch / base SHA: `fix/p0-cross-model-action-context-v1` /
  `a5888014a2e395f2679f886c7e16946d4898cc96`.
- Formal Product Layer / Layer Target / Module: P0 platform frontend / generic
  action-response navigation / `frontend/apps/web`.
- Standard vs User-Specific: platform mechanism only. No payment,
  construction, customer, fixture, database, credential or environment
  semantics are introduced.
- Reason / boundary: action responses could carry an authoritative target
  model, Action and context while the frontend retained the source page's
  business-category, menu and list query. The source values could therefore
  override the backend target and make a professional target form render with
  the source form's title and context. Cross-model navigation now clears all
  source-scoped contract state, preserves only shell diagnostics, and gives
  the explicit backend target query final authority. Same-model navigation
  retains its current context and an unknown target remains conservative.
- Why Here / Why Not Elsewhere: navigation inheritance is shared frontend
  contract behavior. P1 remains responsible for producing the target action
  and product contract; no model name, payment label or URL keyword is used.
- Blast radius / validation: ContractForm and ActionView action responses now
  share the same boundary rule. Generic `x.source` to `x.target` tests cover
  target model/action/menu/context fidelity, stale business/list reset,
  same-model preservation, missing-model behavior, explicit target-query
  precedence and the real form-navigation runtime. Strict typecheck, static
  build and the complete frontend release-unit collection pass locally.

# P0 action-result title authority (2026-08-15)

- Branch / base SHA: `fix/p0-action-result-title-authority-v1` /
  `7b1fe48151ee19adc72d8062d77c98b5e863e5a7`.
- Formal Product Layer / Layer Target / Module: P0 platform / normalized action
  continuation presentation / `smart_core` and the generic contract frontend.
- Reason / boundary: a transient Odoo action could authoritatively override its
  target title, but normalization discarded that title while retaining only
  action/model/view references. The target create page therefore fell back to
  a business-category label even though the backend returned a professional
  continuation title.
- Why Here / Why Not Elsewhere: action-result presentation is a shared target
  contract fact. No payment, construction, customer, fixture, database or
  environment special case is introduced.
- Blast radius / validation: generic cross-model and same-model action
  continuations. Backend normalization, route projection and final create-page
  identity tests prove the transient title survives end to end while stale
  source query state remains excluded.

# P0 semantic group reparenting authority (2026-08-15)

- Branch / base SHA: `fix/p0-semantic-group-reparent-v1` /
  `da09ae2dc39f6fdd030ef9c889ffd09c3ecaf7d4`.
- Formal Product Layer / Layer Target / Module: P0 platform / generic final
  form-group projection / `smart_core`.
- Reason / boundary: when a published semantic entry surface used the same
  section title as a group nested in a legacy/category sheet, the generic
  projector moved fields into that nested group and then discarded the legacy
  sheet. The final normalized contract consequently lost the entire semantic
  section and its fields. Under semantic authority, matching groups are now
  reusable only at the authoritative top level; repeated projection remains
  idempotent.
- Why Here / Why Not Elsewhere: the P1 product contract, business policy,
  native view and normalized field status all contained the missing facts.
  Their loss occurred only in the shared P0 reparenting algorithm. No payment,
  construction, frontend, fixture, database, credential or environment
  special case is introduced.
- Blast radius / validation: all semantic entry surfaces whose section titles
  collide with nested legacy groups. A generic `demo.payment` regression
  proves same-named receipt/payment groups survive as top-level semantic
  sections, their fields remain attached, the discarded legacy sheet does not
  survive, and a second projection is byte-for-byte idempotent. The complete
  standalone UI-contract boundary collection passes 70/70.

# P1 payment work-summary performance closure (2026-08-16)

- Branch / base SHA: `fix/p1-work-summary-performance-v1` /
  `6f6aaa90b65caed16df6577993ecdb2d28319a41` (after the P0 semantic-group
  prerequisite entered `main`).
- Formal Product Layer / Layer Target / Module: P1 construction-industry
  standard product / payment-request work-item and work-summary read path /
  `smart_construction_core`.
- Standard vs User-Specific: standard payment-workflow performance only. No
  customer exception, P0 contract behavior, frontend presentation, runtime
  profile or environment topology is changed.
- Reason / boundary: the product work-item projection recalculated the same
  action advisories, active project funding baseline and reserved-payment sum
  for every request, while the outer work summary loaded the same project
  execution items twice. The implementation now reuses request-local shared
  funding facts and projection results; record-specific amount, state,
  permission and final business verdicts remain authoritative and are still
  evaluated per request.
- Why Here / Why Not Elsewhere: these queries implement existing P1 payment
  funding and work-item rules. They are not generic P0 normalized-contract
  behavior, a frontend concern, or P4 runtime configuration.
- Blast radius / validation: `my.work.summary` and
  `payment.request.available_actions` only. Governed `sc_test` targeted tests
  report 36 tests with `0 failed / 0 errors` (42 test-stat entries, including
  three pre-existing audit-model skips). With 80 synthetic payment requests,
  the product workspace retains 80 todo plus 80 initiated items while cold
  execution improves from 208 to 50 SQL queries and about 198 ms to 78.5 ms;
  the outer summary improves from 407 to 111 SQL queries and about 356 ms to
  125.4 ms. A real `/api/v1/intent` probe with a disposable finance-manager
  identity returns the 80 visible todo items in 276–298 ms after the first
  352 ms request. The probe identity and its randomly generated credential are
  removed immediately after measurement.
- Rebase verification: on exact base `6f6aaa90`, the governed targeted
  collection again reports 42 test-stat entries / 36 executed tests with
  `0 failed / 0 errors`; `make test.unit`, generated-report guard and
  `git diff --check` pass. The same 80-record cold probe remains at 50 SQL
  queries / 90.49 ms for the product workspace and 111 SQL queries / 154.26 ms
  for the complete work summary, with the same 160-item result.
- External local-gate note: the all-history personal-data scanner walks
  `git rev-list --all`, so this shared multi-worktree repository also exposes
  unrelated local PFL checkpoint blobs to `ci.local.quick`. The clean
  `6f6aaa90` tree reproduces the same unrelated historical fixture findings;
  no false-positive exemption or scanner change is carried by this P1 topic.

# P0 nested permission-rights status authority (2026-08-16)

- Branch / base SHA: `fix/p0-permission-status-nested-rights-v1` /
  `f971e3aa88ff6c0e3d3e915ca39aaef22f7ae030`.
- Formal Product Layer / Layer Target / Module: P0 platform / normalized
  global permission-status projection / `smart_core`.
- Standard vs User-Specific: generic permission-envelope consumption for all
  models. No construction, payment, customer, fixture, database or runtime
  profile semantics are introduced.
- Reason / boundary: the authoritative runtime shape is
  `permissions.effective.rights`, but two normalized status paths treated the
  enclosing `effective` object as the rights map. Editable fields could
  consequently carry `auth=edit` while the same page was downgraded to
  `pageAuth=read`.
- Why Here / Why Not Elsewhere: permission envelope normalization is shared P0
  contract behavior. P1 must not duplicate permission decisions and the
  frontend must not override a contradictory backend contract.
- Blast radius / validation: V2 global page authorization for every model.
  Generic nested edit, read-only and all-denied fixtures prove canonical
  extraction, page/field consistency and fail-closed behavior; existing flat
  head-permission and readonly-profile behavior remain covered.

# P0 final modifier dependency hydration (2026-08-16)

- Branch / base SHA: `fix/p0-final-modifier-dependency-hydration-v1` /
  `1e4b87099653e93053fd6eb1359908869382b6c5`.
- Formal Product Layer / Layer Target / Module: P0 platform / final normalized
  modifier dependency hydration / `smart_core`.
- Standard vs User-Specific: generic form-contract correctness for all models.
  No construction, payment, customer, frontend, fixture, database or runtime
  profile semantics are introduced.
- Reason / boundary: the initial form snapshot used an unqualified 80-field
  payload budget before extension hooks and final runtime action projection.
  A late normalized action could therefore reference a valid scalar field
  absent from `dataContract.mainData`, causing the faithful frontend modifier
  evaluator to hide an otherwise valid action. The 80-field budget now has an
  explicit name and remains limited to opportunistic display hydration; fields
  referenced by the final normalized modifier graph form a separate required
  dependency closure.
- Why Here / Why Not Elsewhere: dependency collection and record hydration are
  shared P0 contract mechanics. P1 remains the business-action authority and
  the frontend continues to render the normalized modifier without fallback or
  model-specific inference.
- Blast radius / validation: existing-record form contracts only. The helper
  reads only missing, known scalar dependencies through the current-user model
  environment after runtime actions are projected and before trim/seal. It
  performs no read when no dependency is missing, excludes relation and large
  payload fields, and keeps missing values fail-closed on read denial. Direct
  behavior collections pass 74/74 handler and 12/12 PageAssembler tests;
  `make test.unit`, UPC architecture guards, responsibility/boundary guards,
  generated-report guard and `git diff --check` pass. `ci.local.quick` remains
  externally blocked by pre-existing all-history P1 synthetic bank-account
  findings; this P0 topic does not add or broaden a personal-data exemption.

# P0 renderer-neutral scene component driver lab (2026-08-16)

- Branch / base SHA: `codex/p0-ui5-scene-foundation-spike-v1` /
  `1e5eed0470cfb03a3fd17bfe16e624ab418b137e`.
- Formal Product Layer / Layer Target / Module: P0 platform / renderer-neutral
  scene component drivers / `frontend/packages/ui` and the isolated
  `frontend/apps/scene-ui5-spike` validation app.
- Standard vs User-Specific: generic platform mechanism only. The payment
  scene is a static representative fixture; no payment model, permission,
  backend, database, runtime profile or customer exception is introduced.
- Reason / boundary: a scene contract must remain authoritative while the
  component engine is replaceable. The lab places native controls, TDesign
  Vue Next and SAP UI5 Web Components behind one lazy driver registry and one
  provider. Scene components consume a generic component model and semantic
  primitive ports instead of vendor imports or an `isUi5` branch.
- Why Here / Why Not Elsewhere: driver loading, component identity, density
  and preference are shared frontend platform concerns. Business facts and
  draft values stay above the provider; P1 does not know which renderer is
  active and the backend contract is unchanged.
- Blast radius / validation: isolated UI package/app, one exact TDesign
  dependency, static guard, browser probe and Make validation target only.
  `make verify.frontend.scene_component_drivers` proves one contract across
  all three drivers, desktop and 390px layouts, zero horizontal overflow,
  no chapter navigation, no business network writes, lazy vendor loading,
  user preference persistence and preservation of unsaved field state across
  driver replacement. The production frontend renderer remains untouched.
- Follow-up capability closure: the common contract and all three drivers now
  include contract-driven risk notices, two relation-detail tables and a
  submit-review overlay. Editable values and overlay-open state are both owned
  above the replaceable provider, so the browser probe proves continuity while
  switching an open UI5 dialog to a TDesign drawer. Invalid preview or stored
  driver identifiers fail closed through a generic organization/user
  preference policy resolver. The formal boundary, loading budget and
  production-entry criteria are frozen in
  `docs/architecture/scene_component_driver_foundation_v1.md`.
- Loading resilience follow-up: the provider now distinguishes requested and
  resolved drivers, exposes a visible fallback fact and returns to the native
  safe driver when an optional driver loader fails. The browser injects a UI5
  load failure and proves the page remains usable without network or console
  errors. TDesign heavy primitives and UI5 alert/table/dialog registration are
  split behind async primitive boundaries; a request-quiescence gate prevents
  route/driver changes from aborting late supplier dependencies.
- Scene coverage follow-up: the renderer-neutral contract now has isolated
  collection and hierarchy surfaces in addition to the object page. Native,
  TDesign and UI5 render all three scene categories; collection selection and
  hierarchy expansion remain above the provider and survive driver switches.
  The 390 collection profile uses contract-backed cards rather than horizontal
  page overflow. Preference resolution now exposes the authority source and
  proves organization lock, user override, organization default, system
  default and safe fallback without leaking driver identifiers into a
  business contract.
- Accessibility and token follow-up: the provider now maps a vendor-neutral
  semantic token profile independently from the selected component driver.
  Enterprise-neutral, business-soft and accessible-contrast profiles change
  visual semantics without rebuilding business state. Browser gates verify a
  persisted high-contrast preference, at least 7:1 text/surface contrast,
  visible keyboard focus, unique ids, accessible names, Space/Enter collection
  selection and keyboard hierarchy collapse across driver replacement.
- Normalized collection pilot follow-up: an explicit P0 adapter now maps a
  frozen, non-payment company-directory `Unified Page Contract V2` snapshot
  into the renderer-neutral collection surface. The adapter rejects missing
  read-only authority, source authority, widget declarations or exact columns;
  it also rejects enabled selection and non-empty actions instead of inferring
  `name`, `document` or `status`. A build feature plus preview switch keeps the pilot reversible;
  it does not touch the production frontend, backend, database or fixture.
