# 后端数据逻辑文档

## 概述

本文档记录 sce-backend-odoo 后端的统一契约读取数据逻辑，便于后续精准控制字段显示、隐藏和转换。

## 数据加载链路

### 1. 前端请求入口

前端通过 `/ui/contract` 接口请求数据，传递以下关键参数：
- `op` / `subject`: 操作类型（nav/menu/model/view/action_open）
- `action_id`: 动作 ID
- `menu_id`: 菜单 ID
- `model`: 模型名称
- `record_id`: 记录 ID
- `view_type`: 视图类型（tree/form）
- `contract_surface` / `surface`: 契约表面（user/hud/native）
- `contract_mode`: 契约模式（user/hud）

### 2. 控制器分发

文件：`addons/smart_core/handlers/ui_contract.py`

`UIContract` 控制器根据 `op` 参数分发到不同的处理方法：

| op 值 | 处理方法 | 说明 |
|-------|---------|------|
| `nav` | `_op_nav` | 导航数据 |
| `menu` | `_op_menu` | 菜单数据 |
| `model` | `_op_model` | 模型数据 |
| `action_open` | `_op_action_open` | 动作打开（表单/列表） |
| `view` | `_op_view` | 视图数据 |

### 3. action_open 处理链路

`_op_action_open` 是表单页面的主要加载路径：

```
_op_action_open
  → _dispatch_model_contract(model, view_type, ...)
    → ActionDispatcher.dispatch(payload)
      → PageAssembler.assemble_page_contract(p, action)
```

**关键点**：`action_open` 路径**不经过** `_shape_delivery_data` 和 `apply_contract_governance`。

### 4. nav/menu/model/view 处理链路

对于 `op=nav/menu/model/view`，数据经过契约治理管道：

```
_op_xxx
  → _shape_delivery_data(data, contract_mode, contract_surface, ...)
    → apply_contract_governance(data, contract_mode, contract_surface="user")
      → _apply_domain_overrides(data, effective_mode)  [仅当 normalized_surface != "native"]
        → 遍历 DOMAIN_OVERRIDE_REGISTRY 中的所有 handler
```

### 5. ActionDispatcher 分发

文件：`addons/smart_core/app_config_engine/services/dispatchers/action_dispatcher.py`

`ActionDispatcher.dispatch` 根据 `subject` 分发：

| subject | 处理方式 |
|---------|---------|
| `model` | `PageAssembler.assemble_page_contract(p)` |
| `action` | 解析动作类型（act_window/client/server/url/report），act_window 走 `PageAssembler.assemble_page_contract` |
| `operation` | execute/onchange/validate/report 四类网关 |

### 6. PageAssembler 页面契约装配

文件：`addons/smart_core/app_config_engine/services/assemblers/page_assembler.py`

`assemble_page_contract` 构建完整的页面契约，包括：
- `fields`: 字段描述符映射（从 `app.model.config` 或 ORM `fields_get()` 获取）
- `views`: 视图配置（tree/form）
- `search`: 搜索配置
- `permissions`: 权限配置
- `buttons`: 按钮配置
- `toolbar`: 工具栏配置
- `workflow`: 工作流配置
- `reports`: 报表配置
- `validator`: 校验器配置

## 契约治理管道

### apply_contract_governance

文件：`addons/smart_core/utils/contract_governance.py`

函数签名：
```python
def apply_contract_governance(
    data: dict | Any,
    contract_mode: str,
    *,
    contract_surface: str = "user",  # 默认 user
    source_mode: str = "",
    inject_contract_mode: bool = True,
) -> dict | Any:
```

### normalized_surface 计算

```python
normalized_surface = str(contract_surface or "").strip().lower()
if normalized_surface not in CONTRACT_SURFACES:
    normalized_surface = "hud" if contract_mode == "hud" else "user"
```

### 关键分支

