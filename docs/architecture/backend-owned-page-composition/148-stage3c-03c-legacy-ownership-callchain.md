# 148 · BNVA-019 Stage 3C-03C-01 · 旧 ownership 调用链

## 定义位置

`unified_page_contract_v2_assembler.py` 的 `_page_composition_contract`：

```text
if "primary_facts" in slot_ids and "other_facts" in group_ids:
    把 widget_field_codes 中未归属、非技术字段，归属到
    slot:primary_facts / group:other_facts
```

## 上游来源

`primary_facts` / `other_facts` 由 `ui_contract_v2_form_structure.py` 的旧字段名
启发式 DEFAULT 路径产生（identity/relation/term/fact/amount/... 分类清单）。

## 触发条件

1. 当前是 form。
2. 没有 `native_authority` / `entry_semantic_surface`（未选中权威）。
3. 原生投影失败，回退到启发式 DEFAULT。

## 是否覆盖已有 ownership

否。只补「未归属」的 layout-rendered 字段，不覆盖已有 fieldOwnership。

## 真实运行

五个样本 + PC-01/02 均未触发（都走 native_form_slots / container_tree /
task_sections）。该兜底仅在原生投影抛异常的兼容回退路径可达。

