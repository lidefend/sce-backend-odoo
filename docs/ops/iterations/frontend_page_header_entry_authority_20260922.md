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
  `verify.frontend.product_page_header.unit`）：A 权威正式面 ≡ 登记轴；B 入口存在且委托权威、不得自建
  `header`／`h1`；C 声明转发必须真实转发；D 固定轴不得留字面量且必须由登记表解析；E 薄入口声明面 ⊆ 登记面；
  F **调用方传入属性 ⊆ 入口声明面**（D1 这一类缺陷的直接封堵）；G 直接消费权威的文件集合 ≡ 登记表；
  H 轴决策完整、id 唯一、`not_exposed`／`fixed` 必须给理由。
- **Python 守卫升级** `scripts/verify/frontend_product_page_header_guard.py`：固定档位单一来源检查（含
  「不得硬编码」）、登记表必须包含全部入口路径、入口契约测试必须存在且仍接在
  `verify.frontend.product_page_header.unit` 上（防止门禁被静默摘掉）；新增 2 条负例单元测试。

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
| 入口契约 | `product_page_header_adapter_contract_test.ts` | **PASS** `entries=4 axes=15 call_sites=4 direct_consumers=3` |
| 守卫 | `verify.frontend.product_page_header.unit` | **PASS**（Node 模型 28 例；契约测试；守卫单测 **14 例**；守卫脚本 `adapters=3`） |
| 取值呈现 | `scripts/verify/frontend_localized_display_contract_test.ts` | **PASS** `sources=686 consumers=18` |
| 静态 | `lint:src` | **PASS**（0 error／39 条既有风格 warning） |
| 类型 | `typecheck:strict` | **PASS** |

**门禁非空洞实证（影子副本 14 项注入，全部 CAUGHT）**：调用方传未声明属性／薄入口少转发声明轴／薄入口自建 `h1`／
薄入口自建 `header`／未登记的权威直接消费者／权威新增 prop 未登记／薄入口新增未登记输入／薄入口硬编码固定轴／
登记表漏某入口一条轴决策／登记表指向不存在文件／登记表重复入口（由集合等价捕获，id 唯一断言为二次防线）／
受管例外失去对权威的委托／薄入口删掉固定轴解析调用／`not_exposed` 不给理由。每例在 `/tmp` 影子副本上注入并重跑，
工作树文件未被修改。

`KanbanPage` 死属性的实证：改前 `git show de9a230d:...KanbanPage.vue` 的 `PageHeader` 绑定为 10 条属性，其中 6 条
不在 `page/PageHeader` 声明面内；改后为 3 条（`v-if`＋2 条）。门禁 F 会在任何一条重新出现时失败。

## 6. 排除项与残限

- **薄入口仍不暴露全部轴**（如 `design-system/ScPageHeader` 无 `statusSlot`）：这是本次**显式登记**的决策，
  不是收口遗漏。把它改成转发会是可见表达变化，需要单独的产品决策与运行态证据。
- **`breadcrumb`／`variant` 无任何入口转发**：同上，登记表逐条给出理由。
- **`ContractFormProductHeader` 的 365 行领域内容**（契约动作证据、原生状态栏、移动端动作结算）不在本批收口：
  它需要领域面自己的批次；本批只声明它是**受管例外**且必须继续委托权威渲染。
- **门禁不是 AST 分析**：F 用属性名与已声明 prop 比对（含 kebab／camel 归一与 `data-`／`aria-`／`v-`／`@`／`#` 放行），
  动态属性展开 `v-bind="obj"` 无法枚举——本批四个调用点均无此形态，若将来出现必须在该守卫内显式登记。
- **未做运行态浏览器抽验**：本批唯一运行期变化是「移除无消费方属性」，不改变可见表达；仍无 `local.dev` 证据。
- `verify.frontend.scene_component_bridge.guard`、`frontend_style_system_guard`（`ContractFormPage.vue` 1905>1900）与
  `verify.frontend.release_navigation_policy.guard`（菜单投影差异）在本批之前即为失败，属既有债务，本批不修、不掩盖。

## 7. 未做与下一步

- 上一批复核 A′／B′ 点名的**登记完整性**已在本批补上：`productMyWorkPresentation`／`ApiKeyManagementView`／
  `PaymentSettlementIntroduceDialog`／`BoqImportPreviewPanel`／`RelationSearchDialog` 的本地回退与格式化事实，
  已在 `frontend_localized_display_contract_test.ts` 中以**正锁**（缺一即失败）登记，任何漂移都必须重新决策。
- 仍未做（下一批候选）：①上述文件**并入权威**（需要产品措辞决定 ＋ 运行态抽验）；②`normalizeFieldType` 对非字符串
  `ttype` 的越契约输入收紧为 `string`；③登记式约束从「按文件成员放行」改为「按内容指纹锁定」；④13 个并行组件族
  权威边界声明；⑤权限判定单一权威。
- Next Step：冻结本批 HEAD → L1 → exact-head `ci.local.quick` 回执 → 两轮独立只读复核 → 显式合并授权 →
  `make pr.push`／`pr.create`／`pr.ready`／`pr.merge` → 主仓库 `make main.sync` → `make branch.cleanup.feature`。
