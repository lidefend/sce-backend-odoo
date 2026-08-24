# Merge Policy Gate Fast-Lane Validation v1

## Purpose

This document defines the first controlled runtime proof for the Fast lane of
the GitHub `merge_policy_gate`. It is an audit-only change and is deliberately
limited to repository documentation so the risk classifier must select
`FAST`.

## Authority and boundaries

- Required check: `merge_policy_gate` only.
- Protected target: `main`; pull requests remain mandatory.
- Bypass actors: none.
- This proof changes no product runtime code, database state, workflow file,
  CI classifier, Make target, dependency, or credential.

## Exact acceptance criteria

For this pull request, the aggregate workflow must show:

1. `classify` succeeds and reports `FAST`.
2. `fast` succeeds.
3. `full` is skipped.
4. `merge_policy_gate` succeeds exactly once on the PR head.
5. The PR remains mergeable through the standard squash-merge path.

The proof is invalid if an unlisted changed path causes a fail-closed
classification, if the aggregate check binds a different head, or if a
repository rule grants a bypass actor.

## Execution evidence record

Each Fast-lane proof records the following values against the exact PR head:

- base SHA and head SHA;
- the complete changed-path list;
- classifier lane and reason;
- conclusion of `fast`, `full`, and `merge_policy_gate`;
- PR mergeability and the absence of bypass actors.

The record is review evidence, not a replacement for the GitHub check run.

## Fast-run review procedure

Review the aggregate workflow before opening the individual legacy workflow
pages. A valid Fast run has a successful aggregate check even though the
legacy `public_guard` history-scan job is intentionally skipped. The
`public_guard_classify` check remains visible to show the fail-closed
classification that caused that skip.

## Follow-up evidence

After this Fast proof merges, a separate product-runtime PR must prove the
Full lane. That later PR is not authorized to rely on this document as runtime
verification evidence.
