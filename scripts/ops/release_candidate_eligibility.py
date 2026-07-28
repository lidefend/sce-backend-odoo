#!/usr/bin/env python3
"""Fail-closed eligibility policy for immutable release candidates."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


SUPERSESSION_SCHEMA = "sce.candidate_supersession.v1"
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
DIGEST_IMAGE_REF = re.compile(r"^[a-z0-9][a-z0-9._/-]+@sha256:[0-9a-f]{64}$")
BLOCKING_STATUS_MARKERS = ("SUPERSEDED", "REVOKED", "INVALID")


class CandidateEligibilityError(RuntimeError):
    """A structured fail-closed candidate qualification result."""

    def __init__(self, reason_code: str, detail: str, candidate: str = "UNKNOWN"):
        super().__init__(detail)
        self.reason_code = reason_code
        self.candidate = candidate


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CandidateEligibilityError(
            "INVALID_SUPERSESSION_DECLARATION"
            if "supersession" in label.lower()
            else "INVALID_CANDIDATE_DECLARATION",
            f"{label} is missing or invalid",
        ) from exc
    if not isinstance(payload, dict):
        raise CandidateEligibilityError(
            "INVALID_SUPERSESSION_DECLARATION"
            if "supersession" in label.lower()
            else "INVALID_CANDIDATE_DECLARATION",
            f"{label} must be a JSON object",
        )
    return payload


def validate_supersession(
    candidate: dict[str, Any],
    supersession: dict[str, Any],
) -> dict[str, Any]:
    candidate_name = str(candidate.get("candidate_name") or "")
    source_sha = str(candidate.get("source_sha") or "")
    image_ref = str(candidate.get("image_ref") or "")
    if (
        not candidate_name
        or not FULL_SHA.fullmatch(source_sha)
        or not DIGEST_IMAGE_REF.fullmatch(image_ref)
    ):
        raise CandidateEligibilityError(
            "INVALID_CANDIDATE_DECLARATION",
            "candidate immutable identity fields are missing or invalid",
            candidate_name or "UNKNOWN",
        )

    required = {
        "schema_version",
        "candidate_name",
        "failed_candidate_sha",
        "failed_image_ref",
        "status",
        "reason",
        "promotion_allowed",
        "new_candidate_required",
    }
    if set(supersession).isdisjoint(required) or any(
        key not in supersession for key in required
    ):
        raise CandidateEligibilityError(
            "INVALID_SUPERSESSION_DECLARATION",
            "supersession declaration is incomplete",
            candidate_name,
        )
    if supersession.get("schema_version") != SUPERSESSION_SCHEMA:
        raise CandidateEligibilityError(
            "INVALID_SUPERSESSION_DECLARATION",
            "supersession schema is unsupported",
            candidate_name,
        )
    if not isinstance(supersession.get("promotion_allowed"), bool) or not isinstance(
        supersession.get("new_candidate_required"), bool
    ):
        raise CandidateEligibilityError(
            "INVALID_SUPERSESSION_DECLARATION",
            "supersession boolean policy fields are invalid",
            candidate_name,
        )
    if (
        supersession.get("candidate_name") != candidate_name
        or supersession.get("failed_candidate_sha") != source_sha
        or supersession.get("failed_image_ref") != image_ref
    ):
        raise CandidateEligibilityError(
            "CANDIDATE_IDENTITY_MISMATCH",
            "supersession identity does not match the immutable candidate",
            candidate_name,
        )
    status = str(supersession.get("status") or "").strip().upper()
    reason = str(supersession.get("reason") or "").strip()
    if not status or not reason:
        raise CandidateEligibilityError(
            "INVALID_SUPERSESSION_DECLARATION",
            "supersession status or reason is missing",
            candidate_name,
        )
    blocked = (
        supersession["promotion_allowed"] is False
        or supersession["new_candidate_required"] is True
        or any(marker in status for marker in BLOCKING_STATUS_MARKERS)
    )
    return {
        "candidate": candidate_name,
        "candidate_source_sha": source_sha,
        "candidate_image_ref": image_ref,
        "supersession_status": status,
        "promotion_allowed": supersession["promotion_allowed"],
        "new_candidate_required": supersession["new_candidate_required"],
        "blocked": blocked,
        "reason_code": "SUPERSEDED_CANDIDATE" if blocked else "ELIGIBLE_CANDIDATE",
    }


def assert_candidate_eligible(
    candidate_path: Path,
    supersession_path: Path,
) -> dict[str, Any]:
    candidate = load_json(candidate_path, "candidate declaration")
    supersession = load_json(supersession_path, "candidate supersession declaration")
    result = validate_supersession(candidate, supersession)
    if result["blocked"]:
        raise CandidateEligibilityError(
            "SUPERSEDED_CANDIDATE",
            "candidate is superseded; a new immutable candidate is required",
            result["candidate"],
        )
    return result


def audit_supersession(
    candidate_path: Path,
    supersession_path: Path,
) -> dict[str, Any]:
    candidate = load_json(candidate_path, "candidate declaration")
    supersession = load_json(supersession_path, "candidate supersession declaration")
    result = validate_supersession(candidate, supersession)
    return {
        "result": "PASS",
        "audit": "SUPERSESSION_DECLARATION_VALID",
        **result,
    }


def blocked_lines(exc: CandidateEligibilityError) -> str:
    return "\n".join(
        (
            "RESULT=BLOCKED",
            f"REASON={exc.reason_code}",
            f"CANDIDATE={exc.candidate}",
            "NEW_CANDIDATE_REQUIRED=true",
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action",
        choices=("audit-supersession", "verify-eligibility"),
    )
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--supersession", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.action == "audit-supersession":
            result = audit_supersession(args.candidate, args.supersession)
        else:
            result = assert_candidate_eligible(args.candidate, args.supersession)
    except CandidateEligibilityError as exc:
        print(blocked_lines(exc))
        return 42
    print("CANDIDATE_ELIGIBILITY=" + json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
