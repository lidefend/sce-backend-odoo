# RC Publication Transaction Contract v1

[中文](release_publication_transaction_v1.md)

## Goal

A candidate accepted by `release.candidate` may only be published through:

```bash
ENV=dev make release.publish \
  VERSION=1.0.0-rc.5 \
  CANDIDATE_ATTEMPT_ID=<candidate-attempt-id> \
  EXPECTED_SOURCE_SHA=<full-40-char-sha>
```

This command writes to the registry, GitHub/Gitee tags, and a GitHub Release, so
it requires one explicit external-publication authorization. It never deploys
production.

## Evidence boundary

- The candidate attempt report, manifest, archive, SBOM, logs, and summary are
  never modified.
- Publication uses an independent
  `artifacts/release/candidates/<version>/publications/<publication-attempt-id>/`.
- `publication-plan.json` freezes candidate report, manifest, archive, SBOM,
  image content, source SHA/tree, tool contract, and every external target.
- `publication-report.json` atomically records state transitions and verified
  remote identities.
- `publications/latest.json` is only an atomic index, never the sole evidence.

The old `immutable_candidate_publish.sh` denies direct execution.
`release.candidate.publish` is only a compatibility alias for the new contract.

## Preflight and execution order

Before any external write, the workflow verifies:

1. candidate readiness and all frozen hashes;
2. GitHub/Gitee main SHA and tree;
3. required checks;
4. the local image content identity;
5. absence of registry version/source tags;
6. absence of GitHub/Gitee Git tags;
7. absence of the GitHub Release;
8. the per-version publication lock and safe paths.

It then:

1. pushes both image tags, resolves one registry digest, pulls by digest, and
   verifies the image ID;
2. creates one controlled annotated tag on GitHub/Gitee and verifies each peeled
   commit;
3. creates a GitHub prerelease and rereads its tag, source, publication attempt,
   and digest identity;
4. writes `PUBLICATION_COMPLETE=true` only after every remote identity matches.

## Recovery and idempotency

Registry, Git tags, and Releases cannot form a globally atomic transaction. A
failure never deletes or moves a remote object. Resume explicitly selects the
same publication attempt:

```bash
ENV=dev make release.publish \
  VERSION=<version> \
  CANDIDATE_ATTEMPT_ID=<candidate-attempt-id> \
  EXPECTED_SOURCE_SHA=<sha> \
  PUBLICATION_ATTEMPT_ID=<publication-attempt-id>
```

Resume revalidates every frozen identity. Completed stages are verified from the
remote and skipped when they match; conflicts fail closed. Reinvoking a
completed version does not publish it again.

## External boundary

This entry does not deploy production, connect to a production database, delete
branches, or automatically roll back by deleting tags or images. Production
deployment remains a separate explicit authorization.