```python
if normalized_surface != "native":
    _apply_sanitize_governance(data, effective_mode)
    _apply_semantic_governance(data, effective_mode)
    override_failures = _apply_domain_overrides(data, effective_mode)  # ★ 仅非 native 时调用
    _preserve_native_layout_labels(data)
    _emit_relation_entry_semantics(data)
    _normalize_business_field_labels(data)
    _ensure_scene_contract_envelope(data)
else:
    override_failures = []  # ★ native surface 跳过 domain overrides
```

**重要**：当 `contract_surface="native"` 时，`_apply_domain_overrides` 不会被调用，所有通过 `register_contract_domain_override` 注册的 handler 都不会执行。

## Domain Overrides 注册机制

### 注册方式

文件：`addons/smart_construction_core/services/contract_governance_overrides.py`

```python
from odoo.addons.smart_core.utils.contract_governance import register_contract_domain_override

def _my_override_handler(data: dict, contract_mode: str) -> None:
    # 处理逻辑
    pass

register_contract_domain_override(
    "my_override_name",
    _my_override_handler,
    priority=30,
)
```

### 注册表

文件：`addons/smart_core/utils/contract_governance_domain_overrides.py`

```python
DOMAIN_OVERRIDE_REGISTRY: list[dict[str, Any]] = []

def register_contract_domain_override(name, handler, *, priority=100):
    # 按 priority 排序，priority 越小越先执行
    DOMAIN_OVERRIDE_REGISTRY.append({"name": name, "priority": priority, "handler": handler})
    DOMAIN_OVERRIDE_REGISTRY.sort(key=lambda item: item.get("priority") or 100)

def apply_domain_overrides(data: dict, contract_mode: str) -> list[dict[str, Any]]:
    # 遍历所有注册的 handler，异常被捕获并记录到 failures
    for row in DOMAIN_OVERRIDE_REGISTRY:
        handler = row.get("handler")
        try:
            handler(data, contract_mode)
        except Exception as exc:
            failures.append({"name": ..., "error_type": ..., "message": ...})
    return failures
```

### 已注册的 overrides

| 名称 | priority | 说明 |
|------|----------|------|
| `smart_construction_core.project_form` | 10 | 项目表单 domain 覆盖 |
| `smart_construction_core.project_intake_form` | 20 | 项目录入表单治理 |
| `smart_construction_core.project_ledger_form_surface` | 30 | 项目台账表单表面治理 |
| `smart_construction_core.partner_form_surface` | 30 | 合作伙伴表单表面治理（仅非 native surface 生效） |

## 字段隐藏机制

### 1. Domain Override 方式（仅非 native surface）

在 `register_contract_domain_override` 的 handler 中调用 `_hide_field`：

```python
def _hide_field(data: dict, fields_map: dict, name: str) -> None:
    descriptor = _as_dict(fields_map.get(name))
    if descriptor:
        descriptor["semantic_type"] = "technical"
        descriptor["surface_role"] = "hidden"
        descriptor["technical"] = True
        fields_map[name] = descriptor
    semantics = _as_dict(data.get("field_semantics"))
    semantics[name] = {"semantic_type": "technical", "surface_role": "hidden", "technical": True}
    data["field_semantics"] = semantics
    visible_fields = data.get("visible_fields")
    if isinstance(visible_fields, list):
        data["visible_fields"] = [item for item in visible_fields if _text(item) != name]
```

**限制**：仅在 `normalized_surface != "native"` 时生效。

### 2. 前端字段可见性判断

文件：`frontend/apps/web/src/pages/contractForm/useRecordFormLayout.ts`

```typescript
function isFieldVisible(name: string) {
    const semantic = context.fieldSemanticMeta(name);
    if ((semantic.technical || semantic.semantic_type === 'technical') && !context.showHud.value) return false;
    if (semantic.surface_role === 'hidden' && !context.showHud.value) return false;
    // ...
}
```

前端根据 `field_semantics` 中的 `surface_role="hidden"` 或 `technical=true` 来隐藏字段。

### 3. native surface 的字段隐藏

