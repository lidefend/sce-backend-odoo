#!/usr/bin/env bash
set -euo pipefail

# Historical entry point retained to fail closed. Repository synchronization is
# exclusively GitHub main -> Gitee main through mirror_main_gitee.sh.
echo "[gitee_github_mirror] BLOCKED reverse_sync_disabled" >&2
exit 2
