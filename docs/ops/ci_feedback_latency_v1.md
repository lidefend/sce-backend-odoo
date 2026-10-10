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

The full candidate suite runs nightly at `18:30 UTC` (`02:30 Asia/Shanghai`).
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
