# Frontend runtime debug opt-in follow-up

- Branch: `fix/frontend-runtime-debug-flag-20261110`
- Main baseline: `ca032b92dd1131485313b9299b5e799c67f1d525`
- Layer: P0 generic frontend diagnostic logging
- Owner: `frontend/apps/web/src/utils/logger.ts`

## Trigger

The post-merge independent review found that `DEBUG_INTENT=1` and `?debug=1`
were resolved but still gated behind `DEV=true`. Non-development acceptance
builds therefore reached debug branches while the centralized logger discarded
the output.

## Correction

Runtime opt-in is now independent from build-time development defaults:

- `DEV=true` plus `VITE_DEBUG_LOGS` enables configured development logs.
- Explicit `DEBUG_INTENT=1` or `?debug=1` enables debug/info in any build.
- Production without explicit opt-in still emits only errors.

## Verification

- `make verify.frontend.console.guard`: PASS, 7 guard tests plus the logger
  runtime probe covering quiet, verbose, production quiet, non-development
  storage opt-in and non-development URL opt-in.
- `make verify.frontend.typecheck.strict`: PASS.
- `make verify.frontend.lint.src`: PASS, 0 errors and 4 existing warnings.

## Remaining

- Clean exact-head iteration.
- PR publication and exact-head remote checks.
- Protected merge and main readback.
