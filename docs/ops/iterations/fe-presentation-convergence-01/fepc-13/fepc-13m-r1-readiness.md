# FEPC-13M-R1：采用范围与动作守卫准入

结论：**A 未通过；B 已通过；C 不实施；D 新标题行为未执行。** 本PR只修复P4验证工具，提交采用范围核查证据，不修改任何产品呈现。I1a及新契约路线继续暂停，不提出恢复它们的自动建议。

## 身份与范围

起点与实时GitHub main：`e0ce73b47b800da181a224913937720d9c5d77ba`。分支 `audit/fepc-13m-minimal-title`。启动R1时继承本专题尚未提交的FEPC-13M方案、I1a暂停记录及任务元数据；这些是本次PR明确纳入的文件，不是产品代码残留。FEPC-13I-00记录的16项源文件指纹仍匹配。

归属P4 `scripts/verify`：过期静态断言修复；P0组件和权限行为不变。无需改正式schema、后端、配置或数据库。仅本地测试，无Demo认证或请求。复用[FEPC-13M方案](fepc-13m-minimal-rendering-plan.md)及[有效标题历史声明](effective-title-declarations.json)，不把历史节点路径或坐标当当前选择规则。

## A：真实调用链与不可跨越的选择缺口

`ContractFormPage.vue` 构造 `canonicalFormRenderState` 和页头身份，原生路径经 `CanonicalNativeFormSurface.vue` 将 `nativeBridge.primaryNodes/subordinateNodes` 传给 `NativeFormTreeRenderer.vue`。另有 `ContractFormNativeCanvas.vue` 调用相同renderer，因此修改公共默认行为会波及其他路径。

`canonicalFormRenderState.ts` 调用现有presenter生成最终字段只读状态。`canonicalNativeFormBridge.ts` 对当前节点/字段建立WeakMap，传递canonicalNodeId、canonicalWidgetId；它能精确回答“正在渲染哪个实例”。`NativeFormTreeRenderer.vue:149–173`把收藏、输入、只读h2拆为兄弟节点；文本叶子可以单独交给插槽，收藏与输入不需要移动。

**缺少的是选择依据，不是定位工具。**

- `pageIdentityAdapters.ts:primaryRecordName`根据当前页面数据生成展示字符串；`buildContractFormPageIdentity`没有返回被选中的原生nodeId/widgetId。
- `ContractFormPage.vue:pageDisplayTitle`组合canonical shell title与pageIdentity，未声明对应原生occurrence。
- `CanonicalNativeFormSurface.vue`当前没有“页头实际可见且身份就绪 + 目标标题实例”的采用参数。
- `titleFieldForNode`返回该原生标题的字段，不证明它是冗余副本；`primary_fields/title_field`也没有occurrence归属。
- 当前树内node对象/ID可以唯一定位，但不能据此决定“应省略谁”。取第一个h1/唯一h1、字段名name、字符串相等、模型/项目ID、历史locator/坐标均不满足用户给定条件。
- 即便当前样本只有一个h1，也不能由此排除其他表单的独立标题、复合标题、额外语义或同字段多个occurrence。这是未证明的范围，不声称所有无新契约方案都不可能。

插槽职责可以明确而不实施：只读h2处提供默认内容，slot传当前node及其field；逐个递归调用仅在调用方提供slot时转发，否则保持默认h2；采用面只能在唯一目标、查看态、页头实际可见且身份就绪时替换叶子。编辑/创建/预览及其他表单走默认内容。具体调用方尚不能给出满足条件的目标选择，故按阶段A第6条和阶段C门禁停止，**没有添加空置插槽，也没有建立第二套配置**。

下一步需要产品重新限定可被验证的采用规则/验收范围，而不是让执行器自行选择启发式。本PR不强迫选择新协议，不以“先加插槽以后补依据”绕过门禁。

## B：过期守卫与修复

原入口 `make verify.frontend.native_form_action_presentation.unit`：13 tests，1 failure。守卫假设ScButton总数为3；当前模板实际有两条普通动作分支、一个容器展开按钮和一个既有显式anchor。

合法性证据：

- `NativeFormTreeRenderer.vue:20`的anchor仅调用 `navigateExplicit(node, $event)`；`:587`在当前 `[data-native-contract-structure]` 根下调用 `navigateToDeclaredNode`，不调业务动作或写API。
- `nodeComponentPresentation.ts:86`验证注册能力、targetContainerId唯一性、原生节点身份、目标可见性、支持的目标类型和非空文字；拒绝href/onclick/target和额外子节点。
- `isNodeRenderable`继续要求nodeComponent.visible及isNodeVisible；`navigateToDeclaredNode:160`激活时再次检查唯一、可见、非hidden/inert，并且只scrollIntoView/focus。不新增权限计算。
- 原失败涉及的模板、工具及输入文件逐字节等于上述main；分类为validation_tool_defect，不是本轮产品回归。

修复不是把总数3改成4。按职责精确分类：2条普通动作、1个容器展开、1个声明anchor；拒绝未分类/交叉分类按钮。anchor要求完整精确属性集合和既有click处理器；拒绝额外事件、动态事件、v-bind注入、inline handler、submit、错误节点身份及重复属性。普通动作disabled/事件和展开按钮原保护仍保留。没有改组件、按钮事件、权限或处理函数。

## 实际测试（非零）

| 层 | 命令/证据 | 状态与覆盖 |
| --- | --- | --- |
| L0 | HEAD/main + 源文件字节对照 | passed；产品文件未修改 |
| L1/L2 red | 同一native动作入口，先增加回归再修守卫 | failed：15 tests，13 failure/subtest报告；证明旧规则拒绝合法基线、且不能验证新增anchor约束 |
| L1/L2 green | `make verify.frontend.native_form_action_presentation.unit` | passed：15 tests；其中新增anchor测试含11个定向变异；守卫自身也PASS |
| L2 | `make verify.frontend.node_component.unit` | passed：36 cases；包括有效目标、缺失/重复/隐藏目标及激活复核；不是浏览器验收 |
| L2复用 | `make verify.frontend.canonical_form_presenter.unit` | passed：前轮主组177 cases及其他命名组；复用相同main产品/测试输入，本轮仅修改独立Python守卫与测试，不影响该入口输入 |
| L2复用 | `make verify.frontend.standard_form_composition.unit` | passed：123 cases；同上，未重复运行不变输入 |
| D标题行为 | 查看/编辑/创建/收藏/可访问性/页头切换 | not_run：无候选实现，不能用上述通过代替新UI效果证明 |

日志保留于本地 `.runtime/fepc13m/`：`native-action.log`为原失败，`r1-red.log`为新增测试红灯，`r1-green.log`和`r1-node-component.log`为修复结果；presenter.log和composition.log保留原始通过。当前候选Quick和远端CI结果放PR正文，避免为追加门禁记录改变候选。

## 交付边界与回滚

可独立验收的结果是守卫修复与范围核查，而非标题修复。撤销两项Python文件差异即可撤销守卫修复；不会影响运行时。附带FEPC-13M原方案及I1a暂停记录，保留时间顺序，旧失败由本R1关闭，不抹去记录。

无新协议、新schema、新标题字段、新插槽或CSS；无业务写入、部署、自动合并。09-04仍未解决，F1待核实且暂不修复。等待独立审查，本PR通过也不代表标题省略已经获得实施准入。
