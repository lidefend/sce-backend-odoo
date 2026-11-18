# Frontend release login probe entry (2026-11-18)

## Boundary

- Formal Product Layer: P4
- Layer Target: frontend page-identity and delivery-hardening browser login entries
- Module: `make/runtime_ops.mk`, verification-lane registration, delivery-hardening and release-local entry tests
- Standard vs User-Specific: platform delivery verification standard

The page-identity and release browser targets called
`frontend_acceptance_login_probe.py` directly after starting the acceptance
backend. The same Make fragment already routes the performance probe through
`acceptance.runtime.login_probe`, which loads the managed profile, checks backend
runtime identity, and then invokes the same HTTP credential probe.

Why here: the observed 401 belongs to release verification wiring. No product
route, credential or backend behavior is changed.

Why not elsewhere:

- no frontend, contract, business action or permission change;
- no acceptance credential or database mutation;
- no retry increase, assertion relaxation or browser-result substitution.

Blast radius: the login entries used by `verify.frontend.page_identity.browser`
and `verify.frontend.delivery_hardening.release.browser`, plus their explicit
verification-lane registrations.

## Evidence

- Baseline: `main@129df3827f4e8cffbc8302d626ec590ff63c14d9`.
- The initial governed release browser run stopped at the direct login script with
  a sanitized opaque HTTP 401 after fixture and release snapshot passed.
- The separately governed `acceptance.runtime.login_probe` then passed HTTP 200
  against the same backend, P4 profile and fixture actor.
- This establishes a validation-entry defect: the browser targets bypass the
  managed login path already present in the same Make fragment.
- Incremental validation exposed the matching lane-registration drift:
  `scripts/dev/acceptance_artifact.py` is remote-only but was not frozen. Both
  direct-probe entries are replaced by the acceptance helper registration, so the
  remote-only allowance remains 85 rather than expanding.

## Acceptance

- Page identity and release browser use the managed login target.
- Focused guards have non-zero tests and reject direct-script regression while
  preserving cleanup, backend, login and frontend ordering.
- The managed browser entry is rerun and its real result is recorded.

## Validation

| Check | Result |
| --- | --- |
| `verify.frontend.delivery_hardening.guard` | PASS; 17 tests |
| `verify.frontend.standard_preview.unit` | PASS; 139 tests plus 42 policy checks |
| `ci.local.iteration` | PASS; 5 affected targets, 74 verification-lane tests |
| `verification lane coverage` | PASS; remote-only allowance remains 85 |

The first modified-tree browser attempt reached the new managed login entry but
was stopped by the release-snapshot clean-checkout gate. Browser execution is
therefore deferred to the committed candidate and is not reported as passed.

## Rollback

Revert this P4 batch. No database or runtime state requires restoration.
