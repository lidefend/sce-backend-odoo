# Platform browser probe per-entry credentials (2026-10-20)

## Scope

P4 ops delivery tool. This batch closes the registered follow-up from
`PLATFORM-ADMIN-CREDENTIAL-MECHANISM-20261020`: the path-namespace browser probe
hard-coded the demo password for both entries.

## Change

- `scripts/verify/path_ns_c_s4_browser_probe.mjs` no longer carries a literal
  password. The demo entry reads `SC_DEMO_USER_PASSWORD`; the platform entry
  reads `SC_PLATFORM_ADMIN_PASSWORD`.
- A missing variable fails closed with exit code 2 before Playwright is loaded.
- The same-name `admin` identity is retained so the probe still proves
  cross-namespace isolation; only the secrets become entry-scoped.
- `scripts/verify/test_path_ns_c_s4_browser_probe_credentials.py` guards the
  contract: no literal password, both governed variables present, credentials
  resolved before Playwright, and the login form fills the resolved values.

## Classification

The probe is verification tooling, not runtime product code. It therefore lives
under `scripts/verify/` instead of `scripts/ops/`: `scripts/ops/**` is bound to
the `ops-runtime` acceptance lane, while `scripts/verify/**` is classified as
governance static. Moving it keeps the acceptance binding truthful instead of
demanding deployed-runtime evidence for a tool the deployment never loads. The
two retired `scripts/ops/...` paths are recorded in the run scope as removals.

## Verification

`make verify.path_namespace.acceptance.unit` runs the existing path-namespace
acceptance unit plus the new credential-contract unit. Missing credentials were
also exercised directly; the probe exits before browser startup.

## Risk and rollback

The probe is evidence tooling, not runtime product code. Reverting the script and
its unit test restores the previous behaviour without touching deployment state.

## Next step

A later platform-entry change reruns the probe with the two governed variables
supplied by the operator's environment. No credential value is recorded here.
