# FEPC-13D 原生标题身份投影契约设计

状态：设计建议，等待 GPT 审查；所有新名称、版本和 JSON 均为拟议表达，不是当前支持的正式契约。未修改 schema、运行时字段、配置或渲染器；09-04 尚未修复。

## 目标、依据与范围

页头负责页面主要身份和固定页头。仅在权威声明明确授权时，省略指定原生名称 occurrence 的只读视觉文本；保留名称编辑输入、收藏控件、其他字段及附加子节点。不是隐藏字段，不是删除标题容器，不改变数据/权限/动作。

基线 GitHub main `b918f2a01fbbea01b7665d8c3448ed820050ffae`。复用 [FEPC-13R 核验](title-ownership-update.md)、[当前 DOM](runtime-title-observation.json)、[有效声明](effective-title-declarations.json)；当前 Demo 身份仍以这些已审查证据中的 SHA 为准，本轮未重新采集。FEPC-13 技术职责分析见 [PR #763](https://github.com/lidefend/sce-backend-odoo/pull/763)。13R 原始文档本轮从本地保存提交 `6b87e4b1e0153a3c1bb83bd2f3617030f957decf` 按字节复用，随独立设计 PR 携带以供审查，不依赖未合并 PR 的文件。

拟议机制归属 P0 smart_core 的通用契约声明/编译与通用前端消费；具体表单是否启用必须由已有 P1/P2/P3 权威发布来源明确声明，本设计不选择或发布项目配置。设计文档归 P4，不让探针或前端决定业务身份。

## A. 现有能力盘点（源码事实）

| 能力 | 真实载体/消费 | 本题边界 |
| --- | --- | --- |
| 页面标题 | `formStructureContract.navigation.title`、pageInfo.pageName → presenter.shell.title；pageIdentityAdapters 的 profile.title_field/primary_fields/记录取值链；ContractFormProductHeader 的 subtitle 优先 identityTitle | 可确定显示值，但不能把某个原生 occurrence 标成冗余副本；现有 subtitle 优先链必须在将来显式绑定下消除分叉，不能只改原生端 |
| occurrence 定位 | types.ts `ContractV2Widget`：widgetId、ownerContainerId、nativeLocator、occurrenceIndex、sourcePosition；schema.ts decodeWidget 校验 locator/index 成对出现 | 可精确绑定当前响应中的实例，不能按 fieldCode 全局省略；这些标识不是跨所有继承视图永不变化的业务 ID |
| 可见性与只读 | container visible/invisible、widgetStatus、globalStatus.effectiveRenderProfile；presenter 合成 ancestor/page/field readonly | visible=false 会隐藏字段/操作；readonly=false 不是当前页面一定可编辑。均未表达“文本副本可省略，控件仍保留” |
| 字段呈现扩展 | componentConfig、fieldDescriptor 字典及语义组件注册 | 宽松字典不是任意新产品语义的授权，不应把页头身份权威塞入字段控件私有属性 |
| 结构与来源 | formStructureContract.structureVersion=1.0/1.1；sourceAuthority/governance_source；slots/fieldRoles/容器节点 | 支持声明归属，但现有 navigation 严格只接受 title；没有跨页头与原生 occurrence 的身份关系 |
| 既有去重 | presenter 容器 ancestorTitle、floorplan suppressRepeatedTitles | 去重的是容器 title，不是名称字段值和收藏所在区域；不可扩展为字符串相等隐藏 |
| actionContract.identityPolicy | assembler 声明 object=button_type_and_backend_method、window=action_id 等 | 是动作身份政策，不是页面记录身份；不得借用同名 identity 载体 |
| hideTitle | ProductPageHeader 保留语义 h1、隐藏页头视觉标题 | 与页头主要身份目标相反，不采用 |
| 版本/能力 | client.ts 发 accepted_contract_versions 2.0/2.1/2.2 与 clientCapabilities；schema.ts 只收对应外层版本及 structureVersion 1.0/1.1；node_component_capabilities.py 对节点能力逐请求验证 | 说明存在协商输入，不证明任意新属性可自动降级。现有 node 能力校验缺能力会拒绝，不应误称自动移除字段 |

现有正式 JSON Schema 位于 `docs/architecture/unified_page_contract_v2/unified_page_contract_v2.schema.json`，多个结构 additionalProperties=false；前端 schema.ts 的 rejectUnknownKeys 明确报错。`contract_version_compatibility.py` 的通用 check_consumer 允许未知 key，与 Web 严格解码器不是同一保证，不能用通用“additive”结论代替真实旧客户端验证。

## B. 候选比较与唯一推荐

详细比较见 [选项 JSON](title-identity-projection-options.json)。拒绝：hideTitle、容器/字段 invisible、按 fieldCode 或字符串相等隐藏。对比两个可表达的新增方案：

- 每个 widget.componentConfig 中增加隐藏规则：局部容易落地，但必须额外声明页头权威，产生多处副本/合并优先级，控件配置还可能被旧客户端静默忽略。
- **推荐：在现有 formStructureContract.navigation 下增加一个有版本约束的 recordIdentity 关系对象**，集中绑定页头记录身份来源与精确原生 occurrence 引用。不在每个 widget 复制策略，不建第二套标题配置系统。

这是最小的新增语义关系，不是零成本字段改名。它复用既有 navigation、widgetId、来源权威和发布生命周期；代价是正式 schema/decoder/协商/presenter/渲染适配均需后续独立授权。缺少 formStructureContract 的表单保持旧行为，本版本不自动补造结构。

## C. 拟议表达与约束

以下是**片段示例，不是完整合法响应**。示例占位 widgetRef 不对应可发布配置；具体绑定必须由编译后的有效布局解析得出。`navigation.title` 仍是既有导航/页面名称，不静默换成记录值。

```json
{
  "pageInfo": { "contractVersion": "2.3.0" },
  "formStructureContract": {
    "structureVersion": "1.2",
    "navigation": {
      "title": "示例表单",
      "recordIdentity": {
        "source": { "scope": "main_record", "fieldCode": "identity_field" },
        "primarySurface": "page_header",
        "readonlyTextProjections": [
          { "widgetRef": "field.identity_field.occ.example", "policy": "omit_when_primary_visible" }
        ]
      }
    }
  }
}
```

拟议能力标识 `form.record_identity_projection.v1`；结构对象无需再加独立 version，复用 structureVersion 和能力版本，避免三处定义同一策略。外层 2.3 是新 Web 严格解码格式的发布边界，不声称当前服务器已支持该版本。实施前必须证实实际协商输出，不可只改 accepted_contract_versions 文案。

语义：

1. source 只能引用当前授权 mainData 中一个声明可读的非关系文本字段；v1 不支持表达式、字符串拼接、跨记录、raw SQL、fallback 或按模型推断。没有合法非空记录身份时不交付启用关系，不删除任何原生内容。业务值来自授权数据，不在结构契约复制标题文本。
2. primarySurface 固定 page_header；有效声明要求页头承担该记录身份，不能继续让独立 subtitle 或隐式 name fallback 覆盖它。只有这个受声明约束的身份表面才可发出“已可见”就绪状态；不是 DOM 文本相等判断。
3. readonlyTextProjections 精确引用当前布局 widgetId。编译器须验证该 widget 唯一、fieldCode 等于 source.fieldCode、父容器为支持的原生标题结构、该 widget 属于当前记录作用域。不能自动枚举所有同名字段。一个字段其他 occurrence 保持原样。
4. 交付层将“定义中的稳定 locator/occurrence 引用”解析为当前响应 widgetId；布局或继承变动导致找不到/多义必须拒绝发布/响应，不回退到字段名。定义使用现有发布载体与 sourceAuthority 的来源版本，不新增独立配置表。具体载体绑定能力须在实施准入时证明。
5. 只省略该文本叶子的**视觉副本**，不设置字段 invisible、不删除原生 h1 容器、不删除整个 native-title-row、不移除字段 schema/数据、不移动 favorite。不是 DOM 父节点消失规则。空白容器压缩和布局重排不在本次设计授权内。
6. 页头提供完整主身份与可访问 h1。原生收藏保持现有可访问名称、disabled/权限、焦点顺序和 field-change 事件；若具体表单操作依赖原生文本 ID 作 accessible name，则须保留语义文本/关联后才能省略视觉文本。不能让按钮失去可访问名称。

### 唯一激活条件与模式

只有版本/能力已协商、关系声明有效、globalStatus 的最终模式为 readonly、现有 presenter 的最终字段为 readonly、目标 occurrence 可见、页头身份已成功呈现且未被隐藏时，消费 `omit_when_primary_visible`。这是拟议协议的固定机制，不是前端自行制定的新业务判断。

- edit / create 一律不应用本策略：名称输入或原有只读字段表现、收藏及全部子节点保持；即使字段自身 readonly=true 也不由本策略隐藏。
- readonly 时 widgetStatus.readonly=false 并不构成否决：FEPC-13R 已证明页面模式和字段授权不同，复用 presenter 既有最终 readonly 合成，不新增第二套权限公式。
- 页头初始未挂载、loading/error 或临时不可见：不激活省略；原生文本保持。只有页头就绪才切换，同一事务更新身份来源，禁止先隐藏原生再等页头返回。
- 已声明 primarySurface 但配置同时隐藏页头、重复 primarySurface、来源冲突：属于非法声明，编译/解码拒绝，进入现有显式契约错误态；不得默默挑一个权威来源。普通未声明旧表单不因此停机。
- 配置预览仍通过同一能力/版本和引用验证，但不激活视觉省略，以保留字段定位和配置可见性；运行时正常表单才消费该关系。此为拟议 v1 明确规则，不由 CSS 猜测设计器。

## C1. R1：最终呈现状态的唯一权威

新消费逻辑只能读取同一份 `canonicalFormRenderState.model` 中目标 occurrence 的 `CanonicalFormField.renderProfile / readonly / visible`，不得重新读取原始 widgetStatus 计算另一套权限。具体既有链为：

`ContractFormPage.renderProfile` → `resolveEffectiveContractRenderProfile`（消费 globalStatus.effectiveRenderProfile；路由仅是请求意图）→ `resolveCanonicalFormRenderState` → `presentContractV2Form` → `fieldFromWidget` 的 `CanonicalFormField`。

`fieldFromWidget` 已合成页面模式、pageAuth、祖先 disabled/readonly、container/slot readonly、字段 auth 与 widget/selector 状态。这里描述既有事实，不将其复制成新协议中的可独立维护公式。`canonicalFieldToFormSection` 继续以 `field.readonly || field.disabled` 适配控件；这个控件禁用适配不成为文本省略的第二个判定来源。

拟议激活谓词仅消费既有输出：有效关系及协商成立、同一响应/布局绑定有效、持久记录、非配置预览、目标 `renderProfile=readonly` 且 `readonly=true` 且 `visible=true`，以及绑定页头身份就绪可见。任何模式/快照不一致或presenter错误均不得激活；缺少已声明引用走显式契约错误，不自行用路由或widgetStatus兜底。edit/create即使字段readonly或disabled也不激活。

FEPC-13R 中global readonly与widget readonly=false并存时，presenter仍输出readonly=true，这是复用现有呈现合成的结果，不是授予/撤销权限。省略仅消费名称 occurrence 的输出；不写回字段auth/readonly，不修改收藏自己的schema、disabled、授权判断或事件descriptor。

## C2. R1：定义引用、响应引用与失效

| 标识 | 唯一职责 | 不允许用途 |
| --- | --- | --- |
| 定义引用 | 既有治理载体中的目标view身份 + 绑定的有效布局版本/摘要 + nativeLocator + occurrenceIndex；附带预期fieldCode和原生标题节点类型作完整性校验 | 不把locator称为跨版本永不变化ID，不只保存name |
| nativeLocator | 在该版本最终继承布局中定位结构路径 | 不以路径最近、末尾相似或同名字段替代缺失路径 |
| occurrenceIndex | 与locator共同区分已声明的字段出现位置 | 不作为当前DOM索引或全模型序号 |
| widgetId / wire widgetRef | 编译器在当前响应唯一解析出的实例引用 | 不写入长期业务配置，不跨layout快照复用 |
| sourcePosition | 源顺序/诊断证据 | 不参与猜测迁移，不作为稳定引用主键 |

上述定义引用是拟议编译约束，复用已有定义版本/view/来源身份，不在本轮新增字段。稳定性承诺只在绑定的有效布局版本内成立：现有widgetId可由locator/occurrence派生，不能据此推断跨视图版本语义稳定。

解析次序：先核对主记录作用域、授权来源及完整有效布局身份；再以定义tuple查最终树，要求恰好一个字段occurrence；核对预期fieldCode、标题节点类型与所属记录；最后使用该节点的真实widgetId生成wire引用。fieldCode只作完整性断言，不能用于枚举候选或恢复绑定。定义中重复规则或多个规则冲突也拒绝。

零匹配、多匹配、继承视图更换、节点移动、布局摘要变化：旧绑定失效，不启用省略。编译器返回明确诊断并阻断该非法启用关系的发布/响应；不会以缺省方式接受损坏定义。即使新路径上碰巧出现同名字段，也不自动重新绑定。只有权威定义负责人核对新布局并重新批准绑定后才能交付新关系。未声明关系的旧契约则仍正常运行，二者不可混淆。

缓存分两层：允许复用未含客户端交付差异的声明中间结果；最终响应的key/依赖必须覆盖定义版本、目标view及有效布局摘要、record作用域、角色/公司、最终profile、协商版本与能力集合。只要任一绑定输入变化，旧关系不得命中。单个响应中的树、关系和身份来源必须原子产生。

增量更新：只有既有patch载体能证明base快照身份且布局/定义/模式不变时，才允许同一绑定下的数据更新；涉及布局、定义、view、能力、mode或身份来源改变必须使关系失效并完整重载。若现有patch不能证明这些条件，v1禁止携带该关系的增量路径，改用全量契约刷新；不能把新widgetId拼到旧树。刷新期间不执行旧省略策略，保持文本可见或既有加载态；错误态不再操作旧DOM。

## C3. R1：视觉省略与可访问语义

以下为协议强制验收条件，不是“建议改善”：

- 页头必须保留可访问的主要身份h1和完整授权名称。仅aria-label、被aria-hidden的h1或已视觉隐藏的页头均不能满足primary-ready；不得靠原生标题被删后才发现页头不可用。
- 原生收藏保留原accessible name、role、pressed状态（如原有）、disabled、tab顺序、focus、事件和descriptor。不得将其移到页头，不因省略名称而扩大授权或重新生成事件。
- 省略对象是指定名称的视觉文本叶子，不是h1容器、native-title-row或字段集合。禁止对父节点使用display:none、hidden、aria-hidden等方式实现。
- 若原文本参与aria-labelledby/aria-describedby或其他辅助技术关联，保留其ID与文本语义，可采用既有visually-hidden呈现；不得删节点或对其aria-hidden，也不得留下悬空ID引用。若关联不能明确验证，则不激活省略并报告可访问性阻断，不能以截图正常放行。
- 无关联依赖的纯视觉副本可以不再进入重复朗读序列，但必须先证明页头h1仍提供该身份；具体DOM实现选择必须通过可访问树与键盘验收，协议不要求制造第二个无意义隐藏heading。
- 状态切换/重载/标题更新不得移除当前聚焦控件，不能改变其顺序或可访问名称；edit/create保留原名称输入、label及键盘操作。

## D. 向后兼容与发布设计

采用“外层版本 + 结构版本 + 能力”共同准入；不以其中任意一个替代其余条件。

1. 新客户端继续接受原有 2.0–2.2/结构1.0–1.1；recordIdentity 未声明则完全旧行为，包括可能重复的标题。
2. 新服务端仅向接受 2.3 且声明新能力的客户端交付结构1.2关系。只接受旧版本/缺能力的客户端获取合法旧结构投影：剥离关系、保留全部原生字段/文本/动作，退回已有受支持结构版本。不能只删 key 却保留旧解码器拒绝的1.2/2.3版本标记。
3. 旧服务端向新客户端返回原契约时保持旧表现。旧客户端收到误发的新对象必须按实际严格 decoder 拒绝，作为交付缺陷；不声称“客户端会忽略”。无公共支持版本则返回明确版本不兼容，不伪造旧版本标签。
4. 新结构中已声明的错误引用、未知 policy、重复/冲突、字段泄露风险不可在降级时掩盖；先验证定义，再为不支持的客户端生成安全旧投影。旧投影仅放弃视觉优化，不放弃权限或事实。
5. 服务端 capability/结构/外层版本、角色/公司/record/view/profile、有效声明版本必须进入现有缓存身份或逐请求投影边界，证明旧客户端不会拿到新缓存。前端完整加载与增量 patch 必须一致协商；无法保证时使相关 patch 失效并要求完整契约刷新，禁止沿用悬空关系。
6. 定义撤回、客户端回滚或能力关闭时停止省略、恢复原文本；不需要数据迁移。采用既有发布生命周期/版本回退机制，不修改已发布定义历史。退回会重新出现重复标题，属于明确兼容退化，不是信息丢失。

现有节点能力校验不直接适用到本关系，不能直接复用其“缺能力即报错”来让所有旧客户端失去页面。后续需要在相同请求级交付边界实现经过测试的安全旧投影，且保留对非法定义的 fail-closed。

### D1. R1：三个候选标识分别承担什么职责

| 候选 | 职责 | 为什么在本方案中不能只保留另一个 |
| --- | --- | --- |
| 外层2.3.0 | 整个响应的语法/交付边界与accepted_contract_versions协商 | 能力字符串不能让只接受2.0–2.2的严格pageInfo decoder接受新格式；不把新payload伪标旧版本 |
| structureVersion 1.2 | 标识formStructureContract.navigation新增关系的嵌套结构语法 | 外层版本不说明此表单片段采用哪种结构；旧1.0/1.1仍可存在于新客户端读取范围，片段必须可单独验证 |
| form.record_identity_projection.v1 | 客户端实际实现该呈现语义及交付降级的准入 | 接受外层版本不等于已实现视觉省略/辅助技术行为；其他客户端可能支持2.3而未实现该能力 |

三者是本推荐方案的互补边界，不声称从理论上无法设计其他协议；这些具体标识仍待批准。若将来要合并边界，需要独立的兼容证明，不能在实现中省略检查。

当前真实支持只有Web请求声明2.0/2.1/2.2、显式能力列表、pageInfo正则及structureVersion的严格解码。现有node capability校验证明请求级能力验证有入口，但没有实现本关系的安全旧投影。要真正支持此路径，后续必须同时修改正式schema、服务端协商/交付、缓存隔离、客户端广告和严格解码；仅增加接受版本字符串不构成支持。

降级必须在最终序列化前完成：先验证源定义 → 计算双方支持的版本和能力 → 生成对应旧结构或新结构 → 用该目标版本真实schema校验 → 输出匹配的版本标记。无共同版本明确拒绝。旧客户端路径必须移除新关系并恢复合法旧structureVersion和外层版本，同时保留原生文本、字段与动作；禁止仅改标记或仅删字段。

兼容证明必须固定真实旧客户端decoder版本及其输入fixture，验证“新服务端给旧客户端”的payload确实通过它，而误发新结构会拒绝；再用新decoder验证旧payload、合法新payload和非法关系。通用additive分析只作辅助，不作为放行依据。完整载荷与patch均执行同一边界。

## E. 风险与实施准入

复合身份（名称+编号等）不纳入 v1 自动省略集合；独立标题、附加文本/子节点保持，除非另有明确且已批准的身份定义。无 record、缺字段、字段不可读/空值、动态模板身份、重复 occurrence 解析不唯一均不能自动补造授权。数据变更后必须原子更新页头与文本状态，避免显示旧身份。

实施之前必须批准：本推荐对象/版本、真实发布载体与定位绑定、服务端降级与缓存隔离方案、所有模式及可访问行为矩阵。禁止把本设计 JSON 复制到运行时直接启用。验收见 [兼容矩阵](title-identity-compatibility-matrix.md) 和 [回归计划](title-identity-regression-plan.md)。

## 源码核查索引

所有路径均相对仓库根，绑定上述 main；本轮只读：

- `frontend/apps/web/src/app/contracts/v2/{types.ts,schema.ts,client.ts,clientCapabilities.ts}`：正式前端类型、严格解码与请求能力。
- `docs/architecture/unified_page_contract_v2/unified_page_contract_v2.schema.json`：正式 JSON Schema。
- `frontend/apps/web/src/app/presentation/contractFormPresenter.ts`（最终 readonly 合成、shell.title），`canonicalFormFloorplan.ts`（容器标题去重）。
- `frontend/apps/web/src/pages/contractForm/{canonicalNativeFormBridge.ts,canonicalFormRenderer.ts,ContractFormProductHeader.vue}`、`components/template/NativeFormTreeRenderer.vue`：字段 occurrence 到实际文本/控件。
- `addons/smart_core/core/{unified_page_contract_v2_assembler.py,node_component_capabilities.py,contract_version_compatibility.py}` 与 `handlers/ui_contract_v2.py`：当前外层2.2、动作identityPolicy、节点能力校验、兼容工具与交付入口。

“新增版本如何协商/降级”是方案要求，未宣称已由上述代码实现。运行时事实、源码事实和拟议规则必须分别审查。
