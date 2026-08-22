# NATIVE-VIEW-CONTRACT-CAPABILITY-CLOSURE

## Q0 topic bootstrap

- Status: completed
- Branch: `codex/fix-project-layout-container-normalize`
- Baseline: `35f31407ab34ffff1d43de264e51de5f858a2596`
- Baseline authority: `origin/main`
- Worktree: `/home/lidefend/workspace/sce-backend-odoo`
- Formal Product Layer: P0 platform kernel product
- Supporting layer: P4 verification and delivery tooling
- Runtime authority: existing `local.clean` profile only
- Product result: every formal product native-view capability is traceable to a
  normalized contract and renderer outcome, or fails closed with a stable
  reason code.

## Frozen boundary

- No construction-industry or customer-specific semantics enter `smart_core`.
- The frontend consumes declared contract semantics and never infers product
  meaning from a model, menu, XML ID, role, label or route.
- No new Compose project, database, port, volume, credential, fixture system or
  runtime profile is created by this topic.
- Database-writing and shared runtime acceptance remain serialized.
- The pre-existing dirty primary worktree is excluded from this candidate.

## Q1 entry criteria

- Regenerate the formal product view-structure baseline from this branch.
- Freeze the complete candidate fingerprint.
- Produce a capability-atom ledger for every formal product surface.
- Record every transition through native, normalized, semantic, renderer and
  interaction layers.
- Reject missing transitions, unknown fallbacks and zero-surface reports.

## Initial evidence

- `origin/main` fetched at `35f31407ab34ffff1d43de264e51de5f858a2596`.
- PR #275 is merged into that baseline and its required checks passed.
- The completed CI-fix worktree was detached through the governed cleanup
  entrypoint; its local branch reference remains at
  `ed9fcc995fd966a702bb5c6a5b8998f6f80e0a1c`.
- This worktree was created through `make workspace.worktree.create` with the
  exact full baseline SHA.

## Q1-1 contract definition

- Candidate fingerprint: `4655fcb28c1101ee80500ceb4088177da153349a`.
- Scope: contract definition only; no runtime, database, Make, or global gate mutation.
- Result: capability atom schema, terminal-state rules, reason-code registry,
  and bilingual contract semantics frozen for the Q1 collector.

## Q1-2 governed structure collector

- Start commit: `72c37653`.
- Scope: complete worktree fingerprint, read-only native structure exporter,
  fail-closed integrity guard, and targeted unit tests.
- Validation: `python3 -m unittest scripts.verify.test_product_view_structure_contract`.
- Result: `14` non-zero tests passed; no database, Make, baseline, or global
  preflight mutation was performed.

## Q1-3 local.clean structure authority

- Odoo authority: Odoo 17 public `get_view()` user-visible arch, with
  `_get_view()` limited to provenance diagnostics.
- Candidate fingerprint: the authoritative complete digest is embedded in the
  tracked view-structure baseline; this run record intentionally avoids a
  self-referential future-HEAD value.
- Runtime: `local.clean` / `sc-local-clean` / `sc_clean` / `^sc_clean$`,
  `demo_data=false`.
- Export: `89` formal menus, `65` models, `280` resolved surfaces; form `87`,
  tree `84`, search `89`, pivot `9`, graph `6`, kanban `4`, activity `1`.
- Validation: `21` targeted tests passed; baseline guard passed; independent
  `local.clean.view_structure_gate` re-export matched the tracked baseline.
- Evidence carrier: the generated baseline is the only exact fingerprint
  exclusion; its source digest is recomputed from the current scope and its
  source HEAD must be an ancestor of the carrier HEAD.
- Containment: the known `local.clean.health` frontend-root `403` belongs to
  the environment/frontend layer. It was not rerun or repaired in this batch.

## Q1-4 product capability loss ledger

- Status: completed.
- Mechanism commits: `0b465d65`, `48c268c2`, `58037b4e`, `1847e131`,
  `659c3dc4`, and `e64e6a3b`.
- Evidence-carrier commit: `ecb96e35`.
- Final clean-HEAD fingerprint: `87aa0e279860b3b8223f0df2d04775ae20a4f54746a4a85d6ce6a2e9cd31ee0f`.
- Final scope path count: `6531`.
- Runtime identity: `local.clean` / `sc-local-clean` / `sc_clean` /
  `^sc_clean$`, `demo_data=false`.
- Governed commands: `make local.clean.view_structure_baseline`,
  `make local.clean.view_structure_gate`, and
  `make local.clean.view_capability_ledger_gate`.
- Structure result: `89` formal menus, `65` models, `280` resolved surfaces;
  every surface resolved successfully.
- Ledger result: `26,531` native candidates and classified atoms, `0`
  unclassified, `0` ambiguous, `0` ready, `0` fallback, `26,531`
  unsupported, and `0` silent loss.
- Targeted verification: `7` ledger mutation tests were collected inside the
  governed Make gate; the standalone capability/taxonomy suite collected `12`
  tests. Zero-test execution is not accepted.
- Evidence semantics: `4,770` occurrence origins remain explicitly unproven
  with the native first-loss reason; the remaining `21,761` atoms use the
  normalized-mapping first-loss reason. No static frontend symbol is promoted
  to end-to-end readiness.
