# Authentication Surface Professionalization Gap Audit v1

Date: 2026-08-31
Status: current-state audit
Scope: `frontend/apps/web` authentication entry, activation, recovery, API-key management, and their governance guards

## Identity and boundary

- Audit type: static, reproducible, read-only; no browser, runtime, database, fixture, or remote mutation.
- Formal Product Layer: P0 platform kernel product.
- Layer Target: frontend authentication surface governance and professionalization boundary.
- Modules:
  - `frontend/apps/web/src/views/LoginView.vue`
  - `frontend/apps/web/src/views/AccountActivationView.vue`
  - `frontend/apps/web/src/views/PasswordRecoveryView.vue`
  - `frontend/apps/web/src/views/ApiKeyManagementView.vue`
  - `frontend/apps/web/src/app/presentation/professionalComponentRegistry.ts`
  - `scripts/verify/frontend_page_contract_boundary_guard.py`
  - `scripts/verify/frontend_page_contract_orchestration_consumption_guard.py`
  - `scripts/verify/auth_credential_frontend_guard.py`
  - `scripts/verify/user_activation_security_contract.py`

## Current evidence summary

| Surface | Current governance state | Professionalization state | Evidence |
| --- | --- | --- | --- |
| Login | Consumes page contract sections/actions | Partial | `LoginView.vue`, `frontend_page_contract_orchestration_consumption_guard.py` |
| Platform-admin login entry | Reuses login surface with route-aware runtime | Partial | `router/index.ts`, `frontend_platform_runtime_config_guard.py` |
| Account activation | Dedicated security guard; consumes page contract sections/actions | Partial | `AccountActivationView.vue`, `user_activation_security_contract.py`, `frontend_auth_surface_guard.py` |
| Password recovery | Dedicated page; consumes page contract sections/actions | Partial | `PasswordRecoveryView.vue`, `frontend_page_contract_boundary_guard.py`, `frontend_auth_surface_guard.py` |
| API-key management | Dedicated security guard; explicit high-sensitivity exemption from ordinary auth page-contract family | Partial and split | `ApiKeyManagementView.vue`, `auth_credential_frontend_guard.py`, `frontend_auth_surface_guard.py` |
| Professional component registry | Generic families plus minimal auth family keys | Seeded | `professionalComponentRegistry.ts`, `frontend_auth_surface_guard.py` |

## Findings

### F1. Authentication flow is governed by multiple parallel mechanisms, not one professionalized surface model

`LoginView.vue`, `AccountActivationView.vue`, and `PasswordRecoveryView.vue` now consume `usePageContract(...)`, including contract-driven actions and section enablement. `ApiKeyManagementView.vue` remains outside the ordinary auth page-contract family by explicit high-sensitivity decision.

This is not an immediate runtime bug. It is a productization gap: one authentication journey is split between:

- page-contract orchestration;
- bespoke page-local composition;
- security-only companion guards.

The remaining gap is narrower than before. Login, activation, and recovery now share one governed auth entry model, but high-sensitivity credential management still uses a dedicated surface. Future MFA, approval challenge, device trust, SSO fallback, or managed credential confirmation can extend the auth surface more cleanly than before, but the sensitive branch still needs explicit professional ownership.

### F2. Boundary guard now narrows the auth exemption to the explicit high-sensitivity surface

`frontend_page_contract_boundary_guard.py` now requires `AccountActivationView.vue` and `PasswordRecoveryView.vue` to consume the page-contract mainline. Only `ApiKeyManagementView.vue` remains outside that family, and `frontend_auth_surface_guard.py` now checks that this stays an explicit high-sensitivity exception instead of a silent drift.

### F3. Authentication-specific professional component keys now exist, but are only minimally seeded

`professionalComponentRegistry.ts` now contains a minimal auth family:

- `sc.auth.credential_entry`
- `sc.auth.secret_confirmation`
- `sc.auth.challenge_status`
- `sc.auth.one_time_secret`
- `sc.auth.support_action`

This closes the prior "no auth family at all" gap. The family is still only seeded:

- base field;
- relation field;
- detail collection;
- business value;
- action;
- readable value fallback.

No auth-specific renderer or page pattern consumes those keys yet. Authentication UX therefore still depends partly on page-local markup and security-specialized surfaces, but future contract-driven extension now has a reserved platform vocabulary.

### F4. Sensitive auth surfaces have security guards, but not unified professionalization guards

The repository already protects sensitive flows well in isolation:

- `user_activation_security_contract.py` enforces POST-only, no-store, no query token, no browser persistence, and `save_session=False` for activation/recovery bootstrap routes.
- `auth_credential_frontend_guard.py` enforces one-time secret display, no browser storage, no console logging, and evidence-capture denial for API-key display.

These guards prove security boundary intent. `frontend_auth_surface_guard.py` now adds one cross-surface professionalization check for login, activation, recovery, API-key sensitivity markers, page-contract routing, and minimal auth registry ownership. The remaining gap is not absence of a unified guard, but that the sensitive API-key surface is still intentionally separate from the ordinary auth page-contract family.