对于 `action_open` 路径（native surface），由于不经过 `apply_contract_governance`，需要在 `PageAssembler.assemble_page_contract` 或更早的阶段处理字段隐藏。

可能的方式：
- 在 `app.model.config` 中配置字段的 `surface_role` 或 `technical` 属性
- 在 `PageAssembler._to_fields_map` 中添加字段过滤逻辑
- 在视图配置（`app.view.config`）中排除字段

## 数据结构

### 表单契约数据结构

```python
data = {
    "head": {
        "title": str,
        "model": str,           # 模型名称，如 "res.partner"
        "view_type": str,       # 视图类型，如 "form"
        "action_id": int,
        "domain": list,         # 域过滤
        "context": dict,        # 上下文
        "permissions": dict,    # 权限
        "render_profile": str,  # 渲染配置
        "access_policy": dict,  # 访问策略
    },
    "views": {
        "form": {
            "layout": list,     # 布局节点
            "header_buttons": list,
            "button_box": list,
            "stat_buttons": list,
            "business_actions": list,
            "statusbar": list,
        },
        "tree": {...},
    },
    "fields": {
        "field_name": {
            "string": str,          # 字段标签
            "type": str,            # 字段类型
            "relation": str,        # 关联模型（many2one/one2many/many2many）
            "required": bool,
            "readonly": bool,
            "domain": list,         # 字段域
            "context": dict,        # 字段上下文
            "semantic_type": str,   # 语义类型
            "surface_role": str,    # 表面角色（hidden/core/advanced）
            "technical": bool,      # 是否技术字段
            # ... 其他属性
        },
    },
    "field_semantics": {
        "field_name": {
            "semantic_type": str,
            "surface_role": str,
            "technical": bool,
        },
    },
    "visible_fields": list,     # 可见字段列表
    "search": dict,
    "permissions": dict,
    "buttons": list,
    "toolbar": dict,
    "workflow": dict,
    "reports": list,
    "validator": dict,
    "model": str,               # 顶层模型名称（可能与 head.model 不同）
    "view_type": str,           # 顶层视图类型
    "contract_surface": str,    # 契约表面（治理后设置）
    "render_mode": str,         # 渲染模式（native/governed）
    # ... 其他属性
}
```

## 关键注意事项

1. **action_open 不经过契约治理**：通过 `action_id` 打开的表单页面，数据走 `ActionDispatcher` → `PageAssembler`，不经过 `apply_contract_governance`，因此 `register_contract_domain_override` 注册的 handler 不会执行。

2. **native surface 跳过 domain overrides**：即使经过 `apply_contract_governance`，如果 `contract_surface="native"`，也会跳过 `_apply_domain_overrides`。

3. **字段隐藏的权威来源**：前端根据 `field_semantics[field_name].surface_role === "hidden"` 或 `technical === true` 来隐藏字段。要隐藏字段，需要确保这两个属性被正确设置。

4. **model 字段位置**：`data["head"]["model"]` 和 `data["model"]` 可能不同。在 domain override handler 中，应使用 `head.get("model") or data.get("model")` 来获取模型名称。

5. **override handler 异常静默**：`apply_domain_overrides` 会捕获 handler 的异常并记录到 failures，但不会抛出。如果 handler 没有生效，应检查是否有异常被静默捕获。

## 调试技巧

1. **在 handler 中添加 print 语句**：由于 Odoo 日志可能不显示，使用 `print()` 可以直接输出到 stdout。

2. **检查 handler 是否被调用**：在 handler 开头添加 `print("[DEBUG] called")`，然后查看 `docker logs <container>`。

3. **检查 data 结构**：在 handler 中输出 `data.keys()` 和 `data.get("head", {}).get("model")`，确认数据结构和模型名称。

4. **检查 contract_surface**：在 `apply_contract_governance` 调用处检查 `contract_surface` 参数，确认是否为 "native"。

5. **检查前端请求参数**：在浏览器 Network 面板中查看 `/ui/contract` 请求的参数，确认 `contract_surface` 和 `op` 的值。


