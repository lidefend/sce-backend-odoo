# Frontend Static Image Decoupling (2026-10-18)

## Objective

The custom frontend source lives in the main repository. It is built into
static assets and shipped in an independent nginx image. The Odoo runtime
image must not contain frontend assets, nginx, Node or npm.

## Executed Evidence

- Dev Odoo image assertions passed: no `/opt/sce/frontend`, no
  `/usr/share/nginx/html/index.html`, no `nginx`, `node` or `npm`; Odoo starts.
- Production Odoo image assertions passed with the same checks.
- Frontend image assertions passed: `index.html`, `.build-sha256`, `nginx`,
  `io.sce.frontend.sha256`; `/healthz` and `/` return 200.
- Local demo `sc-local-dev-nginx-1` mounts the main-repo `dist-dev`; `/web/login`,
  `/` and `/healthz` return 200.
- `make verify.frontend.static.image.decoupling`: 148 tests passed, receipt
  reusable; `make ci.local.iteration`: PASS.
- `test_production_release_contract` retains one pre-existing failure
  (`test_admin_identity_tool_has_a_python310_ci_runtime_gate`) whose workflow
  assertion is already absent at the baseline commit; it is unrelated to this batch.

## Contract

- Odoo image: `ODOO_IMAGE_REF` + `EXPECTED_IMAGE_DIGEST`.
- Frontend image: `FRONTEND_IMAGE_REF` + `EXPECTED_FRONTEND_IMAGE_DIGEST`.
- Both images share `SOURCE_SHA` revision but keep independent digests; identical
  refs are rejected.
- `image-manifest.json` schema v3 carries `frontend_*` archive, registry and
  scan fields. The product release manifest is v4 and fails closed when either
  image identity is missing or mismatched.

## Boundaries

No production deployment, registry push or shared-carrier write was performed.
