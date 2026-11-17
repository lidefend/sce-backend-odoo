# Mainline frontend release gate recovery (2026-11-17)

## Identity

- Branch: `fix/mainline-ci-release-gate-20261117`
- Baseline main: `b9909e8e103001a8e598c3575d77bcc58f1e8314`
- Formal product layer: P4 ops delivery tool
- Layer target: frontend release validation corpus and static release audit

## Observed failure

GitHub Actions scheduled run `frontend_release_gate` (`43999456147`) failed for
the exact mainline SHA above. Its uploaded `static.json` reports the `lint`
command with exit code 1 while the other static checks pass. The missing
downstream evidence files are consequences of that earlier lint failure.

The same failure reproduces locally with `make verify.frontend.lint`:

- `frontend/apps/web/scripts/canonical_form_presenter_test.ts:4351`
- `frontend/apps/web/scripts/canonical_form_presenter_test.ts:4412`

Both findings are `@typescript-eslint/no-explicit-any`.

## Ownership

The test corpus consumes contract types. The fix belongs in the P4 validation
corpus by using the already exported `ContractV2Snapshot` type. Ignoring the
scripts directory, disabling the ESLint rule, or changing the release gate
would hide the defect and is excluded.

## Scope and exclusions

Owned code is limited to the two typed snapshot declarations in
`canonical_form_presenter_test.ts` plus this run's agent metadata. Product
source, contract declarations, workflow checks, runtime configuration,
databases, fixtures, deployment, and unrelated lint warnings are excluded.

## Validation

The failing mainline command was reproduced before the edit:

- `make verify.frontend.lint`
- Result: failed with 2 errors and 4 warnings
- Blocking findings: explicit `any` at lines 4351 and 4412

After replacing both declarations with `ContractV2Snapshot`:

| Entry | Result | Evidence |
| --- | --- | --- |
| `make verify.frontend.canonical_form_presenter.unit` | PASS, 177 cases | `.runtime/agent-runs/MAINLINE-CI-RELEASE-GATE-20261117/canonical_form_presenter.log` |
| `make verify.frontend.lint` | PASS, 0 errors, 4 pre-existing warnings | `.runtime/agent-runs/MAINLINE-CI-RELEASE-GATE-20261117/frontend_release_lint.log` |
| `make ci.local.iteration` | PASS, required targets exited zero | `.runtime/frontend-dev-validation/executions/20261117T021956Z-3771048-700218010/receipt.json` |
| `make verify.ci.scheduled_gates` | PASS | terminal result; all scheduled-gate suites passed |
| `frontend_static_release_audit.py` with acceptance build variables | PASS, all 10 static checks | `artifacts/frontend-release-audit/static.json` and `.runtime/agent-runs/MAINLINE-CI-RELEASE-GATE-20261117/frontend_static_release_audit.log` |
| `make ci.delivery.freeze.prepare` | PASS, generated evidence current | no tracked generated-evidence drift |

The exact static audit evaluated the workspace at baseline commit
`b9909e8e103001a8e598c3575d77bcc58f1e8314` plus the owned dirty scope.
Local checks establish the candidate stage only. Current-head remote CI remains
pending until the fix branch is published and all required workflows pass.
