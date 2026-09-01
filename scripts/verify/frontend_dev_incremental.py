#!/usr/bin/env python3
"""Run the smallest registered frontend checks affected by live source changes.

This is a development feedback tool.  It deliberately never builds a candidate,
captures browser evidence, refreshes generated reports, or computes a candidate
fingerprint.  Those operations remain part of the one-shot exact-head
publication qualification flow.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WATCH_ROOTS = (
    "frontend/apps/web/src",
    "frontend/apps/web/scripts",
    "scripts/verify/frontend_",
)
STATE_PATH = ROOT / ".runtime/frontend-dev-validation/status.json"


@dataclass(frozen=True)
class Rule:
    fragments: tuple[str, ...]
    targets: tuple[str, ...]


RULES = (
    Rule((
        "/views/LoginView.vue",
        "/views/AccountActivationView.vue",
        "/views/PasswordRecoveryView.vue",
    ), (
        "verify.frontend.auth_credential.guard",
        "verify.frontend.auth_surface.guard",
        "verify.frontend.page_pattern_reference_parity.unit",
    )),
    Rule(("/layouts/AppShell.vue", "/layouts/AppShell.css", "/navigation/"), (
        "verify.frontend.navigation_shell.unit",
        "verify.frontend.page_pattern_reference_parity.unit",
    )),
    Rule(("/components/design-system/",), (
        "verify.frontend.primitive_adapter.unit",
        "verify.frontend.page_pattern_reference_parity.unit",
    )),
    Rule(("/pages/contractForm/", "/components/template/"), (
        "verify.frontend.canonical_form_presenter.unit",
        "verify.frontend.product_page_pattern.unit",
        "verify.frontend.page_pattern_reference_parity.unit",
    )),
    Rule(("/components/action/", "/components/product-list/"), (
        "verify.frontend.collection_action_toolbar.unit",
        "verify.frontend.page_pattern_reference_parity.unit",
    )),
    Rule(("scripts/verify/frontend_page_pattern_reference_parity_guard.py",), (
        "verify.frontend.page_pattern_reference_parity.unit",
    )),
)
FALLBACK_TARGET = "verify.frontend.typecheck.strict"
FORBIDDEN_DEVELOPMENT_TARGET_PARTS = ("quick", "build", "browser", "release", "fingerprint")


def select_targets(paths: list[str]) -> list[str]:
    selected: set[str] = set()
    frontend_changed = False
    for path in paths:
        normalized = path.replace("\\", "/")
        frontend_changed = frontend_changed or normalized.startswith("frontend/apps/web/")
        for rule in RULES:
            if any(fragment in normalized for fragment in rule.fragments):
                selected.update(rule.targets)
    if frontend_changed and not selected:
        selected.add(FALLBACK_TARGET)
    targets = sorted(selected)
    if any(part in target for target in targets for part in FORBIDDEN_DEVELOPMENT_TARGET_PARTS):
        raise RuntimeError("development validation selected a candidate-only target")
    return targets


def watched_files() -> list[Path]:
    files: set[Path] = set()
    for relative in WATCH_ROOTS:
        source = ROOT / relative
        if source.is_file():
            files.add(source)
        elif source.is_dir():
            files.update(path for path in source.rglob("*") if path.is_file())
    return sorted(files)


def content_snapshot() -> dict[str, str]:
    result: dict[str, str] = {}
    for path in watched_files():
        relative = path.relative_to(ROOT).as_posix()
        result[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def changed_paths(before: dict[str, str], after: dict[str, str]) -> list[str]:
    return sorted(path for path in before.keys() | after.keys() if before.get(path) != after.get(path))


def write_state(*, status: str, paths: list[str], targets: list[str], returncode: int | None) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schemaVersion": 1,
        "mode": "development_incremental",
        "status": status,
        "changedPaths": paths,
        "targets": targets,
        "returncode": returncode,
        "candidateEvidence": False,
        "heavyValidationIncluded": False,
    }
    STATE_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_targets(paths: list[str]) -> int:
    targets = select_targets(paths)
    if not targets:
        write_state(status="no_relevant_change", paths=paths, targets=[], returncode=0)
        print("[frontend.dev.incremental] no relevant frontend validation")
        return 0
    print(f"[frontend.dev.incremental] paths={len(paths)} targets={','.join(targets)}", flush=True)
    write_state(status="running", paths=paths, targets=targets, returncode=None)
    result = subprocess.run(["make", "--no-print-directory", *targets], cwd=ROOT, check=False)
    status = "passed" if result.returncode == 0 else "failed"
    write_state(status=status, paths=paths, targets=targets, returncode=result.returncode)
    print(f"[frontend.dev.incremental] {status.upper()} returncode={result.returncode}")
    return result.returncode


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--watch", action="store_true", help="watch source content and validate after each settled batch")
    parser.add_argument("--path", action="append", default=[], help="validate an explicit repository-relative path")
    parser.add_argument("--interval", type=float, default=0.75)
    parser.add_argument("--debounce", type=float, default=0.8)
    return parser.parse_args()


def watch(interval: float, debounce: float) -> int:
    previous = content_snapshot()
    write_state(status="watching", paths=[], targets=[], returncode=None)
    print("[frontend.dev.watch] watching; candidate build/browser/fingerprint are excluded", flush=True)
    try:
        while True:
            time.sleep(interval)
            current = content_snapshot()
            paths = changed_paths(previous, current)
            if not paths:
                continue
            time.sleep(debounce)
            settled = content_snapshot()
            paths = changed_paths(previous, settled)
            run_targets(paths)
            previous = settled
    except KeyboardInterrupt:
        write_state(status="stopped", paths=[], targets=[], returncode=0)
        print("[frontend.dev.watch] stopped")
        return 0


def main() -> int:
    args = parse_args()
    if args.watch:
        return watch(args.interval, args.debounce)
    if not args.path:
        raise SystemExit("at least one --path is required outside --watch mode")
    return run_targets(args.path)


if __name__ == "__main__":
    raise SystemExit(main())
