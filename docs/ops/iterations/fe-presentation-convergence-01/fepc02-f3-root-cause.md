# FEPC-02 / F3 根因追踪结论

结论：F3“项目台账列值重复语义”是审计方法误报，不是视觉缺陷，无需修改产品代码。

## 追踪链

- 项目台账 action 绑定 tree 视图 `view_project_my_list_tree`
  （`addons/smart_construction_core/views/core/project_list_views.xml`）。
- 列声明里 `lifecycle_state` string="项目状态"、`contract_amount` string="合同总额"
  都是列头 label，与单元格值无关。
- 单元格内出现的前缀来自两个设计系统组件：
  - `ScStatusBadge.vue`：`statusPrefix` 默认 `'状态：'`，渲染在
    `<span class="sc-visually-hidden">{{ statusPrefix }}</span>` 内。
  - `ScMoney.vue`：`label` 渲染在
    `<span v-if="label" class="sc-visually-hidden">{{ label }}：</span>` 内。
- `.sc-visually-hidden` 定义在 `frontend/apps/web/src/styles/product-patterns.css:448`：
  `position:absolute; width/height:1px; clip:rect(0,0,0,0); clip-path:inset(50%)`，
  视觉不可见、仅辅助技术可读。

## 实测证据

项目台账第一行：

| 列 | innerText（含辅助文本） | visually-hidden 前缀 | 前缀几何尺寸 |
| --- | --- | --- | --- |
| 项目状态 | `状态： 草稿` | `状态：` | 1×1 px |
| 合同总额 | `合同总额： ¥11,227,000.00` | `合同总额：` | 1×1 px |

视觉可见内容只有 `草稿` 和 `¥11,227,000.00`，前缀从不出现在可见画面。

## 误判原因

`innerText` 不排除 `clip` 式 visually-hidden 元素（它不是 display:none / visibility:hidden），
因此把辅助技术文本当成可见文本。截图复核与人工观察均显示纯值，与本结论一致。

## 建议

- 撤销 F3 的“已确认视觉缺陷”裁定，改为“审计方法误报”。
- 不删除 `statusPrefix` / `ScMoney.label`，不修改产品代码。
- 若需要，另立无障碍评估项：桌面表格列头已提供字段 label 时，单元格 visually-hidden
  前缀是否对屏幕阅读器冗余。该问题与视觉展示无关，且需独立的可访问性验收。
