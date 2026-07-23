# Atomic RC Candidate Flow v1

[中文](release_candidate_atomic_flow_v1.md)

## Goal

A routine RC candidate requires one approval and one repository entry point:

```bash
ENV=dev make release.candidate VERSION=1.0.0-rc.5
```

In a clean, dedicated release workspace the entry point automatically:

1. synchronizes GitHub `main` through controlled `main.sync`;
2. freezes the full commit SHA, tree, and `VERSION`;
3. verifies aligned GitHub/Gitee `main` and successful required checks;
4. creates an independent, main-only source repository without alternates,
   binds the full commit/tree, and runs RH010;
5. builds the immutable candidate image from that clean source repository;
6. exports and reloads the image archive;
7. runs Trivy vulnerability/secret scanning and creates a CycloneDX SBOM;
8. emits machine-readable `release-report.json` and concise
   `release-summary.txt`.

A successful summary contains:

```text
CANDIDATE_READY=true
PUBLISHED=false
DEPLOYED=false
```

`CANDIDATE_READY=true` only means that the local immutable candidate passed all
pre-publication gates. It does not mean that an image was pushed, a tag was
created, a Release was published, or production was deployed.

## Identity and failure semantics

- The pre-publication scan binds the immutable local image ID and never invents
  a registry digest.
- `release-report.json` binds the commit, tree, version, tool-contract digest,
  archive checksum, reloaded image ID, frontend checksum, security scan, and SBOM.
- Every real run first creates a collision-safe `attempt_id`. Its report, stage
  logs, clean source repository, and outputs live under
  `artifacts/release/candidates/<version>/attempts/<attempt-id>/`.
- Reports and the `latest.json` index are written atomically. The index is only
  a pointer, never the sole evidence, so an index-write failure cannot corrupt a
  completed attempt.
- A retry always creates a new attempt. It may bind a new source, tree, and tool
  contract and links to the prior failure through `retry_of_attempt_id`. Prior
  attempt reports and logs are never moved, truncated, appended to, or rewritten.
- Resume is limited to one explicitly selected attempt and requires exact
  version, source SHA, tree, tool-contract, source-repository, and
  workflow/schema identity. A mismatch fails closed without modifying evidence.
- A version with `CANDIDATE_READY=true` cannot be silently rebuilt. Legacy
  single-directory failed evidence is recognized read-only and is never migrated
  or rewritten in place.
- The source repository may not use shared/reference cloning, alternates, or
  caller objects. Preparation, identity, and RH010 failures remain separate
  stages and are never repaired with gc/prune.
- A non-blocking per-version lock serializes execution; versions and attempts
  never share or overwrite their evidence directories.

## External-effect boundary

The following actions remain separate, explicitly approved operations:

- registry push;
- formal Git tag;
- GitHub/Gitee Release;
- provenance/attestation publication and signing;
- production deployment.

The atomic candidate flow never invokes the existing
`release.candidate.publish` or production deployment entries.
