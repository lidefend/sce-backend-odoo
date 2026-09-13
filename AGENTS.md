# Agent Instructions

## Codex Execution Policy
- Canonical allowed write branches: `feature/*`, `fix/*`, `refactor/*`, `audit/*`, `release/*`, `codex/*`.
- `CANONICAL_ALLOWED_WRITE_BRANCH_REGEX=^(feature|fix|refactor|audit|release|codex)/.+`
- Always follow `docs/ops/codex_execution_allowlist.md` for all execution and validation steps.
- If a requested action falls outside the allowlist, stop and ask for confirmation before proceeding.
- Always follow `docs/ops/codex_workspace_execution_rules.md` before any write action.
- Mandatory preflight before edits: `pwd` + `git rev-parse --show-toplevel` + `git branch --show-current` + `git status --short`.

## Baseline Iteration Phase (Hard Lock)
`BASELINE_ITERATION_EXECUTION_POLICY=v1`
- This repository is in baseline-backed iteration. Before any mutation, inventory and reuse the registered worktree, Make targets, runtime profile, database, ports, volumes, fixtures, and evidence tools described in `docs/ops/codex_workspace_execution_rules.md`.
- Business topics must consume existing governed infrastructure. They must not derive or create a Compose project, database, port, volume, credential file, fixture system, runtime profile, or test entry. A missing capability is a separately authorized P4 governance task, not an in-topic workaround.
- Required order: governed worktree and exact baseline -> layer/scope declaration -> complete tracked+untracked fingerprint -> lightweight static guards -> risk-selected non-zero targeted tests -> governed incremental module upgrade -> fixture reset -> release snapshot -> governed runtime -> user journey -> delivery documentation and generated-evidence preparation -> freeze clean HEAD -> one exact-head Quick -> independent review -> `make pr.push`.
- A validation command that reports zero tests is a failure. A command executed with an unregistered project/database/profile or manually assembled credentials is diagnostic only and cannot satisfy a gate.
- Synthetic test data may be exempted from personal-data scanning only through the governed false-positive registry, bound to the exact rule, repository path, full immutable Git blob SHA, classification, and a synthetic-fixture reason. Never exempt a directory, wildcard, mutable branch, or all test data.
- One candidate worktree has one writer. Every parallel read-only review and runtime report must bind the same frozen full fingerprint. Shared acceptance database mutations are serialized.
- Worktrees are organized by one independently acceptable product result (PFL), not by P0/P1 responsibility labels. P0/P1 determine code ownership, commit boundaries, review and rollback order; they do not automatically require separate worktrees, branches, PRs or runtime environments.
- Split a worktree only when the proposed topic can deliver independent value, can be accepted without another topic, does not modify the same files, does not contend for the same runtime, and can be rolled back independently. All five conditions are mandatory.
- At most two active worktrees are allowed: one product-delivery worktree and one genuinely independent platform/environment worktree. Before creating a third, finish, freeze or governably clean up an existing worktree.
- Do not rerun full browser acceptance while an earlier static, backend, identity, or normalized-contract gate is known to fail. Fix only the owning layer, refreeze, then resume from the earliest invalidated gate.

### Layered Validation Efficiency (Hard Lock)
- Before running validation, declare the changed paths, affected product layers, risk class, the earliest required validation layer, and explicit reasons for every skipped layer. Validation layers are fixed: L0 identity/fingerprint; L1 syntax, static, architecture, schema, and focused pure tests; L2 non-zero targeted module/contract/frontend tests; L3 governed module upgrade and runtime smoke; L4 frozen-candidate fixture, snapshot, build, and affected browser journeys; L5 independent review, generated reports, full delivery/release gates, and exact-head publication.
- A required earlier layer in `failed`, `not_run`, stale, or identity-mismatched state blocks every later layer. Never run a broad gate to discover a defect that a cheaper owning-layer check can determine.
- A passing result may be reused directly while its full candidate fingerprint is unchanged. After a mutation, an unchanged upstream result may be carried forward only through recorded deterministic impact analysis proving that its command inputs, governed environment identity, and relevant file set are unchanged; bind both the source and current full fingerprints. Do not rerun unchanged passing layers for reassurance.
- A mutation invalidates its earliest affected layer and every downstream result, but not unchanged upstream results. Refreeze the full fingerprint and resume from the earliest invalidated layer.
- Do not retry an unchanged failure. Retry only after the owning product/tool input changed or the exact environment prerequisite was proven recovered; record the failure classification and changed recovery fact first.
- Browser matrices, fixture resets, release snapshots, and full release gates are frozen-candidate activities, not inner-loop debugging tools. During iteration, browser checks cover only declared affected surfaces; the full required matrix runs once at the frozen delivery head.
- The default inner-loop static entry is `make ci.local.iteration`, which prints but does not execute mapped frontend L2 recommendations, followed by the risk-selected affected non-zero L2 target or targets and, only when needed, focused `local.dev.*` runtime checks. Test count follows the declared risk and is never mechanically fixed to one. This L1 entry is not delivery evidence. Run `make ci.delivery.freeze.prepare` before the final commit so generated evidence is reviewed before the clean HEAD is frozen. `make ci.local.quick` is reserved for a clean frozen delivery HEAD and must not be used after every edit or local commit; for this flow it runs once after the final commit.
- Every validation result records layer, exact command/entrypoint, current candidate fingerprint, any carried-forward source fingerprint, status (`passed`/`failed`/`not_run`), non-zero test count when applicable, failure owner, and next earliest valid step. Exit code zero alone is not proof of a passed gate.

