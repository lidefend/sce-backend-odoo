# Remote branch backlog retirement C (2026-10-05)

Formal Product Layer: P4 (ops delivery tool / retirement record).
Layer Target: historical branch retirement entry (`scripts/ops/retire_historical_branch_refs.py`,
`make branch.retire.historical`) and its run records under `.agent/runs/`.
Standard vs User-Specific: platform ops mechanism, not product semantics.
Why Here / Why Not Elsewhere: the retirement tooling and its result index own this decision; no
product module, frontend renderer, runtime configuration or business data is touched.
Blast Radius: two `.agent/runs/**/run.json` result records plus this note; no source, contract,
menu, fixture or runtime artifact changes.

## Purpose

This note is the **single carrier-safe home** for the per-branch names of the eight remaining
`codex/*` origin references that have no exact-head merged pull request. `docs/` is not a
runtime-carrier root (`scripts`, `config`, `deploy`, `make`, `.agent`, `.github`), so migrating
the names here clears the carrier scan without relaxing any guard.

Previously the eight names were also listed literally inside the two run records
`.agent/runs/REMOTE-BRANCH-BACKLOG-RETIREMENT/run.json` and
`.agent/runs/REMOTE-BRANCH-CARRIER-RETIREMENT/run.json`, which made the retirement entry report
`eligible=0 skipped=8` (`referenced by runtime carrier`). Those two records now reference this
note by pointer and no longer contain the literal branch names.

## Owner authorization

Owner-directed backlog review, this session (2026-10-05), authorized **option 1**: retire the
eight unproven `codex/*` origin references in one reviewed-explicit round. This authorization
covers exactly these eight references — it does not broaden to any other branch, and it does not
relax the manifest schema, the recovery-bundle requirement, the exact-tip lease, the
`--force-with-lease` remote deletion, or any audit/gate assertion. `origin/main` identity and the
per-branch tip SHAs below are re-verified by the entry at dry-run and apply time; any drift fails
closed.

## Per-reference adjudication (ordinal order preserved in the run records)

| # | branch | remote tip (origin) | delta files | differing in main | verdict |
|---|--------|---------------------|-------------|-------------------|---------|
| 1 | `codex/backend-contract-lifecycle-authority-v1` | `77aa0689d5ca44bf0f8c4b7beb6c6637fd0677bf` | 226 | 128 | substantial_content_not_in_main; needs_owner_decision |
| 2 | `codex/contract-governance-closure-v1` | `74a44e4e486d22ad97b52cba5215f947fe7a8958` | 202 | 108 | substantial_content_not_in_main; needs_owner_decision |
| 3 | `codex/form-information-architecture-audit-v1` | `60870d90588245cd4a1886ad360dcf25c6defe97` | 93 | 93 | never_integrated; needs_owner_decision |
| 4 | `codex/long-running-business-iteration` | `2eae48075d17ccc5541b7335d82d9efef46a474d` | 106 | 92 | PR #126 CLOSED unmerged at this head (#124/#125 diff-head); needs_owner_decision |
| 5 | `codex/p0-scene-component-bridge-v1` | `9cce637eb7f984568394e01a91c85e011a1abff3` | 74 | 60 | never_integrated; needs_owner_decision |
| 6 | `codex/p0-ui5-scene-foundation-recovery-v2` | `4e1c7c8c270cbaf1c5f8215d6d005b1c8f902468` | 50 | 45 | never_integrated; needs_owner_decision |
| 7 | `codex/p0-ui5-scene-foundation-spike-v1-recovered` | `3923ef9076ddeb95362b8e7be34b180d5314b4d9` | 17 | 17 | never_integrated; needs_owner_decision |
| 8 | `codex/tdesign-enterprise-ui-foundation-v1` | `ccc73282be3f686c5a46f5e4515b18d2094597ad` | 72 | 72 | never_integrated; needs_owner_decision |

The ordinal labels `unproven-codex-reference-01..08` in
`.agent/runs/REMOTE-BRANCH-CARRIER-RETIREMENT/run.json` map to rows 1..8 above in order.

## Carrier-clear result

After this change, `git grep -l -F -e "codex/<name>"` over
`scripts config deploy make .agent .github` is empty for all eight names. The names live only in
this document, the untracked manifest `.runtime/retire/codex-backlog-manifest-20261005.json` and
its reports, and the recovery bundle.

## Evidence references

- Manifest (reviewed_explicit): `.runtime/retire/codex-backlog-manifest-20261005.json`
- Pre-retirement assessment: `.runtime/retire/codex-backlog-report-20261005.json`
- Entry: `make branch.retire.historical` (`scripts/ops/retire_historical_branch_refs.py`)