- page contract policy;
- auth-specific component family;
- sensitive-message presentation model;
- action model;
- readonly/support-state model.

### F5. Authentication pages still own local visual chrome and structure directly

`AccountActivationView.vue` and `ApiKeyManagementView.vue` still define page-local layout and styling for sensitive form surfaces. This is not automatically wrong, but it is a sign that the auth surface has not yet converged on shared professional abstractions comparable to the repository's recent primitive/professional adapter tightening.

The current state is therefore:

- security-sensitive enough to deserve explicit guards;
- important enough to deserve product-specific UX;
- not yet abstracted enough to count as a closed professionalized surface.

## What is not missing

The following are already present and should not be misclassified as missing:

1. Authentication authority boundary.
   `res.users`, Odoo password hashing/authentication, activation purpose binding, and API-key native authority are already frozen in architecture docs.
2. Runtime route and initialization control for login.
   Login redirects, `session.loadAppInit()`, route authority continuation, and platform-admin entry handling are already governed.
3. Sensitive evidence handling for one-time API-key display.
   The repository explicitly blocks unsafe screenshot/trace capture while the secret marker is visible.
4. Activation/recovery transport safety.
   The public bootstrap exceptions are constrained to dedicated POST routes and are forbidden from becoming a wildcard auth transport.

The gap is therefore not "authentication has no rules". The gap is "authentication does not yet share one professionalized frontend surface model".

## Gap classification

| Gap | Layer owner | Current impact | Required follow-up |
| --- | --- | --- | --- |
| API-key management remains outside ordinary auth page-contract family | P0 frontend auth surface | medium | either keep explicit high-sensitivity separation or define a dedicated auth-sensitive contract family |
| Auth professional component family is seeded but not yet consumed by specialized renderers | P0 frontend professional registry | medium | add auth-focused renderer/pattern ownership as needed |
| Sensitive auth UX modeled page-by-page | P0 frontend renderer/patterns | low to medium | converge on shared auth pattern primitives where security policy allows |

## Recommended closure order

### Batch A. Freeze auth-surface boundary

Goal: define one authoritative statement of which surfaces belong to the authentication journey.

Scope:

- login;
- platform-admin login;
- account activation;
- password recovery;
- API-key management.

Deliverables:

- auth-surface audit doc;
- explicit guard inventory;
- no product behavior change.

### Batch B. Introduce auth page-contract policy for exempt auth pages

Status: completed for activation and recovery.

Goal: remove the previous asymmetry where only `LoginView.vue` was in the page-contract mainline.

Target:

- `AccountActivationView.vue`
- `PasswordRecoveryView.vue`
- optionally `ApiKeyManagementView.vue` if secret-display policy can remain explicit and fail-closed.

Requirements:

- section toggles, texts, and page actions move under contract governance;
- security-only invariants remain in dedicated guards;
- no frontend inference of auth method or business semantics.

### Batch C. Add a minimal auth professional component family

Status: seeded.

Goal: avoid future authentication features being added as raw page-local structures.

Suggested initial family:

- `sc.auth.credential_entry`
- `sc.auth.secret_confirmation`
- `sc.auth.challenge_status`
- `sc.auth.one_time_secret`
- `sc.auth.support_action`

This family should remain P0 and generic. It must not encode customer-specific identity policy, approval workflow, or tenant-specific recovery rules.

### Batch D. Replace exemptions with explicit auth-surface guard coverage

Status: partially completed.

Goal: convert "allowed exception" into "governed special surface".

Suggested guard:

- `frontend_auth_surface_guard.py`

Minimum responsibilities:

- auth pages must either consume `usePageContract(...)` or be listed with a narrow, justified exception reason;
- auth pages must not use browser persistence for secrets;
- secret-bearing surfaces must expose evidence-sensitive markers;
- auth-surface actions must route through approved contract/runtime actions rather than page-local ad hoc navigation.

### Batch E. Decide whether API-key management is part of the same page-contract family or a deliberately separate high-sensitivity surface

This decision must be explicit. Both are valid, but only if declared:

- Option 1: include API-key management in auth page-contract governance, while preserving its dedicated security guard.
- Option 2: keep API-key management separate, but classify it as an auth-adjacent high-sensitivity admin surface with its own professional family.

Current repository state has not made that decision explicit enough.

## Proposed acceptance criteria for closure

1. No authentication page remains exempt without a reasoned, machine-checked exception class.
2. Login, activation, and recovery all consume one declared auth page-contract policy surface.
3. Auth-focused professional components exist for at least credential entry, support actions, and one-time secret display.
4. Security guards remain independent and fail-closed; professionalization must not weaken them.
5. Future auth features can be added by extending the auth surface model, not by creating another page-local exception.

## Recommended next exact step

Continue the P0 `auth-surface` governance topic:

1. keep `frontend_auth_surface_guard.py` as the explicit auth-surface gate;
2. decide whether API-key management belongs inside or adjacent to the auth page-contract family;
3. introduce auth-specific renderer or pattern ownership only when a new auth capability actually needs it.
