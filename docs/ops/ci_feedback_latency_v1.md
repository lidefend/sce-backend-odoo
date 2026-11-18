# CI Feedback Latency v1

## Purpose

Keep pull-request validation proportional to delivery risk while preserving the
full release, security, permission, migration, dependency, and unknown-path
boundaries.

The measured pre-change baseline for recent professional frontend pull requests
was:

| Workflow | Typical elapsed time |
| --- | ---: |
| `public_guard` | 4–5 minutes |
| `professional_quality_gate` | 9–14 minutes |
| `frontend_release_gate` | 10–16 minutes |
| `merge_policy_gate` critical path | 14–16 minutes |
| `release_candidate_gate` | candidate-only aggregate on explicit publish path |

The main classification errors were:

- a professional frontend guard under `scripts/verify/frontend_professional_*`
  was also classified as backend code;
- adding a component-family unit target to `make/frontend.mk` promoted an
  otherwise standard frontend batch to a full frontend release audit;
- the false backend identity could start unrelated ORM authorization work.

## Governed lanes

### Fast

Documentation and declared non-runtime metadata. It receives repository and
workflow policy checks but no product build.

### Standard frontend

Ordinary frontend product code, professional frontend guards, and the single
professional extension Makefile. It runs lint, strict typecheck, release unit
tests, and build. It does not run the isolated full release acceptance stack or
backend ORM authorization.

The only Makefile allowed in this lane is:

```text
make/frontend_professional_extensions.mk
```

It may declare and aggregate independently tested professional component-family
targets. It must not contain environment handling, release orchestration,
credentials, Docker/Compose operations, database operations, or privileged
commands.

### Standard backend

Ordinary backend product changes. It retains backend contract, unit, tenant
boundary, and generated-report verification.

### Governance-only

Ordinary PRs that touch CI policy, release orchestration, or other previously
high-risk governance surfaces stay out of the fast lanes, but they no longer
automatically imply candidate-grade publication validation. They run governance
verification suitable for merge qualification.

### Candidate / release

Security, permissions, migrations, dependencies, CI policy, release machinery,
core Makefiles, unknown paths, and mixed unsafe scopes remain fail-closed for
publication. The full professional and frontend release gates remain
authoritative only on explicit candidate paths, and `release_candidate_gate`
summarizes that publication qualification.

The full candidate suite runs nightly at `18:00 UTC` (`02:00 Asia/Shanghai`).
The governed `ci:candidate` label and authorized manual dispatch remain the
immediate paths when publication evidence is needed before that window. An
ordinary push to `main` runs mainline health only; it does not silently become
a release candidate. A failed nightly candidate blocks publication of that
exact head, but does not retroactively invalidate an already merged PR.

## Safety invariants

- `make/frontend.mk`, `make/ci.mk`, `Makefile`, and every unlisted Makefile remain
  high risk.
- CI policy and workflow changes remain high risk.
- Dependency and lockfile changes retain the full frontend release audit.
- A frontend filename cannot downgrade a security, tenant, importer, identity,
  or migration path.
- Unknown paths remain high risk.
- The ruleset directly requires `frontend_release_gate`, `merge_policy_gate`,
  `professional_quality_gate`, and `public_guard`; no workflow polls sibling
  runs to reproduce their result.
- `release_candidate_gate` remains publication-only, exact-head bound, and is
  absent from the ordinary `main` push path.

## Lane telemetry

The eight declared lanes (`local.iteration`, `local.quick`, the three
`remote.professional.backend.*` lanes, `remote.standard_backend`,
`remote.frontend.standard`, `remote.frontend.full`) are exactly the set
`make audit.verification.lane_coverage` measures. Each record binds a lane, one
of that lane's own entrypoints, the exact head, whether the worktree was dirty,
the wall-clock duration and the observed status.

Three rates are reported per lane and per version
(`make lane.telemetry.report TELEMETRY_BY_HEAD=1`):

| Rate | Meaning | Expected |
| --- | --- | --- |
| `pass_rate` | passed runs over all recorded runs | reported, no threshold |
| `degraded_rate` | runs that finished correctly but lost the cheap path (`full_scan_fallback`, `no_shard_reuse`, `detached_from_main`, `receipt_absent`, `partial_lane`) | reported; drives the efficiency backlog |
| `integrity_failure_rate` | records that are malformed or name a lane/entrypoint that does not exist | must be `0` |

`degraded_rate` is the metric a pass/fail counter hides: a lane that is green
but pays a full scan every time looks identical to a cheap one until the
degradation is counted. That is why `make lane.telemetry.check` fails on
integrity while leaving pass and degraded rates as observations rather than
gates.

