#!/usr/bin/env python3
"""Read-only experience-reset scope planner (P4 delivery tooling).

Computes what a scoped experience reset would clean without deleting anything.
Fail-closed: if an experience user authored or edited a demo baseline record,
the planner raises, because the reset must never touch the baseline.
"""
from __future__ import annotations


class ResetScopeError(ValueError):
    pass


def plan_cleanup(
    baseline_fingerprints,
    experience_user_ids,
    business_records,
    artifacts,
) -> dict:
    experience = set(experience_user_ids)
    baseline = set(baseline_fingerprints)
    to_clean_records: list[dict] = []
    baseline_violations: list[dict] = []
    for record in business_records:
        authors = {record.get("create_uid"), record.get("write_uid")} & experience
        if not authors:
            continue
        if record["id"] in baseline:
            baseline_violations.append(record)
        else:
            to_clean_records.append(record)
    if baseline_violations:
        raise ResetScopeError(
            "experience users touched baseline records: %s" % baseline_violations
        )
    to_clean_artifacts = [
        artifact for artifact in artifacts if artifact.get("author_uid") in experience
    ]
    return {
        "records": to_clean_records,
        "artifacts": to_clean_artifacts,
        "baseline_violations": [],
    }
