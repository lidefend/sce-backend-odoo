#!/usr/bin/env python3
"""Safely admit same-origin blob previews in the production edge CSP."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG = Path("/etc/nginx/snippets/scems-security-headers.conf")
CONFIRMATION = "YES_ADMIT_SAME_ORIGIN_BLOB_ATTACHMENT_PREVIEWS"
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
CURRENT = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self' wss:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'; upgrade-insecure-requests"
DESIRED = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self' wss:; frame-src 'self' blob:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'; upgrade-insecure-requests"


class CspError(RuntimeError):
    pass


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def run(command: list[str]) -> None:
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, text=True)
    if result.returncode:
        raise CspError(f"command failed ({command[0]}): {result.stderr.strip()[:500]}")


def verify_tool_identity(expected_sha: str) -> None:
    if not FULL_SHA.fullmatch(expected_sha):
        raise CspError("tool SHA must be a full lowercase SHA")
    marker = ROOT / "DEPLOYMENT_TOOL_SHA"
    if ROOT != Path("/opt/sce/deployment-tools") / expected_sha or not marker.is_file():
        raise CspError("immutable deployment tool root is required")
    if marker.read_text(encoding="utf-8") != expected_sha + "\n":
        raise CspError("deployment tool marker differs")


def desired_content(original: str) -> str:
    if DESIRED in original:
        if CURRENT in original:
            raise CspError("CSP contains competing preview policies")
        return original
    if original.count(CURRENT) != 1:
        raise CspError("expected frozen CSP policy is absent or duplicated")
    return original.replace(CURRENT, DESIRED)


def public_header(base_url: str) -> str:
    request = urllib.request.Request(base_url.rstrip("/") + "/runtime-config.js", method="HEAD")
    with urllib.request.urlopen(request, timeout=10) as response:
        return str(response.headers.get("Content-Security-Policy") or "")


def wait_for_public_policy(base_url: str, *, attempts: int = 20, pause: float = 0.25) -> str:
    header = ""
    for _ in range(attempts):
        try:
            header = public_header(base_url)
        except OSError:
            header = ""
        if "frame-src 'self' blob:" in header:
            return header
        time.sleep(pause)
    raise CspError("public CSP did not admit same-origin blob frames")


def apply(config: Path, evidence: Path, public_base_url: str) -> dict:
    if config != CONFIG or config.is_symlink() or not config.is_file():
        raise CspError("production security header file identity differs")
    if evidence.exists() or evidence.is_symlink():
        raise CspError("evidence path must be new")
    if not public_base_url.startswith("https://"):
        raise CspError("production public HTTPS base URL is required")
    original = config.read_bytes()
    updated_text = desired_content(original.decode("utf-8"))
    updated = updated_text.encode("utf-8")
    evidence.mkdir(parents=True, mode=0o700)
    rollback = evidence / "scems-security-headers.conf.before"
    rollback.write_bytes(original)
    rollback.chmod(0o600)
    changed = updated != original
    try:
        if changed:
            descriptor, raw = tempfile.mkstemp(prefix=".scems-security-headers.", dir=config.parent)
            temporary = Path(raw)
            try:
                os.fchmod(descriptor, 0o644)
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(updated)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, config)
            finally:
                temporary.unlink(missing_ok=True)
        run(["nginx", "-t"])
        if changed:
            run(["systemctl", "reload", "nginx"])
        wait_for_public_policy(public_base_url)
    except Exception:
        if changed:
            shutil.copyfile(rollback, config)
            config.chmod(0o644)
            run(["nginx", "-t"])
            run(["systemctl", "reload", "nginx"])
        raise
    report = {
        "status": "PASS",
        "changed": changed,
        "config": str(config),
        "before_sha256": sha256(original),
        "after_sha256": sha256(updated),
        "rollback": str(rollback),
        "public_base_url": public_base_url,
        "frame_src": ["'self'", "blob:"],
    }
    report_path = evidence / "report.json"
    report_path.write_text(json.dumps(report, sort_keys=True) + "\n", encoding="utf-8")
    report_path.chmod(0o600)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tool-sha", required=True)
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--public-base-url", required=True)
    args = parser.parse_args()
    try:
        if os.environ.get("ENV") != "prod" or os.environ.get("PROD_DANGER") != "1":
            raise CspError("ENV=prod and PROD_DANGER=1 are required")
        if os.environ.get("CONFIRM_PRODUCTION_ATTACHMENT_PREVIEW_CSP") != CONFIRMATION:
            raise CspError("exact attachment preview CSP confirmation is required")
        verify_tool_identity(args.tool_sha)
        report = apply(CONFIG, args.evidence, args.public_base_url)
    except (CspError, OSError, UnicodeError) as exc:
        raise SystemExit(f"[production.attachment-preview-csp] BLOCKED: {exc}") from exc
    print("[production.attachment-preview-csp] PASS " + json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
