# NATIVE-VIEW-CONTRACT-CAPABILITY-CLOSURE

## Q0 topic bootstrap

- Status: completed
- Branch: `feature/native-view-contract-capability-closure-v1`
- Baseline: `35f31407ab34ffff1d43de264e51de5f858a2596`
- Baseline authority: `origin/main`
- Worktree: `/home/lidefend/workspace/sce-backend-odoo-native-view-contract-capability`
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
