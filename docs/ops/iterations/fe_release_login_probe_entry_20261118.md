# Frontend release login probe entry (2026-11-18)

## Boundary

- Formal Product Layer: P0/P4
- Layer Target: frontend release entry plus activity-tab and canonical-navigation accessibility
- Module: `make/runtime_ops.mk`, verification-lane registration, shell guards and shared product-shell components
- Standard vs User-Specific: platform delivery verification standard

The page-identity and release browser targets called
`frontend_acceptance_login_probe.py` directly after starting the acceptance
backend. The same Make fragment already routes the performance probe through
`acceptance.runtime.login_probe`, which loads the managed profile, checks backend
runtime identity, and then invokes the same HTTP credential probe.

Why here: the observed 401 belongs to release verification wiring. No product
route, credential or backend behavior is changed.

Why not elsewhere:

- no contract, business action, permission or backend behavior change;
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
| `verify.frontend.navigation_shell.unit` | PASS; 29 final shell tests, 227 collected assertions across the target |
| `verify.frontend.state_dashboard.unit` | PASS; 25 Python tests plus all keyed activity-tab suites |
| `verify.frontend.standard_preview.unit` | PASS; 139 tests plus 42 policy checks |
| `ci.local.iteration` | PASS; 11 affected targets, 74 verification-lane tests, strict typecheck and lint |
| `verification lane coverage` | PASS; remote-only allowance remains 85 |

The first modified-tree browser attempt reached the new managed login entry but
was stopped by the release-snapshot clean-checkout gate. Browser execution is
therefore deferred to the committed candidate and is not reported as passed.

### Accessibility closure

The first clean-HEAD release browser reached login, performance, three real
journeys and all responsive viewports. It then failed on 26 blocking WCAG A/AA
findings, reduced to two shared P0 causes:

- `.activity-page-tabs[role=tablist]` owned a close `button`, violating required
  tablist children on every business page;
- the TDesign menu's scroll region contained no focusable menu item, preventing
  keyboard access on list, detail, form, dialog and error surfaces.

The P0 fix keeps the official components: only the active activity title is a tab
stop, the active tab is selected, Delete keeps close reachable, the pointer close
control is removed from the accessibility tree, and canonical navigation list
items become focusable with Enter/Space activation. The menu items deliberately
retain native list semantics; assigning `button` roles to `li` elements created
new invalid-list and nested-interactive findings and is not used.

Submenu keyboard activation now resolves the registered
`data-navigation-toggle="submenu"` control before dispatching a click. This is
required because TDesign 1.20.5 attaches submenu expansion to the inner submenu
`div`, not the outer `li`; clicking the outer `li` only works for leaf items. A
dedicated non-zero TypeScript test covers Enter and Space activation for both a
submenu toggle and a leaf item.

The first post-fix matrix removed all activity-tab critical findings. It exposed
that adding `button` roles to the vendor menu's `li` elements introduced invalid
list children and nested-interactive findings. The candidate now keeps those
elements as focusable native list items, preserves `aria-disabled`,
`aria-current` and `aria-expanded`, and handles Enter/Space directly.

### Final matrix

The final clean product candidate `afb3e7029c804dbd9c0774ff4bf792c05387747a` passed the
managed release browser matrix:

- J09 network/conflict recovery, J10 action authority and J11 company-switch work
  continuity all PASS;
- 17 accessibility scans over `wcag2a`, `wcag2aa`, `wcag21a` and `wcag21aa`
  report 0 violations, 0 blocking, 0 critical and 0 serious findings;
- 68 responsive page/viewport checks report zero horizontal overflow;
- all seven performance scenarios pass absolute and relative budgets;
- console, unhandled HTTP, page-error and unhandled runtime error collections are
  empty.

Runtime evidence is recorded in the run index as a non-reusable stage observation:
the target requires a clean product source and emits new source-bound browser
artifacts, while the remote `frontend_release_gate` remains the authoritative
reusable system check. The run record binds the exact profile, database, actor,
artifact hashes and final product SHA. Any successor commit is limited to run and
documentation files, so this product evidence carries forward without rerunning.

## Rollback

Revert this P0/P4 batch. No database or persistent runtime state requires restoration.
