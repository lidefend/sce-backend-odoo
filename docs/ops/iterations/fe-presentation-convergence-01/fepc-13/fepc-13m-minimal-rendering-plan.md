# FEPC-13M：最小标题呈现可行性与候选差异

状态：方案核查完成，产品未修改，候选行为未验收。后续R1已修复本文记录的基线守卫失败，详见 [R1准入结果](fepc-13m-r1-readiness.md)；下方测试与停止结论保留为本轮历史记录。I1a 按所有者最新指令暂停；不因本方案重新启动 C，不新增协议或 schema。

## 基线与边界

GitHub main 与本地起点均为 `e0ce73b47b800da181a224913937720d9c5d77ba`，开始核查时产品文件干净。当前专题分支 `audit/fepc-13m-minimal-title`。仅修改任务记录及本文档，保留 I1a 暂停记录；无产品回退成本。

P4 方案记录，分析对象是 P0 通用前端呈现。未重新登录 Demo、截图或采集 API。FEPC-13R 的两个标题与收藏同区是历史运行时证据，不声称本轮重新验证部署身份。F1 暂停，09-04 未解决。

## 结论：局部文本处理可行，现成的定向省略开关不存在

无需建立新的身份协议才能区分文本、输入与收藏。当前模板已经把它们拆成兄弟节点。修改只读文本叶子不要求删除字段、移走收藏或改变 presenter 权限计算。

但“有独立文本叶子”不等于“已有安全开关”。A 若限定为零扩展复用现有 props/slots，目前不能证明满足全部五项验收。最小扩展是文本叶子的局部呈现入口，成本远小于 C；它仍需要明确页面采用范围，不能以全局隐藏、字段名或字符串相等代替范围决策。尚无多个同类业务场景的证明，因此不把 B 的通用启用作为已经批准的结论。

## 源码事实

行号绑定上述基线。

| 位置 | 已证明的事实 | 影响 |
| --- | --- | --- |
| `frontend/apps/web/src/components/template/NativeFormTreeRenderer.vue:149` | 原生 h1 有专门分支；收藏按钮、ScInput、只读 h2 分别呈现 | 可仅处理 h2，不删除 native-title-row/h1 |
| 同文件 `:164`、`:172` | 输入与文本以最终字段 readonly 互斥 | 不需重新计算字段权限；但编辑/创建中也可能有只读字段，不能单靠 readonly 全局隐藏 |
| 同文件 `:800` | titleFieldForNode 从 fieldSchemasForNodes(fieldChildren(node)) 取首项 | 它代表当前标题字段，并不证明是页头身份副本 |
| 同文件 `:820` | 收藏使用自身 readonly、name、descriptor，原事件为 field-change | 叶子调整不得改变按钮或此函数 |
| `frontend/apps/web/src/pages/contractForm/canonicalNativeFormBridge.ts:74` | resolveCanonicalNativeFieldSchemas 把收藏信息附着到文本字段 favoriteToggle | 保留映射；不删除名称 schema，否则收藏可能随之丢失 |
| 同文件 `fieldNode` / `fieldSchemasForNodes` | canonicalWidgetId、canonicalNodeId 和 WeakMap 提供实例对应关系 | 可给局部呈现入口传递准确 node/field，不按字段名批量筛选 |
| `frontend/apps/web/src/app/presentation/contractFormPresenter.ts:349` | readonly 已合成页面模式、字段授权、祖先/容器和状态 | 直接消费最终结果，不新建权限公式 |
| `frontend/apps/web/src/pages/contractForm/canonicalFormRenderState.ts` | 调 presenter 并返回 model/error，保留 validation 归属 | 本问题无需修改该文件 |
| `frontend/apps/web/src/pages/contractForm/CanonicalNativeFormSurface.vue:9`、`:24` | primary/subordinate 共用 NativeFormTreeRenderer；传 preferReadonlyFacts | 此 prop 改变事实展示，不是标题省略开关 |
| `frontend/apps/web/src/pages/ContractFormPage.vue:1466` | 页头使用 canonicalShellTitle 或 pageIdentity；当前不隐藏页头 | 页头实际可见及身份是否就绪仍是采用条件，不用 hideTitle 修复 |

当前 `#readonly` 插槽传给普通 FormSection，但标题 h2 分支未调用该插槽。通过 bridge.nodeVisible 隐藏节点会改变整个字段/容器可见性，范围过大。标题行只有 data-field-name，按它做 CSS 选择不是稳定的 occurrence 级策略。FEPC-13R 中标题容器 class 为通用 `d-flex flex-row`，不是可安全采用的项目身份标记。

## 三种方案的成本与适用条件

| 方案 | 最小改动 | 本轮判断 |
| --- | --- | --- |
| A0：已有 readonly 插槽或 preferReadonlyFacts | 调用方配置 | 不覆盖专用标题分支，无法直接做到 |
| A1：页面 scoped CSS 隐藏 .native-title-text | 一处样式 | 虽不碰收藏/输入，但 ContractFormPage 是跨模型共享页面；不能证明其他表单不受影响。编辑/创建里的只读字段也可能命中。暂不推荐 |
| B：专用只读标题叶子插槽，默认保持原 h2 | renderer + 递归转发 + 采用面的接线 + 定向测试 | 最小可行技术扩展，不需要新 wire 字段。只作为候选；采用范围、多场景需求仍未确认 |
| C：新身份投影协议 | 跨 schema/编译/交付/客户端 | 暂停，不作为 A 尚未闭合时的自动 fallback |

