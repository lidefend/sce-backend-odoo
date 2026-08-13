from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path
from statistics import median
from typing import Any, Iterable


SCHEMA = "sce.norm.dataset/v1"
QUOTA_CODE = re.compile(r"^[A-Z]{1,3}\d{3,5}$")
NUMBER = re.compile(r"^\(?-?\d+(?:\.\d+)?\)?$")
HEADING_CODE = re.compile(r"编码\s*[：:]\s*([0-9、,， ]{6,})")
SECTION_PREFIX = re.compile(r"^([A-Z])(?:[.．]\d+)+")
BOOK_KIND = {
    "building": ("BUILD", "房屋建筑与装饰工程"),
    "installation": ("INSTALL", "通用安装工程"),
}
COST_KEYS = {
    "综合基价": "price_total",
    "综合单价": "price_total",
    "人工费": "cost_labor",
    "材料费": "cost_material",
    "机械费": "cost_machine",
    "管理费": "cost_management",
    "利润": "cost_profit",
}
IGNORED_TEXT = {"定", "额", "编", "号", "项", "目", "其", "中", "数", "量"}


def _clean(value: Any) -> str:
    return str(value or "").replace("　", " ").replace("\r", "").strip()


def _compact(value: Any) -> str:
    return re.sub(r"\s+", "", _clean(value))


def _bounds(line: dict[str, Any]) -> tuple[float, float, float, float]:
    xs = [float(point[0]) for point in line["box"]]
    ys = [float(point[1]) for point in line["box"]]
    return min(xs), min(ys), max(xs), max(ys)


def _center(line: dict[str, Any]) -> tuple[float, float]:
    left, top, right, bottom = _bounds(line)
    return (left + right) / 2, (top + bottom) / 2


def _rows(lines: Iterable[dict[str, Any]], tolerance: float = 14) -> list[list[dict[str, Any]]]:
    ordered = sorted(lines, key=lambda line: (_center(line)[1], _center(line)[0]))
    result: list[list[dict[str, Any]]] = []
    centers: list[float] = []
    for line in ordered:
        y = _center(line)[1]
        if not result or abs(y - centers[-1]) > tolerance:
            result.append([line])
            centers.append(y)
            continue
        result[-1].append(line)
        centers[-1] = sum(_center(item)[1] for item in result[-1]) / len(result[-1])
    for row in result:
        row.sort(key=lambda line: _center(line)[0])
    return result


def _numeric(value: Any) -> float | None:
    text = _compact(value).replace(",", "")
    if not NUMBER.fullmatch(text):
        return None
    if text.startswith("(") and text.endswith(")"):
        text = text[1:-1]
    return float(text)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _book_family(book_id: str) -> tuple[str, str]:
    prefix = book_id.split("_", 1)[0]
    return BOOK_KIND.get(prefix, (prefix.upper(), prefix))


def _cluster_code_lines(lines: list[dict[str, Any]], tolerance: float = 24) -> list[list[dict[str, Any]]]:
    codes = [line for line in lines if QUOTA_CODE.fullmatch(_compact(line.get("text")))]
    groups = _rows(codes, tolerance=tolerance)
    return [group for group in groups if group]


def _nearest_column(x: float, columns: list[tuple[str, float]]) -> str | None:
    if not columns:
        return None
    ordered = sorted(columns, key=lambda row: row[1])
    code, distance = min(((code, abs(x - center)) for code, center in ordered), key=lambda row: row[1])
    spacings = [ordered[index + 1][1] - ordered[index][1] for index in range(len(ordered) - 1)]
    threshold = min(spacings) * 0.46 if spacings else 180
    return code if distance <= max(45, threshold) else None


def _cost_key(text: str) -> str | None:
    normalized = _compact(text).replace("（元）", "").replace("(元)", "").replace(".", "")
    normalized = normalized.replace("人T费", "人工费")
    for label, field_name in COST_KEYS.items():
        if label in normalized:
            return field_name
    return None


def _latest_text(lines: list[dict[str, Any]], before_y: float, predicate) -> str:
    candidates = [line for line in lines if _center(line)[1] < before_y and predicate(_clean(line.get("text")))]
    return _clean(max(candidates, key=lambda line: _center(line)[1]).get("text")) if candidates else ""


def _printed_page(lines: list[dict[str, Any]], height: float) -> str:
    candidates = [
        re.sub(r"\D", "", _clean(line.get("text")))
        for line in lines
        if _center(line)[1] > height * 0.90
        and re.fullmatch(r"[.·\-— ]*\d+[.·\-— ]*", _clean(line.get("text")))
    ]
    return candidates[-1] if candidates else ""


