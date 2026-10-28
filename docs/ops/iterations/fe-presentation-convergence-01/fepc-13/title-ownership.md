# FEPC-13 项目详情标题职责决策稿

状态：阶段 A 源码追踪完成；阶段 B 待裁定；阶段 C/D 未实施、未执行产品回归。09-04 保持未解决。本 PR 只交付决策稿，不声称已修复重复标题。

基线：GitHub main `b918f2a01fbbea01b7665d8c3448ed820050ffae`；开始时本地 main 同 SHA，工作区干净。核查范围为该基线的通用表单、标题呈现链及 FEPC-09 已存证据，不扩展 F1、关注者、关系空状态、协作消息、数据与配置。

## 结论与停在决策稿的原因

用户指定的产品方向是页头承担主要标题及固定页头职责。源码已能说明两处文本及操作如何产生，但尚不足以证明任一原生 `h1` 是可取消显示的身份副本：它同时是可写名称字段和收藏按钮的呈现位置，通用节点还可能含有额外文本、字段和子节点。

已核查链路中没有找到把“页头记录身份”与某个原生标题 occurrence 绑定、并声明后者为可省略副本的现成策略。`views.form.profile.title_field` 是记录身份取值线索，不等于原生标题去重授权；`hideTitle` 是页头的渲染能力，不是原生标题所有权声明。此结论限定于本次查阅范围，不声称全仓或所有有效契约永不存在此类声明。

因此按任务阶段 B 的停止条件提交决策稿。不删除节点，不按文本相等、字段名 `name` 或模型名推断可隐藏性，不在本轮修改契约。当前可以确定操作归属，尚不能确定安全取消原生标题显示的适用集合。

## 来源与职责（源码事实）

| 层 | 数据与渲染链 | 已确认的职责及限制 |
| --- | --- | --- |
| 页面身份 | `pageIdentityAdapters.ts` 的 `formPrimaryFields` / `primaryRecordName` / `buildContractFormPageIdentity` | 优先读取 profile.title_field、primary_fields，另有既存 name/display_name 取值逻辑。已有记录用授权快照与表单草稿合并，草稿优先；创建与编辑的 identity kind 不同。记录显示文本不是原生节点身份。 |
| 页头输入 | `ContractFormPage.vue:1445` 起，pageIdentity → canonicalShellTitle/pageDisplayTitle/pageDisplaySubtitle | canonical shell.title 来自 presenter 的 structure.navigation.title 或 pageInfo.pageName；页头身份也可能来自 record subtitle，不能只比较 pageDisplayTitle。 |
| 页头实际文本 | `ContractFormProductHeader.vue:174`，identityTitle = trimmed subtitle 或 title；identitySubtitle 为空 | `PageHeaderTemplate` → `ProductPageHeader` 输出 h1；真正显示值须沿此最后一步核对。 |
| 固定页头 | `ProductPageHeader.vue` 的 header、identity/status/actions 插槽及 sticky CSS | h1 属于页头；sticky 与容器、top/z-index 样式属于公共页头。源码声明不代替真实滚动验证。 |
| 原生标题 | `ContractFormNativeCanvas.vue` → `NativeFormTreeRenderer.vue:149` | h1 节点含字段时，取 fieldSchemasForNodes(fieldChildren(node))[0]；只读输出 h2，可写输出 ScInput。仍递归渲染非字段子节点。不能把整个标题区视为纯文案。 |
| 名称与收藏字段 | `canonicalNativeFormBridge.ts:77` 起及兼容链 `nativeLayoutUtils.ts:759` 起 | favorite schema 合并到内容字段的 favoriteToggle，保留 readonly、descriptor、active。原生标题按钮发 field-change，名称输入也发 field-change。本轮不改变这些既存规则。 |
| 顶部操作与返回 | `ContractFormPage.vue:31` 起 → ContractFormProductHeader | direct/overflow/canonical actions、保存、放弃、返回由现有页级 action runtime 负责；返回调用 returnToPreviousPage。不是原生 h1 的孩子。标题行输入编辑与页级编辑/保存入口是不同能力。 |

### 查看与编辑的差别

