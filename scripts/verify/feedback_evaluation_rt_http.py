#!/usr/bin/env python3
"""Run the real local.dev HTTP evidence test and preserve its sanitized result."""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = "FE-GATE-03B1-R6-3-RT"
EVIDENCE_PREFIX = "LOCAL_DEV_FEEDBACK_RT_HTTP_JSON="
EVIDENCE = ROOT / ".runtime/agent-runs" / RUN / "http-evidence.json"
LOG = ROOT / ".runtime/agent-runs" / RUN / "http.log"
EXPECTED_CASES = [
    "describe",
    "evaluate_explicit_clear",
    "evaluate_valid_hidden",
    "evaluate_missing_dependency",
    "evaluate_stale_binding",
    "missing_draft_capability",
    "invalid_context_view",
    "ordinary_onchange",
    "permission_denied",
]


def fail(message):
    raise SystemExit(f"[feedback_evaluation_rt_http] FAIL: {message}")


def main():
    command = [
        "make", "--no-print-directory",
        "verify.feedback_evaluation.rt.http.orm",
    ]
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    main_output = result.stdout + result.stderr
    restore = subprocess.run([
        "make", "--no-print-directory",
        "verify.feedback_evaluation.rt.restore",
    ], cwd=ROOT, text=True, capture_output=True, check=False)
    restore_output = restore.stdout + restore.stderr
    output = main_output + "\n[RESTORE]\n" + restore_output
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text(output, encoding="utf-8")
    if result.returncode:
        fail(f"governed local.dev HTTP entry failed (exit={result.returncode}); see {LOG.relative_to(ROOT)}")
    if restore.returncode:
        fail(f"post-RT restoration check failed (exit={restore.returncode}); see {LOG.relative_to(ROOT)}")
    summary = re.findall(r"0 failed, 0 error\(s\) of (\d+) tests", main_output)
    if len(summary) != 1 or int(summary[0]) <= 0:
        fail("HTTP test did not report one non-zero zero-failure result")
    restore_summary = re.findall(r"0 failed, 0 error\(s\) of (\d+) tests", restore_output)
    if len(restore_summary) != 1 or int(restore_summary[0]) <= 0:
        fail("post-RT restoration check did not report one non-zero zero-failure result")
    rows = [
        line.split(EVIDENCE_PREFIX, 1)[1]
        for line in output.splitlines() if EVIDENCE_PREFIX in line
    ]
    if len(rows) != 1:
        fail("HTTP test did not emit one unique sanitized evidence row")
    try:
        evidence = json.loads(rows[0])
    except json.JSONDecodeError as exc:
        fail(f"HTTP evidence is not valid JSON: {exc}")
    if evidence.get("database") != "sc_dev_demo":
        fail("HTTP evidence did not come from sc_dev_demo")
    source_file = str(evidence.get("source_file") or "")
    if "/mnt/source-addons/smart_core/" not in source_file:
        fail("HTTP evidence source file is not the local.dev source mount")
    cases = evidence.get("cases")
    if not isinstance(cases, list) or [row.get("case") for row in cases] != EXPECTED_CASES:
        fail("HTTP evidence case set is incomplete or out of order")
    if any("token" in json.dumps(row, ensure_ascii=False).lower() for row in cases):
        fail("HTTP evidence contains authentication material")
    payload = {
        "schema_version": 1,
        "run": RUN,
        "profile": "sc-local-dev",
        "candidate_sha": subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=True,
        ).stdout.strip(),
        "test_count": int(summary[0]),
        "restore_test_count": int(restore_summary[0]),
        "case_count": len(cases),
        "log": str(LOG.relative_to(ROOT)),
        "evidence": evidence,
    }
    EVIDENCE.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(EVIDENCE, 0o600)
    print(f"[feedback_evaluation_rt_http] PASS cases={len(cases)} evidence={EVIDENCE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
