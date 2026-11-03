# P4 acceptance artifact custody — 2026-11-03

## Problem and ownership

P4 owns acceptance carrier custody and verification tools. The approved navigation candidate remains `fix/scheduled-navigation-closeout-20261103@f05eb7155387b8bc403881a3c89bd9577cbf0fca`; this infrastructure implementation is a separate candidate requiring its own review.

The original backend was stopped, declared source `cfd3d51cd97b6980819f898390cb3d4e7da2f9fc`, and mounted pc01. Runtime validation required that mount to equal the invoking worktree. Moving between worktrees therefore looked like an environment failure even with identical product inputs. A mutable bind also allowed source changes without changing the reported SHA. The list acceptance preview is 5180; the generic frontend health command checks 5175. Neither endpoint was running at diagnosis. The 5175 pidfile failure alone was not proof about the list preview.

## Implemented boundary

Local acceptance exports selected backend inputs from exact Git objects into the repository's shared Git evidence store. The artifact manifest is compared with the commit, every blob is rehashed, executable modes are checked, and extra files, writable files, symlinks and gitlinks fail closed. Local working-tree edits are never exported. This is local content verification, not a signed production image or completion of the broader ENV-03 artifact-signing design.

Backend startup consumes an explicit Compose override with read-only bindings and `create_host_path=false`. CLI volume overrides alone were experimentally insufficient: this Compose version preserved the original writable flag. Readback must prove the three source roots read-only before startup is reported successful; resource health verifies all declared artifact mounts.

An exclusive lock is acquired using the same target-key convention as acceptance browser probes. A previous container is retained under an exact container-ID-derived rollback name. Failed startup restores its original name and running state. Successful replacement preserves it for controlled recovery; never use a global orphan prune. The data volume, filestore, database, filter and credential authority remain the registered profile's existing identities.

`ACCEPTANCE_ARTIFACT_SHA` explicitly identifies the served source independently of the P4 executor's branch. Product input differences are still rejected; this parameter does not allow a receipt to falsely claim that an old backend serves a new candidate. Exact-head contract/browser receipt gates remain unchanged.

## Validation and limits

The current run is `.agent/runs/P4-ACCEPTANCE-ARTIFACT-20261103/run.json`; original logs and runtime readbacks are under `.runtime/p4-acceptance-artifact/`. Artifact tamper, cross-worktree reuse, invalid paths/modes, explicit readonly mounts and successful/failed replacement are covered by executable tests. Owning runtime tests were made hermetic: no local private `.env.dev` dependency; incomplete entry fixtures and a whitespace-dependent assertion were corrected without dropping assertions.

The approved backend source was brought up from verified readonly artifacts and passed resource health. The existing unchanged frontend build was verified and its 5180 preview started. These are environment observations, not list-page product acceptance. Contract receipt generation correctly refused the dirty P4 implementation tree; it must run from a clean candidate before browser evidence and publication. No UUID changes, fixture reset, module upgrade, production/daily deployment or mainline merge occurred.

## Preventing recurrence

Resolve the required runtime evidence and the actual preview/profile before final Quick and independent review. Reuse a content-identical artifact across worktrees, preserving its actual source identity. A new product artifact requires an explicit deployment; it is not an unplanned environment repair. Do not substitute process liveness, pidfile presence, Quick success, or an old runtime receipt for candidate-bound acceptance. Future work on image signing, credential-carrier decoupling and frontend full-asset custody remains separate and must not be described as delivered by this local backend change.
