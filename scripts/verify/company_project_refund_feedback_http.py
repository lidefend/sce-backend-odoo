#!/usr/bin/env python3
"""Run and preserve sanitized company-refund feedback HTTP evidence."""
import json
import os
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUN = "FE-GATE-04B"
PREFIX = "LOCAL_DEV_COMPANY_PROJECT_REFUND_FEEDBACK_JSON="
LOG = ROOT / ".runtime/agent-runs" / RUN / "company-project-refund-feedback-http.log"
EVIDENCE = ROOT / ".runtime/agent-runs" / RUN / "http-evidence.json"
EXPECTED_CASES = [
    "describe",
    "presence_selected",
    "visible_to_hidden",
    "missing_presence",
    "ordinary_onchange",
    "permission_denied",
    "wrong_company",
    "wrong_view",
    "missing_draft_capability",
]


def fail(message):
    raise SystemExit(f"[company_project_refund_feedback_http] FAIL: {message}")


def main():
    result = subprocess.run(
        ["make", "--no-print-directory", "verify.company_project_refund.feedback.http"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    output = result.stdout + result.stderr
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text(output, encoding="utf-8")
    if result.returncode:
        fail(f"governed local.dev HTTP entry failed (exit={result.returncode}); see {LOG.relative_to(ROOT)}")
    summaries = re.findall(r"0 failed, 0 error\(s\) of (\d+) tests", output)
    if len(summaries) != 1 or int(summaries[0]) <= 0:
        fail("HTTP test did not report one non-zero zero-failure result")
    rows = [
        line.split(PREFIX, 1)[1]
        for line in output.splitlines()
        if PREFIX in line
    ]
    if len(rows) != 1:
        fail("HTTP test did not emit one unique sanitized evidence row")
    try:
        evidence = json.loads(rows[0])
    except json.JSONDecodeError as exc:
        fail(f"HTTP evidence is not valid JSON: {exc}")
    if evidence.get("database") != "sc_dev_demo":
        fail("HTTP evidence did not come from sc_dev_demo")
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
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip(),
        "test_count": int(summaries[0]),
        "case_count": len(cases),
        "log": str(LOG.relative_to(ROOT)),
        "evidence": evidence,
    }
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.chmod(EVIDENCE, 0o600)
    print(
        "[company_project_refund_feedback_http] PASS "
        f"cases={len(cases)} evidence={EVIDENCE.relative_to(ROOT)}"
    )


if __name__ == "__main__":
    main()
