# FEPC-11：关系空状态标题职责收敛

状态：独立产品修复候选，待 GPT 复审；不合并、不部署。

基线：GitHub main `192d4e15a8a2413ba38d52d22f2b761e0d5a570f`，建分支前工作区干净。P0 通用契约渲染；P4 组件验证复用现有 Make 入口。结果索引为 `.agent/runs/FEPC-11/run.json`。

## 声明与来源

[运行时字段投影](declaration-evidence.json)来自账号 wutao 对项目 15 的一次只读 `ui.contract.v2` 请求，HTTP 200、应用成功。只保留三处标签/隐藏声明及祖先标题，不保存认证上下文或业务值。服务仍声明源码 `3f46dd7eba9f351386fee446151ee9eb545d56a4`；这与本轮 Git 基线分别记录，不代表 Demo 已部署修复。

| 字段 | 权威标签 | nolabel | 外层标题职责 |
| --- | --- | --- | --- |
| task_ids | 任务 | false | 关系控件拥有字段标题 |
| collaborator_ids | 合作者 | false | 关系控件拥有字段标题 |
| responsibility_ids | 责任矩阵 | true | 声明的外层 group 已显示“责任矩阵” |

源码对应 `addons/smart_construction_core/views/core/project_views.xml` 的责任矩阵 group、`sc_system` 页面字段。原生布局 `nolabel` 经 `contractFormPresenter.ts` 转为 `hideLabel`，由 `canonicalFormRenderer.ts` 及 `canonicalNativeFormBridge.ts` 传给 `NativeFormTreeRenderer` / `FormSection`，没有在本轮重定义业务名称。

## 根因与最小差异

`FormSection.vue::detailCollectionOwnsVisibleTitle` 在有关系适配器时把明细标题交给关系控件，外层字段 label 因此不显示。`X2ManyRelationRenderer.vue` 的只读标题却被放在 `one2manyRows.length` 分支内部，空与加载状态只剩通用提示；可编辑加载分支同样绕过标题。

本轮只调整 `X2ManyRelationRenderer.vue`：只读标题移到数据分支之前，非空仍只显示一次并保留原计数；可编辑加载状态消费同一字段 label。`hideLabel` 继续决定是否显示字段标题，因此责任矩阵外层已有标题时，不再补一个内层标题。未添加空状态按钮，未修改空状态文案、分页、记录集合、权限或操作。

标题同时脱离仅桌面表格的分支，响应式卡片模式也共用同一标题职责；本轮未做浏览器几何验收。其他 many2many、附件和独立布局投影代码未修改。

## 回归与渲染证据

[组件结果](component-render-evidence.json)提供修复前失败及修复后矩阵。测试先于产品修改：旧实现期望“任务”，实际标题集合为空，断言失败。随后最小修复通过。

- 真实 Vue SSR 渲染现有三个组件；三个字段标签 × 空/加载/非空 × 隐藏/显示 × 只读/可编辑，共 36 个组合；另有 3 个原生外层标题组合。合计 39 场景、147 断言通过。
- 验证字段标题只出现一次、隐藏标题不出现、外层标题只出现一次、记录内容保留、空/加载提示保留、无 Vue 警告；“其他关系明细”证明未按项目字段名称特判。
- `make verify.frontend.professional_detail_collection.unit`：新组件矩阵、既有明细模型、67项结算消费测试、10项契约注册测试、46项明细守卫通过。
- `make verify.frontend.canonical_form_presenter.unit`：177项主测试及既有声明/原生桥接扩展断言通过。
- `make ci.local.iteration`、`make verify.frontend.typecheck.strict` 通过。

测试适配器与记录为合成数据；关闭状态的 `ScDialog` 使用无输出替身，避免 Node SSR 读取浏览器 CSS API，未验证或修改对话框交互。证据证明标题消费与渲染结果，不替代浏览器布局、目标 Demo 或所有角色验收。本轮没有建立独立浏览器车道。

## 边界与回滚

无后端、契约、数据库、Demo 记录或权限变更。F1 继续待核实、暂不修复；不包含关注者、页头、首页指标、日期或客户字段。产品代码仅一个组件，可独立回退本 PR；无数据回滚步骤。精确候选 HEAD 与最终 Quick / 远端检查在 PR 中记录，独立复审尚未完成。
