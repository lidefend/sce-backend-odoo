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
