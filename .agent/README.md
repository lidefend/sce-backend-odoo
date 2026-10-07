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

## First Entry

On first entry to a new task (not on every continuation):

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

## Continuation — All Executors

1. Run the mandatory lightweight identity preflight; resolve the branch with
   `make agent.run.resume`. The direct index is `.agent/active-runs.json`; there is
   no scan of all goals. Branches in distinct linked worktrees resolve independently.
2. Read the selected `run.json` and referenced living batch record only as needed.
   Reconcile changed scope, rules, inputs or environment; reuse unchanged observations.
3. Resume the earliest invalidated necessary check. A previous unchanged failure
   requires diagnosis, not a blind retry. Do not run broad gates to discover cheap defects.
4. Before handoff update the same run's blockers and `next_exact_step`; preserve original
   logs and record actual results, not inferred passes. Completed batches must have an
   explicit next task/closure boundary, not a vague “continue inventory”.

For a new task only, create goal/run/index metadata after preflight, then resolve it
before product edits. Missing or invalid records are a bounded context repair, not a
reason to scan all history. A completed historical workflow is not the default program.
Authority changes require rereading the affected rules; unchanged rules need not be
reloaded in every tool invocation. Higher-priority AGENTS policies always prevail.

## Run Format and Evidence

Use `runs/template/run.json` for executable context, and `goal.yaml` for intent.
`run.json` declares branch, baseline (batch/checkpoint, not automatically origin/main),
scope, environment reference, check targets, dependency inputs, blockers and next step.
Inputs may name files or bounded directories (new/deleted children are detected).
Repository root, `.git`, `.runtime`, traversal and external symlinks are rejected.
Completed/superseded runs report `closed`; they cannot begin/record further checks.
Include test scripts, lock/config files, Make recipes and shared helpers. A change to
this declaration invalidates the check. Do not use the whole repository as a dependency.

Before executing the declared check, run `make agent.run.begin AGENT_CHECK=<id>`
to capture its input state. Recording rejects any intervening input/identity change.
Then `make agent.run.record AGENT_CHECK=<id> AGENT_CHECK_STATUS=passed
AGENT_TEST_COUNT=<nonzero> AGENT_TEST_LOG=<repository-relative-original-log>` records
an executor-attested result in `.runtime/agent-runs/<goal>/`; use `failed` for failure.
It does not execute a command or certify that the reported count is true. Record only
an actually observed command and its original log; independent review checks that claim.
Log hashes, declared inputs, environment and source ancestry are checked on reuse.
Only offline checks can be automatically marked `reusable`; runtime checks require
fresh authoritative environment reconciliation through existing governed tools.

No secrets belong in run records or logs. Receipts are local, not transported between
worktrees and not final-delivery evidence. Documentation-only commits do not invalidate
unrelated source checks. Rebases, missing logs, changed tools or changed inputs invalidate
relevant evidence. No receipt can suppress required remote or final release gates.

Reuse is owned systemically, not per check. `scripts/ops/evidence_scope.py` is the single
reuse authority: a check declares its surface as units with per-unit input fingerprints,
the engine reports reusable/affected/blocked, and recording rejects any unit the run did
not execute or any planned unit it skipped. A governed entry therefore defaults to the
affected exact set and reuses unchanged passing evidence; re-collecting covered evidence or
re-walking a whole surface needs an explicit stated reason. A served-bundle revision is
provenance, not a validity key, so a redeploy alone does not invalidate the set.

`ci.local.iteration` requires the common entry. The frontend planner uses the registered
batch baseline, including committed, staged, unstaged and untracked changes; PR diff
selection retains its whole-branch semantics (`--plan-branch` explicitly). Missing run
registration never triggers a whole-branch fallback during daily iteration. Reusable
targets are listed separately, while unchanged failed targets are blocked for diagnosis. The controller attaches the same bounded
context on launch/resume without executing saved actions. An external executor must use
these Make entries too; repository tools cannot control arbitrary commands outside them.
Service installation is separate: source changes alone do not update a running controller.

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
- the affected exact set for the current delta, the deterministic derivation method and changed
  inputs behind it, and which previously-passed results are carried forward instead of rerun;
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