---

## 关键发现：前端使用 ui.contract.v2 接口（2026-08-28 排查）

### 核心结论

**前端使用的是 `ui.contract.v2` 接口，而不是 `ui.contract` 接口。** 这是两个完全不同的接口，返回的数据结构也完全不同。

- `ui.contract` 接口：返回 `views.form.layout` 结构，字段节点包含 `fieldInfo`、`attributes` 等属性
- `ui.contract.v2` 接口：返回 `layoutContract.containerTree` 结构，每个 container 包含 `widgetList`，每个 widget 包含 `componentConfig`

### 前端数据加载链路（ui.contract.v2）

```
前端 intentRequestRaw({intent: 'ui.contract.v2', params})
  -> 后端 UiContractV2Handler.handle()
    -> 返回包含 layoutContract.containerTree 的契约数据
  -> 前端 decodeContractV2Snapshot(response.data)
    -> normalizeLegacyContractV2Snapshot(value)  [仅规范化已存在的 layoutContract，不做转换]
    -> decodeLayoutContract(root.layoutContract)
      -> decodeContainer(containerTree[i])
        -> decodeWidget(widgetList[i])
          -> componentConfig: optionalRecord(raw, 'componentConfig', ...)
  -> 前端 createContractV2Store(snapshot)
    -> collectWidgets(snapshot)
      -> walkContainers(snapshot.layoutContract.containerTree, (container) => {
          container.widgetList.forEach(pushWidget)
        })
    -> widgetsByFieldCode: indexBy(widgets, widget => widget.fieldCode)
  -> 前端 resolveContractV2FieldDescriptorMap(store)
    -> widgetsByFieldCode.forEach((widget, fieldCode) => {
        const config = asDict(widget.componentConfig)
        ...
        ...(asText(config.surfaceRole) ? { surfaceRole: asText(config.surfaceRole) } : {})
      })
  -> 前端 useRecordContractSemantics
    -> fieldDescriptors = resolveContractV2FieldDescriptorMap(v2ContractStore)
    -> contractFieldSemantics = Object.fromEntries(fieldDescriptors.map(([fieldCode, row]) => [fieldCode, {
        semantic_type: row.semanticType,
        surface_role: row.surfaceRole,
        technical: row.technical,
      }]))
    -> fieldSemanticMeta(name) = resolveFieldSemanticMeta(name, contractFieldSemantics, formFields[name])
  -> 前端 useRecordFormLayout
    -> isFieldVisible(name) {
        const semantic = context.fieldSemanticMeta(name)
        if (semantic.surface_role === 'hidden' && !context.showHud.value) return false
      }
    -> isNativeFieldVisible(name, node) {
        return isNativeFieldVisibleFromNativeLayout({
          ...
          semantic: context.fieldSemanticMeta,
          ...
        })
      }
    -> nativeVisibleFieldNames = collectNativeVisibleFieldNames(nativeFormLayoutNodes, (name, node) => isNativeFieldVisible(name, node))
    -> isWritableFieldVisible(name) = useNativeFormTree.value ? nativeVisibleFieldNames.has(name) : isFieldVisible(name)
```

### 字段隐藏的权威位置

**要隐藏一个字段，必须在 `ui.contract.v2` 接口返回的 `layoutContract.containerTree` 中的对应 widget 的 `componentConfig` 中设置 `surfaceRole: "hidden"`。**

具体位置：
- 后端：`addons/smart_core/handlers/ui_contract_v2.py` 中的 `UiContractV2Handler`
- 数据结构：`contract_v2["layoutContract"]["containerTree"][i]["widgetList"][j]["componentConfig"]["surfaceRole"] = "hidden"`

### 之前修改无效的原因

之前在以下位置的修改对 `ui.contract.v2` 接口完全无效：

1. **`register_contract_domain_override`**：只在 `apply_contract_governance` 中调用，而 `apply_contract_governance` 只在 `ui.contract` 接口的 `_shape_delivery_data` 中调用，`ui.contract.v2` 接口不经过这个管道。