- 查看/编辑/创建共用页头和原生画布链；原生标题实际显示 input 还是 h2 由最终字段 schema.readonly 决定，不能只由路由名推断。
- 顶部操作受 renderProfile、配置预览、canonical renderer、权限/动作声明影响。`useRecordActionPresentation.ts` 与 `contractFormHeaderCanonicalActions.ts` 是动作投影的一部分，`usePrimaryFormActionRuntime.ts` 负责主操作执行，不能用删标题替代动作调整。
- FEPC-09 保存的 name occurrence 定义为 required、非 readonly，并不意味着历史只读页面可写；当时实际 effectiveRenderProfile=readonly。字段定义、最终模式和 DOM 必须分开验证。

## 已有机制为何不能直接作为本次修复

| 机制 | 已有能力 | 本次不能直接推出的结论 |
| --- | --- | --- |
| 页头 hideTitle | 保留语义 h1、视觉隐藏标题及副标题；状态/操作插槽保留 | 当前 suppressPageHeaderTitle 固定 false。直接打开会把视觉主要身份交给原生区，与本轮默认方向相反，也未证明滚动后名称可见。 |
| 原生 h1 → h2/input | 保留名称编辑、收藏及子节点 | 不携带“只是页头副本”的关联或模式策略；不能一律隐藏 h1。 |
| presenter 的 ancestorTitle 去重 | 针对容器标题和祖先标题的文本投影 | 不负责 shell 身份与原生可编辑字段/收藏的跨区域协调。 |
| canonicalFormFloorplan 的 suppressRepeatedTitles | 针对其节点集合的 title 属性去重 | 不等于原生 field.value、收藏操作及页面 h1 的去重授权，不能将该函数扩大到整块原生标题。 |
| title_field / primary_fields | 帮助解析记录身份 | 未声明同一字段的不同 occurrence 均可隐藏，未保证标题仅含该字段、无复合信息。 |

## 最小方案与待裁定点（设计建议，不是已批准契约）

推荐维持页头主要身份及全部操作的现有归属。只有能以权威声明确认某个原生 occurrence 为纯身份副本时，才评估其只读文本的次级呈现或视觉省略；名称编辑输入、收藏与额外语义子节点继续由原生字段层负责。不得把此建议变成前端字符串相等规则。

实施准入需补齐以下决定：

1. 标题呈现负责人确认：只读重复名称是降级为带字段标签的次级事实，还是仅省略重复文本；不能由执行器自行选定新视觉语义。
2. 声明负责人确认：现有有效契约是否已经明确标识该身份 occurrence 与页头的关系。如有，提供实际来源/版本并复用；如无，另行批准最小声明设计，不能在本轮越界新增配置。
3. 明确编辑态：保留完整名称输入，页头名称是否随未保存草稿更新沿用现有行为；不迁移保存、收藏或返回动作。
4. 明确额外语义与通用范围：含静态说明、多字段、不同身份字段、额外子节点、隐藏字段及嵌套标题的节点必须保留；不能把项目样本外推到所有表单。

仅缩小所有原生 h2 字号虽不删除 DOM，也会影响具有独立语义的其他标题，且重复名称依然存在；不将这种全局样式修改冒充已确认的最小修复。

## 后续回归矩阵（尚未执行）

| 场景 | 必须证明 |
| --- | --- |
| 项目查看态、长名称/窄屏 | 一个主要视觉标题层次，名称完整可读，语义 h1 存在，省略对象有声明依据 |
| 项目编辑态及创建态 | 名称输入、校验、草稿显示不变；保存/取消和离开保护不改变 |
| 收藏与顶部编辑入口 | readonly/可写两种收藏状态、原事件载荷和权限保留；编辑入口执行原动作 |
| 滚动与固定页头 | 页面/内容容器滚动后的页头、主要名称和动作可达，不能只断言 position:sticky 字符串 |
| 复合原生标题 | 静态说明、附加字段/子节点不误删，不能只测 name-only 样例 |
| 其他通用表单 | 独立标题、无原生标题、字段值相同但语义不同、配置预览场景无误隐藏 |

复用现有 native renderer/canonical bridge/page identity/header 测试与标准页面浏览器入口，具体用例在方案批准后加入；不建立第二条浏览器车道。本轮无产品实现，以上均为 not_run，不声称回归通过。

## 当前交付边界

仅文档与任务索引变更。L1/Quick/CI 是文档集成检查，不证明标题修复、收藏操作或目标 Demo 全页验收。历史坐标不作为当前运行事实。本轮不调用业务 API、不点击收藏/保存、不修改运行时、不部署、不合并。F1 仍待核实、暂不修复。
