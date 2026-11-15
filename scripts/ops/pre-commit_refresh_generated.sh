#!/usr/bin/env bash
# Pre-commit: auto-refresh tracked generated evidence so a source change never
# leaves stale derived artifacts. The Quick and push preflight remain read-only
# and fail only when a generator drifts or a derived file was edited by hand.
set -euo pipefail

if ! make --no-print-directory refresh.generated_evidence; then
  echo "❌ pre-commit: generated evidence could not be refreshed" >&2
  exit 1
fi

# Stage only the derived-artifact paths this refresh is allowed to touch.
git add -u \
  docs/engineering_convergence \
  contracts/generated \
  docs/audit/test_coverage_registry \
  docs/frontend_productization 2>/dev/null || true

if ! make --no-print-directory audit.verification.lane_coverage.check; then
  echo "❌ pre-commit: generated verification inventory has stale or unregistered dispositions" >&2
  echo "   reconcile the named targets/scripts before committing" >&2
  exit 1
fi

exit 0
