# 自定义前端页头入口权威统一（P0 表达收口第二刀）

**层级**：Formal Product Layer **P0**（平台通用表达机制）；本批的守卫、入口契约测试与批次记录属 **P4**。
Layer Target = `frontend/apps/web` 的**页头入口面**（`ProductPageHeader` 及其薄入口／受管例外入口）。
**标准口径**：平台通用机制，不承载施工行业事实、客户偏好或低代码运行配置。
**Why Here**：`ProductPageHeader` 已经是唯一实现，但**入口**（谁可以进来、进来后哪些正式轴被转发）此前没有任何权威，
只有一条子串守卫 `"ProductPageHeader" in adapter`。结果是「传了不存在的输入被静默吞掉」和「固定轴靠字面量」这两类
缺陷既不会被发现、也不会被拒绝。
**Why Not Elsewhere**：不改视觉、不改契约 schema、不改字段权限／状态动作／业务取值；不改原生视图、fixture、数据库、
Compose/profile、端口或凭据；不新增渲染主链。
**Blast Radius**：页头入口的属性面与固定轴来源；页面身份 h1 的唯一权威不变。
**回滚**：`git revert`（表达层可逆提交，无数据／模式迁移）。

## 1. 触发

用户指令「先统一自定义前端的逻辑，还存在明显的不足」后的第二轮：`frontend_field_semantics_authority_20260921.md`
收口了**取值呈现**面；页头被用户与前一批复核共同点名为下一个「多入口无权威」面。

## 2. 侦察确认的缺陷

| # | 缺陷 | 证据 |
| --- | --- | --- |
| D1 | **调用方传参被静默吞掉**：`KanbanPage.vue` 向 `components/page/PageHeader.vue` 传 `status`、`status-label`、`loading`、`on-reload`、`mode-label`、`record-count` 六个属性，而该入口只声明 `title`／`subtitle`。Vue 属性穿透会把这些落到 `ProductPageHeader` 根元素上，成为无意义的 DOM 属性；作者以为已接线的错误态页头事实其实**从未被消费** | `frontend/apps/web/src/pages/KanbanPage.vue:9-18`（改前）对 `components/page/PageHeader.vue:5-8` |
| D2 | **三个薄入口能力面不一致且无声明**：`template/PageHeader` 转发 9 个属性 ＋ 3 个槽；`design-system/ScPageHeader` 只有 `title`／`subtitle`／`eyebrow` ＋ `actions` 槽；`page/PageHeader` 只有 `title`／`subtitle`。选错入口会静默降级且没有任何提示 | 三个入口文件对比 |
| D3 | **固定轴靠字面量**：`page/PageHeader` 与 `design-system/ScPageHeader` 各自硬编码 `presentation-mode="collection"`，与「集合密度」这一决策没有单一事实来源 | 同上 |
| D4 | **新轴可静默漏过入口**：`ProductPageHeader` 新增一条正式轴时，没有任何机制要求每个入口作出决策 | 守卫原实现仅检查子串 |
| D5 | **受管例外未声明归属**：`pages/contractForm/ContractFormProductHeader.vue`（365 行）持有契约动作证据、原生状态栏与移动端动作结算，是唯一允许多带内容的入口，但「为什么可以」此前只存在于守卫的零散断言里 | 守卫对 contract header 的 marker 断言 |

## 3. 交付内容

- **新增唯一权威** `frontend/apps/web/src/app/presentation/productPageHeaderAdapters.ts`：
  `PRODUCT_PAGE_HEADER_AXES`（15 条正式轴）＋ 四个入口（`page`／`template`／`design-system`／`contract-form`）对
  **每条轴**的显式处置（`forwarded`／`fixed`＋理由／`not_exposed`＋理由）＋`PRODUCT_PAGE_HEADER_DIRECT_CONSUMERS`
  （`ActionView`／`HomeView`／`MyWorkView` 三个直接消费权威的页面）。
- **入口改为消费契约**：`page/PageHeader` 与 `design-system/ScPageHeader` 的固定档位改为
  `resolveProductPageHeaderFixedMode('<id>')`，不再保留字面量；`template/PageHeader` 与
  `ContractFormProductHeader` 的转发面与登记表逐条对齐。
- **调用方订正（唯一运行期变化）**：`KanbanPage.vue` 移除六个无消费方的属性，连带删除只服务于该绑定的
  `modeLabelText` 计算属性与 `pageModeLabel` 导入。`ProductPageHeader` 根元素不再承载 `status`／`status-label`／
  `loading`／`on-reload`／`mode-label`／`record-count` 这些无意义 DOM 属性。**无视觉变化、无业务语义变化**。