2. **`smart_core_finalize_projected_contract_data` 扩展钩子**：只在 `ui.contract` 接口的 `_finalize_projected_contract` 中调用，`ui.contract.v2` 接口不经过这个钩子。

3. **`field_semantics` 中的 `surface_role`**：前端 `ui.contract.v2` 路径不使用后端返回的 `field_semantics`，而是从 `widget.componentConfig.surfaceRole` 中重新构建 `contractFieldSemantics`。

4. **`fields` 中的 `surface_role`**：前端 `ui.contract.v2` 路径不使用后端返回的 `fields` 中的 `surface_role`，而是从 `widget.componentConfig.surfaceRole` 中获取。

### ui.contract.v2 接口的关键文件

| 文件 | 说明 |
|------|------|
| `addons/smart_core/handlers/ui_contract_v2.py` | `ui.contract.v2` 接口的主处理器 |
| `addons/smart_core/core/unified_page_contract_v2_assembler.py` | v2 契约数据的组装器 |
| `addons/smart_core/core/unified_page_contract_v2_client.py` | v2 契约数据的客户端投影 |
| `frontend/apps/web/src/app/contracts/v2/client.ts` | 前端 v2 契约加载器 |
| `frontend/apps/web/src/app/contracts/v2/schema.ts` | v2 契约数据的解码 schema |
| `frontend/apps/web/src/app/contracts/v2/store.ts` | v2 契约数据的 store |
| `frontend/apps/web/src/app/contracts/v2/legacyLayoutNormalizer.ts` | v2 契约数据的 legacy 布局规范化器 |

### 前端关键字段可见性判断

1. **`isFieldVisible`**（`useRecordFormLayout.ts` 第 89 行）：
   ```typescript
   const semantic = context.fieldSemanticMeta(name)
   if (semantic.surface_role === 'hidden' && !context.showHud.value) return false
   ```

2. **`isNativeFieldVisibleFromNativeLayout`**（`nativeLayoutUtils.ts` 第 788 行）：
   ```typescript
   if (semantic.surface_role === 'hidden' && !input.showHud) return false
   ```

3. **`resolveFieldSemanticMeta`**（`nativeLayoutUtils.ts` 第 893 行）：
   ```typescript
   const fromMap = fieldSemantics[name]
   if (fromMap) return fromMap
   const source = descriptor as Record<string, unknown> | undefined
   return {
     semantic_type: String(source?.semantic_type || '').trim().toLowerCase(),
     surface_role: String(source?.surface_role || '').trim().toLowerCase(),
     technical: Boolean(source?.technical),
   }
   ```

### 调试技巧（ui.contract.v2）

1. **检查后端返回的契约数据结构**：在浏览器 Network 面板中查看 `ui.contract.v2` 请求的响应，确认是否包含 `layoutContract.containerTree`。

2. **检查 widget 的 componentConfig**：在 `layoutContract.containerTree` 中遍历找到目标字段的 widget，检查 `componentConfig.surfaceRole` 是否为 "hidden"。

3. **检查前端的 v2ContractStore**：在前端代码中添加调试日志，输出 `v2ContractStore.widgetsByFieldCode.get(fieldName).componentConfig`。

4. **检查前端的 fieldDescriptors**：在前端代码中添加调试日志，输出 `resolveContractV2FieldDescriptorMap(v2ContractStore)[fieldName].surfaceRole`。

5. **检查前端的 fieldSemanticMeta**：在前端代码中添加调试日志，输出 `fieldSemanticMeta(fieldName).surface_role`。

### 后续行动项

1. 在 `ui.contract.v2` 接口的处理逻辑中添加字段隐藏机制，遍历 `layoutContract.containerTree`，找到目标字段的 widget，设置 `componentConfig.surfaceRole = "hidden"`。

2. 可以考虑在 `UiContractV2Handler` 中添加一个扩展钩子，允许其他模块注册字段隐藏规则。

