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

### High risk / release

Security, permissions, migrations, dependencies, CI policy, release machinery,
core Makefiles, unknown paths, and mixed unsafe scopes remain fail-closed. The
full professional and frontend release gates remain authoritative here.

## Safety invariants

- `make/frontend.mk`, `make/ci.mk`, `Makefile`, and every unlisted Makefile remain
  high risk.
- CI policy and workflow changes remain high risk.
- Dependency and lockfile changes retain the full frontend release audit.
- A frontend filename cannot downgrade a security, tenant, importer, identity,
  or migration path.
- Unknown paths remain high risk.
- The aggregate required check and exact-head binding remain unchanged.

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
evidence is produced.
