# Iteration Validation Responsibility v1

Status: active  
Authority: `AGENTS.md`

Before the first mutation or validation run, every executor must declare three
separate lanes:

1. `local_targeted`: affected static, contract and non-zero targeted tests.
2. `remote_integration`: exact PR HEAD against the current target base.
3. `scheduled_release`: current remote main release qualification.

No lane substitutes for another.

Small changes do not run the full `smart_construction_core` module suite locally.
Full module, full browser and Quick suites belong to explicit audit or remote CI.

`local-test.lock` is currently shared across worktrees. A busy lock is an
`environment_defect`, not a PR blocker: do not wait or steal it, run unaffected
offline checks, commit, and create the PR. Exact-head remote CI is then the
integration authority.

A normal PR requires a clean committed HEAD, bounded diff, and accurate local
targeted evidence. Merge requires current exact-head required remote checks.
Scheduled CI separately determines whether the resulting mainline is eligible
for release.