- **结构性门禁** `frontend/apps/web/scripts/product_page_header_adapter_contract_test.ts`（接入
  `verify.frontend.product_page_header.unit`）：A 权威正式面 ≡ 登记轴（权威另不得用 `$attrs`／`useAttrs()`／`attrs` 兜底转发）；
  B 入口存在且**在模板中真实渲染**上游（只留 `import` 不算委托）、不得自建 `header`／`h1`；
  C 声明转发必须真实转发；D 固定轴不得留静态字面量、**绑定值必须引用由登记表解析出的常量**
  （挡住「装饰性调用 ＋ 字面量绑定」的静默分叉）；E 薄入口声明面 ⊆ 登记面且同样不得 `$attrs`／`useAttrs()`／`attrs`；
  F **调用方传入属性 ⊆ 入口声明面**（D1 这一类缺陷的直接封堵）＋**调用点全集钉死**；G 直接消费权威的文件集合 ≡ 登记表；
  H 轴决策完整、id 唯一、`not_exposed`／`fixed` 必须给理由。
  F 与 G 的入口解析同时覆盖**默认导入、具名导入与 barrel 再导出**（`import { ScPageHeader } from '../components/design-system'`），
  标签形态同时覆盖 **PascalCase 与 kebab**，属性扫描**感知引号**（不再把属性值内部的标识符误判为属性名）；
  `<component :is>`（**大小写不敏感**：Vue 把 `Component` 与 `component` 都当动态组件）动态渲染已登记入口、
  对已登记入口使用 `v-bind` 对象展开（含 `v-bind.prop`／`.camel`／`.attr` 修饰符形态，与 `v-bind=` 是同一个
  整对象展开通道）、以及**权威标签自身**的对象展开，一律失败并要求显式登记为守卫边界；
  动态绑定按**属性级**解析（不是正则扫子串），因此**引号不敏感、允许 `=` 两侧空白、覆盖无引号取值**
  （`:is='X'`／`:is = "X"`／`` :is=`X` ``／`:is=X`／静态 `is="X"` 同等对待），并覆盖 `:is.camel`／`:is.prop`／
  `:is.attr` 这些**合法修饰符**（Vue 对它们全部按动态组件渲染）；`data-is="X"` 是普通静态属性，**不得**被误判。
  属性名统一归一到 Vue 实际使用的输入名
  （`:x` ≡ `v-bind:x`，`v-model` → `modelValue`，`v-model:x` → `x`，`.modifier` 不改变 prop 名），
  不再因 `v-` 前缀整体跳过；模块说明符解析同时覆盖相对路径与 vite `@/` 别名；以入口组件同名符号导入却解析不到
  登记入口的说明符**硬失败**（别名／包路径等未登记形态不得让调用点同时躲过 F 与 G）。
  入口源码在分析前先经**模式感知**（模板正文／标签内部／`<script>`・`<style>` 原始段／模板 `{{ }}` 插值）
  的逐字扫描器：HTML 注释与脚本语义里的块注释／行尾 `//` 清零，字符串与模板字面量的
  **内容**掩码——注释或字面量里的「委托渲染」「登记表解析」都不是实现，而掩码视图与原文等长，
  需要真值的断言（固定轴入口 id、绑定标识符）按对齐下标回原文取回。开标签属性块同样**引号感知地**取到真正的
  `>`（属性值里的 `>`／`>=` 不得截断标签）；模板正文里的裸撇号（`<p>owner's</p>`）不得打开引号状态、
  模板正文里的斜杠是文本而不是注释，模板注释里的动态绑定/标签不算调用点（三者否则都是**假失败**）；
  薄入口与权威暴露的槽位必须是**静态具名槽**且受登记表约束（默认槽与 `:name` 动态槽名硬失败，
  单引号与双引号具名槽都合法）；薄入口的声明面只承认**字面量类型**的 `defineProps<{ … }>`
  （`defineProps<` 与 `{` 之间的换行是排版差异）——Options API 的 `props: { … }`（只在其所在 `<script>` 段
  同时声明 `export default` 时才算声明面，否则 `type M = { props: { … } }` 这类类型字面量会被误判）
  与非字面量 `defineProps<T>` 无法静态枚举，一律**硬失败**而不是静默放行；
  入口说明符按**末段**识别，改名导入必须显式登记，动态 `import()`／`require()` 命中入口（含双引号与模板字面量说明符）即硬失败。
  不得绑定字符串字面量、**绑定常量必须由本入口 id 解析**）、薄入口与权威均不得 `$attrs`／`useAttrs()`／`attrs`、
  登记表必须包含全部入口路径、入口契约测试必须**以未被注释的 recipe 行**仍接在
  `verify.frontend.product_page_header.unit` 上（按 Makefile 结构取目标块、先按 Make 规则把 `\` 续行拼成
  逻辑行、再剔除以 `#` 开头的行，防止「注释掉烘焙／执行行、保留文件名」与「用续行承载失败吞噬后缀」的静默摘除）；
  另要求接线目标**只定义一次**（重复目标会让后续 recipe
  覆盖被守卫的那一份）、且该目标必须仍是 `verify.frontend.quick.gate` 与 `verify.frontend.release.unit` 的前置
  （门禁挂点按**前置 token**、先截掉 `#` 注释后比对：行尾注释里的目标名不算依赖）；三条 recipe 必须
  **真的按预期形状执行**——先剔除 `#` 注释与 shell 重定向
  （`2>&1`／`>/dev/null` 不是链式分隔符，且剥离时**不得吞掉紧贴其后的分隔符**），再按
  `;`／`&&`／`||`／`|`／`&` 切段并**不丢弃空段**（尾随 `&` 即视为两段），要求**恰好只剩一段**且该段
  「首 token 就是该程序」「其后紧跟的前 N 个 token 与预期参数**逐个相等且同序**」
  （`@echo <整条命令行>`／`@node --version # <文件名>`／`@node --version <文件名>`／`@node --version; echo <文件名>`
  这类伪命令与链式诱饵都不算，`false && <步骤>`／`<步骤> || true`／`<步骤> &`／`>/dev/null|| true` 因
  「永不执行」或「失败不传播」同样失败）；`textarea`／`title` 按 **RCDATA** 处理（其中的 `<!--` 是文本而非注释），
  `$attrs` 判据分两个视图（具名符号在**字面量已掩码**的视图里判、模板 `v-bind="…attrs…"` 在未掩码视图里判），
  注释剥离与标记扫描同为**模式感知**；固定档位相关检查同样先经引号感知的注释剥离。
  新增 **37** 条负例单元测试（14 → **51 例**）。

## 4. 入口决策表（摘要）

| 轴 | `page` | `template` | `design-system` | `contract-form` |
| --- | --- | --- | --- | --- |
| `title`／`subtitle` | 转发 | 转发 | 转发 | 转发 |
| `eyebrow` | 不暴露 | 不暴露 | **转发** | 不暴露 |
| `breadcrumb` | 不暴露 | 不暴露 | 不暴露 | 不暴露 |
| `presentationMode` | **固定 `collection`** | 转发 | **固定 `collection`** | 转发 |
| `renderProfile`／`dirtyState`／`hideTitle` | 不暴露 | 转发 | 不暴露 | 转发 |
| `variant` | 不暴露 | 不暴露 | 不暴露 | 不暴露 |
| `primaryActions`／`overflowActions`／`exitAction` | 不暴露 | 转发 | 不暴露 | 转发 |
| `metaSlot`／`statusSlot` | 不暴露 | 转发 | 不暴露 | 转发 |
| `actionsSlot` | 不暴露 | 转发 | **转发** | 转发 |

`breadcrumb` 与 `variant` 目前**没有任何入口转发**：两者都由 authority 直接支持，但既有页面路径语境与对话框变体
由导航壳层／调用方直接渲染。这是显式决策而不是遗漏，登记表逐条给出了理由；未来若要启用，必须先在该表改决策。

## 5. 验证证据

| 层 | 入口 | 结果 |
| --- | --- | --- |
| 入口契约 | `product_page_header_adapter_contract_test.ts` | **PASS** `entries=4 axes=15 call_sites=6 direct_consumers=3` |
| 守卫 | `verify.frontend.product_page_header.unit` | **PASS**（Node 模型 28 例；契约测试；守卫单测 **63 例**；守卫脚本 `adapters=3`） |
| 取值呈现 | `scripts/verify/frontend_localized_display_contract_test.ts` | **PASS** `sources=686 consumers=18` |
| 静态 | `lint:src` | **PASS**（0 error／39 条既有风格 warning） |
| 类型 | `typecheck:strict` | **PASS** |

