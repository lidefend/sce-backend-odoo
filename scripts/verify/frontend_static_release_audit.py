#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "artifacts/frontend-release-audit/static.json"
COMMANDS = {
    "style_system": ["make", "--no-print-directory", "verify.frontend.style_system.guard"],
    "shared_semantic_boundary": ["make", "--no-print-directory", "verify.frontend.shared_surface_semantic_boundary.guard"],
    "delivery_hardening": ["make", "--no-print-directory", "verify.frontend.delivery_hardening.guard"],
    "release_navigation_policy": [
        "make",
        "--no-print-directory",
        "verify.frontend.release_navigation_policy.guard",
    ],
    "lint": ["pnpm", "--dir", "frontend/apps/web", "run", "lint"],
    "strict_typecheck": ["pnpm", "--dir", "frontend/apps/web", "run", "typecheck:strict"],
    "production_build": ["pnpm", "--dir", "frontend/apps/web", "run", "build"],
}


def git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def main() -> int:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    results = {}
    failed = False
    for name, command in COMMANDS.items():
        started = time.monotonic()
        completed = subprocess.run(command, cwd=ROOT, text=True)
        results[name] = {
            "command": command,
            "exit_code": completed.returncode,
            "duration_ms": round((time.monotonic() - started) * 1000),
            "result": "PASS" if completed.returncode == 0 else "FAIL",
        }
        failed = failed or completed.returncode != 0
    payload = {
        "schema_version": "frontend-static-release-audit/v1",
        "git_sha": git_sha(),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "checks": results,
        "result": "FAIL" if failed else "PASS",
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[frontend_static_release_audit] {payload['result']} evidence={OUTPUT.relative_to(ROOT)}")
    return 2 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
