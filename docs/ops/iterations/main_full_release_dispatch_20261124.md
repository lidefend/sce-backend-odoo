# MAIN-FULL-RELEASE-DISPATCH-20261124

## Identity

- Initial base: `05762e9628c6b8c40045f66e5438c5a37d187441`
- Branch: `fix/main-full-release-dispatch-20261124`
- Formal product layer: P4 delivery tooling
- Standard vs customer-specific: platform engineering standard

## Problem

The scheduled release lane already performs a full exact-main audit through
five workflows. PR candidate dispatch is not applicable after merge, and the
existing frontend-only dispatch target cannot guarantee that the other four
producer/aggregate workflows were newly created for the same main SHA.

An operator therefore had to issue five ad hoc `gh workflow run` calls and
manually compare their identities. That does not satisfy the repository remote
write and evidence-binding rules.

## Implementation

Added:

- `make release.main_full EXPECTED_MAIN=<full-sha>`
- `scripts/ci/main_full_release_dispatch.py`
- `scripts/ci/test_main_full_release_dispatch.py`

The dispatch sequence is:

1. Require a clean worktree, authoritative repository and live `origin/main`
   equal to `EXPECTED_MAIN`.
2. Capture existing `workflow_dispatch` run IDs for all five workflows.
3. Dispatch only new runs on `main`:
   - `public_guard`
   - `professional_quality_gate`
   - `frontend_release_gate`
   - `merge_policy_gate`
   - `release_candidate_gate`
4. Reject timeout, omission, ambiguity, wrong SHA, wrong branch or wrong event.
5. Write an exact-main dispatch manifest.
6. Wait for all five runs and require every conclusion to be `success`.

The result is `operator_full_audit`. It is not written back as
`scheduled_mainline`. Both can establish exact-head/tree candidate-build
eligibility, but neither authorizes deployment.

## Manual-full discovery

The first manual full audit of main `05762e96` reached the complete backend
suite and exposed a separate baseline evidence defect:

`verify.test.coverage.registry` rejected five newly declared mainline test
groups because their ownership dispositions were absent from
`scripts/verify/test_coverage_registry.yaml`:

- `system_product_release`
- `industry_business_model_02`
- `p0_contract_producer_p0a`
- `p0_contract_producer_p0a_money_evidence`
- `p0_contract_producer_p0c`

The registry was seeded through its governed entry and reviewed. Four groups
are on-demand class-selected gates; `p0_contract_producer_p0a` remains explicit
known unwired debt with review deadline `2026-12-31`. No test was removed,
skipped, weakened or relabelled as passing.

The same manual full run also exposed a separate product-layer blocker:

- `frontend_release_gate` completed the build, acceptance stack and login probe,
  then failed the delivery-hardening browser journey for
  `payment.request/41?action_id=881&menu_id=560`.
- The page rendered `付款申请 · 加载失败` with the generic safe-page error after
  `ui.contract.v2/action_open` returned HTTP 200.

That page-loading failure is classified as `product_defect`, is outside this
P4-only branch, and is not hidden by retry or by weakening the browser gate.
The full release condition therefore correctly remained unsatisfied.

The route failure diagnostic was expanded in P4 so a failed record surface now
keeps bounded evidence for each `ui.contract.v2` response:

- HTTP status;
- operation, model, view type and record/action/menu identifiers;
- envelope `ok`, contract version and trace ID;
- stable error code and bounded error message;
- rendered product-page mode/state identity.

It does not save the full contract payload or business data. This is a
diagnostic capability, not a product fallback.

On a failed route, the acceptance-only `failure-contract.json` additionally
retains the last bounded synthetic contract responses so the exact decoder
failure can be reproduced offline. The artifact is marked
`source=synthetic_acceptance_fixture`; it is not a production payload capture.

## Boundaries

- No product code, contract, ACL, Record Rule, workflow semantics, database,
  fixture or deployment change.
- Required checks remain unchanged.
- The scheduled cron remains the independent scheduled-mainline observer.
- The manual target does not reuse prior successful runs as its own result.

## Validation

- `verify.ci.main_full_release.unit`: PASS, 5 tests.
- `verify.ci.scheduled_gates`: PASS, 110 tests.
- `verify.ci.workflow.contract`: PASS, 498 tests.
- Frontend incremental routing: PASS, 238 tests.
- Backend impact routing: PASS, 37 tests.
- `verify.test.coverage.registry`: PASS, 19 tests; all 229 groups are gated or
  explicitly dispositioned.
- `verify.frontend.delivery_hardening.guard`: PASS, 57 tests, including bounded
  route/contract failure diagnostics.
- `make ci.local.iteration`: PASS after the new route and unit target were
  selected.
- `make ci.delivery.freeze.prepare`: PASS; generated test inventory, coverage
  registry, complexity report and split plan are current.

Manual exact-main workflow-dispatch run `45301861483` / `45301869152` /
`45301875507` / `45301880538` / `45301884892`:

- `public_guard`: SUCCESS
- `merge_policy_gate`: SUCCESS
- `professional_quality_gate`: FAIL (`baseline_evidence_defect`, fixed in this
  candidate by coverage dispositions)
- `frontend_release_gate`: FAIL (`product_defect`, payment request page load)
- `release_candidate_gate`: FAIL closed because not all producers succeeded

Remote exact-head PR CI and the post-merge operator full audit are recorded
separately after their actual runs. Local PASS does not claim either.