**门禁非空洞实证（影子副本 132 项：110 项 CAUGHT ＋ 22 项「假失败防线」STILL-PASS）**：除首批形态（调用方传未声明属性／薄入口少转发声明轴／
薄入口自建 `h1`／薄入口自建 `header`／未登记的权威直接消费者／权威新增 prop 未登记／薄入口新增未登记输入／
薄入口硬编码固定轴／登记表漏某入口一条轴决策／受管例外失去对权威的委托／薄入口删掉固定轴解析调用／
`not_exposed` 不给理由）之外，第二轮复核点名的**全部既有盲区**都被同一批注入覆盖并抓到：
kebab 标签形态（`<page-header :bogus-attr="1">`）、barrel 具名导入的调用点（`ApiKeyManagementView` 加 `record-count="5"`）、
`<component :is>` 动态渲染、`v-bind` 对象展开、契约测试接线被注释掉（esbuild 行／`@node` 行／守卫脚本行三例）、
固定轴绑定字符串字面量、固定轴常量解析错入口 id、只留 `import` 而丢掉模板渲染、权威与薄入口的 `$attrs` 兜底转发、
新增调用点文件。第三轮复核点名的**诱饵类**形态也已全部纳入并抓到：单引号 `<component :is='X'>`、
`{{ '/*' }}` 字符串注释符诱饵（契约测试与守卫两侧）、默认槽／动态槽名／单引号槽名、权威默认槽、
改名默认导入（可解析与不可解析说明符两种）、动态 `import()` 入口、行尾 `//`／双引号／模板字面量三种常量诱饵、
字符串里的假模板委托，以及 recipe 侧的 `@echo <整条命令行>`／`@node --version # <文件名>`／`@true # <文件名> --bundle`。
第四轮复核点名的**绕过与假失败**也都纳入同一批矩阵：`$attrs` 之外的 `useAttrs()`／`attrs` 兜底转发、权威标签自身的 `v-bind` 对象展开、
Options API `props: { … }` 与非字面量 `defineProps<T>`、`:is` 的 `=` 两侧空白变体与静态 `is="X"`、模板字面量 `:is`、
双引号／`require()` 动态说明符，以及 recipe 伪命令与 shell 链式诱饵（`@node --version <文件>`、`@python3 -c "pass"; echo <文件>`、
`@python3 -m unittest --help <文件>`、`@esbuild --version <文件> --bundle`、`;`／`&&` 后接 `echo`）共 **17 项新注入**，全部 CAUGHT。
第五轮复核点名的**绕过与假失败**再并入 15 项：无引号 `:is=ScPageHeader` 与 `:is.camel`／`:is.prop` 修饰符形态、
`false && <步骤>`／`true || <步骤>`（永不执行）与 `<步骤> || true`／`<步骤> ; true`（失败不传播）共 8 项新注入全部 CAUGHT
（上一轮的 4 项防线中 `|| true` 那一项按失败关闭**转为必须抓到**）；反向新增 8 项防线锁定 STILL-PASS：
`data-is` 是普通静态属性、`'no attrs here'` 这类文案不是兜底转发、`type M = { props: {…} }` 不是 Options API
（契约测试与守卫两侧）、模板正文里的裸撇号不得吞掉其后注释、`defineProps<` 与 `{` 之间的换行仍是字面量声明、
`2>&1` 是重定向而不是链式分隔符。
第六轮复核点名的**绕过与假失败**再并入 17 项（12 项 CAUGHT ＋ 5 项 STILL-PASS）：`v-bind.prop`／`v-bind.camel`／`v-bind.attr` 是 `v-bind="obj"` 的等价形态
（编译器同样输出 `_guardReactiveProps` ＋ FULL_PROPS，两个门禁原先都看不见）、`<textarea><!--`／`<title><!--`
（RCDATA 里的 `<!--` 是**文本**，原先会把其后**真实渲染**的整段模板吞成注释）、重定向紧贴分隔符
（`>/dev/null|| true`）／尾随 `&` 后台化／以 `\` 续行承载的失败吞噬后缀、以及把 unit 目标从门禁前置里删掉、
只留成行尾 `#` 注释（子串判定会 PASS）——共 **8 类**新注入（含消息级复核，共 12 项）全部 CAUGHT；反向新增 5 项
防线锁定 STILL-PASS（N11／N12／N13／N14／N14g）：Options API 形态的**普通字符串**不是声明、
声明类型里的**嵌套键**不是顶层 prop、双引号解析常量同样是登记表声明、RCDATA 元素在真实模板（契约测试）
与适配器（守卫）两侧都不吞其后代码。
第七轮复核点名的 **Make 级失败通道**再并入 5 项 CAUGHT：通过 `include` 片段重定义被守卫的目标
（Make 对同一目标取**最后一份** recipe，原文件可以一字未动）、recipe 行的 **`-` 忽略错误前缀**
（`@-esbuild …`／`-@node …`，shell 形状完全正常但 Make 忽略退出码）、**`.IGNORE:` 特殊目标**、
**`MAKEFLAGS` 里的 `-i`／`--ignore-errors`**；反向新增 2 项防线锁定 STILL-PASS（N15／N16）：
`MAKEFLAGS += --no-print-directory` 这类无关开关、以及 `-include` 缺失的**可选**片段仍合法。
第八轮复核点名的 **include 拼写与失败传播覆写**再并入 9 项 CAUGHT：`sinclude`（`-include` 的正式同义词）、
以 `\` 续行承载的 `include`、带引号的 include 路径、**变量目标名**（`$(_HT):` 静态不可知，故按失败关闭要求显式登记）、
片段把 `SHELL` 重定义到恒返回 0 的程序、`.ONESHELL:` ＋尾部 no-op（整条 recipe 只取最后一行的状态）、
`override MAKEFLAGS += -i`／`export MAKEFLAGS := -i`／以续行承载的 `MAKEFLAGS += -i`；反向新增 4 项防线锁定
STILL-PASS（N17–N20）：`sinclude`／续行 include／带引号 include 各引入一个只声明无关变量的片段不得假失败，
`.SILENT:`／`.NOTPARALLEL:` 不是失败传播通道。
矩阵扩到 **132 项（110 项 CAUGHT ＋ 22 项假失败防线 STILL-PASS）**；守卫单测 51 → 55 → **63 例**。
每例在 `/tmp` 影子副本上注入并重跑（esbuild 就地重烘焙，保证登记表改动也被覆盖；影子已镜像根 `Makefile` 与
`make/` 目录，因为 `include` 链本身现在是判据面的一部分），工作树文件未被修改。

`KanbanPage` 死属性的实证：改前 `git show de9a230d:...KanbanPage.vue` 的 `PageHeader` 绑定为 **9 条属性**
（`v-if` ＋ 8 条绑定），其中 6 条不在 `page/PageHeader` 声明面内；改后为 3 条（`v-if` ＋ 2 条绑定）。
门禁 F 会在任何一条重新出现时失败。

## 6. 排除项与残限

- **薄入口仍不暴露全部轴**（如 `design-system/ScPageHeader` 无 `statusSlot`）：这是本次**显式登记**的决策，
  不是收口遗漏。把它改成转发会是可见表达变化，需要单独的产品决策与运行态证据。
- **`breadcrumb`／`variant` 无任何入口转发**：同上，登记表逐条给出理由。
- **`ContractFormProductHeader` 的 365 行领域内容**（契约动作证据、原生状态栏、移动端动作结算）不在本批收口：
  它需要领域面自己的批次；本批只声明它是**受管例外**且必须继续委托权威渲染。
- **门禁不是 AST 分析**：下面**已登记的边界**全部有注入实证（132 项矩阵：110 项 CAUGHT ＋ 22 项假失败防线锁定 STILL-PASS），**仍未静态覆盖的形态**另列如下，两者不得混为一谈：
  - 调用点解析覆盖默认导入、具名导入与 barrel 再导出，另覆盖相对路径与 `@/` 别名；标签覆盖 PascalCase 与 kebab；
    属性名归一到 Vue 实际输入名（`:x` ≡ `v-bind:x`，`v-model` → `modelValue`）；调用点集合被**钉死**为 6 个
    （`ContractFormPage`／`KanbanPage`／`ContractFormProductHeader`／`ApiKeyManagementView`／`NotFoundView`／
    `BusinessConfigContextBar`），新增或改形都必须先改 `KNOWN_CALL_SITES`。
  - `<component :is>`（含大写 `Component`、静态 `is="X"`、`:is = "X"` 空白变体、**无引号** `:is=X`、
    以及 `:is.camel`／`:is.prop`／`:is.attr` 修饰符）动态渲染已登记入口、对已登记入口（**含权威标签自身**）
    使用**字面量** `v-bind="obj"`／`v-bind="{…}"`／`v-bind.prop|.camel|.attr="obj"`（修饰符形态是同一个
    整对象展开通道）对象展开、以及入口用 `$attrs`／`useAttrs()`／`attrs` 兜底转发，
    都**静态不可枚举**，因此被设计为**硬失败**（要求显式登记），而不是静默放行；`data-is="X"` 是普通静态属性，
    明确**不在**该判据内（不得假失败）。`attrs` 判据覆盖**具名符号**与 `v-bind` **取值位**两个视图；
    单独出现在普通绑定取值里的 `:x="$attrs"`（非 `v-bind` 展开）不在此判据内，也不要写成「任何 `$attrs` 出现即失败」。
  - `textarea`／`title` 是 **RCDATA**：其中的 `<!--` 是**文本**而不是注释（与 `<script>`／`<style>` 的原始段同层处理），
    否则 `<textarea><!--</textarea>` 会把其后真实渲染的整段模板吞成注释，让真实调用点对门禁隐身。
  - 薄入口的声明面只承认**字面量类型**的 `defineProps<{ … }>`（`defineProps<` 与 `{` 之间的换行是排版差异）：
    Options API 的 `props: { … }`（只在其所在 `<script>` 段同时声明 `export default` 时才算声明面，否则
    `type M = { props: { … } }` 这类类型字面量会被误判）与非字面量 `defineProps<T>`（类型别名／交叉类型）
    无法静态枚举，同样**硬失败**——否则「声明面 ⊆ 登记面」会整体空转，薄入口可静默新增未登记输入。
    槽位断言对**单引号与双引号具名槽一视同仁**（单引号是合法的静态具名槽，不得假失败），模板注释里的标签／
    动态绑定同样不算调用点（不得假失败）。
  - **仍未静态覆盖的形态（如实登记，逐条）**：①`v-if`／`v-show` 门控掉的真实渲染分支；②把输入名拼在运行时
    字符串里再 `v-bind` 展开；③需要数据流分析才能判定的间接转发（例如把 prop 名从对象键推导出来）；
    ④门禁自身的挂点仍可被有意编辑（本批已把「recipe 行（含 `\` 续行展开与 `#` 注释清除后的逻辑行）」
    「`include` 链上被守卫目标的**唯一定义**」「recipe 行的 Make 前缀（`-` 忽略错误）」
    「`.IGNORE:`／`MAKEFLAGS` 的 `-i`／`--ignore-errors`」「`quick.gate`／`release.unit` 前置 token（覆盖整条
    `include` 链，并与 `make/runtime_ops.mk` 的可累加前置合并）」都纳入断言，但**仍无法阻止有人同时改 recipe 与断言**；
    include 拼写按 `include`／`-include`／`sinclude`（含 `\` 续行、引号路径、一行多路径）**逐个静态解析**，
    `$(VAR):` 这类**变量目标名**、`.ONESHELL:`、以及 `SHELL`／`.SHELLFLAGS` 在链上的**重定义**同样一律硬失败
    （安全方向，需显式登记）；`include $(VAR)` 这类**动态 include** 与条件 include 无法静态展开，即本条残限）；
    ⑤受管例外入口的领域属性面（见上）；⑥计算出的说明符（`import(path)`
    或 `v-bind:is` 里的变量）在解析阶段不可知——工具链只对**字面量**说明符生效，因此运行期拼出的入口路径
    仍需人工评审；⑦配方行的形状判定是「先摘掉 shell 重定向，再按 `;`／`&&`／`||`／`|`／`&` 切段后**恰好只剩一段**，
    且该段**首 token 就是该程序**、**紧随的前 N 个参数逐个相等且同序**」：这挡住了 `@echo <整条命令行>`／`@node --version <文件>`／
    `@node --version; echo <文件>`／`@python3 -c '…'; echo unittest <文件>`／`@python3 -m unittest --help <文件>`／
    `@esbuild --version <文件> --bundle` 这类伪命令与链式诱饵，也挡住了 `false && <步骤>`／`true || <步骤>`
    （**永不执行**）与 `<步骤> || true`／`<步骤> ; true`／`<步骤> &`（**失败不传播**：`&` 后台化后 shell 立刻以 0 退出）；
    重定向的剥离**不吞分隔符**，所以紧贴写法 `>/dev/null|| true`／`2>/dev/null; echo x` 同样失败；
    Make 的 `\` 续行先拼成**逻辑行**再判定，所以 `… \` ＋ `|| true` 这类续行修饰也不会漏；
    「门禁挂点」按**前置 token**（并先截掉 `#` 注释）比对，`# was verify.frontend.product_page_header.unit` 这类
    行尾注释诱饵不再能让门禁 PASS；Make 级的「失败不传播」通道同样被封——recipe 行的 `-` 前缀、`.IGNORE:`、
    `MAKEFLAGS` 里的 `-i`／`--ignore-errors`，以及在 `include` 片段里重定义被守卫的目标（Make 取最后一份 recipe）
    一律失败，代价是被守卫目标的 recipe 必须留在它当前所在的文件、且不得借助 Make 的忽略错误开关（安全方向）；
    `2>/dev/null`／`2>&1`／`>/dev/null`
    这类重定向仍被接受（它们不是链式分隔符），但**任何链式修饰都会假失败**（安全方向，需要显式登记才能通过）；
    同类假失败还包括 `$(ESBUILD)` 变量中继、`sh -c '…'` 包装、把 `--bundle` 等参数换序，以及
    `cd <子目录> && esbuild …`（即便 `cd` 后仍用仓库根相对路径也一律失败）；⑧静态不可枚举的形态
    （动态组件／对象展开／动态 `import()`／改名导入）一律**硬失败**，代价是任何新增的合法形态都必须先改门禁。
    运行态回归的最后一道网是 `verify.frontend.product_page_header.browser`，它**不在** `quick.gate` 内，
    本批亦无 `local.dev` 抽验。
  - **受管例外入口的调用面不在「属性 ⊆ 登记轴」约束内**：`pages/ContractFormPage.vue` 向
    `ContractFormProductHeader` 传的是该入口自带的领域属性面（约 50 条，如 `busy`／`mode`／`statusbar`），
    不是 15 条正式轴。本批只把该调用点登记进调用点全集并禁止 `v-bind` 对象展开；它的属性面收口需要领域自己的批次。
  - 登记表的值本身就是单一事实来源：把 `design-system` 的固定档位从 `collection` 改成别的值会**直接改变渲染**，
    不存在「登记表↔渲染静默分叉」——D 断言绑定值必须引用 `resolveProductPageHeaderFixedMode('<entry>')`，
    常量必须由本入口 id 解析（解析错入口 id 会被抓到）。
- **未做运行态浏览器抽验**：本批唯一运行期变化是「移除无消费方属性」，不改变可见表达；仍无 `local.dev` 证据。
- `verify.frontend.scene_component_bridge.guard`、`frontend_style_system_guard`（`ContractFormPage.vue` 1905>1900）与
  `verify.frontend.release_navigation_policy.guard`（菜单投影差异）在本批之前即为失败，属既有债务，本批不修、不掩盖。

## 7. 未做与下一步

- 上一批复核 A′／B′ 点名的**登记完整性**已在本批补上：`productMyWorkPresentation`／`ApiKeyManagementView`／
  `PaymentSettlementIntroduceDialog`／`BoqImportPreviewPanel`／`RelationSearchDialog` 的本地回退与格式化事实，
  已在 `frontend_localized_display_contract_test.ts` 中以**正锁**（缺一即失败）登记，任何漂移都必须重新决策。
- 仍未做（下一批候选）：①上述文件**并入权威**（需要产品措辞决定 ＋ 运行态抽验）；②`normalizeFieldType` 对非字符串
  `ttype` 的越契约输入收紧为 `string`；③登记式约束从「按文件成员放行」改为「按内容指纹锁定」；④13 个并行组件族
  权威边界声明；⑤权限判定单一权威；⑥`make/codex.mk` 里关于「四门靠 `workflow_dispatch`」的注释与实际
  `pull_request` 事件路径不一致，属下一批的决策项（本批按 PR 事件路径执行，未改该注释）。
- Next Step：冻结本批 HEAD → L1 → exact-head `ci.local.quick` 回执 → 独立只读复核（A／B → A′／B′ → A″／B″ → A‴／B‴ →
  A⁗／B⁗ → A⁵／B⁵ → A⁶／B⁶ → A⁷／B⁷ 共 16 次；本轮修订后再由 A⁸／B⁸ 验证，合计 18 次）→ 显式合并授权 →
  `make pr.push`／`pr.create`／`pr.ready`／`pr.merge` → 主仓库 `make main.sync` → `make branch.cleanup.feature`。

## 8. 独立只读复核与修订（对 `cc36a37a`／`a4b5c094`／`4ea84a5b`／`86b48ac3` 等历次冻结候选）

八轮共 16 次复核（A／B → A′／B′ → A″／B″ → A‴／B‴ → A⁗／B⁗ → A⁵／B⁵ → A⁶／B⁶ → A⁷／B⁷）均对本批**产品代码**给出安全结论
（`cc36a37a..HEAD` 零 `src` 改动、无能力回退、无新增类型错误、L5 回执真实、
`PRODUCT_PAGE_HEADER_DIRECT_CONSUMERS` 与真实 import 集合完全一致），且都在 base 上逐字复现了三项既有失败。
**无 S0／S1**；问题集中在**门禁强度**与**文档数字**：

| 出处 | 问题 | 修订 |
| --- | --- | --- |
| Round A S3-F1 | F 不覆盖 kebab 标签与具名／barrel 导入，`call_sites` 只断言 `>0`，可静默从 4 缩到 3 | 调用点解析扩展到具名／barrel 导入与 kebab 标签；调用点集合改为**钉死等价**（现为 6 个） |
| Round A S3-F2 | 断言 B 用 `source.includes('ProductPageHeader')`，对 `contract-form` 近乎恒真 | B 改为**模板级断言**：必须渲染解析到权威／已登记入口的本地组件标签 |
| Round A S4-F3 / Round B S2-2 | `:presentation-mode="'collection'"` ＋ 装饰性解析调用可绕过「不得硬编码」；登记表值改动亦全绿 | D 断言 `:presentation-mode` 必须绑定标识符，且该常量必须 `= resolveProductPageHeaderFixedMode('<本入口 id>')`；守卫同步收紧并加 6 条负例 |
| Round B S2-1 | F 跳过 `<component :is>` 与 `v-bind`；E 只看 `defineProps`，`$attrs` 可静默转发 `not_exposed` 轴 | 动态 `:is`／对象展开改为硬失败；权威与薄入口一律禁止 `$attrs`（契约测试 ＋ 守卫双点） |
| Round B S2-3 | 守卫「防静默摘除」只是子串存在性：注释掉 esbuild／`@node` 行仍 PASS | 守卫改为解析 `make/frontend.mk` 目标块，只接受**未被注释**的 recipe 行，并同时要求守卫单测行与守卫脚本行 |
| Round A O1 / Round B S3-1 | 文档称改前 `PageHeader` 绑定「10 条属性」 | 订正为 **9 条属性**（`v-if` ＋ 8 条绑定）；切换日志中「`design-system` 4 属性＋1 槽」订正为 **3 props ＋ 1 slot** |
| 额外发现（本轮自证） | 属性名扫描用正则，会把属性值内部的标识符（`v-if="... status !== 'error'"`）误判为属性名 | 属性扫描改为**引号感知**的逐字扫描器 |
| Round B′ S2-N1 | F1 只扫小写 `<component`，而 Vue 的 `isComponentTag` 同时接受 `Component`；新文件用 `<Component :is="ScPageHeader">` 可同时躲过 F1、调用点集合同等与 G | 动态组件扫描改为 `<[Cc]omponent` |
| Round B′ S2-N2 | `v-bind:prop`（与 `:prop` 等价）与 `v-model` 因 `v-` 前缀被整体跳过——「静默丢参」存在一 token 绕过 | 属性名统一归一：`v-bind:x` ≡ `:x`，`v-model` → `modelValue`，`v-model:x` → `x`，`.modifier` 不改变 prop 名 |
| Round B′ S3-N2 | 守卫只取目标块的**第一份** recipe；在文件末尾重复定义同名目标会让后续 recipe 生效并绕过守卫 | 守卫要求接线目标**只定义一次**；esbuild 行必须是真实调用（`@echo esbuild …` 不算） |
| Round B′ S3-N4 | `delegationTarget` 只认相对路径，`@/` 别名导入（vite `resolve.alias['@'] = src`）对入口清册不可见 | 模块说明符解析补上 `@/` 别名 |
| Round B′ S3-N3 | 切换日志同一条目内残留「共 14 例」与「守卫单测 20 例」自相矛盾 | 删除残留表述，数字统一 |
| Round A′ S2-1 | F 的标签块用非贪婪正则扫到第一个 `>`，属性值里的 `>`／`>=`／`=>` 会**截断标签**，其后未声明属性静默放行（`:title="a > b" record-count="5"`） | 开标签属性块改为**引号感知**扫描；注入 F11／F12 覆盖 |
| Round A′ S3-2 | 薄入口新增槽位没有任何 ⊆ 约束（可暴露未登记槽） | E 增加槽位约束：`<slot name="X">` 必须对应 `forwarded` 的 `XSlot`；注入 E3 覆盖 |
| Round A′ S3-3 | 未登记的别名／包路径导入形态会让调用点同时躲过 F 与 G | 模块说明符解析补 `@/` 别名；以入口同名符号导入却解析不到入口 → 硬失败；注入 F10／F13 覆盖 |
| Round A′ S3-4 | 注释诱饵可满足 B 的模板委托与 D 的常量解析断言 | 入口源码分析前统一**剥离注释**；注入 B3／D4 覆盖 |
| Round A′ S3-5 | `2e66e87d` 自称防静默摘除，但把 unit 目标从 `verify.frontend.quick.gate` 前置里摘掉仍全绿 | 守卫断言该目标必须仍是 `quick.gate` 与 `release.unit` 的前置；注入 W6 覆盖 |
| Round A′ S4-2 | 三条守卫断言（登记表须含入口路径／须声明 axes＋consumers／契约测试须存在）无负例 | 新增 7 条负例单元测试（20 → 27 例；原文误记为「22 → 27」） |
| Round A″ S4-1 | 文档与切换日志的守卫单测例数沿革记错（历史上不存在 22 例那一档） | 按 `git show <c>:…\|grep -c 'def test_'` 的实测序列 14→14→20→20→27→34 订正 |
| Round A″ S2-A | 两个门禁的**注释剥离**都不是字面量感知：`{{ '/*' }}…{{ '*/' }}` 可把真实代码从门禁眼里夹掉（`$attrs`／槽位／字面量三类注入在 `d93bb013` 上全部 NOT-CAUGHT） | 契约测试与 Python 守卫的注释剥离都改为**引号感知**的逐字扫描器（注释→空格、长度/下标对齐）；注入 S2A-F1／F2／G／G2 覆盖 |
| Round A″ S3-3 | 改名默认导入 ＋ 不可解析说明符、以及动态 `import()` 入口，可让调用点同时躲过 F／F2／G | F2 命中判据补「说明符末段」；新增 F2b「改名导入必须显式登记」与 F3「动态 `import()` 命中入口即硬失败」；注入 F15／F16／F17 覆盖 |
| Round A″ S3-4 | 行尾 `//`、双引号字符串、模板字面量三种**常量诱饵**可满足 D | 新增掩码视图 `codeOnly`（字面量内容逐字符掩掉、与原文等长）：B／C／D 只认掩码视图，D 的入口 id 按对齐下标在原文取真值；注入 D5／D6／D7 覆盖 |
| Round A″ S3-5 | recipe 断言仍是子串判定：`@node --version # <文件名>` 与 `@echo <整条命令行>` 可满足 | `_is_real_command` 先剔除 `#` 注释与输出重定向，要求**首个 token 就是该程序**；注入 W7／W8／W9／W10 覆盖 |
| Round B″ S2-A | `<component :is='ScPageHeader'>`（单引号）绕过 F1 | 动态组件绑定改为**引号不敏感**；注入 F14 覆盖 |
| Round B″ S3-B | `@echo .bin/esbuild …` 仍被算子串接线检查满足 | 同 S3-5 修复；`@echo` 形态另有 3 条守卫单测负例 |
| Round B″ S3-C | 薄入口的默认槽／动态槽名无任何约束 | 槽位约束改为「只接受静态具名槽」，默认槽与 `:name` **硬失败**；权威侧同样钉死；注入 A4／E4／E5／E6 覆盖 |
| Round B″ S3-D | §6 标题「已知边界已全部显式登记」与紧随其后的「仍未静态覆盖」自相矛盾 | §6 标题改写为「已登记的边界有注入实证／仍未覆盖的形态逐条另列」，并把第三轮实证形态补进残限 |
| Round B″ S4-B / Round A″ S4-2 | 「39 项注入全部 CAUGHT」与「已知边界已全部登记」措辞过宽 | 矩阵扩到 **59 项**（8 类新形态）并全部 CAUGHT；措辞按「已登记边界」限定 |
| Round A‴ B-1 | `useAttrs()`／`getCurrentInstance().attrs` 可绕过「薄入口不得兜底转发未登记轴」，而薄入口又不在 F1 的 `v-bind="obj"` 扫描面内 | A3 升级为 `$attrs`／`useAttrs()`／`attrs` **三者等效硬失败**，覆盖权威与全部登记入口；新增 F4 钉住**权威标签自身**的对象展开；注入 B5／B5g／B6 覆盖 |
| Round A‴ B-2 / Round B‴ B-3 | recipe 判定可被 `;`／`&&` 链式诱饵绕过（`@node --version; echo <文件名>`、`@node <real> || true`、`@echo`），并与文档 §6⑦ 自述矛盾 | `_is_real_command` 改写为 `_matches_recipe`：按 `;`／`&&`／`||`／`|`／`&` 切段后要求「某段首 token 就是该程序 ＋ 紧随参数**逐个相等且同序**」；注入 W11／W12／W13／W14／W15／W16／W17 覆盖；文档 §6⑦ 按切段规则重写 |
| Round A‴ B-3 / Round B‴ B-2 | F3 只认单引号动态说明符 → 双引号／模板字面量 `import("…")` 与 `require()` 完全不扫 | F3 改为**引号不敏感**并覆盖 `require`；注入 F18／F19 覆盖 |
| Round B‴ B-1 | F1 的 `:is` 正则不允许 `=` 两侧空白 → `:is = "ScPageHeader"` 绕过 | F1 改为 `=` 两侧空白可选、引号不敏感，并覆盖静态 `is="X"`；注入 F20／F21／F22 覆盖 |
| Round B‴ B-4 | `declaredPropsOf` 只解析 `defineProps<{…}>`：同文件并存 Options API `props: {…}` 或 `defineProps<T>()` 可静默新增未登记输入 | 只承认**恰好一处**字面量 `defineProps<{ … }>`；`props: {` 与非字面量 `defineProps<` 一律硬失败；注入 E7／E8 覆盖 |
| Round A‴ B-4（理论项） | 改名导入 ＋ 非入口 basename 说明符仍不可静态判定 | 维持「解析不到入口即硬失败」＋人工评审，如实登记为残限（未新增机制） |
| Round B‴ B-5（S4） | F1 走原文 → 模板注释里的 `<component :is>` 是**假失败** | F 循环改走 `stripComments`（模板注释里的标签不再是调用点）；注入 N1 锁定 STILL-PASS |
| Round B‴ B-6（S4） | 槽断言硬编码 `name="` → `<slot name='actions' />`（合法）被**假失败** | 槽位匹配改为**引号不敏感**；注入 N2 锁定 STILL-PASS |
| Round B‴ B-7（S4） | D 断言过严（`resolve…(`page`)`／字符串拼接／`let` 声明会误判） | **接受为安全方向，不改**（如实登记，不掩盖） |
| Round B‴ O-1（过程） | 复核期间观察到 3 个门禁文件被并发改动（即本轮 A‴／B‴ 修订），HEAD/tree 未动 | 第四轮修订提交后**重新冻结并重绑 L1＋L5**，再以新 head 进入第五轮复核 |
| Round A⁗ S2-1 | `_matches_recipe` 只要求「存在某一段匹配」，于是 `false && <步骤>`／`true || <步骤>` 让步骤**永不执行**而守卫仍 PASS；`|| true`／`; true` 又让**失败不传播**（A⁗ S3-1） | 形状判定收紧为「先摘掉 shell 重定向，再切段后**恰好只剩一段**」；注入 W18／W19／W20／W21／W22 覆盖（**含消息级断言**），`2>&1`／`2>/dev/null` 仍被接受为真实步骤 |
| Round B⁗ S2-1 | F1 漏掉**无引号**取值（`:is=ScPageHeader`）与 `:is.camel`／`:is.prop`／`:is.attr` 修饰符，而 Vue 对它们全部按动态组件渲染（`_resolveDynamicComponent`）；`vue/html-quotes` 只是 warn，`.camel/.prop/.attr` 无任何 lint 信号 | F1 改为**属性级**解析（不再正则扫子串），覆盖四种取值形态与修饰符；注入 F23／F24／F25 覆盖（**含消息级断言**） |
| Round B⁗ S4-1 | F1 的 `\b(?:is\|v-bind)` 命中 `data-is="X"`（普通静态属性）→ **假失败** | 属性级解析天然排除：属性名必须恰为 `is`／`v-bind`／`:is…`／`v-bind:is…`；注入 N5 锁定 STILL-PASS |
| Round B⁗ S4-2 | 注释剥离的引号状态被模板正文里**未配对**的撇号打乱（`<p>owner's</p>`）→ 其后的模板注释被当成实现（**假失败**） | 扫描器改为**模式感知**（模板正文／标签内部／`<script>`・`<style>` 原始段／`{{ }}` 插值）：正文里的裸撇号不打开引号状态，正文里的斜杠是文本；注入 N8 锁定 STILL-PASS |
| Round A⁗ S4-1 / Round B⁗ S4-3 | `/\battrs\b/` 命中普通字符串（`'no attrs here'`）与无关命名 → **假失败** | 判据拆成两个视图：具名符号在**字面量已掩码**的视图里判、模板 `v-bind="…attrs…"` 在未掩码视图里判（契约测试与守卫两侧）；注入 N6／N6g 锁定 STILL-PASS |
| Round A⁗ S4-2 / Round B⁗ S4-3 | `!\|\bprops\s*:\s*\{/` 命中 TS **类型字面量** `type M = { props: { … } }` → **假失败**；`defineProps<\n{` 也被当成非字面量 | Options API 判定限定为「所在 `<script>` 段同时声明 `export default`」；`defineProps<` 与 `{` 之间允许空白；注入 N7／N7g／N9 锁定 STILL-PASS |
| Round A⁗ S4-3 | §6 的「对象展开一律硬失败」比实现宽：`v-bind="obj"`（变量承载）并未硬失败 | §6 措辞限定为**字面量**对象展开，变量形态归入残限③（需数据流分析），不再夸大 |
| Round B⁗ S4-4 | §5 的「80 项注入，全部 CAUGHT；另有 4 项」与 §6 的「80/80 CAUGHT」口径冲突 | 统一为「95 项矩阵：84 项 CAUGHT ＋ 11 项假失败防线 STILL-PASS」（**当轮口径**；此后逐轮扩到 112／119 项，见 §5），并在 §5 给出分组计数 |
| Round A⁵ S2-1 | `_matches_recipe` 仍可被三种形态绕过：①重定向**紧贴**分隔符（`>/dev/null\|\| true`）时剥离重定向会连分隔符一起吞掉；②尾随 `&` 后台化（`<步骤> &`）后 shell 立刻以 0 退出；③Make 的 `\` 续行把 `… \` ＋ `\|\| true` 拼成一条命令，而判定只看物理行 | 重定向剥离改为不吞分隔符（`[^\s;\|&]+`）且**不丢弃空段**（尾随 `&` 即两段）；`_active_recipe_lines` 先按 Make 规则拼**逻辑行**；注入 W23／W24／W25／W26／W27／W28 覆盖（含消息级断言），`2>&1`／`2>/dev/null`／`>/dev/null` 仍被接受 |
| Round A⁵ S2-1（挂点） | 门禁挂点用**子串**判定 `gate_lines[0]`：把 unit 目标从真实前置里删掉、只留成行尾 `#` 注释仍然 PASS | 改为按**前置 token** 比对（先截掉 `#` 注释，并统计该目标的多处定义行）；注入 W29 覆盖 |
| Round A⁵ S4-1 | Options API 判定走**未掩码**视图：一句普通字符串（`const doc = "export default { props: { title: String } }"`）即触发硬失败 | 改用**整文件掩码视图**的 `<script>` 段判定；注入 N11 锁定 STILL-PASS |
| Round A⁵ S4-2 | `defineProps<{…}>` 字面量体被**平铺**扫键：嵌套对象／函数类型里的键被当成顶层 prop（假失败，且嵌套键与轴同名时让「调用方传参 ⊆ 声明面」变松） | 新增 `declaredPropNames`：只在**括号深度为 0** 处取键；注入 N12 锁定 STILL-PASS |
| Round B⁵ S2-G1 | `v-bind.prop=`／`v-bind.camel=`／`v-bind.attr=` 是 `v-bind="obj"` 的等价形态（编译器同为 `_guardReactiveProps` ＋ FULL_PROPS），两个门禁都看不见（一 token 绕过） | 对象展开判据改按**基名**（`/^v-bind(\.[\w-]+)*$/`），守卫正则改 `v-bind(?:\.[\w-]+)*\s*=`；注入 F26／F27／F28 覆盖 |
| Round B⁵ S2-G2 | `<textarea><!--`／`<title><!--` 让「模式感知」扫描器把其后**真实模板**整段当注释夹掉（RCDATA 里的 `<!--` 是文本）→ 真实调用点对门禁隐身 | 扫描器新增 **RCDATA** 模式（`textarea`／`title` 内不识别 `<!--`）；注入 F29／F30 覆盖，N14／N14g 锁定合法用法不假失败 |
| Round B⁵ S2-G3 | 尾随 `&` 使切段只剩一段 → 判真，而后台化让步骤失败不传播 | 与 A⁵ S2-1 同源修复：**不丢弃空段**；注入 W24／W27 覆盖 |
| Round B⁵ S4-G4 | D 断言只容忍单引号（`resolve…('page')`），守卫却容忍单双引号 → 两个门禁**互相矛盾** | 契约测试 D 断言同步接受 `['"]`；注入 N13 锁定 STILL-PASS |
| Round B⁵ S4-G5（说明性） | `_code_only` 会掩码模板属性取值，故 `:x="$attrs"` 这类**取值位**的 `$attrs` 不在判据内 | 不是对象展开通道（`v-bind="…"` 由未掩码视图覆盖），无需修；§6 已改为明确措辞，不再写成「任何 `$attrs` 出现即失败」 |
| Round A⁶ S2-1 | 守卫只解析 `make/frontend.mk`：被 `include` 的片段重定义 `verify.frontend.product_page_header.unit` 时，Make 取**最后一份** recipe（仅一条 warning），断言里的 recipe 被整条替换而原文件一字未动；实测 `include make/frontend_override.mk` ＋ `printf '…unit:\n\t@echo overridden\n'` → 守卫 **PASS** | 守卫改为按 `include`／`-include` 展开 **Makefile 链**（跳过 `$(…)` 动态 token），要求被守卫目标在链上**只定义一次**；注入 W33 覆盖 |
| Round A⁶ S3-1 | Make 的**失败忽略**通道完全未被检查：recipe 行 `-` 前缀（`@-esbuild …`／`-@/usr/bin/node …`）、`.IGNORE:` 特殊目标、`MAKEFLAGS += -i` 都让步骤「执行但失败不传播」，且不改 shell 形状；实测三种形态守卫均 **PASS** | `_matches_recipe` 的前缀字符集含 `-` 即判失败；新增 `_ignore_error_forms`：`.IGNORE:` 目标与 `MAKEFLAGS` 的 `-i`／`--ignore-errors` 一律失败；注入 W30／W31／W32／W34 覆盖，N15（无关开关）／N16（缺失的可选 `-include`）锁定 STILL-PASS |
| Round A⁶ S3-2 / Round B⁶ S2-1 | 冻结候选 `4ea84a5b` 在复核时刻**没有** exact-head L5 回执，而批次文档把它列为证据（复核者只能只读，无法代跑） | 由作者在 `4ea84a5b` 上重跑 L1 ＋ `make ci.local.quick` 并复验回执（`…/codex/evidence/ci.local.quick/4ea84a5b….json`，tree `96faa246…`）＝ **VERIFIED**；本轮修订产生新 HEAD 后再次重绑重跑 |
| Round B⁶ S4-1 | 切换日志末条仍写「六轮共 12 次」，与同块的「第七轮」自相矛盾 | 随本轮修订统一为「七轮共 14 次」（修订后再由 A⁷／B⁷ 验证＝16 次） |
| Round A⁶ O-1 | §6④ 只声明了 recipe 行与前置 token 两处断言，未覆盖 Make 级形态 | §6④／⑦ 已补上 `include` 链、`-` 前缀、`.IGNORE:`、`MAKEFLAGS -i` 与「动态 include 不可静态展开」的残限说明 |
| Round A⁷ S2-1 | `include` 有**静态可解析**的同义／拼写形态此前被逐物理行的 `^\s*-?include` 漏掉：`sinclude`、以 `\` 续行承载的 include、带引号路径、`$(VAR):` 变量目标名——四种都能把被守卫 recipe 静默替换而守卫 PASS，而文档却宣称「凡能静态解析的 include 链都扫」 | `_include_tokens` 改在**逻辑行**上匹配 `(?:-|s)?include`、去引号、支持一行多路径；新增 `_non_literal_targets`：链上任何 `$(…)` 目标名一律硬失败（本仓库当前为零）；注入 W35／W36／W37／W38 覆盖，N17／N18／N20 锁定 STILL-PASS |
| Round A⁷ S3-1 | `SHELL := /bin/true` 与 `.ONESHELL:` ＋尾部 no-op 同样「不改 recipe 字面内容」就让失败不传播，既未处理也未登记 | 新增 `_failure_propagation_overrides`：`.ONESHELL:` 出现即失败；`SHELL`／`.SHELLFLAGS` 与「被守卫目标只定义一次」同口径——**跨 include 链最多定义一次**，重定义即失败；注入 W39／W40 覆盖 |
| Round A⁷ S4-1 | `MAKEFLAGS` 的 `override`／`export` 前缀与续行承载形态未被匹配（`override MAKEFLAGS += -i` 等） | `_ignore_error_forms` 的正则补上 `override`／`export`／`unexport` 前缀并改在**逻辑行**上判定；注入 W41／W42／W43 覆盖 |
| Round A⁷ S4-2 | §5／§6 仍以**上一轮**的 112 项（96＋16）充当当前矩阵数，与 §5 末尾／切换日志的 119 项冲突 | 本轮统一为 **132 项（110 项 CAUGHT ＋ 22 项 STILL-PASS）**；守卫单测统一为 **63 例** |
| Round B⁷（APPROVE） | 逐条核验回执／例数／矩阵／文档／生成物／干净度／排除项七类声明**全部为真**，无夸大、无掩盖、无 S0–S4 发现 | 无需修订；另更正了作者口述的两个非文档数字（守卫单测为 924 行而非约 960 行） |

修订后重跑：`verify.frontend.product_page_header.unit`（模型 28 例 ＋ 契约测试 `call_sites=6` ＋ 守卫单测 55 例 ＋ 守卫
`adapters=3`）、`verify.frontend.localized_display.unit`、`navigation_shell`／`product_page_pattern`／
`page_pattern_reference_parity` 定向、`lint:src`（0 error／39 warning）、`typecheck:strict`、全量 `vue-tsc --noEmit`
（仍 32 条、文件集合与 base 一致；全部修订未触碰任何 `src` 文件）、L1、exact-head L5 回执，以及影子副本
**132 项**注入矩阵（110 项 CAUGHT ＋ 22 项假失败防线锁定 STILL-PASS）；守卫单测 45 → 51 → 55 → **63 例**。

**已知让步（Round B′ 确认可接受，仍如实登记）**：受管例外入口 `ContractFormPage → ContractFormProductHeader`
传约 55 条领域属性，因该入口是 `exception_implementation` 而跳过「属性 ⊆ 登记轴」比对，故其拼写错误的 prop
仍会被静默丢弃（仅靠人工评审）。收口方式应是按该入口自身 `defineProps` 做允许集校验，属领域面自己的批次。
