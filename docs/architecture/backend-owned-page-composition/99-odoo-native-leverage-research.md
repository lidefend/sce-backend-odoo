# 99 · Odoo 原生能力利用度 · 整体只读研究

## 结论先行

后端契约链路已经用了 Odoo 的 `get_view()`/`fields_view_get()` 取合并视图，这是对的；
但取到之后又建了一条**并行的自定义解析 + 组装管线**，把 Odoo 已经算好的结构再推导一遍。
最大的架构问题不是“没用 Odoo”，而是：

> 原生视图 arch 已经用 `<group name="...">` 声明了字段 → 业务分组，
> 但 fieldOwnership 却用**字段名启发式**另推导了一套 slot/group，
> 于是系统里同时存在两套不一致的业务结构，再用 Guard / pageComposition / diagnostics
> 去兜两套之间的差异。

## 一、当前数据流

```text
ir.actions.act_window / menu
        ↓
model.get_view() / fields_view_get()   ← 已合并继承、已按用户裁剪组、已算 modifiers
        ↓ 返回 arch(str) + fields(dict) + toolbar
view_Parser/contract_Parser.py          ← 又用 lxml 把 arch 重新解析一遍
        ↓ lossless_parse_xml + _parse_form_view + _collect_modifiers
page_assembler.py (4634 行)             ← 再组装成 layout/fields/subviews
        ↓
ui_contract_v2.py (4295 行)             ← 再富化 formStructureContract
        ↓
unified_page_contract_v2_assembler.py (5729 行)  ← 再组装 V2 contract
        ↓
ui.contract.v2 JSON → Vue 前端
```

链路核心代码规模（约 1.7 万行）：

- `unified_page_contract_v2_assembler.py` 5729
- `page_assembler.py` 4634
- `ui_contract_v2.py` 4295
- `view_orchestrator.py` 1316
- `ui_contract_v2_projection.py` 1128
- `view_Parser/*` 517
- `ui_contract_v2_form_structure.py` 488
- `form_structure_authority.py` 450

## 二、Odoo 原生已经提供了什么

1. **合并后的视图 arch**：`get_view()` 已应用 `inherit_id` 继承、按 groups 裁剪节点。
2. **字段元数据**：`fields` dict（string / type / help / required / readonly），
   `fields_get()` 是模型级字段真相。
3. **已求值的 modifiers**：`invisible` / `readonly` / `required`（含上下文表达式）
   在 `fields_view_get` 的 `_postprocess_view` 阶段已算好并写进 arch 的 `modifiers`。
4. **业务结构本身**：`<group name="sc_project_information_identity">` 等原生组，
   已经把“字段属于哪个业务分组”声明清楚了——这是最该被复用的结构事实。
5. **toolbar / search / action 域与上下文**：`get_view()` 与 `act_window` 已给出。

## 三、重复/绕弯点（有据可查）

1. **重新解析 arch**：`contract_Parser.py:208` `_parse_arch_root` 用 `etree.fromstring`
   把 `get_view()` 返回的 arch 字符串再解析；`_lossless_parse_xml` 再保真遍历一遍。
2. **重新收集 modifiers**：`base.py` 引入 `safe_eval` 归一 modifiers，而 Odoo 已在
   `fields_view_get` 阶段求值。
3. **重新回填字段 label**：`_enrich_view_fields_info` 用 `root.xpath(".//field[@name]")`
   把 `<field string>` 再写回 `fields[name]["string"]`，而 `get_view().fields` +
   `fields_get()` 本来就有 string。
4. **最核心：业务结构双轨**：
   - 原生 arch 有 11 个 `sc_project_information_*` 组（identity/entity/contact/
     arrangement/schedule/responsible/responsibility/description/collaboration/trace）。
   - 但 `ui_contract_v2_form_structure.py` 用**字段名启发式**
     （`identity_fields`、`relation_candidates`、`term_fields`、`amount_fields`、
     `status_fields`、`collaboration_fields`…）另推导出 5 个自定义 slot
     （overview / primary_facts / amount_progress / collaboration / details_source）。
   - 于是 containerTree 保留原生组，formStructureContract 保留自定义 slot，
     两者不一致，再用 fieldOwnership + Guard + diagnostics 兜底。

## 四、改进方向（建议，未实施）

1. **fieldOwnership 直接由原生组推导**：字段属于哪个 `<group name>`，就归属哪个
   组；不要再用字段名猜 identity/relation/term/amount。
2. **slot 映射到原生结构**：把顶层 `<sheet>` 下的原生 group 层级作为 slot/group 的
   唯一来源，删除字段名启发式清单。
3. **V2 contract 瘦身为 Odoo 视图的投影**：容器树、字段、modifiers、toolbar 尽量
   原样投影，减少二次推导。
4. **删除“技术字段排除”这类补丁**：技术字段（active、write_date、message_* 等）
   本来就不在业务 `<group>` 里，按原生组推导自然就不会被误当业务字段。

## 五、风险与边界

- 这是架构层面的瘦身方向，不能在一次提交里硬改；需要先确认前端对
  formStructureContract.slots 的消费假设，再设计“原生组即 slot/group”的映射。
- 保留 `get_view()` 作为唯一视图入口（这一点已经正确）。
- 本报告只读，未改任何产品代码。
