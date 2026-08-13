from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from .parser import build_dataset


EXPECTED_BOOKS = {
    "building_1",
    "building_2",
    "installation_1",
    "installation_2",
    "installation_3",
    "installation_4",
}


def _write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def verify_release(dataset: dict, *, require_source_hashes: bool) -> list[str]:
    errors = []
    book_ids = {row["book_id"] for row in dataset["source_books"]}
    if book_ids != EXPECTED_BOOKS:
        errors.append(f"source book set mismatch: expected={sorted(EXPECTED_BOOKS)} actual={sorted(book_ids)}")
    if dataset["metrics"]["page_count"] != 1218:
        errors.append(f"expected 1218 OCR pages, got {dataset['metrics']['page_count']}")
    if require_source_hashes:
        missing = [row["book_id"] for row in dataset["source_books"] if not row["source_sha256"]]
        if missing:
            errors.append(f"missing source PDF hashes: {', '.join(missing)}")
    if dataset["metrics"]["item_count"] == 0:
        errors.append("no quota items extracted")
    installation_rules = [row for row in dataset["rules"] if row["book_id"].startswith("installation_")]
    if not installation_rules:
        errors.append("installation volumes produced no rule records")
    if dataset["metrics"]["error_count"]:
        errors.append(f"review queue contains {dataset['metrics']['error_count']} blocking errors")
    cost_mismatches = []
    for item in dataset["items"]:
        component_total = sum(
            float(item[field] or 0.0)
            for field in ("cost_labor", "cost_material", "cost_machine", "cost_misc")
        )
        if component_total and abs(float(item["price_total"] or 0.0) - component_total) > 0.05:
            cost_mismatches.append(item["code"])
    if cost_mismatches:
        errors.append(
            f"{len(cost_mismatches)} items fail price component integrity: "
            + ", ".join(cost_mismatches[:10])
        )
    return errors


def electronic_review_rows(dataset: dict) -> list[dict]:
    rows = list(dataset.get("review_issues") or [])
    for item in dataset["items"]:
        component_total = sum(
            float(item[field] or 0.0)
            for field in ("cost_labor", "cost_material", "cost_machine", "cost_misc")
        )
        delta = abs(float(item["price_total"] or 0.0) - component_total)
        if component_total and delta > 0.05:
            rows.append({
                "severity": "review", "code": "price_component_mismatch",
                "book_id": item["book_id"], "pdf_page": item["source_pdf_page"],
                "quota_code": item["code"], "field": "cost_components",
                "message": f"综合单价与费用分项合计相差 {delta:.2f}，综合单价保留，费用分项待人工复核。",
            })
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ocr-dir", type=Path, required=True)
    parser.add_argument("--source-dir", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--release", action="store_true")
    args = parser.parse_args()
    dataset = build_dataset(args.ocr_dir, args.source_dir)
    errors = verify_release(dataset, require_source_hashes=args.release)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "norm-dataset.json").write_text(
        json.dumps(dataset, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _write_csv(
        args.output / "quota-items.csv",
        dataset["items"],
        [
            "specialty_code", "chapter_code", "code", "name", "unit_raw", "price_total",
            "cost_direct", "cost_labor", "cost_material", "cost_machine", "cost_misc",
            "work_desc", "book_id", "source_file", "source_pdf_page", "source_printed_page",
            "source_confidence", "source_digest",
        ],
    )
    resources = []
    for item in dataset["items"]:
        for resource in item["resources"]:
            resources.append({"quota_code": item["code"], "specialty_code": item["specialty_code"], **resource})
    _write_csv(
        args.output / "resources.csv",
        resources,
        [
            "specialty_code", "quota_code", "sequence", "resource_type", "name", "unit_raw",
            "unit_price", "quantity", "quantity_confidence", "source_bbox",
        ],
    )
    _write_csv(
        args.output / "rules.csv",
        dataset["rules"],
        [
            "code", "specialty_code", "chapter_code", "title", "rule_type", "content", "book_id",
            "source_file", "source_pdf_page", "source_printed_page", "source_confidence", "source_digest",
        ],
    )
    report = {"status": "PASS" if not errors else "FAIL", "errors": errors, "metrics": dataset["metrics"]}
    review_rows = electronic_review_rows(dataset)
    _write_csv(
        args.output / "review-queue.csv", review_rows,
        ["severity", "code", "book_id", "pdf_page", "quota_code", "field", "message", "confidence"],
    )
    (args.output / "review-queue.json").write_text(
        json.dumps(review_rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    report["electronic_archive"] = {
        "status": "COMPLETE_WITH_REVIEW_QUEUE",
        "review_count": len(review_rows),
        "blocking_for_system_activation": bool(errors),
    }
    (args.output / "release-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
