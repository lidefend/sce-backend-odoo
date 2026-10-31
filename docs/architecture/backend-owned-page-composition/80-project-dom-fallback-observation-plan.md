# 80 · Project DOM Fallback Observation Plan（PC-007）

## 结论

DOM 级运行时观察能力：READY_WITH_CONSTRAINTS

## 现有能力

- `scripts/verify/playwright_runtime.mjs`：`launchChromium`，可从缓存或
  `PLAYWRIGHT_WS_ENDPOINT` 复用浏览器。
- `scripts/verify/frontend_project_detail_summary_browser.mjs`：已有项目详情
  浏览器观察脚本。
- 候选前端在 `http://127.0.0.1:5178` 在线。

## 可观察的 DOM 事实

`ContractFormPage.vue` 已在根节点输出结构来源属性：

```text
data-form-composition
data-form-composition-reason
data-detail-composition / data-detail-composition-adopted
data-v2-shadow-layout-source / data-v2-shadow-global-source
data-v2-shadow-field-overlap / data-v2-shadow-source-context
```

这些属性可直接区分最终 DOM 的布局来源（legacy-form-section 与
official-standard-detail），无需猜测。

## Vue computed 惰性求值要点

- `useRecordFormFieldSchemas.ts:106` 的 `layoutNodes` 是 `computed`，只有被
  消费者访问才求值；消费点在 `ContractFormPage.vue:820/1415/1427/1727/1873/1888`。
- `ContractFormPage.vue:2084`：`formStructureContract.structureAuthority ===
  'container_tree'` 选择 native 快照，否则为空。
- 判定必须区分三阶段：函数被调用 / 结果被消费 / 节点进入最终 DOM。

## 观察计划（4H-02B）

1. 用 Playwright 分别打开 590/1776 与 652/944。
2. 读取根节点 `data-form-composition` 等结构来源属性。
3. 统计 `NativeFormTreeRenderer` 节点数与 legacy FormSection 字段节点数。
4. 记录两个入口是否一致，是否出现 legacy 字段进入最终 DOM。

本轮只做计划，不执行；执行属于 4H-02B。