3. 更新文档，记录 `ui.contract.v2` 接口的完整数据链路和字段隐藏机制。

## 关键问题排查记录：country_id 字段隐藏失败的根因与解决方案

### 问题描述

在客户档案（res.partner）表单中，后端已正确设置 `country_id` 字段的 `componentConfig.surfaceRole = "hidden"`，前端 `isNativeLayoutNodeVisible` 也正确返回 `false`，但页面上仍然显示 `country_id` 字段。

### 根因分析

经过全链路深度排查，发现前端存在**两条独立的渲染路径**：

1. **ContractFormNativeCanvas 路径**（字段配置编辑模式）：
   - 使用 `nativeFormLayoutNodes`（已通过 `filterVisibleNativeLayoutNodes` 过滤）
   - `isNativeLayoutNodeVisible` 函数正确检查 `surface_role === 'hidden'`
   - 此路径下 `country_id` 字段被正确隐藏

2. **ContractFormDriverHost 路径**（正常业务模式，`v-if="!showCurrentFormFieldConfigScope"`）：
   - 使用 `nativeBridge.primaryNodes` 和 `nativeBridge.subordinateNodes`
   - `nativeBridge` 通过 `buildCanonicalNativeFormBridge` 函数构建
   - **关键问题**：`buildCanonicalNativeFormBridge` 返回的 `nodeVisible` 函数只检查 `node.visible !== false`，**不检查 `surface_role === 'hidden'`**
   - 同时，`fieldNode` 函数没有将 `field.componentConfig.surfaceRole` 传递给节点的 `attributes`

### 解决方案

修改 `canonicalNativeFormBridge.ts` 文件：

1. **在 `fieldNode` 函数中**，将 `field.componentConfig.surfaceRole` 和 `technical` 传递给节点的 `attributes`：
   ```typescript
   attributes: {
     // ... 其他属性
     surfaceRole: text((field.componentConfig as Record<string, unknown>)?.surfaceRole),
     technical: (field.componentConfig as Record<string, unknown>)?.technical === true,
   },
   ```

2. **在 `nodeVisible` 函数中**，检查节点的 `attributes.surfaceRole === 'hidden'` 和 `technical === true`：
   ```typescript
   nodeVisible(node) {
     if (node.visible === false) return false;
     const attrs = (node.attributes || {}) as Record<string, unknown>;
     const surfaceRole = text(attrs.surfaceRole);
     if (surfaceRole === 'hidden') return false;
     if (attrs.technical === true) return false;
     return true;
   },
   ```

### 关键文件清单

| 文件 | 位置 | 作用 |
|------|------|------|
| `canonicalNativeFormBridge.ts` | `frontend/apps/web/src/pages/contractForm/` | 构建 `nativeBridge`，包含 `fieldNode` 和 `nodeVisible` 函数 |
| `ContractFormDriverHost.vue` | `frontend/apps/web/src/pages/contractForm/` | 正常业务模式的表单渲染组件，使用 `nativeBridge.primaryNodes` |
| `ContractFormNativeCanvas.vue` | `frontend/apps/web/src/pages/contractForm/` | 字段配置编辑模式的表单渲染组件，使用 `nativeFormLayoutNodes` |
| `ContractFormPage.vue` | `frontend/apps/web/src/pages/` | 表单页面主组件，通过 `v-if="!showCurrentFormFieldConfigScope"` 选择渲染路径 |

### 经验教训

1. **前端存在多条渲染路径**：修改字段可见性逻辑时，必须检查所有渲染路径，不能只检查一条。
2. **`nodeVisible` 函数是关键**：`NativeFormTreeRenderer` 组件使用传入的 `isNodeVisible` 函数来判断节点是否可见，不同渲染路径传入的函数可能不同。
3. **`fieldNode` 函数需要传递完整的字段元数据**：如果 `fieldNode` 函数没有将 `componentConfig.surfaceRole` 传递给节点，那么 `nodeVisible` 函数就无法检查它。
4. **调试时需要确认当前使用的渲染路径**：可以通过检查 `showCurrentFormFieldConfigScope` 的值来确认当前使用的是哪条渲染路径。

