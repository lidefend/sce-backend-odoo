# 161 · BNVA-019 Stage 3C-04 · 后端内核全链路验收

## 基线

- 当前 HEAD：`ab5c03f3e74ab7f782096e08c22be0ab89ef71c4`
- 产品收口提交：`12f0e53363fa4d6a44719a4a01ed8113344c7f57`
- 工作树：Clean；缓存 pin：`v25-legacy-fallback-retirement`

## 六项验收结论

### 1. 原生事实单一规范化入口 — 达成（Form 主 arch）

Form 主 arch 的唯一入口是 `native_view_projection.project_native_view`：
一次 `get_view()`、一次 `etree.fromstring()`，并把 `_arch_root` 存入
`RequestScopedCarrier`。Business Adapter 与 Layout Adapter 通过同一 carrier
复用同一份解析根（`app_view_config._safe_get_view_data` store，
`view_Parser.base._view_root` 优先复用 `_arch_root`）。

tree / kanban / pivot / calendar / gantt / search 及内联 x2many 子视图、
onchange / draft_feedback / node_validation 保持独立解析，属于合法分治，
不统计为重复。

### 2. Adapter 职责清晰 — 达成

- Business Structure Adapter（`ui_contract_v2_form_structure.py`）：
  slots / fieldGroups / fieldOwnership / Identity / Section / 字段生命周期。
- Layout Adapter（`view_Parser` + `layout_semantics.py`）：
  containerTree / columns / widgets / toolbar / search / 布局语义。

无跨 Adapter 推导：Business 侧无 widget/toolbar/containerTree 生成；
`layout_semantics.py` 显式声明不得推导 Identity / Section / fieldOwnership / role。

### 3. RequestScopedCarrier 生命周期可靠 — 达成

显式载体，绑定具体 cursor 对象 + uid + su + context digest（lang/tz/
allowed_company_ids/contract_action_id），拒绝关闭/不一致 cursor；LRU 上限 32；
请求入口创建（`ui_contract_v2.py:688`），finally 中 `close()`（`:611-614`）。
非 `id(cursor)` 身份、非模块级全局。定向测试 9/9 通过。

### 4. 旧消费者退出重复事实获取 — 达成

`_fallback_parse` 与 `node_component_validation` 已收敛；onchange /
draft_feedback 按 02B 裁定保留独立请求；Assembler 不再重读 arch、重解析 XML。

### 5. V2 Assembler 仅契约规范化与组装 — 达成

`unified_page_contract_v2_assembler.py` 无 `get_view` / `fromstring` / `etree`
调用；`fieldOwnership` 仅消费并校验引用，不再生成 catch-all；无
`primary_facts / other_facts` 隐式补齐。

### 6. 原生投影失败明确诊断 — 达成

失败且无配置时返回最小结构（`slots=[]`、`fieldRoles={}`、`fieldOwnership={}`、
`structureAuthority=container_tree`）；`pageComposition` 分类为
`unclassified_historical` 并携带 `PAGE_COMPOSITION_FIELD_OWNERSHIP_MISSING`
(V10)。显式 `entry_semantic_surface` 仍保持 `task_sections + task`。