def _source_bbox(group: list[dict[str, Any]]) -> list[float]:
    bounds = [_bounds(line) for line in group]
    return [
        round(min(row[0] for row in bounds), 2),
        round(min(row[1] for row in bounds), 2),
        round(max(row[2] for row in bounds), 2),
        round(max(row[3] for row in bounds), 2),
    ]


def _parse_table_block(
    page: dict[str, Any],
    code_group: list[dict[str, Any]],
    end_y: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    lines = page["lines"]
    width = float(page["width_px"])
    height = float(page["height_px"])
    code_y = median(_center(line)[1] for line in code_group)
    columns = sorted(
        [(_compact(line["text"]), _center(line)[0]) for line in code_group], key=lambda row: row[1]
    )
    first_column_y = _center(min(code_group, key=lambda line: _center(line)[0]))[1]
    column_y_offsets = {
        _compact(line["text"]): _center(line)[1] - first_column_y for line in code_group
    }
    block_lines = [line for line in lines if code_y + 8 < _center(line)[1] < end_y]
    row_groups = _rows(block_lines)

    cost_rows: list[tuple[float, str, list[dict[str, Any]]]] = []
    for row in row_groups:
        label = "".join(
            _clean(line.get("text")) for line in row if _center(line)[0] < min(width * 0.51, columns[0][1] - 25)
        )
        field_name = _cost_key(label)
        if field_name:
            label_lines = [
                line for line in row if _center(line)[0] < min(width * 0.51, columns[0][1] - 25)
            ]
            cost_rows.append((median(_center(line)[1] for line in label_lines), field_name, row))
    first_cost_y = min((row[0] for row in cost_rows), default=end_y)

    resource_header_candidates = [
        line
        for line in block_lines
        if _center(line)[1] > first_cost_y + 8 and _compact(line.get("text")) in {"名", "名称"}
    ]
    resource_header_y = min((_center(line)[1] for line in resource_header_candidates), default=end_y)
    cost_rows = [row for row in cost_rows if row[0] < resource_header_y - 4]

    # Scanned tables are often skewed: cells in the right-most column can sit
    # several pixels lower than cells in the first column.  Normalize each
    # numeric cell with the vertical offset observed in its code header before
    # choosing the nearest cost anchor.
    values: dict[str, dict[str, float]] = defaultdict(dict)
    cost_anchors = [(y, field_name) for y, field_name, _ in cost_rows]
    # Estimate the table's numeric-baseline offset from the comprehensive-price
    # row.  Some scans put numbers above the printed label baseline, others put
    # them 10-15 pixels below it.
    price_anchor_index = next(
        (index for index, row in enumerate(cost_anchors) if row[1] == "price_total"), None
    )
    numeric_baseline_offset = 0.0
    if price_anchor_index is not None:
        price_y = cost_anchors[price_anchor_index][0]
        next_y = (
            cost_anchors[price_anchor_index + 1][0]
            if price_anchor_index + 1 < len(cost_anchors)
            else price_y + 50
        )
        samples = []
        for line in block_lines:
            number = _numeric(line.get("text"))
            code = _nearest_column(_center(line)[0], columns)
            if number is None or not code:
                continue
            normalized_y = _center(line)[1] - column_y_offsets.get(code, 0.0)
            if price_y - 20 <= normalized_y < (price_y + next_y) / 2:
                samples.append(normalized_y - price_y)
        if samples:
            numeric_baseline_offset = median(samples)
    expected_anchors = [
        (y + numeric_baseline_offset, field_name) for y, field_name in cost_anchors
    ]
    for line in block_lines:
        number = _numeric(line.get("text"))
        x, y = _center(line)
        if number is None or not cost_anchors:
            continue
        code = _nearest_column(x, columns)
        if not code:
            continue
        normalized_y = y - column_y_offsets.get(code, 0.0)
        anchor_y, field_name = min(expected_anchors, key=lambda row: abs(normalized_y - row[0]))
        if abs(normalized_y - anchor_y) > 24.0 or y >= resource_header_y - 4:
            continue
        values[code][field_name] = number

    variant_region = [
        line
        for line in lines
        if code_y + 8 < _center(line)[1] < first_cost_y - 5
        and _center(line)[0] > width * 0.28
        and _compact(line.get("text")) not in IGNORED_TEXT
        and _numeric(line.get("text")) is None
    ]
    shared_name_parts: list[str] = []
    variants: dict[str, list[str]] = defaultdict(list)
    for row in _rows(variant_region):
        candidates = [line for line in row if _compact(line.get("text")) not in IGNORED_TEXT]
        if not candidates:
            continue
        if len(candidates) == 1 and len(columns) > 1:
            text = _clean(candidates[0].get("text"))
            if text and text not in shared_name_parts:
                shared_name_parts.append(text)
            continue
        for line in candidates:
            code = _nearest_column(_center(line)[0], columns)
            text = _clean(line.get("text"))
            if code and text:
                variants[code].append(text)

    heading = _latest_text(
        lines,
        code_y,
        lambda text: bool(HEADING_CODE.search(text)) or bool(re.match(r"^[A-Z](?:[.．]\d+)+", text)),
    )
    bill_match = HEADING_CODE.search(heading)
    bill_code = re.sub(r"\D", "", bill_match.group(1)) if bill_match else ""
    section_title = re.sub(r"[（(]?编码\s*[：:].*$", "", heading).strip(" （(")
    work_content = _latest_text(lines, code_y, lambda text: "工作内容" in text)
    work_content = re.split(r"工作内容\s*[：:]", work_content, maxsplit=1)[-1].strip()
    unit_text = _latest_text(
        lines,
        code_y,
        lambda text: bool(re.match(r"^单位\s*[：:]\s*\S+", text)),
    )
    unit = re.split(r"单位\s*[：:]", unit_text, maxsplit=1)[-1].strip() if unit_text else ""
    printed_page = _printed_page(lines, height)
    family_code, family_name = _book_family(page["book_id"])

    items: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    shared_name = " ".join(shared_name_parts).strip()
    for code, _ in columns:
        variant = " / ".join(dict.fromkeys(variants.get(code, [])))
        item_name = " ".join(part for part in (section_title, shared_name, variant) if part).strip()
        item_name = item_name or f"{family_name} {code}"
        cost = values.get(code, {})
        cost_labor = cost.get("cost_labor", 0.0)
        cost_material = cost.get("cost_material", 0.0)
        cost_machine = cost.get("cost_machine", 0.0)
        cost_management = cost.get("cost_management", 0.0)
        cost_profit = cost.get("cost_profit", 0.0)
        record = {
            "specialty_code": f"{family_code}-{code[0]}",
            "chapter_code": f"{family_code}-{bill_code or code[:2]}",
            "code": code,
            "name": item_name,
            "unit_raw": unit,
            "price_total": cost.get("price_total"),
            "cost_direct": round(cost_labor + cost_material + cost_machine, 6),
            "cost_labor": cost_labor,
            "cost_material": cost_material,
            "cost_machine": cost_machine,
            "cost_misc": round(cost_management + cost_profit, 6),
            "work_desc": work_content,
            "book_id": page["book_id"],
            "source_file": page["source_file"],
            "source_pdf_page": int(page["pdf_page"]),
            "source_printed_page": printed_page,
            "source_confidence": float(page["mean_confidence"]),
            "source_bbox": _source_bbox(code_group),
            "source_digest": _sha256_bytes(
                _canonical_json({"page": page["pdf_page"], "code": code, "lines": block_lines})
            ),
            "resources": [],
        }
        items.append(record)
        for field_name in ("unit_raw", "price_total"):
            if record[field_name] in (None, ""):
                issues.append(
                    {
                        "severity": "error",
                        "code": "missing_required_item_field",
                        "book_id": page["book_id"],
                        "pdf_page": page["pdf_page"],
                        "quota_code": code,
                        "field": field_name,
                    }
                )

    item_by_code = {item["code"]: item for item in items}
    if resource_header_y < end_y:
        resource_lines = [
            line for line in lines if resource_header_y + 12 < _center(line)[1] < end_y - 6
        ]
        resource_type = "other"
        for row in _rows(resource_lines, tolerance=16):
            markers = "".join(
                _compact(line.get("text")) for line in row if _center(line)[0] <= width * 0.10
            )
            if "人" in markers:
                resource_type = "labor"
            elif "材" in markers:
                resource_type = "material"
            elif "机" in markers:
                resource_type = "machine"
            names = [
                line
                for line in row
                if width * 0.08 < _center(line)[0] < width * 0.39
                and len(_compact(line.get("text"))) > 1
                and _numeric(line.get("text")) is None
            ]
            name = "".join(_clean(line.get("text")) for line in names).strip()
            if not name or name in {"（元）", "(元)", "单价（元）", "扫描全能王创建"} or _cost_key(name):
                continue
            units = [line for line in row if width * 0.38 <= _center(line)[0] < width * 0.46]
            prices = [
                line
                for line in row
                if width * 0.44 <= _center(line)[0] < width * 0.54 and _numeric(line.get("text")) is not None
            ]
            unit = "".join(_clean(line.get("text")) for line in units).strip()
            unit_price = _numeric(prices[-1].get("text")) if prices else None
            for line in row:
                quantity = _numeric(line.get("text"))
                if quantity is None or line in prices or _center(line)[0] < width * 0.52:
                    continue
                code = _nearest_column(_center(line)[0], columns)
                if code and code in item_by_code:
                    item_by_code[code]["resources"].append(
                        {
                            "sequence": len(item_by_code[code]["resources"]) + 1,
                            "resource_type": resource_type,
                            "name": name,
                            "unit_raw": unit,
                            "unit_price": unit_price,
                            "quantity": quantity,
                            "quantity_confidence": float(line.get("confidence") or 0.0),
                            "source_bbox": _source_bbox(row),
                        }
                    )
    return items, issues


def _rule_from_page(page: dict[str, Any], has_items: bool) -> dict[str, Any] | None:
    raw_lines = page["lines"]
    content_lines = []
    for line in raw_lines:
        text = _clean(line.get("text"))
        if not text or "扫描全能王" in text:
            continue
        if re.fullmatch(r"[.·\-— ]*\d+[.·\-— ]*", text):
            continue
        content_lines.append(text)
    content = "\n".join(content_lines).strip()
    if len(content) < 80:
        return None
    has_rule_signal = any(token in content for token in ("说明", "说•明", "计算规则", "分册说明", "总说明"))
    if has_items and not has_rule_signal:
        return None
    headings = [
        text
        for text in content_lines[:12]
        if any(token in text for token in ("说明", "计算规则"))
        or bool(re.match(r"^[A-Z](?:[.．]\d+)+", text))
    ]
    title = " / ".join(headings[:2]) or f"{page['discipline']}第 {page['pdf_page']} 页说明"
    heading_match = next((SECTION_PREFIX.match(text) for text in content_lines[:10] if SECTION_PREFIX.match(text)), None)
    family_code, _ = _book_family(page["book_id"])
    specialty_code = f"{family_code}-{heading_match.group(1)}" if heading_match else f"{family_code}-GENERAL"
    code_match = next((HEADING_CODE.search(text) for text in content_lines[:10] if HEADING_CODE.search(text)), None)
    business_code = re.sub(r"\D", "", code_match.group(1)) if code_match else ""
    if "计算规则" in content:
        rule_type = "calculation"
    elif "分册说明" in content:
        rule_type = "volume"
    elif "总说明" in content:
        rule_type = "general"
    else:
        rule_type = "chapter"
    return {
        "code": f"{page['book_id']}-P{int(page['pdf_page']):04d}",
        "specialty_code": specialty_code,
        "chapter_code": f"{family_code}-{business_code}" if business_code else "",
        "title": title[:240],
        "rule_type": rule_type,
        "content": content,
        "book_id": page["book_id"],
        "source_file": page["source_file"],
        "source_pdf_page": int(page["pdf_page"]),
        "source_printed_page": _printed_page(raw_lines, float(page["height_px"])),
        "source_confidence": float(page["mean_confidence"]),
        "source_digest": _sha256_bytes(_canonical_json(raw_lines)),
    }


def parse_page(page: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    groups = _cluster_code_lines(page["lines"])
    items: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    for index, group in enumerate(groups):
        next_y = median(_center(line)[1] for line in groups[index + 1]) if index + 1 < len(groups) else float(page["height_px"])
        block_items, block_issues = _parse_table_block(page, group, next_y - 8)
        items.extend(block_items)
        issues.extend(block_issues)
    rule = _rule_from_page(page, bool(items))
    rules = [rule] if rule else []
    if float(page.get("mean_confidence") or 0.0) < 0.80:
        issues.append(
            {
                "severity": "warning",
                "code": "low_page_confidence",
                "book_id": page["book_id"],
                "pdf_page": page["pdf_page"],
                "confidence": page.get("mean_confidence"),
            }
        )
    return items, rules, issues


def _source_books(pages: list[dict[str, Any]], source_dir: Path | None) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for page in pages:
        grouped[page["book_id"]].append(page)
    result = []
    for book_id, book_pages in sorted(grouped.items()):
        first = book_pages[0]
        source_path = source_dir / first["source_file"] if source_dir else None
        source_sha = _sha256_bytes(source_path.read_bytes()) if source_path and source_path.is_file() else ""
        ocr_digest = _sha256_bytes(
            _canonical_json(
                [
                    {
                        "pdf_page": page["pdf_page"],
                        "line_count": page["line_count"],
                        "mean_confidence": page["mean_confidence"],
                        "text": page["text"],
                    }
                    for page in sorted(book_pages, key=lambda row: row["pdf_page"])
                ]
            )
        )
        result.append(
            {
                "book_id": book_id,
                "discipline": first["discipline"],
                "volume": first["volume"],
                "source_file": first["source_file"],
                "source_sha256": source_sha,
                "ocr_sha256": ocr_digest,
                "page_count": len(book_pages),
                "first_page": min(page["pdf_page"] for page in book_pages),
                "last_page": max(page["pdf_page"] for page in book_pages),
            }
        )
    return result


def build_dataset(ocr_dir: Path, source_dir: Path | None = None) -> dict[str, Any]:
    paths = sorted(ocr_dir.glob("*/*.json"))
    if not paths:
        raise ValueError(f"no OCR pages found below {ocr_dir}")
    pages = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    items: list[dict[str, Any]] = []
    rules: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    page_index = []
    for page in pages:
        page_items, page_rules, page_issues = parse_page(page)
        items.extend(page_items)
        rules.extend(page_rules)
        issues.extend(page_issues)
        page_index.append(
            {
                "book_id": page["book_id"],
                "pdf_page": page["pdf_page"],
                "page_type": "quota_table" if page_items else ("rule" if page_rules else "other"),
                "line_count": page["line_count"],
                "mean_confidence": page["mean_confidence"],
                "item_count": len(page_items),
                "rule_count": len(page_rules),
            }
        )
    seen: dict[tuple[str, str], dict[str, Any]] = {}
    unique_items = []
    for item in items:
        key = (item["specialty_code"], item["code"])
        if key in seen:
            issues.append(
                {
                    "severity": "error",
                    "code": "duplicate_item_code",
                    "specialty_code": key[0],
                    "quota_code": key[1],
                    "first_page": seen[key]["source_pdf_page"],
                    "duplicate_page": item["source_pdf_page"],
                }
            )
            continue
        seen[key] = item
        unique_items.append(item)
    items = unique_items

    specialty_rows: dict[str, dict[str, Any]] = {}
    chapter_rows: dict[tuple[str, str], dict[str, Any]] = {}
    for item in items:
        family = "房屋建筑与装饰工程" if item["specialty_code"].startswith("BUILD-") else "通用安装工程"
        specialty_rows.setdefault(
            item["specialty_code"],
            {"code": item["specialty_code"], "name": f"{family} {item['specialty_code'].rsplit('-', 1)[-1]}"},
        )
        chapter_rows.setdefault(
            (item["specialty_code"], item["chapter_code"]),
            {
                "specialty_code": item["specialty_code"],
                "code": item["chapter_code"],
                "name": re.sub(r"^[A-Z](?:[.．]\d+)+", "", item["name"]).strip()[:240] or item["chapter_code"],
                "level": 1,
                "parent_code": "",
                "norm_code_start": item["code"],
            },
        )
    for rule in rules:
        family = "房屋建筑与装饰工程" if rule["specialty_code"].startswith("BUILD-") else "通用安装工程"
        specialty_rows.setdefault(
            rule["specialty_code"],
            {"code": rule["specialty_code"], "name": f"{family} {rule['specialty_code'].rsplit('-', 1)[-1]}"},
        )

    source_books = _source_books(pages, source_dir)
    metrics = {
        "page_count": len(pages),
        "book_count": len(source_books),
        "specialty_count": len(specialty_rows),
        "chapter_count": len(chapter_rows),
        "item_count": len(items),
        "resource_count": sum(len(item["resources"]) for item in items),
        "rule_count": len(rules),
        "error_count": sum(issue["severity"] == "error" for issue in issues),
        "warning_count": sum(issue["severity"] == "warning" for issue in issues),
    }
    dataset = {
        "schema": SCHEMA,
        "catalog": {
            "code": "CN-SC-2020-VALUATION",
            "name": "四川省2020建设工程工程量清单计价定额",
            "region_code": "CN-SC",
            "edition_year": "2020",
            "version": "2020版数字化第1版",
            "catalog_type": "valuation",
        },
        "source_books": source_books,
        "specialties": sorted(specialty_rows.values(), key=lambda row: row["code"]),
        "chapters": sorted(chapter_rows.values(), key=lambda row: (row["specialty_code"], row["code"])),
        "items": sorted(items, key=lambda row: (row["specialty_code"], row["code"])),
        "rules": sorted(rules, key=lambda row: row["code"]),
        "page_index": page_index,
        "review_issues": issues,
        "metrics": metrics,
    }
    dataset["dataset_sha256"] = _sha256_bytes(_canonical_json(dataset))
    return dataset
