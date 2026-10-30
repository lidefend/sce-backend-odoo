# P4 Candidate Acceptance Probe Identity — Batch Record

Branch: `fix/candidate-acceptance-probe-identity`
Base: `29d34c171304c09d4e02b69f70d547bc49379c73`

## Layer declaration

- Formal Product Layer: P4 ops delivery tool
- Layer Target: frontend acceptance runtime carrier
- Module: frontend acceptance harness

## Fixed gaps

1. `verifyServedIdentity` did not stamp the isolated entry headers on the external
   candidate identity probe and did not verify the served namespace. It now reads
   `SC_ENTRY_NAMESPACE/AUDIENCE/SHARED_SECRET/ROUTE_VERSION`, fails closed when they
   are missing for candidate, and verifies the served `namespace_id`.
2. `verify.frontend.list_surface_structure.browser` hardcoded the shared carrier
   (`5180` / `sc_frontend_acceptance`). It now resolves profile-aware frontend/API
   URL and database and fails closed on unknown profiles.

## Exclusions

No product contract, view, ACL, record rule, approval, navigation or business data
changes. No merge or deploy.