### Local development lifecycle (Hard Lock)
- Local feature iteration uses only `make local.dev.*`: project `sc-local-dev`, database `sc_dev_demo`, and fixed `sc_local_dev_*` volumes. It is the persistent demo-backed feature database.
- Daily-data compatibility uses only `make local.sample.*`: project `sc-local-sample`, database `sc_dev_sample`, and fixed `sc_local_sample_*` volumes. It is technical sample data and is not feature/demo authority.
- Clean installation uses only `make local.clean.*`: project `sc-local-clean`, database `sc_clean`, and fixed `sc_local_clean_*` volumes. It is disposable and contains no demo/fixture authority.
- Never assemble local Compose, database, dbfilter, port, volume, or credential commands by hand. Never use one profile's env file or volumes with another profile. Preserve/refresh/discard/rebuild only through their exact governed Make targets and confirmations.

## Database Architecture Governance
- `docs/governance/database_architecture_policy.md` is the single authoritative database architecture policy.
- Before any task involving database creation, copy, upgrade, migration, destruction, module lifecycle, tenant provisioning, users or multi-company design, fixture or acceptance environments, filestore/session/backup/restore, or cross-tenant interfaces and analytics, read and apply that policy.
- Every database-writing task must resolve the target database role, tenant, environment, exact database filter, and filestore identity before any write. An unresolved role or a policy violation is a fail-closed stop.
- UM-P1 and all later user-module productization tasks inherit this policy. UM-P2 installation rehearsal must use a newly created isolated customer-tenant rehearsal database.

## Architecture Guard
- Always follow `ARCHITECTURE_GUARD.md` and `docs/architecture/ai_development_guard.md` before making code changes.
- For frontend page work, always follow `docs/architecture/native_view_reuse_frontend_spec_v1.md`.
- For product/module boundary decisions, always follow `docs/product/formal_product_boundary_v1.md` and then map the decision to `docs/architecture/backend_contract_boundaries.md`.
- For every implementation task, explicitly identify `Formal Product Layer`, `Layer Target`, `Module`, and `Reason` before coding.
- Boundary decision is mandatory before every iterative change that touches contracts, forms, menus, frontend rendering, runtime configuration, data repair, or business semantics. Before editing, answer:
  - `Formal Product Layer`: P0 platform kernel product, P1 construction industry standard product, P2 specific user product, P3 low-code configuration product, or P4 ops delivery tool.
  - `Layer Target`: concrete module/mechanism target, such as `smart_core`, `smart_construction_core`, `smart_construction_custom`, low-code runtime configuration, ops repair/replay, or frontend renderer.
  - `Standard vs User-Specific`: whether the rule belongs to the platform mechanism, construction product standard, confirmed customer baseline, administrator runtime configuration, or one-off ops repair.
  - `Why Here`: why the chosen layer owns the rule.
  - `Why Not Elsewhere`: why the rule must not be placed in another P0-P4 product layer, frontend, runtime config, or module as applicable.
  - `Blast Radius`: expected affected menus/models/contracts and what validation will prove containment.
- Platform core must not receive industry or customer-specific business semantics. Put construction-industry defaults in `smart_construction_core`; put stable customer-specific differences in `smart_construction_custom` or a dedicated customer module; keep temporary administrator changes in low-code runtime configuration; use migration scripts only for repair/replay/verification. Keep frontend changes limited to generic contract rendering behavior.
- Ownership rules for configuration and orchestration:
  - `smart_core` owns platform mechanisms only: contract models, versioning, publishing, rollback, low-code handlers, orchestration merge behavior, and generic frontend contract consumption. It must not encode construction-industry semantics or customer preferences.
  - `smart_construction_core` owns construction-industry standard defaults: models, menus, actions, native XML baselines, standard business fields, standard search/list/form behavior, and semantics that every standard construction deployment should inherit.
  - `smart_construction_custom` owns stable customer/user preferences and delivery configuration: customer-specific form layouts, field order, labels, visibility, role/company defaults, confirmed low-code results, and confirmed user data baselines that must survive rebuilds and upgrades.
  - User product changes must separate function/preference from data baseline. Stable customer preferences and stable customer data can both belong to P2, but they need separate carriers, replay paths, and validation evidence. One-off data repair remains P4 until it is customer-confirmed as a long-term data baseline.
  - Low-code configuration is an editing surface and runtime carrier, not the final architectural owner. If a low-code change becomes a confirmed standard, move it to the industry module; if it becomes a confirmed customer preference, move it to the custom module; if it is experimental, it may remain runtime data.
  - Ops scripts are for migration, repair, replay, and verification. They must not be the long-term source of truth for platform behavior, industry defaults, or customer preferences.

## AI Engineering Context

This repository maintains AI engineering context under `.agent/`.

Before making changes:

1. Read `.agent/context.yaml`
2. Identify related goals under `.agent/goals/`
3. Check related decisions under `.agent/decisions/`

When executing work:

- Follow existing contracts.
- Preserve recorded architecture decisions.
- Prefer small incremental changes.
- Generate verification evidence for completed work.

The `.agent/` directory records engineering context and decisions. It does not replace existing source code, contracts, tests, or CI rules.
