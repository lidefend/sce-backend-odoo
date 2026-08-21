# `.agent` Engineering Context

`.agent` is the repository-local execution context for engineering agents. It records
what is being pursued, which decisions constrain the work, which capabilities may be
used, how a governed workflow proceeds, and what evidence a concrete run produced.
It does not replace source code, contracts, tests, CI, or the policies under `docs/`.

## Authority Order

When records conflict, use this order and fail closed:

1. `AGENTS.md`
2. `docs/ops/codex_execution_allowlist.md`
3. `docs/ops/codex_workspace_execution_rules.md`
4. `ARCHITECTURE_GUARD.md`
5. `docs/architecture/ai_development_guard.md`
6. Active decisions under `.agent/decisions/`
7. The selected goal, workflow, and run records

Lower-priority records may narrow higher-priority rules but must never relax them.

## Directory Contract

- `context.yaml`: stable repository facts, authority references, runtime identities,
  lifecycle rules, and default evidence expectations.
- `goals/`: bounded outcomes with status, scope, exclusions, and acceptance criteria.
- `decisions/`: durable architecture or operating decisions. Active decisions are
  mandatory constraints for matching work.
- `capabilities/`: actions an agent may perform and the evidence each action requires.
- `workflows/`: ordered execution paths. A workflow references policy; it does not
  create an alternative runtime, database, test entry, or release path.
- `runs/<goal-id>/`: resumable execution state for a specific goal.

## Required Start Sequence

Before any mutation:

1. Read `context.yaml` and select exactly one goal.
2. Load every active decision related to the goal.
3. Run the repository preflight required by `AGENTS.md`.
4. Inventory registered worktrees, dirty tracked files, staged files, and untracked
   files without changing them.
5. Declare `Formal Product Layer`, `Layer Target`, `Module`, `Standard vs
   User-Specific`, `Why Here`, `Why Not Elsewhere`, and `Blast Radius`.
6. Freeze one batch with one objective, an explicit file scope, exclusions,
   acceptance criteria, rollback, and stop conditions.
7. Create or resume the matching run record before editing.

## Parallel Work Isolation

- One candidate worktree has one writer.
- Pre-existing dirty files belong to an unknown or declared in-flight owner until
  explicitly assigned. Preserve them and exclude them from the batch scope.
- A newly appearing change must stop the run until its owner and treatment are
  confirmed.
- Read-only reviewers bind to the same frozen candidate fingerprint and do not create
  a second implementation line.
- Never hide, restore, stage, commit, or rewrite another task's changes.

## Batch State Machine

Use these states consistently:

- `planned`: goal exists but its execution boundary is not frozen.
- `active`: one batch is executing with a frozen boundary.
- `blocked`: the run cannot make meaningful progress and the blocking condition is
  recorded.
- `verification_pending`: implementation is complete but required governed checks
  have not run or have not passed.
- `completed`: acceptance, evidence, documentation, and rollback information are all
  recorded.
- `superseded`: a newer goal or decision explicitly replaces the record.

Do not mark a run `completed` merely because files were edited.

## Run Evidence Contract

Every active run must identify:

- baseline full SHA and current branch;
- formal product layer and exact file scope;
- pre-existing dirty paths excluded from ownership;
- commands actually executed and their results;
- non-zero collected tests when tests are required;
- generated artifact paths and immutable fingerprints when applicable;
- remaining risks, rollback path, and next exact step.

Unknown, not-run, failed, and passed are different states. Never report `not_run` as
`passed` and never use a zero-test command as gate evidence.

## Change Rules

- Prefer the smallest batch that produces an independently reviewable result.
- Product work must reuse registered Make targets, runtime profiles, databases,
  ports, volumes, fixtures, credentials, and evidence tools.
- `.agent` changes describe and constrain execution; they must not silently change
  product contracts or business semantics.
- Changes to repository execution mechanisms belong to P4 and require their own
  goal, workflow, verification evidence, and rollback path.
