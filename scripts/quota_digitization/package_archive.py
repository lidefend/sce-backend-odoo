from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


DELIVERABLES = (
    "norm-dataset.json", "quota-items.csv", "resources.csv", "rules.csv",
    "review-queue.csv", "review-queue.json", "release-report.json",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--structured", type=Path, required=True)
    parser.add_argument("--ocr", type=Path, required=True)
    parser.add_argument("--workbook", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        shutil.rmtree(args.output)
    args.output.mkdir(parents=True)
    for name in DELIVERABLES:
        shutil.copy2(args.structured / name, args.output / name)
    shutil.copy2(args.workbook, args.output / args.workbook.name)
    text_dir = args.output / "searchable-text"
    text_dir.mkdir()
    for book_dir in sorted(path for path in args.ocr.iterdir() if path.is_dir()):
        pages = []
        for page_path in sorted(book_dir.glob("*.json")):
            page = json.loads(page_path.read_text(encoding="utf-8"))
            pages.append(
                f"\n===== PDF PAGE {int(page['pdf_page']):04d} | OCR {float(page['mean_confidence']):.4f} =====\n"
                + page.get("text", "").strip()
                + "\n"
            )
        (text_dir / f"{book_dir.name}.txt").write_text("".join(pages), encoding="utf-8")
    readme = """四川省2020建设工程工程量清单计价定额电子档

内容：结构化 Excel、CSV、JSON、逐页检索文本、复核清单、质量报告和 SHA256 清单。
电子档可用于检索、编辑、人工核对和后续数据治理。
复核清单中的费用分项不得直接作为自动计价权威值；请按来源页完成校正。
原始扫描 PDF 未重复打包，来源文件名和 SHA256 已记录在工作簿及 JSON 数据集内。
"""
    (args.output / "README.txt").write_text(readme, encoding="utf-8")
    files = [path for path in sorted(args.output.rglob("*")) if path.is_file()]
    manifest = {
        "schema": "sce.quota.electronic_archive/v1",
        "status": "COMPLETE_WITH_REVIEW_QUEUE",
        "files": [
            {"path": path.relative_to(args.output).as_posix(), "bytes": path.stat().st_size, "sha256": sha256(path)}
            for path in files
        ],
    }
    (args.output / "MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    archive_path = shutil.make_archive(str(args.output), "zip", root_dir=args.output)
    print(json.dumps({"output": str(args.output), "archive": archive_path, "files": len(files) + 1}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
