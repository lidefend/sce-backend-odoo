"""P4 exact-inventory preservation of demo files, without deleting any content.

Uses the installed immutable continuity resolver. Stops only the resolved demo
application before moving unreferenced bodies within its own volume. Unknown
files remain preserved outside the live database filestore, with a reversible
manifest. No database records, collection markers or backup assertions change.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import stat
import sys
import time


def digest(rows):
    return hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def checked_path(root, row):
    name = row["path"]
    if not re.fullmatch(r"[0-9a-f]{2}/[0-9a-f]{40}", name):
        raise RuntimeError("Not an exact store body path")
    target = root / name
    if root.is_symlink() or target.parent.is_symlink() or target.is_symlink():
        raise RuntimeError("Symlink refused")
    info = target.stat()
    if not stat.S_ISREG(info.st_mode):
        raise RuntimeError("Non-regular body refused")
    content = hashlib.sha1(target.read_bytes()).hexdigest()
    if info.st_size != row["size"] or content != row["sha1"] or name.split("/")[1] != content:
        raise RuntimeError("File content drift")
    return target


def move_preserved(source, destination, rows):
    """Same-volume move; prevalidate all bodies and reverse partial moves on error."""
    if destination.exists() or destination.is_symlink():
        raise RuntimeError("Preservation destination already exists")
    for row in rows:
        checked_path(source, row)
    destination.mkdir(mode=0o700)
    moved = []
    try:
        if source.stat().st_dev != destination.stat().st_dev:
            raise RuntimeError("Preservation must stay on the same volume")
        for row in rows:
            original = checked_path(source, row)
            saved = destination / row["path"]
            saved.parent.mkdir(mode=0o700, exist_ok=True)
            os.rename(original, saved)
            moved.append(row)
            checked_path(destination, row)
    except BaseException:
        for row in reversed(moved):
            original = source / row["path"]
            if original.exists():
                raise RuntimeError("Rollback collision; preserved manifest must be reconciled")
            os.rename(destination / row["path"], original)
        raise


def restore_preserved(source, destination, rows):
    for row in rows:
        checked_path(destination, row)
        if (source / row["path"]).exists():
            raise RuntimeError("Restore would overwrite an existing live file")
    for row in rows:
        (source / row["path"]).parent.mkdir(exist_ok=True)
        os.rename(destination / row["path"], source / row["path"])


def snapshot(c, contract):
    scan = c._scan_filestore(contract)
    rows = c._attachment_store_rows(contract)
    inventory = c._classify_filestore(scan, rows)
    if inventory["missing_count"] or inventory["checksum_mismatch_count"] or scan.get("irregular"):
        raise RuntimeError("Broken referenced attachment pair or irregular entries")
    referenced = dict(rows)
    unknown = [r for r in scan["files"] if r["path"] not in referenced
               and not r["path"].startswith("checklist/")]
    if len(unknown) != inventory["unknown_entry_count"]:
        raise RuntimeError("Inventory includes unsupported marker/pending classification")
    for row in unknown:
        if not re.fullmatch(r"[0-9a-f]{2}/[0-9a-f]{40}", row["path"]) or row["path"].split("/")[1] != row["sha1"]:
            raise RuntimeError("Unknown body is not content-addressed")
    return unknown, inventory, c._sentinels(contract)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("plan", "apply"))
    parser.add_argument("--tool-sha", required=True)
    parser.add_argument("--expected-source", required=True)
    parser.add_argument("--expected-uuid", required=True)
    parser.add_argument("--expected-inventory", default="")
    args = parser.parse_args()
    for value in (args.tool_sha, args.expected_source):
        if not re.fullmatch(r"[0-9a-f]{40}", value):
            raise RuntimeError("Exact SHA required")
    root = Path("/opt/sce/deployment-tools") / args.tool_sha
    if (root / "DEPLOYMENT_TOOL_SHA").read_text().strip() != args.tool_sha:
        raise RuntimeError("Immutable tool identity mismatch")
    sys.path.insert(0, str(root / "scripts/ops"))
    import daily_candidate_data_continuity as c
    contract = c._load_contract(root / "scripts/ops/daily_candidate_data_continuity_contract_v1.json")
    if contract["duty"] != "demo":
        raise RuntimeError("Only the declared demo duty is supported")
    runtime = c._assert_runtime(contract)
    if runtime["source_revision"] != args.expected_source or runtime["source_worktree_dirty"]:
        raise RuntimeError("Deployed source differs")
    rows, inventory, sentinels = snapshot(c, contract)
    if sentinels["database_uuid"] != args.expected_uuid:
        raise RuntimeError("Database generation changed")
    plan = {"schema": "daily_demo_filestore_preservation.v1", "duty": "demo",
            "runtime": runtime, "database_uuid": args.expected_uuid, "files": rows,
            "inventory_sha256": digest(rows), "before": inventory,
            "database_writes": 0, "content_deleted": 0}
    if args.phase == "plan":
        print(json.dumps(plan, indent=2))
        return
    if os.environ.get("CONFIRM_DEMO_FILESTORE_PRESERVE") != "PRESERVE_EXACT_UNREFERENCED_DEMO_FILES":
        raise RuntimeError("Exact preservation confirmation required")
    if not rows or args.expected_inventory != digest(rows):
        raise RuntimeError("Approved inventory differs or is empty")
    container = runtime["odoo_container_id"]
    inspect = c._inspect(container)
    mounts = [m for m in inspect["Mounts"] if m.get("Name") == contract["odoo_data_volume"]
              and m.get("Destination") == c.ODOO_DATA_MOUNT and m.get("Type") == "volume"]
    if len(mounts) != 1:
        raise RuntimeError("Declared volume mount missing")
    volume = Path(mounts[0]["Source"])
    if not volume.is_absolute() or volume.is_symlink():
        raise RuntimeError("Unsafe volume location")
    source = volume / "filestore" / contract["filestore_scope"]
    if source.resolve() != source:
        raise RuntimeError("Symlink in live filestore ancestry")
    parent = volume / "acceptance-preserved"
    if parent.is_symlink():
        raise RuntimeError("Unsafe preservation parent")
    parent.mkdir(mode=0o700, exist_ok=True)
    lock_fd = os.open(parent / ".lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    destination = parent / args.expected_inventory
    manifest = parent / (args.expected_inventory + ".json")
    if manifest.exists() or destination.exists():
        raise RuntimeError("Preservation already recorded; read back before retry")
    plan.update({"status": "prepared", "live_root": str(source), "preserved_root": str(destination),
                 "odoo_data_volume": contract["odoo_data_volume"],
                 "restore_rule": "Stop exact demo container; verify every saved hash and absence of live collision; move each manifest path back; restart and read back."})
    manifest.write_text(json.dumps(plan, indent=2) + "\n")
    manifest.chmod(0o600)
    moved = False
    def interrupted(signum, frame):
        raise RuntimeError("Preservation interrupted; restoring files and service")
    signal.signal(signal.SIGTERM, interrupted)
    try:
        c._run(["docker", "stop", "--time", "30", container])
        if c._inspect(container)["State"]["Running"]:
            raise RuntimeError("Demo application did not stop")
        # Re-read database references after all application workers have stopped.
        if c._sentinels(contract) != sentinels:
            raise RuntimeError("Database changed during preservation preflight")
        references = dict(c._attachment_store_rows(contract))
        if any(row["path"] in references for row in rows):
            raise RuntimeError("A selected file is now referenced")
        move_preserved(source, destination, rows)
        moved = True
        if c._sentinels(contract) != sentinels:
            raise RuntimeError("Database changed during preservation")
        plan["status"] = "preserved"
        manifest.write_text(json.dumps(plan, indent=2) + "\n")
    except BaseException:
        if moved:
            restore_preserved(source, destination, rows)
        plan["status"] = "failed_files_restored"
        manifest.write_text(json.dumps(plan, indent=2) + "\n")
        raise
    finally:
        c._run(["docker", "start", container])
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        state = c._inspect(container)["State"]
        if state.get("Running") and state.get("Health", {}).get("Status", "healthy") == "healthy":
            break
        time.sleep(2)
    else:
        raise RuntimeError("Demo health recovery timed out; preserved manifest retained")
    after = c.baseline(contract)
    for row in rows:
        checked_path(destination, row)
    plan.update({"status": "PASS", "after": after, "manifest": str(manifest),
                 "restoration_verified": "all preserved bodies retain exact original hashes"})
    manifest.write_text(json.dumps(plan, indent=2) + "\n")
    print(json.dumps(plan, indent=2))


if __name__ == "__main__":
    main()