- Independent review: final backend and governance reviews reported
  `S0=0`, `S1=0` against the frozen candidate.
- Rollback: revert the evidence-carrier commit first, then revert Q1 mechanism
  commits in reverse order. Q1 introduces no product business semantics,
  customer data, database fixture, runtime profile, or frontend activation.

## Q2 active boundary

- Formal Product Layer: P0 platform mechanism, supported by P4 evidence and
  gates.
- Scope: `modifier.*`, `action.*`, `permission.*`, plus root
  `create/edit/delete`; the reference blast radius is `5,271` atoms (`5,143`
  behavior-family atoms plus `128` root behavior atoms).
- Excluded until Q3: layout and field semantics, search/group/order/paging,
  x2many presentation, chatter, template, widget, and kanban content closure.
- Dynamic verdicts require governed user, company, record, and mode evidence;
  the `local.clean/system/main` carrier cannot be generalized to other
  contexts.

## Q2 PR-worktree continuation (2026-08-21)

- The completed native-view closure commits were integrated into PR #276 at
  `c2968fb6a29e74335eb2ed0c16d9187578aada4b` without merging `main`.
- The current PR worktree is the only writer for Q2. The existing
  `local.clean` profile remains the sole runtime authority and must be rebound
  through governed `make local.clean.*` targets before new runtime evidence is
  accepted.
- Q2 continues with one objective: promote only occurrence-preserving native
  modifier, action, permission and root-behavior atoms from explicit
  unsupported status to evidence-backed terminal outcomes. Professional page
  layout and construction-specific semantics remain excluded.

## Q2-1 static form modifier occurrence closure (2026-08-21)

- Scope: only static boolean `readonly`, `required`, `invisible`, and
  `column_invisible` form occurrences. Dynamic expressions, actions,
  permissions and root behaviors remain fail-closed for later Q2 increments.
- Evidence rule: one applied native contributor, exact numeric native locator
  and occurrence index, exact raw normalized value, explicit parsed semantic
  value, and the production `runtimeOccurrenceState` frontend consumer.
- Governed result: `26,531` atoms conserved; `358` ready, `433` fallback,
  `25,740` unsupported, `0` unclassified, `0` ambiguous, and `0` silent loss.
- Validation: `26` capability/map unit tests, the fingerprint-bound
  `make local.clean.view_capability_ledger_gate`, Web UPC V2 guard, and the
  canonical form presenter `49`-case suite passed.
- Infrastructure correction: contract exporters now copy governed fingerprint
  and structure inputs into the registered Odoo container before execution;
  evidence validation accepts the repository's governed `artifacts` symlink
  while still rejecting absolute paths and `..` traversal.

## Q2-2 form root capability closure (2026-08-21)

- Scope: explicit native form-root `create`, `edit`, and `delete` attributes.
  Relation permissions, buttons, dynamic expressions and `js_class` remain
  outside this increment.
- Carrier: `capabilities.native_root_attributes` preserves only explicitly
  declared XML values; `can_create`, `can_write`, and `can_delete` retain the
  normalized boolean semantics. The existing effective permission intersection
  and public UPC V2 shape remain unchanged.
- Terminal policy: `23` proven `create/edit` atoms are ready because the
  canonical store drives save and readonly behavior. The `18` proven delete
  atoms move to classified fallback until a dedicated delete interaction is
  independently verified.
- Governed result: `381` ready, `451` fallback, `25,699` unsupported and `0`
  silent loss across the conserved `26,531` atoms.
- Validation: `28` capability/map tests, `20` parser tests, governed
  `local.clean` `smart_core` upgrade and capability-ledger gate, Web UPC V2
  guard, canonical presenter `49` cases, readonly capability `14` cases, and
  form-render split guard passed.

## Q2-3 form action identity capability closure (2026-08-21)

- Scope: exact native form button attributes carried by authoritative
  `layout`, `header_buttons`, or `stat_buttons` occurrences. Button structure
  nodes, nested subview actions, business action semantics and action layout
  remain outside this increment.
- Parser and assembler correction: `level=smart` now maps to canonical
  `stat_buttons`, and the UPC V2 assembler consumes that canonical region.
  All `37` governed stat buttons are authoritative; the non-authoritative
  layout copy remains filtered so each backend identity is emitted once.
- Evidence rule: locator, occurrence index, authoritative flag, capability
  key and raw value must all match `native_identity`. Any drift fails closed.
  The frontend evidence binds the existing canonical
  `resolveCanonicalFormActionExecution`; no page fallback or label inference
  was introduced.
- Terminal policy: `889` exact form action attributes move from unsupported to
  `CAPABILITY_ACTION_IDENTITY_REDUCED` fallback. None are promoted to ready
  until final interaction/value equivalence is independently proven.
- Governed result: `381` ready, `1,340` fallback, `24,810` unsupported and `0`
  silent loss across the conserved `26,531` atoms.
- Validation: `25` ledger/map tests, `21` parser tests, `66` UPC runtime tests,
  governed `local.clean` `smart_core` upgrade and capability-ledger gate,
  canonical presenter `49` cases, header action presentation, UPC V2 action,
  Web consumer/architecture guards and strict TypeScript passed.
