# Editor 前端专题技术设计

> 本文受根目录 [`README.md`](../../README.md) 总体集成计划约束，仅描述候选能力，不代表已进入产品主线。

> 执行状态：`ADR-PENDING`。编辑器正文是运行时记录内容，不得嵌入 capability 定义；具体编辑器技术、canonical format 和净化库均未决定。

## 1. 定位

Editor 是 P0 通用受限富文本渲染与编辑机制。具体业务字段是否可编辑、内容用途、附件权限和保存动作由正式契约及对应业务产品层决定。共享前端不得按模型名或页面名称启用编辑器。

## 2. 首期范围

- 段落、标题、有序/无序列表、粗体、斜体、链接、受控表格。
- 只读、编辑、dirty、saving、success、validation error、conflict 状态。
- 粘贴纯化、撤销重做、中文输入法、键盘导航和移动端基本编辑。
- 附件只通过正式上传 intent，编辑器正文仅保存受控引用。

首期不包含任意 HTML、脚本、内联样式、iframe、外部媒体嵌入和插件市场。

## 3. 契约

```json
{
  "capability": "content.rich_text",
  "schema_version": "1.0",
  "format": "restricted_html",
  "content_ref": "authorized-runtime-record-ref",
  "readonly": false,
  "max_length": 20000,
  "allowed_features": ["paragraph", "heading", "list", "strong", "em", "link"],
  "sanitization_policy": "sc_restricted_html_v1",
  "attachment_policy": null,
  "version": "etag-or-record-version",
  "actions": {
    "save": {"intent": "content.rich_text.save", "enabled": true}
  }
}
```

缺少策略、版本或保存动作时，组件必须降级为只读。

## 4. 安全模型

- 服务端净化是权威边界，前端净化只用于即时反馈。
- 标签、属性、URL scheme 使用固定 allowlist。
- 禁止 `script`、事件属性、`javascript:`、`data:text/html`、任意 iframe 和未授权外链资源。
- 保存携带版本；冲突时不得静默覆盖。
- 粘贴内容先转为 canonical format，再进入编辑状态。
- 附件访问继续受记录规则、公司范围和临时 URL 有效期约束。

## 5. 前端分层

| 层 | 职责 |
| --- | --- |
| Schema | 严格解析 capability、format、features、actions |
| Runtime | dirty、保存、取消、冲突、重试、附件任务 |
| Assembler | 转换为编辑器 view model，不推断业务用途 |
| Renderer | 工具栏、内容区、状态提示、键盘和无障碍 |

候选 `src` 代码迁入主仓库前必须拆除独立 API 假设，并适配现有 SDK、Token 和 ScIcon。

## 6. 验收

- XSS 与 URL scheme 正反例。
- 服务端净化前后等价性。
- 中文输入法、粘贴、撤销、选择区和焦点恢复。
- 390×844 至 1440×900 响应式。
- 只读权限、保存失败、网络重试和版本冲突。
- 大内容长度限制与性能预算。

## 7. 实施顺序

1. ADR：restricted HTML 与结构化 JSON 二选一。
2. Schema 与服务端净化策略。
3. 只读 renderer。
4. 本地编辑状态与无障碍。
5. 正式保存 intent、版本冲突和附件。
6. 浏览器安全与五视口验收。
