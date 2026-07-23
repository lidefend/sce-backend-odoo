#!/usr/bin/env bash
set -euo pipefail

echo "[candidate.publish] DENY: legacy manifest-mutating publisher is disabled." >&2
echo "[candidate.publish] Use ENV=dev make release.publish VERSION=... CANDIDATE_ATTEMPT_ID=... EXPECTED_SOURCE_SHA=..." >&2
exit 2
