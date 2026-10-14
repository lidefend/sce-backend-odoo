# -*- coding: utf-8 -*-
"""Static guard: counterparty-identity aggregations must carry company and currency.

The project counterparty position view and its cross-project summary both declare
``company_id`` and ``currency_id`` as part of their identity key.  Their row-count
audits rebuild the same aggregation to prove the projection neither drops nor
duplicates rows, so an oracle that groups by a strictly coarser key is blind to
company/currency collapsing: it stays green while the projection silently merges
two companies' or two currencies' counterparty positions into one row.

This guard fails when any aggregation (projection or audit oracle) that groups by
the counterparty identity columns omits ``company_id`` or ``currency_id``.
"""

from __future__ import annotations

import json
import re
from collections import OrderedDict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

PROJECTION_MODELS = (
    "addons/smart_construction_core/models/projection/finance_project_counterparty_position.py",
    "addons/smart_construction_core/models/projection/finance_counterparty_position_summary.py",
)
AUDIT_SCRIPTS = (
    "scripts/verify/finance_project_counterparty_position_audit.py",
    "scripts/verify/finance_counterparty_position_summary_audit.py",
)
# The identity anchor: a GROUP BY that carries these two columns is aggregating by
# counterparty identity and therefore must also partition by company and currency.
IDENTITY_ANCHORS = ("counterparty_project_id", "counterparty_name")
REQUIRED_PARTITIONS = ("company_id", "currency_id")

GROUP_BY_RE = re.compile(r"GROUP\s+BY\b([^\n]*)", re.IGNORECASE)


def identity_grouping_keys(text):
    """Return every GROUP BY column list that aggregates by counterparty identity."""
    keys = []
    for match in GROUP_BY_RE.finditer(text):
        raw = match.group(1)
        columns = [token.strip().strip("()").split(".")[-1] for token in raw.split(",")]
        columns = [column for column in columns if column]
        if all(anchor in columns for anchor in IDENTITY_ANCHORS):
            keys.append(columns)
    return keys


def detect(source_label, text):
    errors = []
    keys = identity_grouping_keys(text)
    if not keys:
        errors.append({"key": "identity_aggregation_missing", "source": source_label})
        return keys, errors
    for columns in keys:
        for required in REQUIRED_PARTITIONS:
            if required not in columns:
                errors.append(
                    {
                        "key": "identity_aggregation_missing_partition",
                        "source": source_label,
                        "grouping_key": columns,
                        "missing": required,
                    }
                )
    return keys, errors


def scan():
    errors = []
    summary = OrderedDict()
    for relative in (*PROJECTION_MODELS, *AUDIT_SCRIPTS):
        path = ROOT / relative
        if not path.is_file():
            errors.append({"key": "source_missing", "source": relative})
            continue
        keys, source_errors = detect(relative, path.read_text(encoding="utf-8"))
        summary[relative] = {"identity_grouping_keys": keys}
        errors.extend(source_errors)
    return summary, errors


def selftest():
    """Negative control: the guard must reject the pre-fix oracle keys."""
    pre_fix = (
        "   GROUP BY counterparty_type, counterparty_project_id, partner_id, counterparty_name\n"
        "   GROUP BY project_id, counterparty_type, counterparty_project_id, partner_id, counterparty_name\n"
        "   GROUP BY company_id, currency_id, counterparty_type, counterparty_project_id, partner_id, counterparty_name\n"
    )
    keys, errors = detect("selftest", pre_fix)
    flagged = {tuple(error.get("grouping_key", ())) for error in errors}
    if len(keys) != 3:
        raise SystemExit(
            f"FINANCE_POSITION_AUDIT_PARTITION_GUARD=SELFTEST_FAIL: parsed {len(keys)} keys"
        )
    if len(flagged) != 2:
        raise SystemExit(
            "FINANCE_POSITION_AUDIT_PARTITION_GUARD=SELFTEST_FAIL: coarse keys not rejected"
        )
    print("FINANCE_POSITION_AUDIT_PARTITION_GUARD=SELFTEST_PASS")


def main():
    summary, errors = scan()
    result = OrderedDict()
    result["status"] = "PASS" if not errors else "FAIL"
    result["summary"] = summary
    result["errors"] = errors
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    import sys

    if "--selftest" in sys.argv[1:]:
        selftest()
    else:
        main()