Records live in `.git/codex/evidence/lane_telemetry/<lane>.jsonl`. Recording
never runs a lane, signs coverage or relaxes a check.

Local lanes report automatically where the entrypoint is already instrumented:
`make ci.local.quick` files its own observation. Remote lanes have no
in-repository execution point, so they stay `no data` until their CI workflow
records a run through `make lane.telemetry.record`; a missing observation is
reported as missing and never inferred from a sibling lane.

## Expected effect

Professional frontend batches that use the extension surface should select:

```text
lane=STANDARD
frontend_mode=standard
professional_mode=standard_frontend
backend_changed=false
frontend_full_required=false
```

This removes the 10–16 minute release acceptance and unrelated ORM work from the
ordinary component-development critical path. Full release acceptance is still
required when a release-critical surface changes and when formal release
evidence is produced through the explicit candidate path.

## Integration-cycle efficiency (2026-10-20)

The product/demo integration showed that the dominant cost was not a single
gate, but repeated push/fix/regenerate cycles. Each remote round costs roughly
8–10 minutes, while the guards that failed were mostly cheap local checks.

Use [the integration cycle playbook](integration_cycle_playbook_20261020.md):

1. take an ownership snapshot before calling a file in flight;
2. run the integration fast bundle before the first push;
3. refresh generated evidence once and run exact-head Quick once;
4. push one converged candidate, not one push per assertion;
5. collect all remote failures before the next local fix batch;
6. merge only with required checks and the exact-head Quick receipt, and keep
   `pr.merge` runtime-evidence exclusions explicit.

## Target-scoped Make dependency reuse (2026-11-18)

A local receipt that declares a Make fragment uses the selected target's
dependency material, not the fragment's whole-file hash. The material includes:

- the active literal `include` closure;
- every rule block that defines the selected target or a literal prerequisite
  reached from it;
- recursive `$(MAKE) <target>` calls;
- the selected target's `.PHONY` identity;
- Make variables referenced by that material, including their referenced
  variables; and
- the content of file prerequisites outside the target graph.

Editing another target in the same `make/ci.mk` or `make/frontend.mk` therefore
does not invalidate an unchanged receipt. Editing the selected recipe, a reached
prerequisite, a relevant variable, or an included target override does.

A receipt written before this mechanism is projected only when all of these are
provable: Git confirms the recorded whole-file bytes and mode at the receipt
head, the receipt had no dirty Make source, and the historical target material
equals the current material. A hash mismatch, dirty Make input, unavailable
history, or target-material change remains stale. The old whole-file hash is
never treated as target-specific proof.

## Backend focused PR execution (2026-11-18)

Ordinary pull requests with backend runtime impact now run the exact changed ORM
test selectors from their impact-safe modules. The complete module baseline
remains mandatory for scheduled, explicit-candidate and operator full audits.
If a runtime change has no changed executable test selectors, the planner falls
back explicitly to complete affected modules rather than producing an empty
green suite.

Each module keeps the original direct `make test ... | tee` execution path.
GNU `timeout --foreground` applies the ten-minute focused-PR or twenty-minute
formal-lane ceiling without placing Make in a new process group or inserting
another process/session wrapper into its execution semantics. A shell heartbeat
reports the current module and elapsed time every thirty seconds. Timeout exits
with status 124 and preserves the partial test log and evidence attempt, so a
hung test cannot occupy the 240-minute workflow ceiling invisibly.

Authenticated historical receipts remain observation-only unless all existing
closure authorities pass. They may still supply exact measured module durations
for shard balancing. Discovery accepts the current
`backend-execution-<run-id>-<shard>` artifact name and the legacy
attempt-qualified name for attempt one.

Each focused or full backend shard materializes the event-bound integration base
as `refs/remotes/origin/main` before consulting the frozen plan or invoking Make.
That ref is the exact pull-request base SHA when supplied, and the fetched
authoritative mainline tip for schedule, candidate, and operator full runs. The
resolved commit is exported as `VIEW_STRUCTURE_BASELINE_SHA` so inherited Make
guards consume the same identity without independently probing a ref that the
shard checkout may not have fetched. A missing or mismatched ref fails before
database or module-test preparation.

The backend suite also disables the generic per-module `pip install` step.
Repository ORM tests resolve `odoo_test_helper` from the tracked
`addons/odoo_test_helper` stub, while the runtime image owns its production
dependencies. This removes a network package-index round trip from every module
and makes the test entry independent of package-index latency. A named one-off
test container is retained until the workflow cleanup step, so a module timeout
can preserve and print its process log instead of deleting the only diagnostic
carrier with `docker compose run --rm`.
