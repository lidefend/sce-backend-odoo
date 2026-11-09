# B2 build identity and deployment receipt

Status: active

- Formal Product Layer: P0 platform identity with P4 deployment plumbing
- Layer Target: `smart_core` runtime identity, web build identity and governed daily deployment
- Branch baseline: `main@ed3525193bc9a7fd6731cdbbd427cbf867f57bfd`
- Excluded: business contracts, ACL, menus, models, business data and B3 image delivery

## Server baseline before deployment

- `/opt/projects/repos/sce-product-odoo` HEAD: `0b35cacecafeb3c1a078f031b8de9ccf5fb173fe`
- Demo and platform APIs already report the deployed SHA and frontend fingerprint.
- `/t/demo/build-info.json` currently falls through to SPA HTML.
- The server has no `.deployed.json` receipt.

Implementation and validation results are appended to this living record.

## Implementation

- `Vite` now defines `__SC_BUILD_SHA__`, `__SC_BUILD_TIME__`,
  `__SC_BUILD_ENV__` and `__SC_BUILD_VERSION__`, and emits
  `build-info.json` as a first-class build asset.
- The build identity includes the exact source SHA, build timestamp,
  deployment environment and product version. The existing canonical artifact
  fingerprint therefore covers the self-description as well as the JavaScript
  bundle.
- The session store exposes `source_revision`; the shared desktop/mobile
  sidebar footer renders `<prerelease> · <9-char SHA>`, shows the full SHA and
  build time on hover, and copies the complete identity on click.
- Daily frontend builds declare `SC_SOURCE_REVISION`, `SC_DEPLOY_ENV=daily` and
  the exact build time before Vite runs. The source-revision alignment entry
  writes both `SC_SOURCE_REVISION` and `SC_DEPLOY_ENV` to every selected duty.
- `/api/runtime-version` now separates deployment `environment` from the
  existing `runtime_environment` (`demo` or `dev`). This keeps demo-seed and
  runtime safety semantics intact while giving the deployment identity a
  single `daily` value.
- The daily release sequence now records a timestamped local receipt and the
  server-side `.deployed.json`, then verifies `build-info.sha`,
  `runtime-version.git_sha`, deployment git HEAD and `receipt.git_head`.
  Local receipts retain the newest 30 deployments.

## Focused validation

- `verify.daily.runtime.build_identity`: 8 tests PASS.
- `verify.daily.runtime.source_revision.align`: 8 tests PASS.
- `verify.daily.runtime.frontend.build`: 25 tests PASS.
- `verify.daily.runtime.release_orchestration.unit`: 51 tests PASS.
- `verify.platform.runtime_identity.unit`: 2 tests PASS.
- `verify.frontend.runtime_identity.unit`: 19 assertions PASS.
- `verify.frontend.dev.incremental.unit`: 102 tests PASS.
- `verify.frontend.standard_preview.unit`: 131 tests plus 42 Node assertions PASS.
- `verify.frontend.typecheck`: PASS.
- Focused ESLint on the changed frontend sources: PASS.
- `verify.frontend.build` at a fixed identity: PASS; `build-info.json` reports
  `sha=ed3525193bc9a7fd6731cdbbd427cbf867f57bfd`, `environment=daily`,
  `built_at=2026-11-10T00:00:00.000Z`, `version=1.0.0-rc.20`.
- The canonical frontend fingerprint was computed twice:
  `c87cbbf733cec363c37f3b586baa78bced9e24693a291a855db51738dbd73c0b`,
  byte-identical across both reads.

## Negative proof

`test_daily_runtime_build_identity.py` mutates each independent identity carrier
in turn: `build-info.sha`, demo runtime `git_sha`, deployment git HEAD and
`receipt.git_head`. Each mutation must produce a mismatch, so a four-way
identity disagreement cannot pass silently.

## Deployment and browser readback

The daily candidate deployment at `5932931824c0123f574ec1e40d5e4483dd544e18`
completed all nine governed steps:

- source bundle sync;
- frontend build and `build-info.json` generation;
- demo/platform duty refresh;
- deployment-environment alignment for both duties;
- published-face convergence;
- single-entry verification;
- timestamped receipt plus server `.deployed.json`;
- four-way build-identity verification.

Observed identities:

- build-info SHA: `5932931824c0123f574ec1e40d5e4483dd544e18`;
- demo runtime git SHA: `5932931824c0123f574ec1e40d5e4483dd544e18`;
- platform runtime git SHA: `5932931824c0123f574ec1e40d5e4483dd544e18`;
- receipt git HEAD: `5932931824c0123f574ec1e40d5e4483dd544e18`;
- frontend fingerprint:
  `08650b0a899e73445be9773bc13a8cc5b6de9a4c9933469860af8e84456cfe73`;
- environment: `daily`;
- eight demo/platform containers: running and healthy.

Browser walkthrough on `/platform-admin` displayed
`rc.20 · 593293182`; hover exposed the full SHA, build time and environment,
and click reported `已复制`. Browser console and page errors were zero.

Evidence:

- release sequence:
  `.runtime/final-acceptance/daily-deployed/release/candidate/5932931824c0123f574ec1e40d5e4483dd544e18/release.json`
- identity verification:
  `.runtime/final-acceptance/daily-deployed/release/candidate/5932931824c0123f574ec1e40d5e4483dd544e18/build-identity-verification.json`
- local receipt:
  `.runtime/final-acceptance/daily-deployed/daily/20261109T163037264000Z/receipt.json`
- page identity:
  `.runtime/b2-build-identity/page/page-identity.json`
- screenshot:
  `.runtime/b2-build-identity/page/build-identity-footer-1440.png`

Two pre-deployment failures were classified as P4 tooling defects and fixed:
the release orchestrator leaked parent make's frozen recursive arguments into
the duty-plan subprocess, and the duty stack did not forward `SC_DEPLOY_ENV`
into Odoo. Both were corrected with focused tests; a failed environment
alignment rolled back automatically before the successful deployment above.
