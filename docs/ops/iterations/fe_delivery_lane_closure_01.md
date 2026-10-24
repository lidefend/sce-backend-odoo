# FE-DELIVERY-LANE-CLOSURE-01

## Classification

Deterministic contract/frontend tests: `verify.native_advisory.unit`,
`verify.node_component_capabilities.unit`, `verify.node_component_validation.unit`,
`verify.onchange.feedback_evaluation.unit`, `verify.record_error_proof.unit`,
`verify.frontend.feedback_evaluation.unit`, `verify.frontend.node_component.unit`,
`verify.frontend.project_detail_summary.browser`.

Runtime feedback acceptance: config preview, two HTTP evidence entries, and two
browser ticket lanes. Deployment post-check: daily runtime entry identity.

## Execution record

The eight deterministic targets are wired into the existing contract and form
runtime graph. The five feedback runtime entries and the daily post-deployment
identity entry have explicit bundle lanes. No Quick/runtime coupling was added.

Results:

- lane audit: PASS, zero-reference targets 642 (baseline 643), unregistered 0;
- lane audit unit: 73 tests PASS;
- backend offline units: PASS;
- frontend node/feedback/summary units: PASS, including 28 summary browser checks;
- Playwright vendor coupling guard: PASS, 7 tests;
- CI workflow contract: PASS, 79 tests;
- runtime/deployment bundle plans: verified with `make -n`;
- guard registry: PASS after prerequisites were merged into the original target
  declarations instead of duplicate rules;
- repeated generated-report refresh: stable.

The pushed CI run `40069199108` exposed an environment routing defect: the
summary Playwright probe ran in the `standard` frontend lane, but that lane only
restored and installed Chromium for `full`. The probe remains part of the shared
`verify.contract_form_runtime_state.behavior` target, so both exact-head Quick
and the remote frontend lane exercise it. Standard and full frontend lanes now
restore the lockfile-keyed Playwright cache and install Chromium when the cache
misses; the `skip` lane remains unchanged.

## Evidence input policy correction

The exact-head merge gate then exposed a second systemic issue: the acceptance
policy treated every `make/**` and `scripts/ci/**` change as an input to every
runtime suite. A Quick-only edit in `make/ci.mk` therefore invalidated the
presentation, list and relation runtime receipts even though their executable
surfaces were unchanged.

The registry now declares suite-local file inputs plus exact Make targets and
variables. The fingerprint contains only those target/variable stanzas, while a
missing configured target or variable at the evaluated head remains fail-closed.
For the current transition:

- `frontend_presentation` input identity is unchanged from `aef7ae51…`;
- `list_surface_structure` input identity is unchanged from `aef7ae51…`;
- `relation_roundtrip` changes because its Make entrypoint now passes the
  governed relation login and resolution variables, so it must run at the new
  head.

The recorder permits a reviewed fingerprint-policy migration only when the
suite inputs computed at the old and new heads are identical; evidence bytes are
still revalidated and the previous digest is retained for audit. Unrelated Make
or CI changes must no longer invalidate runtime evidence.
