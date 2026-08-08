#!/usr/bin/env python3
"""Copy one governed production backup set to the daily acceptance host.

The program is installed and executed on the daily host.  It pulls six exact
files over the existing private SSH hop, validates the production backup
contract locally, and publishes the set atomically.  It never connects to a
database and never overwrites a completed backup set.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path

from production_backup_restore import validate_backup_set


BACKUP_ID = re.compile(r"^sc_production-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}$")
FILES = (
    "database.dump",
    "deployment-metadata.json",
    "filestore.tar.gz",
    "manifest.json",
    "SHA256SUMS",
)
SOURCE_HOST = "172.31.4.192"
SOURCE_ROOT = Path("/data/backups/sc_production")
TARGET_ROOT = Path("/data/backups/sc_production")
CONFIRMATION = "SYNC_VERIFIED_PRODUCTION_PAIR_TO_DAILY_ACCEPTANCE"


class SyncError(RuntimeError):
    pass


def _run(args: list[str]) -> None:
    completed = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if completed.returncode:
        detail = completed.stderr.decode(errors="replace").strip().splitlines()
        raise SyncError(detail[-1][:300] if detail else "backup transfer failed")


def sync(backup_id: str) -> dict:
    if os.environ.get("CONFIRM_PRODUCTION_ACCEPTANCE_BACKUP_SYNC") != CONFIRMATION:
        raise SyncError("exact production acceptance backup sync confirmation is required")
    if not BACKUP_ID.fullmatch(backup_id):
        raise SyncError("invalid production backup set identity")
    TARGET_ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
    if stat.S_IMODE(TARGET_ROOT.stat().st_mode) & 0o077:
        raise SyncError("target backup root permissions must not exceed 0700")
    final = TARGET_ROOT / backup_id
    if final.exists() or final.is_symlink():
        raise SyncError("completed target backup set cannot be overwritten")
    staging = Path(tempfile.mkdtemp(prefix=f".incoming-{backup_id}-", dir=TARGET_ROOT))
    staging.chmod(0o700)
    try:
        for name in FILES:
            source = f"root@{SOURCE_HOST}:{SOURCE_ROOT / backup_id / name}"
            target = staging / name
            _run([
                "scp", "-q", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
                "-i", "/root/.ssh/id_ed25519", "--", source, str(target),
            ])
            target.chmod(0o600)
        manifest = validate_backup_set(staging)
        os.replace(staging, final)
        return {
            "status": "PASS",
            "source_host": SOURCE_HOST,
            "backup_set_id": backup_id,
            "target": str(final),
            "backup_pair_verified": manifest["backup_pair_verified"],
            "database": manifest["database"],
            "production_database_write_count": 0,
        }
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backup-set-id", required=True)
    args = parser.parse_args()
    print(sync(args.backup_set_id))


if __name__ == "__main__":
    main()