---

## 字段标签本地化机制（继承社区模块的正确方式）

### 核心原则

**我们的模块继承了社区模块，最终生效的应该是我们的设置，而不是原生设置。**

### 问题现象

在 `partner_business.py` 中重新定义了 `res.partner` 模型的字段标签：
```python
category_id = fields.Many2many("res.partner.category", string="业务分类")
```

但前端显示的还是 Odoo 原生的中文翻译"标签"，而不是我们定义的"业务分类"。

### 根因分析

Odoo 的字段标签翻译机制：

1. **`ir.model.fields` 表**中的 `field_description` 字段是一个翻译字段（`jsonb` 类型），存储为 `{"en_US": "...", "zh_CN": "..."}`
2. **Python 代码中的 `string` 属性**被写入 `field_description` 的 `en_US` 键
3. **`.po` 翻译文件中的翻译**被写入 `field_description` 的对应语言键
4. **翻译的匹配是基于 `ir.model.fields` 表中记录的 XML ID**，而不是基于 `msgid`

问题在于：
- 我们的 Python 代码正确更新了 `en_US` 的值（变成了"业务分类"）
- 但 Odoo 原生的中文翻译（`zh_CN` = "标签"）没有被覆盖，因为我们的翻译文件引用格式不正确

### 正确的解决方案

**方案：在 Python 代码中定义 `string` + 在翻译文件中提供中文翻译**

1. **Python 代码**（`partner_business.py`）：
```python
category_id = fields.Many2many("res.partner.category", string="业务分类")
```

2. **中文翻译文件**（`i18n/zh_CN.po`）：
```po
#: model:ir.model.fields,field_description:base.field_res_partner__category_id
msgid "业务分类"
msgstr "业务分类"
```

**关键点**：翻译文件中的引用必须使用正确的 XML ID（如 `base.field_res_partner__category_id`），而不是字段名（如 `res.partner.category_id`）。

### 验证方法

检查数据库中 `ir.model.fields` 表的 `field_description` 字段：
```sql
SELECT name, field_description FROM ir_model_fields 
WHERE model = 'res.partner' AND name = 'category_id';
```

正确结果：
```json
{"en_US": "业务分类", "zh_CN": "业务分类"}
```

### 已本地化的字段清单

| 字段名 | 原生中文标签 | 我们的中文标签 |
|--------|-------------|---------------|
| `category_id` | 标签 | 业务分类 |
| `company_type` | 公司类型 | 客户类型 |
| `industry_id` | 工业 | 行业 |
| `vat` | 税项ID | 统一社会信用代码 |
| `is_company` | 是公司 | 企业/组织 |
| `company_registry` | 公司注册 | 工商注册号 |
| `bank_ids` | 银行 | 账户 |
| `child_ids` | 联系人 | 联系人 |
| `state_id` | 州 | 省/州 |
| `country_id` | 国家 | 国家/地区 |

### 经验教训

1. **不要使用 `translate=False` 来绕过翻译问题**：这会破坏多语言支持，是一种降级方案。
2. **继承社区模块的正确方式**：在 Python 代码中重新定义 `string`（覆盖 `en_US`），在翻译文件中提供中文翻译（覆盖 `zh_CN`）。
3. **翻译文件的引用格式很重要**：必须使用 XML ID（如 `base.field_res_partner__category_id`），而不是字段名。
4. **模块更新后需要验证**：检查数据库中 `field_description` 字段的 `zh_CN` 值是否被正确覆盖。
5. **每个字段可能有多个 XML ID**：原生模块的 XML ID（如 `base.field_res_partner__category_id`）和我们模块的 XML ID（如 `smart_construction_core.field_res_partner__category_id`），翻译文件中使用任意一个都可以。
