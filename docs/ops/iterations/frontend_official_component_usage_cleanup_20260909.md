# 前端官方组件用法全量收口（2026-09-09）

## 目标与边界

- Formal Product Layer：P0 平台通用组件适配与主题桥；P4 仅负责清单、守卫和证据。
- Layer Target：`frontend/apps/web/src/components/design-system`、`frontend/packages/ui/src/kits/tdesign/theme.css`、`@sc/design-tokens` 与 official design alignment inventory。
- Standard vs User-Specific：TDesign 1.20.5 的公开 API、公开插槽和公开样式扩展点属于平台通用规则，不承载施工行业或客户差异。
- Why Here：组件适配器负责把产品语义投影到官方驱动；主题桥只能消费官方公开 token 或项目自有语义节点。
- Why Not Elsewhere：不在业务页面继续依赖 TDesign 内部 DOM，不修改 P1/P2/P3 业务规则或运行时配置，也不以 P4 脚本承载产品表现。
- Blast Radius：Input、Select、Card、Alert、Button 的通用呈现，以及使用其既有 appearance 的页面；不触碰后端、契约、路由、权限、数据库、fixture 或业务动作。

## Batch A：公开扩展点与样式清单归零

### 本批目标

将权威清单中 14 个 internal vendor selector gaps 与 16 个 visual literal gaps 全部清零，并让 `--check` 对完成条件 fail-closed。

### 不做清单

- 不升级或替换锁定的 `tdesign-vue-next@1.20.5`。
- 不修改业务字段、菜单、表单、接口或状态语义。
- 不创建 Compose project、数据库、端口、卷、凭据或 fixture。
- 不执行业务写入、发布、push、PR 或 merge。

### 执行步骤

1. 以已安装 1.20.5 的 `type.d.ts` 和实现为证据，迁移到 `inputClass`、`inputProps`、`bodyClassName`、default/operation slot 等公开接口。
2. 让 Button 只依赖适配器自有 `.sc-btn__content`，不选择 `.t-button__text`。
3. 将视觉字面量映射到现有 token；确需新增的稳定尺寸写入 component token 单一事实源并重新生成产物。
4. 刷新 official design alignment inventory，并让 `--check` 同时验证快照一致性和四项完成条件。
5. 运行非零定向测试、primitive adapter、rendering detail、token guard、严格类型检查和 `git diff --check`。

### 验收标准

- `unknownProjectTokenOverrideCount=0`。
- `internalVendorSelectorGapCount=0`。
- `visualLiteralGapCount=0`。
- `orphanedProductAppearanceVariantCount=0`。
- 定向单测非零且全部通过；严格类型检查通过。
- 冻结候选上的受管只读页面旅程无浏览器错误、无业务 mutation。

### 回滚与停止条件

- 回滚单位：本批独立提交；token 源与生成物必须一起回滚。
- 若公开 API 在锁定版本中不存在、清单无法归零、类型检查失败或真实页面几何/交互退化，停止后续浏览器验收，只修复 P0 所有层并重新冻结。
- 若需要数据库、fixture、契约或业务语义变化，按 P1/P4 新任务另行授权，不在本批绕行。

## Batch B：全量公开 API 使用守卫

### 本批目标

对所有 `TDesign*` 正式消费者建立锁定版本公开入口、公开属性/事件/插槽的机器核验，消除靠人工记忆判断“官方用法”的缺口。

### 验收标准

- 正式源码没有私有 `lib/cjs/src` 导入或未登记的 TDesign 直连消费者。
- 组件适配器的关键受控值、事件与插槽和已安装 1.20.5 类型声明一致。
- 现有 strict typecheck、primitive adapter guard 与新增官方 API 守卫均通过且测试数非零。

### 回滚与停止条件

- 每个不兼容组件按拥有层独立修复；不得通过 `any`、`unknown` 强转或放宽类型来通过守卫。
- 若发现需要改变产品交互语义，停止并拆出独立 PFL 批次。
