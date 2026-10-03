# Historical branch reference retirement

This entrypoint retires only the references listed in an exact reviewed
manifest. It does not infer references from naming, ancestry, or matching local
and remote branch names.

## Preview

```bash
make branch.retire.historical \
  HISTORICAL_RETIREMENT_MANIFEST=docs/ops/manifests/historical_branch_retirement_20260911.json \
  HISTORICAL_RETIREMENT_REPORT=artifacts/codex/historical-branch-retirement/dry-run.json
```

The default is read-only. Every reference reports either `eligible` or `skip`,
with local and remote identity evaluated independently.

## Prepare and verify recovery

```bash
make branch.retire.historical \
  HISTORICAL_RETIREMENT_MANIFEST=docs/ops/manifests/historical_branch_retirement_20260911.json \
  HISTORICAL_RETIREMENT_REPORT=artifacts/codex/historical-branch-retirement/bundle-preparation.json \
  HISTORICAL_RETIREMENT_BUNDLE=/absolute/recovery/path/historical-branch-retirement.bundle \
  PREPARE_BUNDLE=1
```

The bundle is accepted only when `git bundle verify` succeeds and its advertised
heads cover every expected local SHA and every declared present remote SHA. A
bundle-preparation failure stops before reference deletion.

## Apply after separate authorization

Actual retirement is not authorized by creating or reviewing the manifest. It
requires a later authorization bound to the exact manifest SHA-256:

```bash
make branch.retire.historical \
  HISTORICAL_RETIREMENT_MANIFEST=<manifest> \
  HISTORICAL_RETIREMENT_REPORT=<apply-report> \
  HISTORICAL_RETIREMENT_BUNDLE=<verified-bundle> \
  HISTORICAL_RETIREMENT_MANIFEST_SHA256=<approved-sha256> \
  HISTORICAL_RETIREMENT_CONFIRM=RETIRE_APPROVED_HISTORICAL_REFERENCES \
  APPLY=1
```

The command rechecks live identities, worktree occupancy, open pull requests,
and bundle coverage immediately before deletion. A changed or newly occupied
entry is skipped. A remote deletion failure leaves that entry's local reference
intact and does not broaden the approved list.

## Squash-merged tips (`reviewed_explicit`)

Containment defaults to ancestry. Because a squash merge creates a new commit,
the merged branch tip is never an ancestor of `main`, so an ancestry-only entry
for it is always skipped. For a tip whose PR is confirmed merged at its exact
head, an entry may instead declare a recorded owner review:

```json
{
  "branch": "codex/example",
  "local": {"state": "present", "sha": "<full-sha>"},
  "remote": {"state": "present", "sha": "<full-sha>"},
  "containment": "reviewed_explicit",
  "reviewed_explicit": {"authorization": "<owner decision>", "reviewed_at": "2026-10-04"},
  "reason": "...",
  "evidence": ["..."]
}
```

`containment` accepts only `ancestry` (default) or `reviewed_explicit`.
`reviewed_explicit` requires a non-empty `authorization` and a `reviewed_at`
matching `YYYY-MM-DD`; an unknown mode or a missing field aborts manifest
loading. This replaces **only** the ancestry proof. Local and remote SHA drift,
open pull requests, checked-out branches, runtime-carrier references,
related-work evidence and the manifest SHA-256 binding all still fail closed,
and every declared tip must remain obtainable so the recovery bundle can
contain it. There is no force switch.

## Restore one reference

List the recovery heads first:

```bash
git bundle verify <bundle>
git bundle list-heads <bundle>
```

Each branch has a local recovery head under
`refs/codex/historical-retirement/<manifest-prefix>/local/<full-branch-name>`.
Branches whose remote existed also have a `/remote/` recovery head. Restore to a
new review branch first; do not overwrite an active branch:

```bash
git fetch <bundle> \
  refs/codex/historical-retirement/<manifest-prefix>/local/<full-branch-name>:refs/heads/recovery/<review-name>
```

Remote recovery requires a new explicit remote-write authorization and a
governed Make entrypoint. The bundle itself does not push or restore anything.
