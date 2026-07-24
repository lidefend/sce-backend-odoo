# RC6 Candidate Identity Freeze Runbook v1

## Frozen identity

RC6 is the product source commit
`fb1f2b5a6e93fb4d7865023e6cda2961848c3cb8`. The reviewed declaration is
`config/releases/rc6_candidate.json`. Advancement of `main` does not change this
candidate.

The only promotion reference is the digest-bound `image_ref` in that
declaration. Tags, including the unique source tag used for the initial registry
push, are not promotion identities.

## Identity chain

The declaration deliberately records three distinct identities:

- `image_manifest_digest`: immutable OCI manifest identity used in the image ref;
- `registry_config_digest`: the config object referenced by that manifest;
- `local_daemon_image_id`: the local Docker daemon's image identity.

These fields must not be compared as if they had identical semantics. Candidate
identity is proven by the manifest-to-config chain and by the OCI
`org.opencontainers.image.revision` label matching the frozen source SHA.

## Verification

Run from a clean repository checkout:

```sh
ENV=dev make verify.release.rc6.identity
```

The verifier fails closed when the SHA is shortened or changed, a movable image
reference is introduced, the manifest digest is replaced, the OCI revision
drifts, any required PR merge identity changes, or a required CI check is not
successful.

The registry source tag is single-write. Publication refuses to overwrite an
existing source tag. A rebuild producing a different digest requires a new
reviewed declaration and cannot silently mutate RC6.

## Scope boundary

Freezing candidate identity does not perform a database restore, module upgrade,
clone rehearsal, daily-candidate deployment, or production access. The next
consumer must use the exact `source_sha` and digest-bound `image_ref` from the
declaration.
