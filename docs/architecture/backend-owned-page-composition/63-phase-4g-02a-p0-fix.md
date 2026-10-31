# 63 · Phase 4G-02A P0 Fix（_text NameError）

## Verdict

READY_WITH_CONSTRAINTS

## 修复内容

`scripts/verify/page_composition_integrity_guard.py` 新增局部辅助函数：

```python
def _text(value: Any) -> str:
    return str(value or "").strip()
```

- 位置：`_as_list` 之后、`_rule` 之前。
- 语义：与仓库既有 `_text` 惯例一致（`str(value or "").strip()`）。
- 范围：仅修复 PC-005 中 `_text` 未定义导致的潜在 `NameError`，未重构 Guard。

## 修复理由

PC-005 在 `slots` 非空时调用 `_text(...)`，但文件未定义该函数。此前五个已知
样本 slots 为空或未采集，未触发；payment.request（slots=9）已具备触发条件。

## 实施前基线

- branch：`feature/pc01-r2-identity-status`
- HEAD：`a9cd2fd5879d8a5358c2ad737602e0ae72644555`
- Guard 版本：`1.0.0`
- 工作树：保留全部既有未提交改动，未 reset / clean / 覆盖 / 清理。
- 保护对象确认：`unified_page_contract_v2_assembler.py`、
  `page_composition_integrity_guard.py`、`docs/architecture/`、
  `docs/research/`、`.agent/decisions/ARCH-DECISION-004.yaml` 均未受影响。

## 测试

新增 `scripts/verify/test_page_composition_integrity_guard.py`，12 项回归全部
通过，覆盖任务书要求的 10 类场景，并以 slots=9 结构验证不再出现 NameError。
详见 64 号文档。

## 回归确认

- 真实样例 `guard-sample-action590.json`：overall NOT_VERIFIED、PC-005
  NOT_VERIFIED、PC-006 PASS，与修复前一致。
- `main()` 返回 0，JSON 与 Markdown 均正常产出。
- Guard 未被任何 Make/verify 链路引用，Shadow 退出码语义未改变。

## 本轮新发现（不修复，移交 4G-02C）

测试暴露出 PC-005 的既有语义缺陷：

1. `ownerSlotRef` 使用 `slot:<slot_id>`，而 Guard 内 slot id 使用裸 `id`
   （如 `identity`）。`other_slots = slot_ids - {primary_slot}` 因此永远
   减不掉主 slot，合法辅助投影可能被误判。
2. `fieldRefs` 为不可迭代标量（如整数）时仍可能抛 `TypeError`（与 `_text`
   无关的既有健壮性问题）。

以上均不属于本轮 P0 范围，已按最小修复纪律保留，列入 4G-02C。

## 文件变更

- 修改：`scripts/verify/page_composition_integrity_guard.py`（新增 `_text`）。
- 新增：`scripts/verify/test_page_composition_integrity_guard.py`。
- 未改：assembler、Schema、业务配置、权限、数据库、Legacy fallback。