建议保留 A 的“仅页面呈现”目标，若需要扩展，范围止于 B 的一个文本叶子入口，先明确采用面，再另行授权实现。不修改 bridge 的收藏附着逻辑，不修改 renderState 或 presenter 的最终 readonly 计算。

## 最小候选代码形状（未应用）

只对原 h2 分支加默认插槽；名字是候选组件 API，不是新增契约字段：

```vue
<slot v-else name="readonly-title-text" :node="node" :field="titleFieldForNode(node)">
  <h2 class="native-title-text">{{ titleFieldValue(titleFieldForNode(node)) || titleFieldForNode(node)?.label }}</h2>
</slot>
```

完整差异不能只算上述几行：还需要给每个递归 NativeFormTreeRenderer 调用按已有方式转发该插槽，且只在调用方确实提供时转发，保证默认内容仍然存在。采用面的容器也须转发。收藏 ScIconButton、ScInput、fieldSchemasForNodes、emitTitleFavoriteToggle 均不改变。

页面层采用条件必须同时满足：查看态、最终字段只读、主要页头实际存在并就绪、明确选中的当前标题实例、没有未保留的辅助技术依赖。编辑、创建、预览、独立标题、复合标题、其他未采用表单保留默认 h2。不能用固定项目 ID/模型名、历史 locator/坐标、字符串相等或同名字段全局搜索补齐缺失条件。

**未解决项是采用范围，不是协议版本**：当前没有已证明的现成页面声明/采用规则，能唯一选中此次冗余文本且排除独立原生标题。后续需要对“哪一类页面/标题采用该视觉策略”作小范围产品决定。尚不能把该模板片段作为可直接上线补丁。若产品接受仅降低重复标题视觉级别而非完全省略，则应另行评估更小的局部排版方案，不能把这两个目标偷偷互换。

可访问性：省略仅针对视觉文本。若仍有 aria-labelledby/aria-describedby 依赖，保留对应 ID/文本；不对父节点 aria-hidden/display:none。收藏的名称、pressed、disabled、焦点顺序及事件保持。页头隐藏、身份加载或路由切换时回到默认可见文本，避免两个标题都消失。

## 实际执行与证据限制

执行对象为未改动的 main 产品代码。本轮没有候选渲染实现，因此以下结果只证明基线，不证明去重效果。

| 命令 | 结果 | 真实覆盖与限制 |
| --- | --- | --- |
| `make verify.frontend.canonical_form_presenter.unit` | passed | 日志主组报告 177 cases，另有命名分组；不把它们随意累加。包括 readonly/edit、创建默认关系绑定、字段状态与名称/收藏 bridge 投影。不是标题 DOM 或键盘验收 |
| `make verify.frontend.standard_form_composition.unit` | passed | 123 cases；显式采用范围、表单组合及既有调用方，不是新标题策略验收 |
| `make verify.frontend.native_form_action_presentation.unit` | failed | 13 tests，1 failure；静态守卫仍要求总计3个 ScButton，现有模板还有 nodeComponent anchor 按钮。其余12项通过，但整个入口失败；后续 guard 命令未执行 |
| 新方案的只读/编辑/创建/普通表单 DOM、键盘、滚动/固定页头 | not_run | 无候选实现，不伪称端到端通过 |

本地原始日志：`.runtime/fepc13m/presenter.log`、`composition.log`、`native-action.log`。日志不随产品交付。

失败分类：已证明是基线存在的守卫/模板不一致；工具断言陈旧是源码支持的解释，不把它升级成动作运行时缺陷。失败测试及4项输入文件、守卫文件均与基线逐字节相同。未重试同一失败、未放宽守卫、未修产品。该项需独立处理后才能声称全套原生动作回归通过。遵循仓库先关闭已知交付阻断的规则，本轮不跑 Quick、不发布新的实现候选。

## 未来最小回归（本轮 not_run）

在现有 presenter / native-action / 标准表单及既有浏览器验收入口扩充，不建新车道：

1. 目标查看态：一个主要视觉身份标题，原名称数据不变；收藏节点及可访问名称保留。
2. 编辑与创建：输入、校验、保存/取消入口保持；即使某个字段只读也不触发查看态策略。
3. 未采用的普通表单、独立/复合标题、相同字段多个 occurrence：DOM 与基线一致。
4. 收藏权限分别允许/拒绝：disabled、descriptor、事件参数和焦点不变。
5. 嵌套容器：插槽只作用于明确选中叶子，默认 slot 不被空转发吞掉，其他子节点保留。
6. 页头不可见/身份未就绪/切换路由：不省略原生文本；验证辅助技术引用和固定页头。

## 当前交接

本轮提交的是可审查的局部方案，不是产品修复。I1a 保持暂停，无 schema/编译器变更；C 不自动恢复。最小技术改动位置已确定，但安全采用范围与基线守卫失败尚未闭合。下一步由产品复核是否接受该局部入口及其适用范围，再授权小批次实现；不部署、不合并。
