# 16 · Integrity Guard Implementation

## Delivered

- `scripts/verify/page_composition_integrity_guard.py`
- 独立执行入口，支持 JSON / Markdown 报告。
- 规则基线：PC-001 ~ PC-010。
- Shadow 运行，不改变现有发布门禁退出码。

## Usage

```bash
python3 scripts/verify/page_composition_integrity_guard.py \
  --input <evidence.json> \
  --output-json report.json \
  --output-markdown report.md
```

## Separation

Guard 不重新解析 V2 assembler 业务结构，只消费证据集合并做规则判定。

