# 前端门禁基线对齐（P4 门禁 ＋ P2 最小抽取）

## 1. 交付结论

- 分支 `feature/frontend-stability-gate-baseline-v1`，基线 `main@de9a230d3faab18dd60a219f445f932a8af9d7f5`
  （PR #521「自定义前端字段语义单一权威」的 squash 合入点）。本轮目标由用户指令「先不合并，继续迭代，目标是前端代码稳定」确定。
- 本轮把**三条在基线上即为红的既有门禁**全部转绿，且不靠放宽门禁：一条用最小抽取（真降行数）、一条把失效的整串字面量断言
  换成**职责分离的两层**——语义下沉为单一权威并由**可执行真值表**（102 例）证明，守卫只绑**接线**（十项断言 ＋ 内容绑定，自带 262 例非空自检）、
  一条补齐权威导航清单登记（后端已发布但前端从未登记）。
- 本轮**零产品行为变更**：抽取为纯函数下沉（同一输入同一输出，已由独立复核机械复算）、导航清单为**审计清单**
  （`frontend/apps/web/src` 与 `addons/` 均无消费方，菜单由后端 XML 驱动）、桥接守卫为断言现代化＋删除抽取遗留的死变量。
- 交付口径：`批次验收完成`＝目标门禁与 quick gate 在冻结 head 全绿 ＋ 独立只读复核通过；本轮**未**推送远端、
  **未**合并（GitHub 账号 `lidefend` 被平台封禁，见 §7），故不构成 `主线集成完成`。

| 门禁 | 基线（main `de9a230d`） | 本批冻结 head |
| --- | --- | --- |
| `verify.frontend.style_system.guard` | FAIL `ContractFormPage.vue exceeds 1900 lines: 1905` | **PASS**（1892） |
| `verify.frontend.scene_component_bridge.guard` | FAIL `collaboration region must follow …` | **PASS** `checks=129` ＋ 内建自检 262/262（`checks` 已改为**运行时统计**） |
| `verify.frontend.release_navigation_policy.guard` | FAIL `finance`／`project_a_member` 投影差异 | **PASS** `roles=4 released_leaf_identities=85` |
| `verify.frontend.quick.gate` | FAIL（停在 `scene_component_bridge.guard`） | **PASS**（`[OK] verify.frontend.quick.gate done`） |

表注：`verify.frontend.quick.gate` 的前置项里只含上述**一条**桥接守卫（`make/frontend.mk:423`），
`style_system.guard` 与 `release_navigation_policy.guard` 不在该聚合目标内，此行只表示聚合目标本身在基线上被桥接守卫卡停。

## 2. 架构边界

- `Formal Product Layer`：**P4**（门禁、生成物、批次记录）；其中 `ContractFormPage.vue` 的抽取属既有 **P2** 前端表达模块的
  责任下沉，不新增产品语义。
- `Layer Target`：`frontend/apps/web/src/pages/ContractFormPage.vue` ＋ `pages/contractForm/contractRuntimeVm.ts`
  （运行态 VM 权威）、`scripts/verify/frontend_scene_component_bridge_guard.py`、
  `config/frontend/authoritative_navigation.json`。
- `Standard vs User-Specific`：全部为**平台通用机制**，不承载施工行业事实、客户偏好或低代码运行配置。
- `Why Here`：三条红灯分别是「文件行数棘轮」「协作区权威形状」「角色发布面 ⊆ 前端权威清单」，其权威本来就分别属于
  这三个文件；修复必须发生在权威所在处。
- `Why Not Elsewhere`：不新增前端渲染主链、不改契约 schema、不改字段权限／状态动作／业务取值、不改原生视图、
  数据库、Compose/profile、端口或凭据；不改后端 `ROLE_SURFACE_OVERRIDES`（后端发布面本身是权威，前端清单才是滞后项）。
- `Blast Radius`：页头／表单运行态策略上下文派生（角色码、角色码集合、能力集合、结构权威）与协作区可见性判定；
  导航清单影响 4 个角色的发布面声明（仅审计面）。`Rollback`：`git revert`（表达层与门禁层可逆提交，无数据／模式迁移）。

## 3. 变更范围

源代码（6）：

- `frontend/apps/web/src/pages/ContractFormPage.vue`：**1905 → 1892**（-13）。删除两处就地派生改为消费权威；
  移除随之不再使用的 `collectRuntimeCapabilities`／`resolveContractV2FormStructureContract` 导入；
  删除抽取后被架空、无任何消费方的 `runtimeRoleCodes` computed（-2，见 §8 修订 R4）。
- `frontend/apps/web/src/pages/contractForm/contractRuntimeVm.ts`：**169 → 262**（+93）。新增 8 个具名权威：
  运行态 4 个——`resolveRuntimeRoleCode`、`resolveRuntimeRoleCodes`、`buildContractFormPolicyContext`、
  `resolveNativeStructureAuthority`；协作区 4 个——`COLLABORATION_SURFACE_KINDS`、`isCollaborationSurfaceKind`、
  `hasCollaborationNode`、`resolveCollaborationVisibility`（见 §8 修订 R15）。
- `frontend/apps/web/src/pages/contractForm/ContractFormDriverHost.vue`：**383 → 383**（净 0）。协作区可见性不再
  就地派生：删除 `hasCollaborationNode` computed 与本地 `collaborationKind`，改为把运行态能力、抑制属性与下属区
  节点当作实参交给单一权威；模板侧 `:has-collaboration` 与 `v-if` 接线不变（见 §8 修订 R15）。
- `frontend/apps/web/scripts/contract_form_collaboration_authority_test.ts`：**新增**。导入真实模块并执行
  **102 例**真值表（全部用 `strictEqual`，故「真值对但返回类型被削弱」也算失败；第六轮起**同一张表在 `node` 域
  与浏览器域各跑一遍**，故 51 → 102），由
  `verify.frontend.contract_form_collaboration_authority.unit` 以 `esbuild --bundle --platform=node` ＋ `node` 运行，
  且已是 `verify.frontend.scene_component_bridge.unit` 的前置项（因而进入 `verify.frontend.quick.gate`／
  `verify.frontend.release.unit`）。见 §8 修订 R16／R24。
- `scripts/verify/frontend_scene_component_bridge_guard.py`：**445 → 7007 行**（+6562）。协作区断言为**十项
  职责分离的接线判定**——①委派等值（＋宿主不得自声明该权威，且必须以**字面 specifier** 从 VM 导入，
  `import { X as Y }` 与否决解构均被拒）②规则形状（第六轮起三个权威体各须**逐字等于**守卫里登记的**规范
  表达式**，只允许确定性归一化——空白、`x['m']`→`x.m`、注释屏蔽；第七轮起定位读窗本身须**自证对齐**——
  在**保长**屏蔽文本上定位、并断言 `_blank_comments_and_strings(source[span]) == blanked[span]`，不成立即报
  「misaligned read window」，而不是读回一段别处的文本）③类型清单被消费（谓词的合规文本出现在
  **字符串字面量**里不再能顶替真 body：先「屏蔽注释与字符串」定位函数体、再从**原文**读回）
  ④消费接线（区域插槽须是承载标志元素的**直接子元素**；标签扫描跳过 `{{ … }}` 插值、把 14 个 void 元素视为
  自闭合；第七轮起承载标志的元素**及其所有祖先**不得带字面死门〔`v-if="false"`／`v-show="false"`／无值
  `v-show`〕，`#collaboration` 在模板里**恰出现一次**〔多声明的空插槽会被编译器取后者、顶掉已接线的那个〕，
  且插槽区间内必须仍有 `<NativeCollaborationPanel` 起始标签、该面板也不得带字面死门；第九轮起**面板 `v-if` 须与
  `showCollaborationPanel` 等值**〔此前只测字面假值〕、**计算插槽名**〔`#[name]`／`v-slot:[name]`〕即拒；第十轮起
  死门判定改为**登记式等值清单**——载体／祖先／面板只允许带**已登记**的那几条 `v-if`，`v-show` 与未登记的
  `v-else`／`v-else-if` 一律拒绝〔`v-if="hasCollaboration && false"` 是**真实谓词但恒假**，不属字面假值，此前两个域都读不到〕）
  ⑤证明接线（目标**唯一定义**、`esbuild` 输入为**字面路径**、outfile **独占**、`node` 按 basename
  锚定；第六轮起扫描 `Makefile` ＋ `make/*.mk`〔除 `frontend.mk`〕，并拒**变量名目标**与任何含 `$(`／`${`
  的配方行）⑥内容绑定（sha256）⑦页面侧两属性的**属性表 ＋ 元素级 ＋ 逐处表达式**绑定（拒绝任何 `v-bind`）
  ⑧宿主／证明**模块同一性**⑨**模块纯净性**（第七轮建立、第八轮补全：整模块不得读运行环境全局／`import.meta`；
  顶层语句只允许**真实模块用到的形状**〔`import`／`export`／`type`／`interface`／`function`；`declare`／`abstract`／
  `async` 第八轮移出——`abstract class` 的静态初始式同样在加载期运行〕；**`export` 前缀**的 `enum`／`class`／
  `namespace`／`abstract class`／`declare` 按**加载期声明**拒绝〔成员与静态初始式同样是加载期求值〕；**运行时
  `import` 的 specifier 须落在已复核清单内**〔类型导入被擦除，豁免〕，因为具名 import 与副作用 import 执行的是
  同一段第三方加载期代码；第九轮起 specifier 改从 **`from` 子句**读取并拒**尾随文本**，模块**无法切分即拒**
  〔未闭合的注释／字符串／模板〕，**正则字面量**按一等不透明 span 处理〔`return /[']/g` 里的引号曾开启幻影字符串〕，
  第十轮起**语句切分**补上 `(`／`[`／`{` 开头语句、ASI 续行与顶层 `}` 后的后随字符三类空洞，**已复核 import 的文件
  内容会被真实读取**并走完整运行时 import 闭包〔此前只比对 specifier 字符串，把门控放进 `./valueUtils` 即可一字不改
  地让规则在浏览器域失效〕；
  顶层绑定只允许「由字符串字面量组成的类型清单」这一种初始式；注释屏蔽改为**字符串
  感知**〔引号里的 `//`／`/*` 不再吞掉其后的语句〕）⑩**偏移保长自证**（第七轮：
  对 `form_host`／`contract_form_vm`／`contract_form_page`／`frontend_makefile` 与一份混注释／字符串／括号访问的
  样本断言 `len(_blank_comments_and_strings(t)) == len(t)`）。
  语义本身交给上一个（可执行）测试；`checks=63` 硬编码改为运行时统计（当前 **129**，内建自检 **260**＝宿主／模块 182 ＋ 页面 21 ＋ import 闭包 57）。
   **据实登记**：本轮增长使其越过 3000 行阈值、由 `split_plan_queue.md` 的 P2 升为 **P1** 项（按注册目标机器生成，未上调任何锁）；
  拆分层已清晰，列入 §7 下一步。见 §8 修订 R15–R19／R22–R49。
- `make/frontend.mk`：新增 `verify.frontend.contract_form_collaboration_authority.unit` 目标，并把该目标加入
  `verify.frontend.scene_component_bridge.unit` 的前置项（相对基线 `+6/−1` 行）。

声明与生成物（5）：`docs/engineering_convergence/complexity_budget_report.md`（守卫 445 → 7007 行）、`docs/engineering_convergence/split_plan_queue.md`（同一原因使其入队列并因 `>= 3000` 行升至 **P1**，两件均机器生成）、
`docs/frontend_productization/rendering-detail/component-driver-takeover-inventory-v1.json`（inputDigest 刷新），
以及本轮按注册目标 `refresh.frontend.rendering_detail.inventory` **二次刷新**的
`component-professionalization-inventory-v1.json` 与 `visual-projection-inventory-v1.json`
（**仅** `inputDigest`／`sourceIdentity` 变化，`surfaces` 逐条不变；起因见 §6 与本表 R27）。
上一轮进入候选的 `config/frontend/authoritative_navigation.json`（+3 条目）、`split_plan_queue.md`、
`p4_p0_03_contract_form_split_evidence.md`（行数锁 1905 → 1892）在本轮未再变动。

提交链（线性、无 merge；计数以 `git rev-list --count de9a230d..HEAD` 为准；截至第十八轮冻结 `e4435c77` 实测 **46 笔**，
第十九轮的三笔收口提交紧随其后）：

**第一批 10 笔**（本文件首次落库时的批次）：`de9a230d → 66fbf1bb → 9a26b257 → 2437519d → 23928265
→ a5525317 → 50faccf5 → ce9450ed → c28a03c6 → 9a671cc8`（`9a671cc8` 处实测计数为 9，本文件首次落库的提交为第 10 笔）。

**其后逐轮复核的收口提交**（按 `git log --oneline --reverse de9a230d..e4435c77` 实测）：第五轮
`74160041`／`c7710b88`／`f2a94f61`；第六轮 `45466b62`／`5e3120dc`；第七轮 `c3b9365f`／`4e9e2fc8`；
第八轮 `f686a811`／`0faf569a`；第九轮 `db734ea5`／`47b9a631`；第十轮 `84724fbd`／`305245f9`；
第十一轮 `1390ace7`／`956dbcbd`；第十二轮 `28e205c6`／`379163ec`；第十三轮 `5193d2fd`／`ab3fa59f`／
`cfa81dd7`／`379829c4`；第十四轮 `e6d3b3ab`／`48aa03cc`／`0692078d`；第十五轮 `50d672a7`／`a5d6afa5`／
`9e5402c3`；第十六轮 `4447cfa6`／`fc460639`／`0137b95b`；第十七轮 `db0c6042`／`36315a00`／`f944b313`；
第十八轮 `b8a06090`／`41559f60`／`4b693076`／`e4435c77`。
**第十九轮据实更正**：本条此前只列第一批 10 笔、并把「本文件所在提交」写成链尾，与 `git rev-list --count` 的实测
不符（R108）。

`66fbf1bb`（运行态权威抽取 ＋ 协作区守卫加固）与 `9a26b257`（导航叶子补登 ＋ 生成物刷新）是本批的前两个功能提交；
`c28a03c6` 是**第三个功能提交**（协作区判定下沉为单一权威 ＋ 可执行真值表 ＋ 守卫接线化）；`23928265`／`50faccf5`
为断言扩展与自检矩阵内建；`2437519d`／`a5525317`／`ce9450ed`／`9a671cc8` 为批次记录与逐轮复核后的修订；
本文件所在提交（第 10 个）承载第四轮复核对**接线语义**的收口（委派等值、插槽父子绑定、证明执行绑定、内容绑定）
与其文档。

## 4. 统一后的口径

1. **`ContractFormPage.vue` 行数棘轮以真实抽取满足，未上调**。抽取内容为两处纯派生：
   运行态角色码／角色码集合／能力集合／策略上下文与结构权威读取。两把锁都未上调：守卫 `SIZE_LIMITS` 的 `1900` 未动，
   `docs/engineering_convergence/complexity_baseline_lock.json` 的 `max_lines`（`5947`，另一把更宽松的限制型锁）也未动；
   `p4_p0_03_contract_form_split_evidence.md` 的行数锁按注册目标刷新为 1892，且该值由
   `scripts/ci/verify_contract_form_split_evidence.py` 机器强制（文档必须等于真实行数），不是人工改小。
2. **协作区（collaboration region）不变量**：可见性＝`运行时能力(props.showCollaborationPanel)` **或**
   `下属节点权威`（仅由 `!props.suppressCollaboration` 抑制）。第二轮复核（A²／B²）已经指出：**用文字令牌证明不了这条
   不变量**——`A || B` 在 `B ≡ 常量` 时是空断言；第三轮复核（A³／B³）用 15＋13 个新向量再次复现：把断言从 1 个位点
   扩到 4 个位点只是把绕过面挪到新的位点，且新增的消费接线断言是对**未剥 HTML 注释**的整份文件做子串检查，一个
   `<!-- … -->` 诱饵即可复位（详见 §8 的 R15）。因此本轮把这条不变量改成**职责分离的两层**：

   **第一层 · 语义由执行证明（唯一权威）**。判定规则下沉到 `contractRuntimeVm.ts` 的三个纯函数
   （`isCollaborationSurfaceKind`、`hasCollaborationNode`、`resolveCollaborationVisibility`），
  由 `verify.frontend.contract_form_collaboration_authority_test.ts` 导入**真实模块**执行 **102 例**
  （第六轮起 `node` 域 ＋ 浏览器域各一遍：51 × 2）：
   类型谓词真值表 13 例（`chatter`／`activity`／大小写与空白变体／`note`／`audit`／空串／纯空白／`0`／`null`／
   `undefined`／对象）、节点权威存在性 9 例、`能力 × 抑制 × 节点` 可见性 25 例，外加 4 条**承重断言**——
   节点权威须能单独点亮、抑制须能单独熄灭、能力须是**替代**而非条件、非协作节点不得点亮。
   该测试的鉴别力由**变异实测**确立（`/tmp/r24t` 影子＝`git archive 9a671cc8` ＋ 覆写证明，修改真实模块后重跑）：
   谓词取反、清空类型清单、谓词体退休为 `return false`、`.some`→`.every`、`||`→`&&`、去掉抑制门、读错字段、
   丢掉 `toLowerCase`、节点权威返回非布尔、能力未布尔化、抑制门升级为「连能力也一起门控」——**11 个真实变异
   全部被该测试报错**；1 次**语义等价改写**（`!Number(input.suppressed)`）正确通过（非漏检）。

   **第二层 · 接线由静态守卫绑定**。`scripts/verify/frontend_scene_component_bridge_guard.py` 不再尝试用令牌证明
  语义，只绑定**接线**（第七轮后为十项，完整枚举见 §6）；最早的**五件**核心如下，五件齐备才 PASS：
   ①**委派等值**：`hasCollaboration` 仍是 `computed`，且其实参**归约后必须恰好等于**指向单一权威的委派式
   （能力 `props.showCollaborationPanel`／抑制 `props.suppressCollaboration`／节点
   `props.renderModel?.zones.subordinate`）；只做确定性脱糖（冗余括号、可选返回类型标注、仅含 `return` 的块体），
   因此取反、逗号丢弃结果、尾随 `|| false`、`? :` 常量化都**不再**能靠保留令牌通过；宿主也不得自行声明该权威。
   ②**规则形状**：权威体须仍以 `||` 连接 `Boolean(input.capability)` 与受 `!input.suppressed` 门控的节点权威，
   且须仍调用节点权威。
   ③**类型清单被消费**：`COLLABORATION_SURFACE_KINDS` 须仍声明 `chatter` 与 `activity`（**可增不可减**），
   且类型谓词函数体须**读取**该常量并做 `.includes(` 成员判定——把清单写成惰性数据即失败。
   ④**消费接线**：**先屏蔽 HTML 注释（`<!-- -->`）与 `<style>` 块，并丢弃 `<script setup>` 段**，再在**真实起始
   标签**上判定——`ObjectTaskPage` 起始标签须带 `:has-collaboration="hasCollaboration"`，`#collaboration` 模板
   起始标签须带 `v-if="hasCollaboration"` 且**位于该元素的区间之内**（插槽必须仍是它的子节点）；模板里**任何一处**
   `:has-collaboration="…"` 都不允许取 `hasCollaboration` 以外的值。
   ⑤**证明接线**：可执行测试须仍被 `make` 目标的配方**真正打包并执行**——该目标须含 `esbuild`（带
   `--bundle --platform=node --outfile=…`）＋ 对同一 outfile 的 `node` 调用行，且该目标须仍是
   `verify.frontend.scene_component_bridge.unit` 的前置项；只留路径不留执行（例如换成 `@echo`）即失败。
   ⑥**内容绑定**：可执行证明文件另有 **sha256 内容绑定**——改动证明（哪怕把断言改成 no-op）必须连同守卫里的摘要
   一起改。它绑的是证明**源码**；配方层另由 ⑤ 绑定「被执行的正是那个字面路径与它独占的 outfile」，
   两层合起来才支撑「运行中的证明就是被复核的那份证明」，**残余面**（`$(VAR)` 展开、`esbuild` 同名别名、
   make 之外的手工执行）见 §6 与 R31，不再声称单靠 ⑥ 即可机器核对。

  守卫自带 **262 例自检矩阵**（63 接受 ＋ 199 拒绝）并在每次运行执行；宿主／模块层 183 例（37 接受 ＋ 146 拒绝）、
  页面层 21 例（7 接受 ＋ 14 拒绝，第六轮新增，此前页面侧无矩阵）、import 闭包 58 例（19 接受 ＋ 39 拒绝，第十轮新增，第十一轮／第十二轮／第十三轮／第十四轮／第十五轮／第十六轮／第十七轮／第十八轮／第十九轮／第二十轮扩围）；判据是「同一断言在每个形状上读对期望值」。

3. **角色发布面口径**：后端 `ROLE_SURFACE_OVERRIDES` 的发布集合必须**逐个**出现在前端
   `config/frontend/authoritative_navigation.json` 的 `leaf_keys` 且 `expected_count` 相等。本轮补齐 3 个**后端已在
   PR #497（`cefeff1f`，2026-09-19）发布、前端从未登记**的叶子（菜单定义本身自 PR #171／`6f86a983` 起即存在）：
   `menu_sc_product_current_account_v1`（`sc.current.account.workspace`）、
   `menu_sc_product_company_project_refund_v1`（`sc.company.project.refund.workspace`）→ `finance`（43 → 45）；
   `menu_sc_product_team_loan_deduction_v1`（`sc.team.loan.deduction.workspace`）→ `project_a_member`（9 → 10）。
   发布身份总数 82 → **85**。三个菜单的来源 `groups` 分别是 `…group_sc_cap_finance_user`／`finance_manager` 与
   `…group_sc_cap_project_user`／`project_manager`，与所属角色的能力面一致，故按「后端权威正确、前端清单滞后」登记，不反向改动后端。

## 5. 验证证据

- `make verify.frontend.quick.gate` **PASS**（`[OK] verify.frontend.quick.gate done`，退出码 0）；同一命令在基线
  `main@de9a230d` 上 **FAIL**（停在 `verify.frontend.scene_component_bridge.guard`）。
  该门禁在上一版 head 上实为**红**（`verify.frontend.rendering_detail_state.unit` 两件生成物陈旧），
  本轮按注册目标二次刷新后复跑才为绿——更正见 R27。
- `python3 scripts/verify/frontend_style_system_guard.py` **PASS**（`hardcoded_color_refs_max=0`，
  `phase0_variable_classification=131`）。
- `python3 scripts/verify/frontend_scene_component_bridge_guard.py` **PASS**
  `checks=129 collaboration_self_check=262`。**`checks` 已是运行时统计**（`require()` 调用计数器，R18 落地），
  不再是有静默漂移风险的历史字面量；`collaboration_self_check` 同时把自检矩阵规模暴露成运行时数字
  （当前 **260** ＝ 宿主／模块 182 ＋ 页面 21 ＋ import 闭包 57）。
- **可执行证明**：`verify.frontend.contract_form_collaboration_authority.unit` →
  `[contract_form_collaboration_authority] PASS cases=102`（退出码 0）。第六轮把**同一张真值表**在
  `node` 域与**浏览器域**各跑一遍（安装 `window`／`document`／`navigator`／`self` 后再跑，末尾断言全局被
  恢复），故 51 → **102**：一条环境门控的权威改写只要在两域里给出不同答案即被该测试抓住（实测
  `/tmp/r35c1` 影子：canonical `rc=0`；`typeof window` 门控与 `globalThis['window']` 门控各 `rc=1`）。
- **该证明的鉴别力（变异实测，`/tmp/r24t` 影子＝`git archive 9a671cc8` ＋ 覆写证明文件，改真实模块后重跑）**：
  11 个**真实变异全部报错**——谓词取反、清空类型清单、谓词体退休为 `return false`、`.some`→`.every`、
  `||`→`&&`、去掉抑制门、读错字段、丢掉 `toLowerCase`、节点权威返回非布尔、能力未布尔化、
  抑制门升级为「连能力也一起门控」；1 次**等价改写**（`!Number(input.suppressed)`，在声明类型 `boolean` 上等价）
  正确通过。**（第五轮补充登记）** 另测 2 个「证明 PASS、守卫按形状收紧 REJECT」的变异：类型谓词后追加
  **不可达**的 `return false;`（语义未变），以及上条等价改写——两者证明均 PASS，守卫分别以「须是单一 `return`」与
  「须仍读到 `!input.suppressed`」拒绝。即**证明断言语义、守卫断言形状**，两侧口径不同，均已如实登记。
  **（第六轮）** 证明改为**两域各跑一遍**（`node` 域 ＋ 浏览器域，共 102 例），故「node 下看得见、浏览器下看不见」
  的环境门控**不再可能两层同绿**：两侧必有一侧读出不同的可见性真值（实测 `/tmp/r35c1`：canonical `rc=0`，
  `typeof window` 门控 `rc=1`，`globalThis['window']` 门控 `rc=1`）；同时守卫把三个权威体从「黑名单禁探针」
  改为**整表达式等值**，探针族**结构性**被拒而非逐拼写枚举。
- **接线守卫的鉴别力（`/tmp/r24` 影子内对真实宿主／模块／Makefile 注入，跑真实守卫与真实证明）**：
  **16 个接线攻击向量全部被拒**（基线 PASS）——委派取反、逗号丢弃结果、尾随 `|| false`、`? :` 常量化、
  wrapper 丢结果、宿主自行遮蔽该权威、绑定改字面 `false` ＋ JS 注释诱饵、绑定改字面 `false` ＋ `<script>` 内
  字符串诱饵、插槽移出承载标志的元素区间、承载元素改名、证明被换成 `@echo`、删掉 `node` 执行行、
  节点权威改读 `zones.primary`、委派被注释掉等。另有一个**新发现**的向量——插槽改名 ＋ 元素**内**的 HTML 注释
  诱饵（`<!-- <template v-if="hasCollaboration" #collaboration /> -->`）——已作为自检矩阵用例覆盖，见 §6。
  第三轮登记的 **A³-V9**（用 `watchEffect` 在运行期把标志强制为 `false`）在第四轮**实测为 PASS，但已证明
  不构成旁路**：`hasCollaboration` 是只读 `computed`，真实 Vue 运行时下该写入触发
  `Write operation failed: computed value is readonly` 且值不变（独立复算：覆写后仍为 `true`）——见 §6 的更正登记。
- **第一轮／第二轮已登记向量的回归**：`&& false`、`=== undefined && true`、`||`→`&&`、节点权威只在注释里、
  字面 `false` 而令牌在行注释里、节点权威只是字符串字面量、第三个操作数、标志不再传给协作区、协作区不再被门控、
  `.some`→`.every`、类型清单删项——在本轮的新断言下**全部仍然失败**；把 `resolveCollaborationVisibility` 调用
  回退成初版「三令牌子串」写法时 **262 例自检矩阵必然报错**并点名形状。
- **第五轮新增向量的实测（`/tmp/r28` 影子＝`git archive 74160041` ＋ 覆写本轮守卫与证明，跑真实守卫）**：
  **18/18 按预期**＝基线 PASS ＋ 1 个形状接受 ＋ 16 个攻击被拒——V21 委派块体忘写 `return`（**本轮真 bug**）、
  V08 同前缀兄弟文件顶替证明、V09 目标二次定义（第二条 recipe `@true`）、V13 `/tmp/b5/fakenode` 假执行、
  V23 从 `./collaborationVisibilityShim` 导入恒 false 权威、S2-F1 outfile 在打包与执行之间被 `cp` 覆盖、
  S2-F1b 第二条 bundling 覆盖同一 outfile、S2-F2 `void <常量>;` ＋ ghost 清单、S3-F3 插槽嵌进 `<CanonicalActionBar>`、
  V06 属性字符串里的同名标签诱饵 ＋ 插槽外移、V01 谓词体 `if (typeof window !== 'undefined') return false;`、
  V02 规则体在 `return` 内按环境三元切换、V03b／V03c 页面 `:suppress-collaboration` 改字面／删除、
  V04a／V04b 页面 `:show-collaboration-panel` 删除（旧画布仍带同名绑定）／改字面。接受的形状是**块体仅含
  `return` 的委派**（与 R22 的脱糖口径一致）。
- **第六轮新增向量的实测（`/tmp/r35_verify.py`／`/tmp/r35_verify2.py`：用**守卫自身的函数**在内存里做变异，
  不落任何文件；修复后重跑）**：修复前 **LEAK**、修复后 **REJECT** 的向量共 13 个——M01 `globalThis['window']`、
  M02 `typeof(self)`、M03 `typeof(window)`、M04 `('window' in globalThis)`、M06 用**字符串字面量里的合规 body**
  顶替真 body、M11 `{{ '' /* '</CanonicalActionBar>' */ }}` 假闭合、M19 `as _rcv` 别名（调用点原文不动）、
  M20 单引号字面量 ＋ 双引号 decoy、M22a／M22b `v-bind` 展开（`collabAttrs`）、M26 `$(VAR)` 目标二次定义、
  M29 `cp attacker.mjs $(VAR)` 覆盖 outfile、M31 `--outfile=$(VAR)`、M34 仅**提及** outfile 的额外配方行。
  **据实登记一处与复核报告不一致**：M18（`import * as _shim` ＋ `const { resolveCollaborationVisibility } = _shim`）
  按 B⁶ 描述是 LEAK，但实测**修复前就已被**「宿主不得自声明该权威」拒绝——非本轮修复项，已在 §8 登记。
  **过严面翻转**（第五轮守卫 `f2a94f61` 实测被拒、本批**接受**）实际为 **2 个**：M14（合法的 `{{ 1<b }}` 插值
  写在插槽前）与 M35（`<br>` 空元素写在插槽前；`<img …>` 等同类的 HTML void 元素同理）——两者已成为矩阵的接受用例。
  **M35b（`<br />`）是「对照」而非翻转**：它**修复前就已接受**（第五轮读取器已按 `tag.rstrip().endswith("/>")`
  把 `/>` 视为自闭合），第七轮实测复核为 `OLD=GREEN`／`NEW=GREEN`，此前与 M35 并列登记不精确，现更正。
  另：M31 实测为 **REJECT**，故 §6 旧文里「`--outfile=$(VAR)` 不在守卫判据内」的登记已不成立（见下）。
- `python3 scripts/verify/frontend_release_navigation_policy_guard.py` **PASS** `roles=4 released_leaf_identities=85`；
  `python3 -m unittest …/test_frontend_release_navigation_policy_guard.py` **OK**（5 例）。
- 清单消费方回归：`product_finance_center_wave1_guard.py` **PASS**；`frontend_product_page_header_guard.py` **PASS**
  `adapters=3`；`PYTHONPATH=scripts/verify unittest test_frontend_release_audit test_frontend_release_evidence_bundle
  test_frontend_release_navigation_policy_guard` **Ran 20 tests OK**；`scripts/ci/enforce_complexity_baseline_lock.py`
  **PASS** `checked=11`。
- `make ci.delivery.freeze.prepare` **PASS** 且 `ci.generated_evidence.preflight` **PASS**
  （`all content-bound generated evidence is current`）；`component_driver_takeover_inventory` **PASS**
  `required=35 missing=0`；`contract_form_split_evidence` **PASS** `lines=1892`；`test inventory is current (1374 entries)`。
- 类型与风格：`typecheck:strict`（门禁口径）**PASS**；`typecheck`（`vue-tsc --noEmit`，非门禁口径）本分支与基线
  **同为 32 条 / 15 文件**、错误文件与分布逐条一致，且**本批改动的 `ContractFormDriverHost.vue` 与
  `contractRuntimeVm.ts` 均无错误**；`lint:src` **0 error / 39 warning**（与既有记录一致）。

#### 5.1 第二／第三轮复核复算过的事实（供下游直接引用）

| 事实 | 复算结论 |
| --- | --- |
| 基线三条门禁为红，且红因如 §1 所述 | 基线影子实跑：bridge guard `FAIL collaboration region must follow …`；nav guard `FAIL`（finance／project_a_member 两条，方向为后端超集、前端滞后）；style guard `FAIL 1905 > 1900` |
| 导航补登 3 条是后端事实而非凑期望值 | 基线 `de9a230d` 的 `core_extension_policy_maps.py` 第 36／389／390 行已列 3 个 xmlid，`menu_product_contract_completion_v1.xml` 第 447／451／452 行已定义菜单，`groups` 与 §4-3 一致；`ROLE_SURFACE_OVERRIDES` 本批未改 |
| 抽取真零行为变更 | 机械等价复算（含 `undefined`／`null`／`''`／空白／大写／非数组／含 `null`／`0`／truthy 非数组）`mismatches=0`，异常类型亦逐字一致 |
| 未上调任何行数锁／复杂度锁 | `git diff de9a230d..HEAD -- scripts/verify/frontend_style_system_guard.py` 与 `-- docs/engineering_convergence/complexity_baseline_lock.json` 均为空；`SIZE_LIMITS[ContractFormPage.vue]` 两侧 1900 |
| 清单不改运行态 | `frontend/apps/web/src` 与 `addons/` 均无 `authoritative_navigation` 消费方（仅审计脚本），菜单由后端 XML 驱动 |
| 封禁说法 | `git ls-remote origin` → `remote: Your account is suspended.`（HTTP 403） |


## 6. 排除项与残限

- **既有失败（本批不修、不掩盖）**：`scripts/verify/frontend_release_audit.py` 在基线 `main` 与本分支均 FAIL。
  失败原因**不是**缺 `artifacts/frontend-release-audit/report.json`——该文件是守卫**自己写出**的产物
  （`main()` 末尾无条件写入，且在配置的受管输出目录里），实际 `missing_evidence=[]`、`blocking_failures` 为
  7 个 `EVIDENCE_SHA_MISMATCH:*`（分节上游证据仍绑定更早的提交：`static.json` 为 `fad9a110…`，
  `frontend-page-identity/`、`frontend-delivery-hardening/` 等为 2026-09-11 的旧件）。正确表述是
  **「上游受管运行态证据未按本 head 重建」，本批未重建**。
  （附带登记：该脚本每次运行都会覆写自身输出，**不是**只读守卫；且 A³-F7 实测其 `--output` **无法**重定向到
  仓库外（内部 `relative_to(ROOT)` 对 `/tmp/…` 抛 `ValueError`），因此连「不覆写仓库内产物地复现一次」都做不到。
  本批不动它，列入 §7 待办。）
- **本批顺带转绿但根因早于本批**：`verify.frontend.rendering_detail_state.unit` 在基线 `main` 上即为红，可复现的
  基线签名是其中两步 `--check` 陈旧——`generate_frontend_rendering_detail_inventory.py --check`
  （`FAIL stale=…/component-professionalization-inventory-v1.json`）与
  `generate_frontend_visual_projection_inventory.py --check`（`FAIL stale=…/visual-projection-inventory-v1.json`）；
  同组的 `frontend_inline_state_guard.py`、`frontend_rendering_detail_state_guard.py` 与
  `generate_frontend_official_design_alignment_inventory.py --check` 在基线与本批均 **PASS**
  （`internalVendorSelectorGapCount: 0`）。本批前端源码改动使该家族的指纹绑定生成物必须刷新
  （注册目标 `refresh.frontend.rendering_detail.inventory`），刷新后三项全部 PASS。
  **（第四轮更正）** 该次刷新只做到 `23928265`；`c28a03c6` 再次改动宿主 `.vue`（协作区判定下沉）后，
  `component-professionalization` 与 `visual-projection` **两件又被置为陈旧**，故本批 head 上这条门禁实为**红**、
  而旧版正文误记为绿（见 R27）。本轮按同一注册目标**二次刷新**，复核 `git diff` 为**仅** `inputDigest`／
  `sourceIdentity` 变化、`surfaces` 逐条不变（即无内容漂移），复跑 `verify.frontend.quick.gate` **PASS**。
  该族在**更早那次**刷新（`9a26b257`）里出现的**非本批**内容漂移，是**既往提交遗留的陈旧生成物**被按注册流程重建：
  `visual-projection` 的
  11 个条目 digest 中只有 `pages/ContractFormPage.vue` 属本批改动，其余 10 个文件的最后一次改动都停在基线
  `de9a230d`；`component-professionalization` 里某组件 `stateTypes` 补登记 `empty`，来源是该文件**在基线版本中就已存在**
  的 `FIELD_VALUE_EMPTY_TEXT`。已如实登记，不声称由本批源码改动产生。
- **守卫边界（诚实登记）**：第三轮复核（A³／B³）证明「令牌齐全但语义被破坏」在**每一位点**都会重现——文本形状
  门禁**无法**证明语义。本轮据此把协作区断言拆成**两层**，并如实登记每层的覆盖与不覆盖：
  - **第一层（语义，可执行）**：`contract_form_collaboration_authority_test.ts` 导入**真实模块**，对四个权威
    （`isCollaborationSurfaceKind`／`hasCollaborationNode`／`resolveCollaborationVisibility` 与类型清单常量）
    跑 **102 例真值表**，由 `verify.frontend.contract_form_collaboration_authority.unit` 以
    `esbuild --bundle --platform=node` ＋ `node` **实际执行**。它是唯一声称「语义正确」的一层。
    **（第六轮）** 同一张表在 **`node` 域与浏览器域各跑一遍**（装／卸 `window`／`document`／`navigator`／`self`
    后复跑并断言全局被恢复）：三个权威体**调用期**内的环境探针**不再可能两层同绿**。**（第七轮据实更正）**
    该结论**不覆盖加载期**——真值表的浏览器域是在 `import` **之后**才装上全局，故模块**顶层**求值的门控两个域
    都没跑到（§8 R42 的 F2 已实测证伪了原来的全称表述）。加载期门控现由第二层⑨（模块纯净性）覆盖。
  - **第二层（接线，文本形状）**：守卫只绑定**接线**、不再重述语义，共**十项**断言（含一项内容绑定）——
    ①**委派等值**（`hasCollaboration` 仍是 `computed`，其实参归约后**必须恰好等于**单一权威的委派式；宿主
    不得自行声明该权威，且必须从 VM 导入它，**且 `import { X as Y }` 这类别名与非 `import` 的 `const { X } = …`
    解构都被拒绝**）；②**规则形状**（**（第六轮改为整表达式等值）** 三个权威体各自须**逐字等于**守卫里登记的
    规范式——`Boolean(input.capability) || (!input.suppressed && hasCollaborationNode(input.nodes))` 等；只有
    确定性归一化〔空白、`x['m']`→`x.m`、注释屏蔽〕可省，故任何**运行期环境探针**结构性地被拒；**（第七轮）**
    定位本身也须自证——`_body_window` 在**保长**屏蔽文本上定位，读回原文前先断言
    `_blank_comments_and_strings(source[span]) == blanked[span]`，不成立即报 `misaligned read window`
    而不是把别处的文本当成权威体）；③**类型清单被消费**
    （`COLLABORATION_SURFACE_KINDS` 须声明 `chatter`＋`activity`，可增不可减，且谓词体须**读取**该常量并含
    `.includes(`；**（第六轮）** 谓词体的合规文本出现在**字符串字面量**里不再能顶替真 body——函数体先按
    「屏蔽注释与字符串」定位、再从**原文**读回）；④**消费接线**
    （`ObjectTaskPage` 起始标签须带 `:has-collaboration="hasCollaboration"`，模板里**每一处**
    `:has-collaboration` 都不允许取别的值（**第七轮起宿主属性也按属性表读，两种引号都接受**——此前按双引号
    正则读，单引号写法是被误拒的过严面，见 §8 R44／R46），`#collaboration` 模板起始标签须带 `v-if="hasCollaboration"`
    且**其最近严格包含元素必须就是那个 `ObjectTaskPage`**——是**直接子元素**，不只是落在区间内〔真实宿主在同一
    元素里还渲染 `<CanonicalActionBar>`，嵌进子组件的插槽编译 0 error 却填不满槽位〕；**（第六轮）** 标签扫描
    跳过 `{{ … }}` 插值段〔否则 `{{ '' /* '</CanonicalActionBar>' */ }}` 会被当假闭合〕并把 void 元素
    〔`<br>`／`<img>`／`<input>` …〕视为自闭合；**（第七轮）** 承载标志的元素**及其所有祖先**都不得带**字面死门**
    〔`v-if="false"`／`v-show="false"`／无值 `v-show`，含 `!true`／`!!false`／`!1`／`!!0`／`null`／`undefined`／
    `void 0`／空串字面量〕，`#collaboration` 在模板里**恰出现一次**〔多声明一个空插槽，编译器取后者，已接线的
    那个被静默顶掉〕，且插槽区间内必须仍有 `<NativeCollaborationPanel` 起始标签、该面板也不得带字面死门；
    **（第九轮）** 该面板的 `v-if` **须恰好等于** `showCollaborationPanel`〔此前只测**字面假值**，`v-if="!hasCollaboration"`
    ／`v-if="NaN"` 这类**真实谓词但恒假**的写法都过——插槽已接线而面板恒不渲染〕，且载体元素区间内出现**计算插槽名**
    〔`#[name]`／`v-slot:[name]`，取什么名字只有运行时才知道〕即拒；**（第十轮）** 死门判定从**字面假值黑名单**改为
    **登记式等值清单**——载体、其**全部祖先**与面板各自的 `v-if`／`v-else-if` 只允许是**已登记**的那几条（宿主侧
    `!preserveAuthoritativeBusinessSections`、`renderModel.identity.presentationMode === 'task'`、`hasCollaboration`、
    `showCollaborationPanel`；页面侧 `!showCurrentFormFieldConfigScope` 与那条 page-section 表达式），
    其余一律拒绝，`v-show` 在整条路径上**一概**拒绝，`v-else` 只允许出现在**已登记的元素**上
    〔`v-if="hasCollaboration && false"` 这类**真实谓词但恒假**的写法此前不是「字面」，因此两个域都读不到，
    B¹⁰ 用真 SSR 实测 `panel=ABSENT` 而门禁恒绿〕）；⑤**证明接线**（该目标在
    `make` 里**唯一**定义，`esbuild` 的输入是**字面路径**且逐字等于证明文件、outfile 在配方里**只出现在两行**
    〔bundling ＋ 执行〕、执行行按 basename 锚定为 `node <outfile>` 且在 bundling 之后，且仍须是
    `verify.frontend.scene_component_bridge.unit` 的前置项；**（第六轮）** 扫描面扩到 `Makefile` ＋
    `make/*.mk`〔除 `frontend.mk`〕，且**变量名目标**与任何含 `$(`／`${` 的配方行一律拒绝）；⑥**内容绑定**（证明文件的 sha256 记在守卫里，
    改动证明必须同时改摘要）；⑦**页面侧绑定**（`ContractFormDriverHost` 起始标签须同时带
    `:show-collaboration-panel="showNativeCollaborationPanel"` 与 `:suppress-collaboration="dispatchContextCollaboration"`，
    模板里**每一处**同类动态写法都不得换成别的表达式，另绑两处页面侧权威派生；**（第六轮）** 页面标签改按
    **属性表**解析〔两种引号 ＋ HTML 实体解码〕，宿主标签上出现**任何 `v-bind`** 即拒绝，每个属性须**恰好**绑
    到那一个页面权威）；⑧**模块同一性**（宿主与证明的
    import specifier 各自解析后必须落在同一个真实模块文件）；⑨**模块纯净性**（**第七轮新增、第八轮补全**：整模块不得出现运行
    环境全局或 `import.meta`；每个**顶层语句**须属声明白名单〔只留真实模块用到的形状，`declare`／`abstract`／
    `async` 第八轮移出〕；**`export` 前缀**的 `enum`／`class`／`namespace`／`abstract class`／`declare` 按**加载期
    声明**拒绝；**运行时 `import` 的 specifier 取 `from` 子句里那一个**〔**第九轮**：此前取的是读窗内**最后一个**字符串
    字面量，`import … from './collaborationPoison' /* './valueUtils' */` 靠注释里的诱饵过闸，而 TS 丢弃注释、真正加载的是
    前者〕，不在已复核清单内即拒、specifier 之后**还有非空文本**即拒〔守卫判不出到底加载哪一个〕，类型导入豁免；
    **（第九轮）** 模块**无法切分即拒**——出现**未闭合**的字符串／模板／块注释 span 时直接失败，而不是继续读一个
    「并非真实存在」的窗口；**正则字面量**按**一等不透明 span** 处理（`return /[']/g` 里的引号曾开启幻影字符串、吞掉其下
    顶层门控）；顶层绑定只允许「由字符串字面量
    组成的类型清单」这一种初始式；注释屏蔽为**字符串感知**；**（第十轮）** 语句切分补上三类空洞——`(`／`[`／`{`
    开头的顶层语句**不再被栈分支吃掉**（`{ poison() }`、`(() => { … })()` 此前读完整个文件都「没有语句」）、
    **分号省略**（ASI）后的下一行标识符也算**语句头**（`export type T = …` 换行后紧跟 `if (typeof window …)` 此前
    被判为**同一条语句的中段**）、顶层 `}` 之后用**后随字符**而非标识符形状判是否续句（`Record<string, { … }>;`
    的类型字面量曾被读成多出一条 `>` 语句）；且**已复核 import 的实际内容会被读取**——`_COLLABORATION_MODULE_IMPORT_SPECIFIERS`
    此前只比对**字符串**而从不打开被导入文件，把门控放进 `./valueUtils` 或 `../../app/contracts/v2/store` 即可保持
    `contractRuntimeVm.ts` **一字不改**而让规则在浏览器域失效；现在按 specifier 解析 → 读文件 → 走**完整的运行时
    import 闭包**（实为 4 个文件），闭包内每个模块都必须可读、可切分且**不得出现任何环境全局或 `import.meta`**）；
    ⑩**偏移保长自证**（**第七轮新增**：对 `form_host`／
    `frontend_makefile` 与一份混注释／字符串／括号访问的样本断言 `len(_blank_comments_and_strings(t)) == len(t)`；
    这是①②③④「在屏蔽文本上定位、再从原文读回」得以成立的前提）。
    读模板前先屏蔽 **HTML 注释与 `<style>` 块**（保偏移）并**丢弃 `<script setup>` 段**，因此第三轮的
    「注释诱饵」以及第四轮新发现的「JS 注释／字符串诱饵」两类向量都已关闭。
  - **不覆盖运行态，以及一处登记过的非旁路（第四轮更正）**：两层都只覆盖**声明与接线**；浏览器里协作区到底出不出
    现仍未被任何门禁覆盖。第三轮登记的「A³-V9 `watchEffect` 覆写」按第四轮实测**不是**真实旁路：`hasCollaboration`
    是只读 `computed`，真 Vue 下该写入是 no-op（`Write operation failed: computed value is readonly`），而把它
    改成可写 `ref` 会被①的「仍须是 computed」拒绝——故 V9 在真实宿主上**不改变语义**，此前「已登记的运行态旁路」
    措辞过强，现按实测更正为「门禁不拒绝、但也不构成绕过」。
    第七轮**补登记**：**加载期**门控（模块顶层读运行环境）此前两层都不覆盖，现由第二层⑨覆盖（实测 F2 向量，
    见 §8 R43）；仍**不覆盖**的是「浏览器里协作区到底出不出」——⑨只保证模块在**加载期与调用期**都只依赖它的
    输入，真组件的渲染结果仍需运行态／组件级测试。
  - **自检矩阵的鉴别力边界（B³-F3；第七轮建立、第八轮按实测重写、第九轮复测）**：矩阵现为 **262 例** ＝ `_COLLABORATION_SELF_CHECK`
    **183 例（37 接受 ＋ 146 拒绝）** 的 **5 元组** `(name, host, module, makefile, expected)` ＋
    `_COLLABORATION_PAGE_SELF_CHECK` **21 例（7 接受 ＋ 14 拒绝）** 的 **3 元组** `(name, page, expected)` ＋
    `_COLLABORATION_IMPORT_CLOSURE_SELF_CHECK` **57 例（19 接受 ＋ 38 拒绝）** 的 **4 元组**；
    两表由 `_collaboration_self_check_failures()` 合并执行，`collaboration_self_check` 由两表长度实时导出。
    **实测有鉴别力的十处**（复算方法：在内存里把守卫自身的机制换掉，看矩阵是否翻转；第九轮按 **120 例**复测）——
    (a) 去掉 `_scan_tags()` 的 **`{{ … }}` 插值跳过**，矩阵报出 `region slot closed by a decoy inside an interpolation`；
    (b) 去掉 **void 元素集合**，矩阵报出 `an HTML void element before the region slot`；
    (c) 撤掉**顶层绑定形状规则**，矩阵报出 3 例（R48 记的 4 例含「非导出顶层绑定」一例，它由**裸声明**分支另拒，第八轮单点复算为 3）；
    (d) 把 `enum`／`namespace`／`using` 放回声明白名单，报出 2 例；
    (e) 把注释屏蔽换回**不识别字符串**的旧形状，报出 2 例（字符串里的 `//` 与未闭合 `/*` 各吞掉一条顶层门控）；
    (f) 把 `./collaborationPoison` **加入**已复核 import 清单，报出 1 例（清单**空集化零翻转**，该规则只放行清单内的 specifier）；
    (g) **彻底移除**导出加载期声明规则（两个模式一起回退）报出 2 例——只把形状放回
    `_COLLABORATION_EXPORT_DECLARATION` 而保留 `_COLLABORATION_EXPORT_LOAD_TIME_DECLARATION` 时**零翻转**，两条须同时停用才可测；
    (h) 把 `_slot_names()` 的**插槽名归一化**换回「按字面 `#collaboration` 计数」，报出 2 例；另**去掉面板／载体的祖先字面死门检查**报出 3 例；
    (i) **停用正则字面量识别**（把 `_JS_REGEX_PRECEDING_CHARS`／`_JS_REGEX_PRECEDING_WORDS` 置空）在矩阵上**零翻转**，
    但**归因不是**旧文写的「矩阵里的正则用例都**同一行闭合**」。**（第十轮据实更正）** 实测该用例仍被拒，理由来自
    **同一轮新增的未闭合 span 拒绝**：`the collaboration authority cannot be segmented: an unterminated string starts at
    offset 856, so every statement below it is unread rather than absent`——正则表一停用，`/[']/g` 里的引号就开启一个走到
    文件末尾也不闭合的字符串。故这条的实测结论应写成「**同轮的另一半规则顶住了它，正则识别本身在矩阵上 0 例**」，
    正则 DFA 的具体行为由 §8 R57 的向量 `R57-1`／`R57-2`（`/[']/g` 与 `/[//]/`）在**真守卫**上证明
    （OLD=GREEN → NEW=REJECT）；旧文的「矩阵用例均同一行闭合」**不成立**，不作为解释保留；
    (j) **停用未闭合 span 拒绝**报出 **1** 例（`an unterminated block comment hides the gate after it`）；
    另三条第九轮实测：**import 规则换回「读窗内最后一个字符串」**（第八轮形状）报出 **1** 例、**计算插槽名不再报哨兵**报出 **2** 例、
    **停用面板 `v-if` 等值规则**报出 **2** 例（三种变异各自的拒绝信息已逐条核对归属）。
    **（第十轮新增）** 停用第九轮的**面板 `v-if` 等值规则**在 120 例上亦报 **0 例**——不是该规则无用，而是第十轮的
    **登记式门禁清单**（面板的允许集合只有 `showCollaborationPanel`）已经把它**包含**：逐条核对 `v-if="!hasCollaboration"`
    与 `v-if="NaN"` 两个用例，各自现在都由新规则报出（旧的等值规则同时再报第二条），故二者构成**纵深防御**、
    计数上不再可分。
    **实测无鉴别力的四处（并撤回第五轮的相反声明）**：把 `_blank_html_comments` 换成恒等函数、把
    `_blank_style_blocks` 换成恒等函数、把引号感知换成「第一个 `>` 即结束」的朴素读法，以及撤掉**偏移保长**
    那条 `require` 或 `_body_window` 里的**读窗对齐断言**，120 例判定**全部不变**——第五轮称「换恒等函数后矩阵
    立刻报出 `region slot renamed with a comment decoy`」，按 77 例／99 例／111 例／120 例复算**均不可复现**；它们现按
    **纵深防御／结构性不变式**登记（`_scan_tags()` 自己就跳过注释，`<style>` 段里的诱饵本来就被标签扫描 ＋
    直接子元素规则拒掉；未闭合子元素在父级结束处逐个收尾已把引号诱饵单独中和；偏移保长与读窗对齐是**前提
    条件**而非用例，其价值由 F1 的构造式假接受实测确立，见 §8 R42）。
    另：引号向量仍**整例**
    有鉴别力，但鉴别的是**第五轮的整组改法**而非其中一项：把**第四轮**的守卫（`74160041`，矩阵 36 例）拿来跑
    同一个宿主，它**PASS**（旧的正则计深度确实被该诱饵复位），当前守卫 REJECT——只是当前代码里
    「未闭合子元素在父级结束处逐个收尾」已把该诱饵单独中和，故去掉引号感知不再被矩阵看见。鉴别力最终仍来自
    **真实宿主**的断言，矩阵只证明「同一断言在每个形状上读对期望值」。
  - **实测接受面／拒绝面（第七轮对真守卫逐项复测）**：
    接受（14，全部在矩阵内）——委派 ＋ 区域完整接线、重排后的委派调用、`=` 两侧带空格的
    属性写法、模块侧类型清单**增项**、**仅含 `return` 的块体**委派、插槽**之后**的同级标记、插槽**之前**的
    `{{ … }}` 插值、插槽**之前**的 void 元素（含 `<BR>` 这类**大写**拼写）、**宿主标志用单引号绑定**
    （`:has-collaboration='hasCollaboration'`，第七轮新增接受面）、**权威体之前先出现一次括号属性访问**
    （`input['capability']` 写在另一个函数里；第七轮新增接受面，正是 F1 的触发形状）。第八轮**新增接受面三例**：**委派实参用括号属性访问拼写**（`props['showCollaborationPanel']`——第七轮因归一化被移出而短暂被拒，第八轮恢复）、**区域插槽写成 `v-slot:collaboration`**、**模板文本里出现 `{{ '#collaboration' }}` 插值**（第七轮曾被误计为「第二次声明」）。第九轮**新增接受面一例**：**已复核 specifier ＋ 其后注释里点名另一个模块**（`import … from './valueUtils'; /* './collaborationPoison' */`——新规则只读 `from` 子句，注释诱饵不再参与判定，正是 R58 反向的**镜像**用例）。另经真守卫逐项复测
    **仍接受**的等价拼写（不在矩阵内）：带返回类型标注的箭头（`(): boolean => …`）、**宿主委派实参**外再加一层括号、
    `export interface …`／`export type …`／
    `export function …` 等模块级声明。**（第九轮据实性更正）** 旧文把 `declare const …`（类型层、无加载期求值）列为
    「仍接受」**与实测不符**——它是顶层语句、落在声明白名单之外，自 R50 起即为**拒绝**（A⁹-S4 报的正是这处自相矛盾）；
    同时**新登记**三条第九轮引入的过严面：裸 `async function …`、空 `export class {}`、空 `export namespace {}`
    （空体不跑加载期代码，却与「导出加载期声明」规则同形被拒）。
    第十轮**新增接受面四例**（全部在矩阵内，见 §8 R63／R64）：**载体带已登记门**（`v-if="!preserveAuthoritativeBusinessSections"`）、
    **祖先带已登记门**（外层 `v-if="hasCollaboration"`）、**模板文案里的撇号**（`<span>don't</span>`——此前 `_js_opaque_spans`
    按整份 `.vue` 文本切字符串，撇号开启一个跨到下一个引号的**幻影字符串**，把 `<script setup>` 里的 `hasCollaboration`
    读成缺失，报 `the collaboration flag is no longer a computed`；现在脚本级屏蔽先取出 `<script>` 区域，模板文案不参与
    JS 词法）、**页面侧已登记的 page-section 祖先与 `ScCard v-else` 分支**。第十轮**新增拒绝面四类**（见 §8 R61–R63）：
    顶层裸块／顶层 IIFE／顶层括号赋值（语句切分）、**ASI 之后**的 `if`、**未登记门**的载体与祖先（含
    `v-else-if="false"` 这种「换个属性名就重开死门」的写法）、**已复核 import 目标文件内**的环境探针（含其**传递**
    依赖）。
    第十一轮**新增接受面两类**（均在矩阵内，见 §8 R70）：**`<script>` 块以 `</SCRIPT>` 闭合**（SFC 解析器接受大写闭合标签，
    此前 `_script_text()` 大小写敏感 ⇒ 整块脚本被判为空、报假 REJECT）、**模板里提到 `<script>` 的 HTML 注释**
    （`<!-- <script> -->`——此前 `native_surface_bridge_errors()` 先按 `<script` 切分、再删注释，模板被判为空而误拒）。
    第十一轮**新增拒绝面五类**（见 §8 R65–R69）：**藏在声明之后的一行调用**（`!gate()`——旧版被判为续句，R65 引入的
    回归已闭合）、**`U+2028`／`U+2029` 之后的语句**（ASI 行终止符，R66）、**语句位的模板字面量**（反引号现被保留为首
    token，R67）、**闭包模块本层的可执行语句 ＋ 经 re-export／动态 `import()` 到达的模块 ＋ 深度触顶**（R68）、
    **已登记路径上的任何 `v-for`**（空迭代与 `v-if="false"` 等价，R69）。
    第十二轮**新增接受面三类**（均在矩阵内，见 §8 R73／R78）：**声明体 `}` 之后的类型续接**（`Record<string, { a: string }>`
    的 `}` 由 `>` 续接，此前与「`}` 后藏语句」同判——`>`／`|`／`&` 三种不能起句的续接保留）、**声明体 `}` 之后的结构续接**
    （`else`／`catch`／`finally`／`while` 仍属同一条语句）、**引号属性值／HTML 注释里提到 `<script>` 的模板**（真宿主与真页面各 1 例；
    此前按裸 `<script` 子串切分，模板或脚本区被判空 ⇒ 假 REJECT）。另 1 例接受面为**闭包模块里的模板字面量插值**
    （`` export const LABEL = `p-${1}`; ``——其 `}` 曾被读成语句头）。
    第十二轮**新增拒绝面六类**（见 §8 R72–R74／R77）：**闭包模块里含 `{` 的字符串字面量之后的一切语句**（`export const OPEN = '{'`
    让其后整文件语句隐形）、**深度触顶模块自身的加载期语句**（触顶此前只报深度、不读内容）、**声明体 `}` 之后的
    `+`／`-`／`/re/`／`from`／`as`／`satisfies` 续接**（藏在声明之后的调用/正则测试）、**闭包模块的 `export default <表达式>`
    与 `export class` 静态初始式**（加载期求值）、**未枚举环境全局出现在声明初始化式里**（`typeof screen`，第十二轮把
    `screen` 一族补进清单）、**动态 `import()` 的非字面量 specifier**（`import('./' + name)`，fail-closed）。
    第十三轮**新增接受面一类**（在矩阵内，见 §8 R83）：**只为类型而导入的包**（`import type { T } from 'pkg'`——类型导入被编译器擦除、
    不在加载期求值，故与相对导入同向接受；同一句去掉 `type` 即拒）。
    第十三轮**新增拒绝面五类**（见 §8 R83／R84）：**闭包成员本层的模块级绑定**（`export const dead = typeof Element !== 'undefined'`／
    `export const box = new Image()` 一类初始化式在**加载期**求值，现由**形状规则**拒绝，不再依赖任何枚举清单）、
    **任意形态的 `export default`**（含 `export default class { static x = … }`——旧版把 `export default class` 当合法声明放行，
    静态初始式因此回到加载期）、**`export =` 赋值导出**（TypeScript 的赋值导出在加载期求值；`tsc`／`esbuild` 实测该形状在 ESM 下不可部署）、
    **非类型包导入**（`import { x } from 'pkg'`——加载期执行的是别人的顶层代码，落在每一个层之外）、
    **动态 `import()` 首实参是字面量但还带第二实参**（`import('./x', { with: {} })`，此前 fail-open）。
    第十四轮**新增接受面一类**（在矩阵内，见 §8 R85／R86）：**声明该有的形状**——`type X = …`／`interface X …`／
    `function f(…)`（`type`／`interface` 是**上下文关键字**，白名单只认拼写，所以「合法声明仍被接受」必须由正向控制证明）
    与**相对再导出到干净模块**（`export * from './fieldUtils'` 仍是可跟的边）。
    第十四轮**新增拒绝面两类**（见 §8 R85／R86）：**以 `type`／`interface` 开头但不是声明的语句**
    （`type(typeof customElements !== 'undefined' && (Array.prototype.includes = () => false));`——首 token 正好在声明白名单上，
    却是**加载期执行的调用**；**权威体层与闭包成员层各自收口**）、**守卫打不开的再导出**
    （`export * from 'pkg'`／`export * as ns from 'pkg'`／`export { a } from 'pkg'`——与 `import { x } from 'pkg'` **同规拒绝**；
    此前既不跟边也不拒绝，因为 `relative_edges()` 只认 `.` 开头的 specifier）。
    第十五轮**新增接受面三类**（在矩阵内，见 §8 R88／R89／R90）：**无空白的相对再导出与副作用导入**
    （`export*from'./x'` 仍是可跟的边、`import'./x'` 仍是可读的边——旧版把前者放行而**不跟边**、把后者误拒）、
    **垫空白后仍合法的声明**（读取窗口按**折叠后**字符计数，`export` ＋ 400 空格 ＋ `function f() {…}` 仍被接受）、
    **嵌套泛型的声明**（`type Wrapped<T extends Box<number>> = T;`／`function read<T extends Box<number>>(…)`）。
    第十五轮**新增拒绝面三类**（见 §8 R88／R89／R90）：**无空白拼写的打不开再导出**
    （`export*from'pkg'`／`export{a}from'pkg'`／`export*as ns from'pkg'`，与有空白拼写同规）、
    **垫空白到读取窗口之外的语句**（`export` ＋ 400+ 空格 ＋ 模块级绑定／再导出）、
    **装饰器插在 `export` 与 `class` 之间**（`export @sealed class Probe { static x = 1; }`：类体在加载期求值，
    而 `class` 那一级只在关键字直接跟随时匹配，故改由出口阶梯的**默认拒绝**收口）。
    拒绝面（fail-closed，方向安全但会卡重构，第七轮逐项实测）——属性**换序**、能力被 `Boolean(...)` 再包一层、
    `props?.showCollaborationPanel`、`props.renderModel?.zones?.subordinate`（双可选链）、
    `props.renderModel.zones.subordinate`（去可选链）、`computed<boolean>(() => …)` 泛型实参、块体里**多一句**
    语句、`v-bind` 对象写法／`v-bind="attrs"`、同文件 helper 抽取、插槽 `v-if` 写成 `!!hasCollaboration` 或
    `hasCollaboration && true`（语义等价但非规范拼写）、插槽内面板组件**改名**（须仍是 `<NativeCollaborationPanel`）。
    第六轮**新增**的拒绝面（形状收紧，均由矩阵点名）：**块体忘写 `return`**（V21）、权威体里出现**第二条
    （哪怕不可达）语句**、权威体的**任意环境探针拼写**（整表达式等值后不再逐拼写枚举）、字符串字面量里的合规 body
    顶替真 body、`import … as` 别名、命名空间解构、`{{ … }}` 里的假闭合、`$(VAR)` 变量名目标、含 `$(`／`${`
    的配方行、页面单引号字面量 ＋ 双引号 decoy、页面 `v-bind` 展开。
    第七轮**新增**的拒绝面（全部由矩阵点名，见 §8 R42–R49）：**载体（或它的任一祖先）被字面 `v-if`／`v-show`
    关掉**、`#collaboration` **声明两次**（后者为空）、插槽内**面板被字面死门关掉**、页面载体（或祖先）同理、
    **模块加载期读运行环境**（顶层 `if (typeof window …)`）、**模块运行非声明语句**（`Object.defineProperty(...)`）、
    **副作用 import**／`export * from`／`export default`、**顶层绑定带加载期初始式**（含 `typeof screen` 这类
    黑名单之外的浏览器全局）、**非导出顶层绑定**、**类型清单由表达式拼装**、`using`／`enum` 顶层声明。第八轮**新增**的拒绝面（全部由矩阵点名，见 §8 R50–R56）：**导出前缀的 `enum`／`class`／`namespace`／`abstract class`／`declare` 加载期声明**、**裸 `abstract class` 的静态初始式**、**顶层语句被字符串里的注释标记屏蔽**、**运行时 import 的 specifier 不在已复核清单内**、**插槽以 `v-slot:` 拼写二次声明**、**插槽内面板被字面死门祖先关掉**。
  - **页面侧**：两个属性（`:show-collaboration-panel` 与 `:suppress-collaboration`）在**另一个文件**里，
    故**不并进宿主矩阵**，而由第六轮新增、第七轮扩到 **13 例（2 接受 ＋ 11 拒绝）** 的
    `_COLLABORATION_PAGE_SELF_CHECK`（夹具 `_collaboration_page()`）驱动——「矩阵外」的旧登记**已不成立**。
    判据由第五轮**文件级子串**升级为**元素级 ＋ 逐处表达式**（⑦），并加**模块同一性**（⑧）与第七轮的**载体／
    祖先字面死门**判定。真实树上的鉴别力由第五轮向量 V03b／V03c／V04a／V04b（全部被拒，见 §5）与第七轮的
    R45 三例（页面载体 `v-if="false"`／`v-show="false"`／祖先 `v-if="false"`）确立。
  - **新增并登记的边界**：**内容绑定**使证明文件不可静默改写（改动必须同 commit 改守卫里的 sha256）；
    反之它本身是 fail-closed 的——证明文件任何改动都会先让门禁报错一次，属预期成本。它绑的是**源码**，
    **不**绑 make 的实际执行物，故由 ⑤ 另做配方层绑定（唯一定义／字面路径／outfile 独占／`node` 锚定）。
    第六轮把⑤的扫描面从 `frontend.mk` 单文件扩到 **`Makefile` ＋ `make/*.mk`（除 `frontend.mk`）**，
    并**拒绝**变量名目标与任何含 `$(`／`${` 的配方行，故 `--outfile=$(VAR)`（M31）、`$(VAR)` 目标二次定义（M26）、
    `cp … $(VAR)` 覆盖 outfile（M29）**现已被拒**——旧登记「`--outfile=$(VAR)` 不在判据内」**已不成立**。
    仍**未**覆盖的残余面如实登记：`esbuild` 被换成同名别名、make 之外的手工执行路径，以及
    `include $(ENV_FILE_RESOLVED)` 之类**后引入**的外部 make 片段（不在 `Makefile` 与 `make/*.mk` 扫描面内）。
  - **收窄后的过严面（方向安全，仍登记；第七轮逐项复测）**：`computed<boolean>(() => …)`、间接化委派
    （`const x = computed({...})` ＋ `computed(() => authority(x.value))`）、`props?.showCollaborationPanel`、
    去可选链的 `props.renderModel.zones.subordinate`、同文件 helper 抽取；以及本轮新增的一项——**三个权威体各自的
    整表达式等值**（白名单式：表达式须逐字等于规范式，故给权威体**多加一层冗余外括号**即被拒，第五轮该写法是被
    接受的）与**配方行含任何 `$(`／`${`**。第七轮**逐项复测确认**的两条：**页面侧 `:suppress-collaboration`
    仍要求精确表达式**（`Boolean(dispatchContextCollaboration)` 这类等价包装被拒）与**顶层声明的形状白名单**
    （`export const KINDS_SET = new Set(COLLABORATION_SURFACE_KINDS);` 这类纯本地缓存也被拒）。
    第七轮**撤销**一条旧登记：宿主模板属性用**单引号**此前被列为过严项，现已接受（宿主层改按属性表读，见 R44）。第八轮**再撤销两条旧登记**：**`props['…']` 括号属性访问**（第七轮因归一化被移出而误拒，见 R51）与**插槽以 `v-slot:` 拼写／模板文本里的 `{{ '#collaboration' }}`**（第七轮按字面文本计数而误拒，见 R52／R54）。第八轮**新登记**两条仍开的面：**字面死门只做有限枚举**（`v-if="false"`／`v-show="false"`／无值 `v-show`；语义等价的其他字面形态未必被枚举到）与 **`v-bind:[动态属性名]`** 不会被属性表收集（见 R55）。第九轮**新登记三条仍开的面**：**面板 `v-if` 只接受与 `showCollaborationPanel` 逐字相等**（`v-if="(showCollaborationPanel)"` 这类等价外括号写法被拒；`=` 两侧空白**仍接受**）、**面板上的 `v-show` 不在判据内**（`v-if="showCollaborationPanel" v-show="true"` 实测 GREEN）、**import specifier 之后出现任何非空文本即拒**（守卫判不出加载哪一个，方向安全但会卡 `import … from 'x' assert {…}` 一类写法）。
    第十轮**登记三条新证据 ＋ 收窄一条旧登记 ＋ 登记一条性质**：①**外括号过严面扩大**——登记的等值清单是**逐字比较**，故 `v-if="(hasCollaboration)"`（以及任何**已登记门**的多余外括号）**一律被拒**，第九轮「`(showCollaborationPanel)` 被拒」由单点变成**整清单的性质**；②**面板 `v-show` 已收口**（第九轮登记的「`v-if="showCollaborationPanel" v-show="true"` 实测 GREEN」**不再成立**：整条路径上的 `v-show` 现在一概拒绝，含恒真的 `v-show="true"`）；③**行注释尾随反斜杠**（`// … \` 续行）在 `_js_opaque_spans` 里按**行尾**结束，属**极端**过严面，已登记**未收口**；④**文档措辞收窄**——`_HTML_ENTITIES` 实际只有 **7 个固定实体**，旧文「HTML 实体解码」比实现宽，现按「只解这 7 个」理解。**性质登记**（不是过严面）：`_blank_spans` **从不遮蔽 `regex` span**，故正则被误判成字符串时只会让守卫**多看见**代码、不会藏东西——这条的失手方向是 fail-closed。
    措辞收窄：第五轮写的「权威体里**任何**非单一 `return` 写法」不精确——实测**跨行书写**单一 `return`
    **仍然接受**（`_condense` 会归一化空白），被拒的是**表达式不等于规范式**或 `return` 之后**还有语句**。
    第十一轮**登记三条新过严面**：①**闭包模块本层语句一律须为声明**——一个合法但会在加载期跑一次纯计算的写法
    （如顶层 `for` 建索引）现在被拒；②**已登记路径上的任何 `v-for` 一律被拒**，包括与门控无关的纯展示迭代；
    ③**`relative_edges()` 只解析可读的相对边**（**第十六轮据实更正**：此处原写 `_closure_relative_specifiers`，**该符号在守卫里不存在**——R76 只改了 §7 第 13 项 ⑦ 的同一笔误，此处漏改），非相对 specifier 与被后缀表覆盖不到的扩展名不在闭包内
    （方向 fail-closed：解析不到即报「无法读取」）。
  - 守卫末尾的 `checks` 已由历史硬编码字面量 `checks=63` 改为**运行时统计**（`require()` 调用计数器），当前
    实测 `checks=129`；`collaboration_self_check` 亦由矩阵长度实时导出（当前 **260** ＝ 宿主／模块 182 ＋ 页面 21 ＋ import 闭包 57；接受 63 ＋ 拒绝 197），
    不再有会静默漂移的常量。
- 未做：`local.dev` 运行态浏览器抽验、`verify.frontend.release.audit` 全链、`ci.local.quick` 以外的较慢套件。
- 既有类型债 32 条（15 文件）仍为本批之前既有，未在本批挪用为改动范围。

## 7. 未做与下一步

- **发布阻断（外部）**：GitHub 账号 `lidefend` 被平台封禁——`git ls-remote origin` 返回
  `remote: Your account is suspended.`（HTTP 403），所有认证读取同为
  `403 {"message":"Sorry. Your account was suspended"}`（两轮独立复核各自只读复现）。因此本批**未**推送、**未**建 PR；
  上一批 `feature/frontend-page-header-entry-authority-v1`（PR #522，A¹¹／B¹¹ 双 APPROVE、exact-head L5 VERIFIED）
  继续冻结待合并。
- 下一批候选（按价值排序）：
  1. **类型债收敛**（32 条 / 15 文件）：`views/SceneContractBlockGridView.vue`（6）、`components/template/one2manyRelationQuery.ts`（4）、
     `pages/contractForm/nativeSectionNavigation.ts`（3）、`pages/ContractFormPage.vue`（3）、`pages/contractForm/canonicalFormRenderer.ts`（2）等。
  2. **权限／角色判定单一权威**：`frontend/apps/web/src/app/pageContract.ts:105` 仍在自行解析 `roleSurface.role_codes`，与本轮
     下沉的 `resolveRuntimeRoleCode(s)` 重复。注意该处**只 `trim()` 不 `toLowerCase()`**，而契约声明侧 (`visibility.roles`)
     原样比较，故「并为单一权威」必须**同时**决定两侧的大小写归一，不能单侧改。
  3. `scripts/release/release_readiness_report.py:74` 硬编码 `authoritative_navigation_leaf_count: 70`，与清单实际
     （本批后 **85**）不一致，应改为从 `config/frontend/authoritative_navigation.json` 派生。
  4. 本轮新登记的 3 个菜单需要一次**受管运行态浏览器清单**（`frontend_surface_inventory_v1.csv` ＋
     `make …frontend_product_maturity_audit`）复核可达性与页面身份；这一步同时是候选 5 的前置：`authoritative_navigation.json`
     的 `source.source_sha` 仍为 `0ac5173be801861ea621dd0e5048c9fc18548049`，正是 `frontend_release_audit` 报
     `EVIDENCE_SHA_MISMATCH:navigation` 的来源。
  5. **重建 `frontend_release_audit` 的 7 个分节运行态证据**（`static`／`navigation`／`delivery_hardening`／`accessibility`／
     `performance`／`responsive`／`error_recovery`）；建议同时给该脚本加 `--check`（默认不写）以恢复「守卫只读」语义。
  6. ~~协作区断言从令牌级升级为表达式结构校验~~ **已完成，方向已改**：第三轮复核证明「文本形状门禁无法证明
    语义」，故不再往「更强的正则／结构校验」加码，而改成两层——**第一层**把语义判定下沉为真实模块的
    四个权威并用**可执行真值表**（现 102 例）证明，**第二层**让守卫只绑定**接线**（第七轮扩为**十项**，见 §6）。
    第四轮把接线从令牌级抬到语义级，第五轮再堵住 §8 R28–R34 的十项（块体 `return`、证明路径／唯一性／
    可执行名／outfile 独占、import specifier、环境探针、ghost 清单、直接子元素、页面侧门禁），第六轮堵住
    §8 R35–R41 的七项（探针黑名单→整表达式等值、字符串 decoy 定位函数体、插值假闭合、`as` 别名与命名空间解构、
    页面单引号／`v-bind` 展开、`$(VAR)` 目标与配方行、void 元素误判），第七轮再堵住 §8 R42–R49 的九项
    （错位读窗、模块加载期环境门控、顶层绑定初始式、`using`／`enum`／`namespace`、载体／祖先字面死门、
    插槽二次声明、插槽内面板死门、页面载体死门、模块图／声明形状）。
    **仍剩两项**：（a）**运行态仍无门禁**——两层都只覆盖**声明与接线**，浏览器里协作区到底出不出没有任何
    门禁覆盖，需要运行态／组件级测试（第四轮已按实测更正：A³-V9 `watchEffect` 覆写**不是**旁路，只读 `computed`
    下写入是 no-op，详见 §6 与 R26；第六轮把证明改为两域复跑，收窄了但**不等于**运行态覆盖，因为跑的仍是
    纯函数而非真组件）；以及第七轮登记的**模块图**残余面——⑨覆盖的是**单个模块文件**的加载期，`import` 链上
    的第三方模块在加载期做什么（含其自身的环境分支）仍不可见，需要模块图／打包层证据。（b）fail-closed
    误判面——§6 登记的等价写法（`v-bind` 对象写法、同文件 helper、`computed<T>()`、权威体冗余外括号、
    `props?.x`／去可选链、页面 `:suppress-collaboration` 的等价包装、顶层声明的形状白名单 等）仍会被拒，
    收敛它们需要**共享的表达式级解析器**（而非继续堆正则），属下一轮候选。
   7. **守卫自身的体量回收（第四轮入池，第七轮加重并由 P2 升为 P1，第八轮再加 243 行、第九轮再加 250 行、第十轮再加 583 行、第十一轮再加 221 行、第十二轮再加 416 行、第十三轮再加 169 行、第十四轮再加 149 行、第十五轮再加 191 行、第十六轮再加 285 行、第十七轮再加 422 行、第十八轮再加 466 行、第十九轮再加 263 行、第二十轮再加 175 行、第二十一轮再加 38 行）**：`frontend_scene_component_bridge_guard.py` 现为 **7007 行**（**第十三轮钉死口径**：按 `scripts/ci/generate_complexity_budget_report.py` 的 `SCAN_ROOTS` ＝ `Makefile`／`addons/`／`scripts/`／`frontend/apps/web/src/`／`.github/workflows/` ＋ 其 `BUDGETS` 扩展名统计，**排除 `docs/` 与 `frontend/pnpm-lock.yaml` 一类 lockfile**；本口径下为本仓**第 1 大代码文件（Python 源码亦第 1）**，见 §8 R81），越过 3000 行阈值
     并被机器生成物登记为 `split_plan_queue.md` 的 **P1** 项（`priority_for`：`lines >= 3000` → P1）。协作区那一层（常量 ＋ `_scan_tags`／`_element_spans_all`／
    `_innermost_element`／`_sole_return_expression`／`_tag_attributes`／`_body_window`／`_dead_gate_failures`／
    `_module_statements` 等 helper ＋ 262 例矩阵 ＋ 自检运行器）已是**自洽单元**，
     可按既有先例（本守卫已在 import `contract_form_semantic_identity_guard`／`scene_audit_disclosure_guard` 两个
     `scripts/verify` 兄弟模块）抽成 `scripts/verify/collaboration_authority_wiring.py`（第六轮又加 `_authority_body`／
     `_expression_failures`／`_tag_attributes`／`_variable_named_rule_lines` 与页面矩阵，协作区那层已占该守卫的
     大半）。本轮**不做**：同一提交里既改语义又搬上千行会让复核无法审；作为独立、可复核的重构列入下一轮。
  8. **本轮已关闭的历史待办**：第 6 项的旧清单里已无遗留（§8 R28–R34 对应第五轮、R35–R41 对应第六轮、R42–R49
     对应第七轮、R50–R56 对应第八轮，全部有实测向量；第八轮 13 例翻转＝10 例 OLD=GREEN→NEW=REJECT ＋ 3 例 OLD=REJECT→NEW=GREEN）。
  9. **第七轮已关闭的上一轮候选**：①**宿主层改用属性表**——已落地（`collaboration_consumption_failures` 经
     `_tag_dynamic_values`／`_tag_attributes` 读属性，两种引号都接受，宿主单引号写法不再被拒，见 R44／R46）。
  10. **第七轮新登记的下一轮候选**：①**权威体冗余括号**可接受化（`_condense` 去一层配对括号后再比对，或改判
     归一化 AST 而非文本）；②**表层白名单精确化**——顶层绑定的形状规则目前只放行「字符串字面量组成的类型清单」，
     可先算出模块真正使用的声明集合再比对，去掉 `export const KINDS_SET = …` 这类纯本地缓存被拒的过严面；
     ③**模块图面**（`import` 链的加载期行为）需要打包层／静态模块图证据，已并入候选 6 的残余面。
  11. **第八轮新登记的下一轮候选**：①**字面死门只做有限枚举**——`v-if="false"`／`v-show="false"`／无值
     `v-show` 之外的**同类**字面形态（矩阵外的等价写法如 `v-if="!!''"`／`v-if="Boolean(0)"`／`v-if="0.0"`）不在判据内；
     **（第十轮据实升级）** 该条**不是「仅过严」，而是一条可达的绕过**——第十轮 B¹⁰ 用真 SSR 实测：
     `<div v-if="hasCollaboration && false">`（祖先）与 `<ObjectTaskPage v-if="!preserveAuthoritativeBusinessSections && false">`
     （载体）都是**真实谓词但恒假**，既不是字面、也不在前一轮任何判据内，渲染结果 `panel=ABSENT` 而门禁 GREEN；
     第十轮已按「**登记式等值清单**」结构性收口（见 R63），本条据此**关闭**为「已收口」；②**`v-bind:[动态属性名]`** 不会被属性表收集；
     ③**模块级重复声明**（同名 `export function` 两次）守卫只认第一处，目前由 esbuild／rollup 构建期兜底拒绝
     （本批用打包层实测确证不可部署，故登记为 POST_MERGE 而非 S1）；④配方里 `esbuild`／`node` **只按 basename 锚定**，
     `/tmp/attacker/esbuild` 一类同名文件可顶替（已登记，未收口）；⑤**`_body_window` 的对齐断言与顶层保长
     `require` 是结构性不变式**，不得被赋予鉴别力（第八轮 B⁸ 的 16635 窗口抽样实测：断言对任何真实输入都不触发）；
    ⑥**运行态／组件级门禁**仍无——两层都只覆盖声明与接线。
  12. **第九轮新登记的下一轮候选**：①**正则字面量族未穷举**——`_js_opaque_spans` 的「`/` 是否开正则」是**启发式**
     （前置字符表 ＋ **13 个**前置关键字；**第十轮据实更正**：旧文写 14，实测 `await,case,delete,do,else,in,instanceof,new,of,return,typeof,void,yield` 共 **13** 个，
     字符表本身 18 个）。该条**只影响正则与其后代码的切分归属**，失手方向为 fail-closed——第十轮实测：
     停用整张正则表后该矩阵用例**仍被拒**，理由是**同轮新增的未闭合 span 拒绝**（`an unterminated string starts at offset 856`），
     故「矩阵 0 例」的正确归因见 §6 鉴别力 (i)；`a = /x/ / y`、模板 `${}` 内嵌、`\u002f` 转义等形态仍未逐一实测；
     ②**`_statement_text` 在原文首个 `;` 截断**，故含 `;` 的字符串／注释会切错语句（已由「specifier 后非空即拒」
     部分兜底，未收口；**第十轮补充**：该函数读的是**注释屏蔽文本**，字符串已由 `_js_opaque_spans` 的不透明处理覆盖，
     残余面是**字符串内含 `;` 且该字符串出现在 import 语句之前**一类构造）；③~~**语句切分空洞**（A⁹ 报）：以 `(`／`{`
     开头的顶层语句不进 `_module_statements`，紧跟顶层 `}` 的 `while` 落在 `_COLLABORATION_STATEMENT_CONTINUATIONS` 里~~
     **第十轮已收口**（见 R61）：`(`／`[`／`{` 开头的顶层语句现在**会被报出**（顶层裸块／IIFE／括号赋值三个形状由矩阵点名），
     ASI 之后的行首标识符也算语句头，顶层 `}` 之后改按**后随字符**判定是否续句（顺带修掉 `Record<string, { … }>;` 被读成多一条 `>` 语句的**假 REJECT**）；
     `while` 仍在续接表内，但那正是 `do … while` 的合法续接，且顶层 `do` 本身已先被拒；
     ④**动态插槽名只扫最内层元素**——落在嵌套容器内的计算名未实测（**第十轮据实**：B¹⁰ 实测该形态**不可部署**——
     真 `@vue/compiler-sfc` 直接抛异常，故按无害登记，不升级）；⑤**面板等值规则的新过严面**（带类型标注、实体编码、外括号）
     与**面板 `v-show`**——**第十轮部分收口**：面板 `v-show` 现在**一概拒绝**（含 `v-show="true"`），外括号仍被拒且已扩为
     整清单的性质（见 §6 过严面）；⑥**Vue 插槽名大小写**（`#Collaboration`）——**第十轮已实测并关闭**：
     真编译器把 `#Collaboration` 编译成 `"Collaboration"`，与 `#collaboration` **不是同一槽位**，守卫一律 REJECT，
     方向安全（被拒的是「插槽名写错」这一真实错误，不是等价写法）。
  13. **第十轮新登记的下一轮候选（第十一轮逐条复核后更新）**：①**`_JS_STATEMENT_INVISIBLE_HEADS` 是启发式**——ASI 语句头判定只对
      「上一有效字符可结束语句 ＋ 行首标识符」成立，隐式续接的极端写法（`satisfies` 之外的运算符别名、`get`／`set` 之外的上下文词）
      仍未穷举——**第十一轮据实缩小**：不能续接表达式的首字符（`!`／`~`／`@`／`#`）已由 R65 移出续句表，`U+2028`/`U+2029` 已由 R66 当换行；
      ②**import 闭包只做「可读 ＋ 环境纯」**的旧分工**已被 R68 取代**：闭包模块现在同样受「本层语句必须是声明」约束，
      「环境无关的加载期载荷由 `node` 域证明兜底」这一分工仍**未由证明侧显式断言**，继续登记；
      ③**闭包规模上限（40 文件）与深度上限（8）是常量**——**第十一轮部分收口**：深度触顶不再静默（R68 改报 failure），
      但**文件数触顶**与**两个上限本身**仍无用例；④**re-export 链已纳入闭包**（R68，含 `export * from` 与动态 `import('…')`），
      本条**据实关闭**；⑤**登记式门禁清单是逐字比较**，等价外括号、实体编码、引号风格改写一律被拒（过严面，见 §6）；
      ⑥**页面侧 `v-else`／`v-else-if` 的兄弟链**只按元素名登记，未校验收支可达性（`ScCard v-else` 是否真的能渲染取决于兄弟 `section`，
      那条兄弟门在清单内，但两者的**联动**没有被断言）；⑦**第十一轮新登记**：`relative_edges()` 只解析**静态可读**的相对
      边——非相对 specifier（tsconfig `paths`／别名／裸包）与被 `_resolve_local_module` 后缀表覆盖不到的扩展名（`.json`／`.vue`）
      仍在闭包之外；⑧**第十一轮新登记**：死门清单的 `v-for` 是**整体拒绝**，`v-for` 迭代**非空但恒为空**的表达式（如 `v-for="n in []"`
      已被拒、但 `v-for="n in emptyList"` 这类**运行期恒空**的写法）不在判据内；⑨**第十一轮新登记、第十二轮据实更正**：真正的开口不是「模板插值」而是**声明初始化式里的自由环境引用**——
      语句位规则只判「这算不算一条语句」，初始化式**内部**探针什么由**枚举式**环境全局清单负责，清单漏项即整体失守
      （`export const dead = typeof screen !== 'undefined'` 在第十二轮前两层同绿）。第十二轮已把 `screen` 一族补入（R74），
      **第十三轮据实收窄**：闭包成员**本层**的开口已改由**形状规则**（而非枚举）收口——模块级绑定、类体与 `export =`
      一律按形状拒绝，枚举清单只作为**函数体内运行期**探针的补充（真实闭包 4 文件**无模块级绑定**，故收紧后仍 PASS）；
      仍**未**覆盖的是模型之外的那一层：函数体里读到的环境名若不在清单内（`customElements` 等）依旧开口，故本条继续登记；
      ⑩**第十二轮新登记**：清单**刻意不含 `fetch`**（真实 `fieldUtils.ts` 命中它，纳入即假 REJECT）与 `top`／`parent`／
      `name`／`status`／`origin`（同名的普通标识符极常见）——「哪些全局算运行环境」这个判定本身没有结构化解法，
      与 ⑨ 同源，登记为**未覆盖面**而非已收口项；⑪**第十二轮新登记**：登记式死门清单覆盖 `v-if`／`v-else-if`／`v-show`／`v-for`，
      **未覆盖** `v-once`／`v-memo` 一类渲染期指令（`v-once` 不改变可达性、方向安全，但「换个指令重开死门」这条面没有穷举）；
      ⑫**第十二轮新登记**：动态 `import()` 的**非字面量 specifier** 已由 R77 fail-closed，但其它**不可跟的边**仍未纳入——
      `require()`／`import.meta.resolve()`／`new Worker(new URL(…))` 这类构造既不在闭包里、
      也不触发任何拒绝（**第十三轮据实补充**：`import(cond ? 'a' : 'b')` 一类**非字面量** specifier 已由 R77 fail-closed，
      `import('./x', { with: {} })` 一类**带第二实参**的字面量已由 R84 收口，**打不开的再导出**
      （`export … from 'pkg'`／`export * as ns from 'pkg'`）已由 R86 与 import 同规收口，三者均不属本条）；
      ⑬**第十四轮新登记**：闭包成员的**顶层 `declare const`**（无运行期代码）仍被「本层语句必须是声明」拒绝，属**既有假 REJECT**；
      **`type`／`interface` 逆用**的前提是闭包内存在**名为 `type` 的标识符**（否则调用即 `ReferenceError`，不构成绕过），R85 已按形状收口；
      ⑭**第十四轮登记的取舍**：闭包成员的任何**模块级绑定**（含 `export const … as const`）一律拒绝——真实闭包 4 文件零绑定，
      故按 fail-closed 保留；代价是未来闭包若需要字面量查表常量会被硬拒。
      ⑮**第十五轮登记的边界**：闭包出口阶梯的**默认已改为拒绝**（R88），因此「未被穷举的合法拼写」今后只表现为**过严**
      而不是放行；仍未穷举的是**非 `export`／`import` 语句**一类的不可跟边（`require()`／`import.meta.resolve()`／
      `new Worker(new URL(…))`，见 ⑫），以及 tsconfig／vite 的**其它路径别名**解析面（R90 只实测了 `@/*`）。
      ⑯**第十六轮登记的边界**（R92）：语句读取窗口有**上限**（`_COLLABORATION_STATEMENT_WINDOW` ＝ 2000 个**折叠后**字符），
      因此一条**具名导出列表本身超过该上限**的语句一律被拒（**过严面**，方向 fail-closed：守卫读不到 `from` 子句即不担保）；
      实测 60 个导出名（约 1.1k 字符）**仍可读并被跟边**，400 个导出名（约 7.2k）被拒。同轮登记的**取**（不是过严面）：
      `_statement_labels()` 把「后随冒号」的词判为**语句标签**而非续句词，故模块顶层的 `foo: { … }` 一定被当成独立语句拒绝——
      真实语言里没有任何续句词后随冒号（`T extends U`／`x satisfies T`／`import … from './x'` 之后都接名字），故不影响合法写法。
      ⑰**第十六轮登记（B¹⁶-S3，POST_MERGE_FOLLOWUP）**：四条**既有**过严面在本轮 head 上复测**仍然被拒**（与第十五轮一致，本轮未收口）——
      跨行书写的动态 `import(\n  './x',\n)`、赋值式 `import fs = require('fs')`、闭包顶层 `declare const`（⑬ 已登记）、
      以及 `export const K = [...] as const`（⑭ 已登记的取舍）；四者都不产生加载期执行，方向 fail-closed。
      ⑱**第十七轮登记的过严面（本轮引入，POST_MERGE_FOLLOWUP）**：F2 的修复让 `>` 与三个闭引号（`'`／`"`／`` ` ``）
      也能结束语句，镜像代价是**跨行续写的类型**的第二行被当作**独立语句**——`export type X = Foo<Bar>` 换行 `[];`、
      `export type X = Foo<'k'>` 换行 `['k'];`、以及类型别名后接**合法语句标签**（`postfix: 1;`）三者都是
      合法 TypeScript，现在一律被拒（**第十八轮据实更正**：真 `tsc 5.9.3`／`esbuild 0.21.5` 实测第二行确为**独立语句**，
      `[];` 真跑到产物——旧文「被切开的数组类型」的机制描述不确，见 R104）。三条已作为**对照夹具**钉进矩阵（名字后缀带 `(registered over-strictness)`），
      故不会静默变化；方向 fail-closed，且真实树（宿主／VM／页面／四个已复核闭包文件）两版均 **0 failures**，
      故**本轮不收口**：让 `[` 继续上一条语句正是本轮刚关掉的吸收通道，重开需要先有能区分「类型位」与「值位」的
      语句解析器，属下一轮候选。同轮**登记**（不是过严面）：`_blank_spans` 在**被擦字面量的末字符**写 `"0"`——
      擦除只发生在字符串／模板字面量内部，故它只让「被擦掉的字面量仍然能结束语句」，方向是**收紧**。
      同轮还**登记**一条**取**：标签判定改为「**跳过任意长度**的空白（含零宽字符）后判冒号」，代价是 `_statement_labels()`
      会多认几个真标签（例如 `x:` 后跟长注释再跟块），方向同样 fail-closed。
      ⑲**第十八轮登记的边界（POST_MERGE_FOLLOWUP；① 已于第十九轮据实更正，见 R108）**：①**`<` 的续接面收窄为
      「语句头仍只剩类型形参表」**——真 `tsc 5.9.3`／`esbuild 0.21.5` 实测：原文举例 `export type A = Record` 换行
      `  <string, number>;` **本身并不编译**（TS1005／TS1109），故「跨行续写的真类型实参」**不是合法写法**，
      旧文把它称作合法续写不确；可复现的**真**过严面是**生成器头**——`export function* gen` 换行
      `<T>(): Iterable<T> {}` 两工具均 rc=0 而本轮仍按「第二行以 `<` 起句」拒绝（已由夹具后缀
      `(registered over-strictness)` 钉住）；方向 fail-closed：`<` 曾是无条件续句字符，正因如此旧式类型断言
      `<unknown>(expr)();` 的整句会隐形）；
      ②**新 fail-closed 面**——`_js_opaque_spans()` 的 `crossed` 规则使**只在原始换行之下才闭合**的引号 span
      （`'`／`"` 字面量跨原始换行）判为「不能切分」而拒绝；全仓扫描 1156 个文件仅 8 个 `.vue` 命中
      （**全部是 SFC 模板属性**，如 `v-else-if="… ⏎ …"`），**无 `.ts` 命中**，四份真实闭包文件 `unsegmentable=0`；
      ③**据实更正**——第 ⑱ 条把跨行 `export type X = Foo<Bar>` 换行 `[];` 描述为「被切开的数组类型」，真 `tsc 5.9.3`／
      `esbuild 0.21.5` 实测第二行是**独立语句**（`[];` 真跑到产物），⑱ 的定性已就地改写（见 R104）。

## 8. 复核后修订

**第一轮**独立只读复核对冻结候选 `2437519d49535a457063f79f2ed2310579216253`（tree `6c2d5bc0…`）：
Round A（据实性＋门禁强度）判 **APPROVE**（S3×3／S4×2，无 S0–S2）；Round B（对抗性）判 **REQUEST_CHANGES**
（S2×1／S3×2／S4×1）。**第二轮**针对修订后的候选 `a55253170c9f4c6792aa0d1f2eca015856aeae3e`：
Round A² 与 Round B² 均判 **REQUEST_CHANGES**，并**一致指出同一类新缺口**——守卫只绑定了标志表达式体，
没有约束它 OR 的节点权威定义与消费接线，于是「标志体不动、权威被换成常量」仍是空断言（R9／R10）。
两轮都确认 R1–R7 的处置属实、无「声称已改但实际未改」。两轮均确认：抽取零行为变更（Round B 机械复算 18＋11 组输入 `TOTAL_MISMATCHES=0`）、
行数棘轮未上调、导航清单登记的是后端事实而非把期望值凑实现、清单不改运行态、冻结回执 VERIFIED、封禁说法属实、
排除项的「均 FAIL」结论属实。修订（绑定提交 `23928265`，工作树未改动的证据实验全部在 `/tmp`）：

| 编号 | 来源 | 发现 | 处置 |
| --- | --- | --- | --- |
| R1 | B·S2／A·S3-1 | 协作区断言只做令牌子串存在性检查：保留三令牌而破坏语义（`&& false`、`=== undefined`、能力被 `&&` 降级、节点权威只在注释／字符串里）仍 **PASS**，且 `!!` 等等价写法反而被拒 | 断言重写：先屏蔽注释与字符串字面量、用括号平衡扫描读 `computed` 实参、要求恰为「能力 `\|\|` 节点权威」两个操作数；`!!`／顺序／冗余括号／单行写法改为接受。§4-2 与 §5 同步改写 |
| R2 | B·S2（建议） | 「负例自检 6/6」是未入库的临时实验，无法防回归 | 把 13 例自检矩阵**内建进守卫**，每次运行都执行；回退到初版断言即自检失败（§5 实测） |
| R3 | A·S3-2／B·S3 | §6 把 `frontend_release_audit.py` 的失败写成「缺 `report.json`」不实：该文件是守卫自身输出，真实阻塞是 7 个 `EVIDENCE_SHA_MISMATCH:*` | §6 改为「上游受管运行态证据未按本 head 重建」；并把「该脚本会覆写自身输出、非只读」登记为 §7 候选 5 |
| R4 | B·S4 | 抽取后 `ContractFormPage.vue` 遗留无人消费的 `runtimeRoleCodes` computed（不产生 TS 错误，但违背「干净抽取」且可能新增 lint warning） | 删除该 computed 与其导入（`resolveRuntimeRoleCodes` 仍由 `buildContractFormPolicyContext` 消费，未变成死导出）：1894 → **1892**，生成物按注册目标重刷 |
| R5 | A·S4-1 | §1 表格易被读成「三条门禁都在 quick gate 内」 | 加表注：quick gate 前置项只含桥接守卫一条；另两条不在该聚合目标内 |
| R6 | A·S4-2 | `complexity_baseline_lock.json` 的 `max_lines`（5947）与守卫 `SIZE_LIMITS`（1900）是两把锁 | §4-1 明确两把锁都未上调，并区分二者；另指明 `p4_p0_03…md` 的行数由 `scripts/ci/verify_contract_form_split_evidence.py` 机器强制 |
| R7 | B·S3／A²·附注 | §6 引用的基线签名 `frontend_official_design_alignment_inventory FAIL incomplete={'internalVendorSelectorGapCount': 1}` **不是基线门禁输出**：基线与中间提交的 `--check` 均为 PASS（`gap=0`）；该串可复现，但来自单测负例 `test_check_fails_closed_when_completion_rule_has_gaps`（注入 `gap=1` 后断言 `main()==1`）的合成场景 | **撤回**作为基线签名，改为可复现的基线签名（两步 `--check` 陈旧），并把该串的来源如实标注；同组其余三项在基线即 PASS 一并写明。结论（单元门禁在基线为红）不变 |
| R8 | A（复核）／B（复核） | 文档若干数字（1905／1894、checks=63、roles=4／85、32 条 15 文件、lint 0/39、Ran 20 OK、非本批漂移归因） | 两轮独立复算一致，无需修订；`ContractFormPage.vue` 行号偏移按 R4 后重测改为 `1165 → 1166` |
| R9 | A²·S2-1／B²·S2 | 守卫只绑定标志表达式体，**不约束它 OR 的那个节点权威的定义**：`hasCollaborationNode := computed(() => false)`（或读空字面量、`.some` 改 `.every`、类型清单删项）时标志体不动，守卫仍 PASS——`A \|\| B` 在 `B ≡ false` 时是**空断言** | 新增两段断言：`hasCollaborationNode` 必须仍读 `props.renderModel?.zones.subordinate`、保留 `.some(`、向协作类型谓词提问；`collaborationKind` 必须仍声明 `chatter` 与 `activity`（可增不可减）；自检矩阵扩到「权威定义域」（+6 例） |
| R10 | A²·S2-2 | 守卫不检查 `:has-collaboration="hasCollaboration"` 这一**消费接线**：改成字面 `false` 或改传原始能力时协作区被永久隐藏／丢弃节点权威，守卫仍 PASS | 新增消费接线断言（`:has-collaboration="hasCollaboration"` ＋ `v-if="hasCollaboration"`），并入自检矩阵（+2 例） |
| R11 | A²·S4-1 | §5 写「8 个应拒绝形状」却枚举 9 项，其中 `!node && false` 在矩阵里并不存在 | §5 改为按矩阵**实际逐项**列举（7 接受 ＋ 15 拒绝，共 22 例） |
| R12 | A²·S4-2 | §6 把上游证据写成「2025-09-11 的旧件」，实际 `generated_at` 为 `2026-09-10T16:09Z`（上海时区即 2026-09-11） | 改为 **2026-09-11** |
| R13 | A²·S4-3／B²·S4 | 切换日志正文仍留旧数字（`1894`、`1167`、`gap=1`、「缺 report.json」、「6/6」）；且 B² 指出 R7 的「不可复现」措辞不实 | 切换日志加「本段取代正文相应数字」声明；R7 措辞按上表更正 |
| R14 | A²·观察／B²·S3 | §6 守卫边界段对「过严面」登记不全且措辞有歧义（`!(props.suppressCollaboration)` 实测被接受却列在「会失败」里）；`checks=63` 是硬编码字面量 | §6 改为按位点枚举的「接受面／拒绝面」清单，并登记 `checks=63` 为历史字面量 |

**第三轮**针对修订后的候选 `ce9450edbde7242a006a8d7fb3e322d6b0cf0ab6`：Round A³ 与 Round B³ **均判
REQUEST_CHANGES**（各 S2×2），并**独立收敛到同一根因**——文本形状门禁无论如何加码都**无法证明语义**：
「令牌齐全但语义被破坏」在每一位点都会重现。两轮均确认抽取零行为变更（`messages=0`）、行数锁未上调、
导航补登是后端事实、封禁属实。

| 编号 | 来源 | 发现 | 处置 |
| --- | --- | --- | --- |
| R15 | A³-F2／B³（根因） | ②③④仍是对**整份文件**的存在性／子串检查：谓词取反、清单惰性化、读错 zone、`.some`→`.every` 都能静默退休而守卫仍 PASS；语义与接线混在一层里无法分辨 | **语义下沉为单一权威**：`contractRuntimeVm.ts` 新增 4 个导出（`COLLABORATION_SURFACE_KINDS`／`isCollaborationSurfaceKind`／`hasCollaborationNode`／`resolveCollaborationVisibility`），宿主删除本地 `hasCollaborationNode` computed 与 `collaborationKind`，改为 `computed` 调用 `resolveCollaborationVisibility({capability,suppressed,nodes})`（净行数 383 → 383）；模板接线不变。S2-1 |
| R16 | B³（根因级最小修复方向） | 22 例自检矩阵**只能证明断言读对令牌**，不能证明语义；缺一层「用真值表执行证明」的载体 | **新增可执行真值表** `frontend/apps/web/scripts/contract_form_collaboration_authority_test.ts`（120 行）：导入**真实模块**，46 例——类型谓词 13（含大小写／空白／`note`／`audit`／空串／纯空白／`0`／`null`／`undefined`／对象）、节点权威 9、可见性 20，外加 4 条承重断言（节点权威须能单独点亮／抑制须能单独熄灭／能力须是**替代**而非条件／非协作节点不得点亮）。S2-2 |
| R17 | 承重（证明必须被机器执行） | 断言若不被聚合目标运行即形同不存在 | `make/frontend.mk` 新增 `verify.frontend.contract_form_collaboration_authority.unit`（`esbuild --bundle --platform=node --format=esm` ＋ `node`），并把该目标加入 `verify.frontend.scene_component_bridge.unit` 前置项，因而进入 `verify.frontend.quick.gate`／`verify.frontend.release.unit`；守卫新增**证明接线**断言（须仍含测试路径、目标定义与聚合前置项）。S2-2 |
| R18 | A³-F1／A³-F2／B³-F5 | ④是对**未剥 HTML 注释**的整份文件做子串检查（`:has-collaboration="false"` ＋ 别处一句注释即可 PASS，正是 R10 声称已关闭的向量）；`checks=63` 是硬编码字面量（运行时实为 124） | 守卫改**五断言职责分离**（委派／规则形状／类型清单被消费／消费接线／证明接线）；新增 `_blank_html_comments()` 与 `_blank_style_blocks()`（**保偏移**），先用 `_template_text()` 屏蔽二者、再用 `_start_tags()` 读**真实起始标签**，故「注释诱饵」与「令牌停放 `<style>`」两类向量关闭；`require()` 加全局计数器 `_CHECKS`，末尾改为运行时统计 `PASS checks=124 collaboration_self_check=26`。S2-2／S4 |
| R19 | B³-F3 | 22 例自检矩阵对「位置／诱饵」零鉴别力（`P1` vs 先剥注释的 `P4` 在矩阵上无分歧、真实宿主上相反） | 矩阵改为 **26 例（4 接受 ＋ 22 拒绝）** 的 **5 元组** `(name, host, module, makefile, expected)`，宿主／模块／Makefile 由工厂 `_collaboration_host()`／`_collaboration_module()`／`_collaboration_makefile()` 构造；调用签名改为 `collaboration_authority_failures(host, module, makefile)`。矩阵**单独**仍无位置鉴别力——该鉴别力显式来自真实宿主断言（第四轮位于 `:1223`，**第五轮后为 `:1726`**），已在 §6 如实登记。S2 |
| R20 | A³-F4／A³-F5／A³-F6／B³-F7 | ①矩阵增量算术：22 − 13 = +9，而修订表只记 R9 的 +6 与 R10 的 +2（差 1 条未登记）；②§3 的「5 个提交」与实测不符；③切换日志的 `13 例` 未被纳入「本段取代正文」声明；④提交链漏记两个功能提交 | ①§5 改为按矩阵**实际**列举并写明来源（缺口那条为接受面）；②§3 提交链按实测更正为 **8 个**并逐个标注角色；③切换日志追加本段并把 `13 例`、`checks=63`、`22 例`、`1894`、`1167`、`6/6` 一并纳入取代声明；④同②。S3／S4 |
| R88 | A¹⁵-F1／B¹⁵-S1（**S1**×2） | **再导出族少一个空格即绕过整条规则**：`_COLLABORATION_RE_EXPORT` 以 `export\s+` 起头，而 `export*from'./x'`／`export{a}from'./x'`／`export*as ns from'pkg'` 都是**合法且加载期求值**的拼写——它们既不匹配该模式、也不被 `relative_edges()` 跟边，而闭包出口阶梯**没有兜底**（不匹配即放行）⇒ 整条链既不看也不拒。两位复核各自用真工具链复现：A¹⁵ 把相对再导出注入真闭包文件并在真浏览器域读到 `ruleAlive=false`；B¹⁵ 用真 `@/` 别名（`tsconfig.json` 的 `"@/*": ["src/*"]`）＋ 真 `esbuild`（0.21.5）证明探针真进了浏览器 bundle，且 `vue-tsc`／`eslint` 均通过 ⇒ **可部署** | ①`_COLLABORATION_RE_EXPORT` 的 `export` 后与 `from` 前改为 `\s*`（`relative_edges()` 复用同一常量，跟边同时恢复）；②闭包出口阶梯补**默认拒绝**：未被「声明形状」或「本地具名导出」读到的 `export` 一律拒（权威体层早有同构兜底，闭包层此前是**沉默放行**）。矩阵 **+5**（三拒 ＋ 一接受 ＋ 兜底一拒）。实测：六条载荷在新树 6 拒／旧树 0 拒，还原即 PASS；停用兜底时自检点名 `export @sealed class` 夹具。S1×2 |
| R89 | A¹⁵-F2（**S1**） | **读取窗口先截断后折叠空白**：`_statement_text` 先取 `source[offset:offset+400]` **再** `re.sub(r"\s+", " ")`，于是 `export` 之后垫 400+ 空格即把语句读成 `export `，出口阶梯**每一级都失配** ⇒ 刚收口的三条拒绝面（模块级绑定／`export =`／再导出）可用空白绕过；A¹⁵ 用同一手法在真闭包文件内联复现（无新增文件）并读到浏览器域真死 | 读取窗口改为**按折叠后的字符计数**（空白随读随折，只有文本能填窗口），并把 `_statement_excerpt` 一并改为读同一份语句文本（拒绝消息不再引用填充空白，实测消息从 `export` 变为 `exportconstdead=()=>1`）。矩阵 **+3**（两拒 ＋ 一接受：垫空格的**合法声明**仍须被接受，否则只是把 fail-open 换成 fail-closed）。实测：`export` ＋ 410 空格 ＋ `const dead = () => 1` 旧树 ACCEPT／新树 REJECT；停用该修复时自检点名垫空白接受夹具。S1 |
| R90 | A¹⁵-F3／A¹⁵-F4（＝B¹⁵-S2／B¹⁵-S3）（**S2**／**S3**） | ①新增的形状规则用 `[^>]*` 匹配泛型参数，`type Wrapped<T extends Box<number>> = T;` 与 `function read<T extends Box<number>>(…)` 被判「不是声明」⇒ **新增假 REJECT**（权威体层与闭包成员层同时）；②`import'./x'` 这类**无空白副作用导入**（合法，且 specifier 相对可读）被报「imports a module the guard cannot open」⇒ **既有假 REJECT** ＋ 消息不准 | ①形状正则的泛型段改为 `[^;]*`（以语句自身的 `;` 为界，不再止于第一个 `>`，且组外补回 `\s*`）；②闭包 import 分支的 `import\s+` 改为 `import\s*`；③R86 行按 B¹⁵-S4 就地补注「收口为部分」。矩阵 **+4**（宿主一接受一拒 ＋ 闭包两接受）。实测：两类载荷旧树 REJECT／新树 ACCEPT。S2／S3 |
| R21 | A³（对抗性回归） | 需要证明「联合门禁」对新型向量仍有效，且**边界必须诚实** | 在 `/tmp/r15guard` 影子内对真实守卫 ＋ 真实证明跑 **17 个攻击向量**，**16 个被拒**（绑定改字面 `false` ＋ 注释诱饵、门控改字面 `false`、协作区整体注释、槽名改 `#collaborationSurface` ＋ 诱饵、`v-if`→`v-show` ＋ 诱饵、`v-bind` 展开对象、绑定移到别的元素、令牌停放 `<style>`、委派丢抑制属性、节点权威改读 `zones.primary`、清单空／删项／惰性化、`||`→`&&`、去掉抑制门、节点权威非存在性化、证明被摘出聚合目标、证明不再被 `esbuild`＋`node` 运行）；**唯一仍 PASS 的是 V9**（`watchEffect` 覆写），按 §6 如实登记为已知运行态旁路，**不声称已覆盖**（第四轮按实测更正：V9 不构成旁路，见 R26）。S3 |

| R22 | A⁴-F1（S2） | ①「委派」仍只做**令牌级**检查：宿主保留全部令牌、但把委派裹进 `()`、加 `!`、用逗号丢弃结果、尾随 `\|\| false`、`? :` 常量化，或自行再声明一个同名权威，都能让接线语义失效而守卫仍 PASS——「令牌齐全但语义被破坏」在**委派位点**原样重现 | ①升级为**委派等值**：实参只做确定性脱糖（冗余括号／`(): T =>` 返回类型标注／仅含 `return` 的块体），归约后**必须恰好等于**指向单一权威的委派式；并新增两条——宿主**不得自行声明**该权威（`def _collaboration_authority` 正则），且**必须从 VM 导入**它；同时把证明的断言全部改为 `strictEqual` 并补 5 例可见性边界（46 例 → **51 例**），堵住「真值对但返回类型被削弱」。S2 |
| R23 | A⁴-F2（S3） | ④只断言 `v-if="hasCollaboration"` **存在**，不约束它挂在哪：把插槽移到别的元素、甚至移出 `ObjectTaskPage`，协作区就不再受该标志门控，而守卫仍 PASS | 新增 `_start_tag_spans()`／`_element_spans()`（深度计数求元素区间），要求 `#collaboration` 起始标签**落在承载该标志的 `ObjectTaskPage` 元素区间之内**，并把 `:has-collaboration` 绑定限定在该元素的起始标签上。**（第五轮更正）** 「区间内」**不等于**「直接子元素」——插槽嵌进该元素的子组件仍满足「区间内」却不渲染，R33 已改为最近严格包含元素判定并同步 §5／§6 措辞。S3 |
| R24 | A⁴-F3／B⁴-F5（S2／S3） | ⑤只绑定「测试路径出现在 Makefile 里」，不绑定**它真的被执行**：配方换成 `@echo` 或删掉 `node` 行仍 PASS；且证明文件可被静默改写（哪怕改成 no-op） | ⑤改为解析该目标的**配方块**，要求同时含 `esbuild … --bundle --platform=node --outfile=<x>` 行**与** `node <x>` 执行行，且仍须是 `verify.frontend.scene_component_bridge.unit` 的前置项；另加⑥**内容绑定**：证明文件 sha256 记在守卫里，改动证明必须同 commit 改摘要（负例实测：摘要改错即 FAIL `the executable collaboration authority proof changed`）。**（第五轮更正）** 该条只绑**源码**、**不**绑 make 的实际执行物，故「运行中的证明＝被复核的证明」原措辞为**过度声称**；实际执行物由 R31 的 outfile 独占绑定覆盖，残余面见 §6。S2／S3 |
| R25 | B⁴-F3／B⁴-F4（S3） | ④读的是**整份文件**（含 `<script setup>`）：把绑定改字面 `false` 再在脚本里留一句 JS 注释或一个同名字符串，即可让子串检查复位并 PASS；且 §6 旧「接受／拒绝面」清单按**旧口径**写成，与真守卫实测不符 | ④读模板前**再丢弃 `<script setup>` 段**（在屏蔽 HTML 注释与 `<style>` 之后，保偏移），JS 注释／字符串诱饵两类向量关闭；自检矩阵由 **26 例扩到 36 例（4 接受 ＋ 32 拒绝）**；§6 的接受／拒绝面按真守卫**逐项实测**重写（第四轮记为 **7 接受 ＋ 10 拒绝**；**第五轮更正**：同一驱动实测为 **6 接受 ＋ 10 拒绝**，共 16 个形状，第四轮计数多 1）。S3 |
| R26 | B⁴-F7／A⁴（S4） | §6 把 A³-V9（`watchEffect` 覆写）登记为「已知运行态旁路」，与实测不符；另需确认 `source/inventory/审计脚本` 面无回归 | 独立复算更正：`hasCollaboration` 是只读 `computed`，覆写触发 `Write operation failed: computed value is readonly` 且**值不变**，故 V9 **不是**旁路（守卫不拒绝、也不构成绕过）；§5／§6／§7 措辞按实测更正。同时复算 `source/inventory/审计脚本` 面无回归（`git status --untracked-files=all` 无未跟踪文件，构建生成物均已入库）。另更正上一轮 §6 的一处反证声明：第四轮称「去掉 `_blank_html_comments` 后矩阵立即报出 `region slot renamed with a comment decoy`」**不可复现**（实测矩阵判定全部不变），原因是该用例的诱饵在元素**外**、被父子绑定规则先一步拒掉；本轮已把诱饵挪到元素**内**，矩阵遂对注释屏蔽**真有**鉴别力（复算：改恒等函数后矩阵立刻只报出该用例）。S4 |
| R27 | 本轮自查（据实性） | §5 声称 `verify.frontend.quick.gate` **PASS**，但按本批 head 复跑为 **FAIL**：`c28a03c6` 把协作区判定移出宿主 `.vue` 之后，该族两个指纹绑定生成物（`component-professionalization-inventory-v1.json`、`visual-projection-inventory-v1.json`）未按注册目标重刷（最后一次刷新停在 `23928265`） | 按注册刷新目标 `refresh.frontend.rendering_detail.inventory` **二次刷新**两件；复核 `git diff` 为**仅** `inputDigest`／`sourceIdentity` 变化、`surfaces` 逐条不变（无内容漂移）；复跑 `verify.frontend.quick.gate` **PASS**。§3 生成物清单由 2 件更正为 **4 件**，§5／§6 的 quick gate 口径按复跑结果更正。S3 |

| R28 | B⁵-V21（S1） | `_normalize_flag_argument` 把块体的 `return` 设为**可选**：`computed(() => { <委派>; })`（箭头返回 `undefined`）与正确委派**归约相等**（复算实测 `True`）→ 守卫 PASS、标志恒假、协作区永不渲染 | 块体必须真含 `return`（`\{return(.*?);?\}` 取代 `\{(?:return)?…`）；矩阵加 2 例（1 接受「块体仅含 `return`」＋ 1 拒绝「块体忘写 `return`」）与 1 例「块体多一句语句」；真实树向量 V21 实测被拒。S1 |
| R29 | B⁵-V08（S1）／V09（S1）／V13（S2） | ⑤用**子串**匹配证明路径（同前缀兄弟 `…test.ts.decoy.ts` 可顶替）；`re.search` 只取**首个**目标定义（第二条 recipe `@true` 不被看见）；执行行正则 `[^\s#]*node` 只要求令牌**以 node 结尾**（`/tmp/b5/fakenode` 可假 PASS） | ⑤改为：目标**唯一定义**（`^target\s*:` 计数必须为 1）；`esbuild` 输入须是**字面量令牌**且逐字等于常量；`esbuild` 与 `node` 按 **basename**（`posixpath.basename`）锚定，执行行只允许恰好 `node <outfile>` 两个令牌。矩阵加 4 例；真实树 V08／V09／V13 实测被拒。S1／S2 |
| R30 | B⁵-V23（S1） | ①只查宿主**导入了同名符号**，不绑 `from '<模块>'` 的 specifier：`import { resolveCollaborationVisibility } from './collaborationVisibilityShim'`（恒 false）可两层同绿 | ①新增 `_import_specifiers_for()`——宿主必须以**字面** `from './contractRuntimeVm'` 导入；并加⑧**模块同一性**：宿主与证明的 specifier 各自经 `_resolved_module_path()` 解析后必须落在同一个真实模块文件 `…/contractForm/contractRuntimeVm.ts`。矩阵加 1 例；真实树 V23 实测被拒。S1 |
| R31 | A⁵-S2-F1（S2） | ⑥只绑证明**文件**（sha256），不绑 make **实际执行物**：在 `@node <outfile>` 前插 `@cp /tmp/evil.mjs <outfile>`（或第二条 esbuild 覆盖同 outfile）即绕过而守卫仍 PASS；§8 R24「运行中的证明＝被复核的证明可机器核对」为**过度声称** | ⑤新增 **outfile 独占**：该 outfile 字面量在配方里只允许出现在**两行**（唯一 bundling 行与唯一执行行），执行行须在其之后；R24 措辞改为「源码层内容绑定 ＋ 配方层路径／独占性绑定」，残余面（`$(VAR)`、同名别名、手工执行）在 §6 登记。矩阵加 2 例；真实树 S2-F1／S2-F1b 实测被拒。S2 |
| R32 | A⁵-S2-F2（S2）／B⁵-V01／V02（S2） | ③只要求谓词体**出现**常量名与 `.includes(`：`void COLLABORATION_SURFACE_KINDS; return ['chatter','activity','ghost'].includes(…)` 可两层同绿；三个权威体只做**令牌存在性**，`if (typeof window !== 'undefined') return false;` 之类**运行期环境开关**（node 下证明看不见）可带全部令牌通过；§8 R15 的「已封堵清单惰性化」为**不实** | 三个权威体改为**单一 `return` 表达式**判定（`_sole_return_expression`）：必须恰好一条 `return`，且**在该返回表达式的文本内**做令牌检查，并**禁止环境探针**（当时用 `typeof window`／`document`／`self`／`globalThis`／`process`／`import.meta` 等 13 种拼写的**黑名单**）；故「常量名停在死语句里」「ghost 清单」「环境门」都被拒。矩阵加 5 例；真实树 S2-F2／V01／V02 实测被拒。S2。**（第六轮更正）** 该「13 种拼写黑名单」已被 B⁶ 用 `globalThis['window']`／`typeof(self)`／`typeof(window)`／`('window' in globalThis)`／`Function('return typeof window')()` 整族绕过；第六轮**删除黑名单**，改判**整表达式等值**（见 R35），探针族由「逐拼写枚举」变为**结构性**被拒——本行的「禁止环境探针」措辞自 R35 起按后者理解 |
| R33 | A⁵-S3-F3（S3）／B⁵-V05／V20／V20b／V06（S2–S3）／第五轮自查 | ④只判「槽起始标签落在 `ObjectTaskPage` 元素区间**内**」：槽可嵌进**子组件**（真实宿主同区就有 `<CanonicalActionBar>`）——编译 0 error、协作区不渲染、守卫却绿；元素区间用**原始正则**计深度，属性字符串里的同名标签可扰动（V06）；第五轮自查又发现**未闭合子元素**会让父级结束标签**静默丢弃**其区间，从而把外移的槽重新「收进」元素 | ④改为**直接子元素**判定：取槽起始标签的**最近严格包含元素**（`_innermost_element`），它必须**就是**承载标志的 `ObjectTaskPage` 区间；元素区间改由**引号感知的标签扫描**（`_scan_tags`／`_element_spans_all`）一次算出，属性字符串与注释里的标签不参与；未闭合元素在父级结束处**逐个收尾**（不再丢弃）。矩阵加 3 例；真实树 S3-F3／V06 实测被拒。S2／S3 |
| R34 | B⁵-V03／V04（S2）／A⁵-S4-F4／S4-F5（S4） | 页面→宿主的 `:suppress-collaboration` **完全无门禁**（改 `false` 即失控开放）；`:show-collaboration-panel` 只做**文件级子串**校验，可被**旧画布**的同名绑定冒充；正文「断言全部 `strictEqual`」不实（`:27` 为 `assert.ok`）；R27「`surfaces` 逐条不变」不精确（实测宿主条目 digest `e8f831bb…`→`67354386…`） | 新增⑦**页面侧元素级断言** `collaboration_page_wiring_failures()`：`ContractFormDriverHost` 起始标签须同时带 `:show-collaboration-panel="showNativeCollaborationPanel"` 与 `:suppress-collaboration="dispatchContextCollaboration"`，模板里**每一处**同类动态写法都必须绑同一页面权威，并绑两处页面侧权威派生；`:27` 改 `strictEqual`（证明 51 例不变）；R27 措辞更正为「条目集合与结构不变，仅 `digest`／`currentInputDigest` 等指纹字段变化」。真实树 V03b／V03c／V04a／V04b 实测被拒。S2／S4 |
| R35 | B⁶-V01–V07（**S1**）／A⁶ 过严面（S4） | 三个权威体的「运行期环境探针」用**黑名单**实现，等价拼写整族绕过（实测 M01 `globalThis['window']`、M02 `typeof(self)`、M03 `typeof(window)`、M04 `('window' in globalThis)` 全部 LEAK），两层同绿而浏览器里协作区恒灭；反向地，合法形状被**误拒**（插槽前的 `{{ … }}` 插值、`<br>` 等 void 元素被当未闭合子元素） | 删除 `_COLLABORATION_ENVIRONMENT_PROBES` 黑名单，三个权威体改判**整表达式等值**（新增 `_COLLABORATION_CANONICAL_KIND_PREDICATE`／`_COLLABORATION_CANONICAL_NODE_AUTHORITY`／`_COLLABORATION_CANONICAL_VISIBILITY_RULE` 三条规范式 ＋ `_expression_failures()`；`_sole_return_expression` 先做注释屏蔽与括号属性访问归一化）；新增 `_HTML_VOID_ELEMENTS`（area/base/br/col/embed/hr/img/input/link/meta/param/source/track/wbr 视为自闭合）与 `_scan_tags` 的 `{{ … }}` 跳过。矩阵 +5（探针变体 4 拒绝 ＋ void 接受 1），真实树 M01–M04 修复后全部 REJECT。S1／S4 |
| R36 | B⁶-V07 模块侧（**S1**） | 三个权威体用 `_blank_comments` 定位函数体后**再从原文读回** → 把合规 body 写进**字符串字面量**、把真 body 换成 `typeof window` 门控，两层同绿（M06） | 新增 `_blank_comments_and_strings`／`_function_body_span`／`_authority_body`／`_declared_kinds`：先按「注释＋字符串**都**屏蔽」定位函数体，再从**原文**读回该区间。矩阵 +1（H60）；M06 修复后 REJECT。S1 |
| R37 | B⁶-V13（**S1**） | 模板里 `{{ '' /* '</CanonicalActionBar>' */ }}` 被标签扫描当成**假闭合**，插槽被重新「收进」`ObjectTaskPage` 区间（M11） | `_scan_tags` 跳过 `{{ … }}` 插值段——Vue 把插值读成**表达式**而非标记。矩阵 +1（H63）；M11 修复后 REJECT。S1 |
| R38 | B⁶-V19（S1）／V26／V27／V29（S1） | `import { X as _rcv }` 别名（调用点原文不动）与 `const { X } = _shim` 命名空间解构让「同一本地名」绑定落空；`$(VAR)` **变量名目标**可二次定义证明目标（后 include 的 `make/*.mk` 同样可定义）；`cp attacker.mjs $(VAR)` 覆盖 outfile | 新增 `_string_literal_at`／`_authority_named_imports`（要求 `local == imported`，返回 `(local, imported, specifier)`）＋ `collaboration_flag_failures` 新增「解构声明」拒绝；`collaboration_proof_failures` 增加 `other_make_sources` 参数（主树传入 `Makefile` ＋ `make/*.mk` 除 `frontend.mk`），新增 `_MAKE_DIRECTIVES`／`_rule_name_part`／`_variable_named_rule_lines`，拒绝**变量名目标**与任何含 `$(`／`${` 的配方行。矩阵 +4（H61／H62／H64／H65）；M19／M26／M29 实测 REJECT（M18 据实登记为修复前已被拒，非本轮项）。S1 |
| R39 | B⁶-V20／V21／V22（**S1**） | 页面侧只做整文件子串／双引号正则：`v-bind` 之前先写**单引号**字面量 ＋ 双引号 decoy（M20）、`v-bind="attrs"` 对象展开（M22a／M22b）都能让守卫绿而 Vue 取字面量 | 新增 `_HTML_ENTITIES`／`_decode_entities`／`_tag_attributes`（两种引号 ＋ 实体解码）／`_bound_dynamic_values`（用 `_scan_tags` 取每个开标签）：`collaboration_page_wiring_failures` 拒绝宿主标签上的**任何 `v-bind`**，要求 `bound[':'+attr] == [authority]`（唯一绑定）并逐处检查动态值；新增 `_COLLABORATION_PAGE_SELF_CHECK`（10 例，2 接受 ＋ 8 拒绝）＋ `_collaboration_page()` 夹具——页面层此前**无矩阵**。M20／M22a／M22b 实测 REJECT。S1 |
| R40 | A⁶-S3×3 | §6 称「矩阵对 HTML 注释屏蔽**有**鉴别力」「(a) 引号感知有鉴别力」不可复现；接受面枚举比标题多 1 项（7 项 vs 标题 6） | 按 **77 例**复算更正（第七轮按 **99 例**复算，结论一致）：恒等化 `_blank_html_comments`／`_blank_style_blocks` 后**零翻转**（撤回该鉴别力声明，改登记为纵深防御）；引号感知换成「第一个 `>` 即结束」的朴素读法**零翻转**（改登记为「该向量整例仍有鉴别力〔第四轮守卫 `74160041` 实测 PASS 它〕、但单项不再被矩阵看见」）；接受面按实测重写为 **8 项**（第七轮为 **10 项**，两处新增见 §6）。S3 |
| R41 | A⁶-S4×2 ＋ 据实性 | §6 的「权威体里**任何**非单一 `return` 写法」措辞过宽（实测**跨行**写单一 `return` 仍被接受）；`docs/ops/iterations/delivery_context_switch_log_v1.md` 第四轮段**重复**编号 ⑦ | 措辞收窄为「按归一化后的**整表达式等值**判」；另**新增登记**两条真正的过严项——权威体**冗余外括号**（第五轮该写法被接受、第六轮被拒）与配方行含任何 `$(`／`${`；switch log 该段重编号为 ⑦／⑧／⑨。S4 |
| R42 | A⁷-F1／B⁷-F1（**S1**） | 「错位读窗」：`_blank_comments_and_strings` 内部夹着会**改变文本长度**的括号属性归一化（`x['m']`→`x.m`），于是「在屏蔽文本上定位 span、再从原文读回」**定位错位**——被判的不是真 body；构造式假接受实测 `window == decoy: True`（把合规 body 写进诱饵位即可两层同绿） | `_blank_comments_and_strings` 改为**保长**（变长变换拆出）；新增 `_body_window(source, name)` 并**自证对齐**（定位后断言 `_blank_comments_and_strings(source[span]) == blanked[span]`，否则报 `has a misaligned read window`）；顶层新增 `form_host`／`contract_form_vm`／`contract_form_page`／`frontend_makefile`／偏移样本的**保长 require**。真实树 `contractRuntimeVm.ts` 复测 shift=0，故 HEAD 未触发——属**潜在不健全**，非已利用。S1 |
| R43 | A⁷-F2／B⁷-F2（**S1**） | **模块级加载期环境门控**两层都不覆盖：`if (typeof window …)`、`Array.prototype.includes` 投毒、`import.meta` 等在模块**加载**（import 求值）时就生效，而守卫此前只读三个权威体的**调用期**表达式 | 新增 `collaboration_module_scope_failures(module)` 并纳入 `collaboration_authority_failures`：整模块禁**运行环境全局**（含 `import.meta`）；顶层语句须属声明白名单；拒副作用 `import`／`export * from`／`export default`。实测 V22／V23／V23b／V24 由 OLD=GREEN → NEW=REJECT。S1 |
| R44 | A⁷-F3a／B⁷-F3b2 ＋ B⁷ 编译器探针 | `#collaboration` **二次声明**——正确插槽之后再写一个（空）插槽，Vue 取**后**声明者，协作区实际不渲染而守卫 GREEN；插槽内面板 `<NativeCollaborationPanel v-if="false">`／`v-show="false"` 同理整块不渲染 | `#collaboration` 必须**恰出现 1 次**；插槽内须含 `<NativeCollaborationPanel` 起始标签，且该标签不得带**字面死门**（`v-if="false"`／`v-show="false"`／无值 `v-show`）。 |
| R45 | A⁷-F3c／F3d／A2 ＋ B⁷ 编译器探针 | 承载标志的元素**被字面死门关掉**（`v-if="false"`／`v-show="false"`），或承载元素的**任一祖先**被关掉——插槽仍在元素区间内，但协作区恒灭而守卫 GREEN | 新增 `_tag_dynamic_values`／`_LITERAL_FALSY_GATES`／`_dead_gate_failures`／`_ancestor_dead_gate_failures`：载体**及其所有祖先**逐个做字面死门检查；页面侧对 `ContractFormDriverHost`（含祖先）同判——实测 R45a／R45b／R45c 全部 OLD=GREEN → NEW=REJECT。 |
| R46 | B⁷（过严面） | 宿主 `:has-collaboration` 按**双引号正则**读，合法的单引号写法（`:has-collaboration='hasCollaboration'`）被**误拒** | 宿主侧改经 `_tag_dynamic_values`／`_tag_attributes` 按**属性表**读（两种引号都接受），单引号写法转为**接受面**并补 3 例矩阵回归；`#collaboration` 与面板断言同改按属性表。S4 |
| R47 | A⁷／B⁷ 据实性 | §3 旧写「**1420 → 2528** 行」与真守卫不符；§6 旧写「任何**运行期**环境探针**不再可能**两层同绿」为**全称过宽**——只覆盖三个权威体的**调用期** | 按实测更正为 **445 → 3136 行**；全称表述收窄为「三个权威体**调用期**内的环境探针不再可能两层同绿，**加载期**门控由第二层⑨覆盖」并登记残余面。S4 |
| R48 | 本轮自查（F2 残余） | 顶层**绑定**带**加载期初始式**仍 GREEN：`export const degraded = typeof screen !== 'undefined' && (KINDS as …).splice(0);`——`screen` 不在环境全局黑名单、形状又是「声明」，于是「证明浏览器域在 import 之后」在门禁下**成立** | 顶层绑定形状**白名单**：顶层 `const`／`let`／`var` 直接拒；`export` 绑定唯一起见放行**由字符串字面量组成的 kind 清单**（`_COLLABORATION_STRING_LITERAL`／`_COLLABORATION_MODULE_BINDING`／`_COLLABORATION_MODULE_KINDS_DECLARATION`），并把 `enum`／`namespace`／`using` 移出白名单（其成员同样在加载期求值）。实测：去掉该规则矩阵翻 **4** 例、放回 enum/namespace/using 翻 **2** 例。S1 |
| R49 | 残余面登记（本轮） | （a）`import` 链上**第三方模块**的加载期行为仍不可见（属模块图／打包层）；（b）fail-closed 过严面仍在：`v-bind` 对象展开、同文件 helper、`computed<T>()`、权威体**冗余外括号**、页面 `:suppress-collaboration` 的等价包装、顶层声明形状白名单（非 kind 清单的本地缓存被拒）；（c）守卫体量 **3136 行**越过 3000 行阈值，`split_plan_queue.md` 项由 **P2 升为 P1** | 如实登记为下一轮候选，**不声称覆盖**；收敛需共享的**表达式级解析器**与模块图证据（§7 第 6／7 项）。S4 |
| R50 | A⁸-S1-1／B⁸-洞1（**S1**） | **导出前缀的加载期声明未被扫描**：`_COLLABORATION_EXPORT_DECLARATION` 仍含 `enum`／`class`／`namespace`／`declare`／`abstract`，顶层语句白名单也仍放行 `declare`／`abstract`／`async`——`export class Degraded { static x = <加载期表达式> }`、`export enum`、`export namespace`、`export abstract class` 与裸 `abstract class` 的成员／静态初始式都在**加载期**求值，而语句游走从不进入声明体，故门禁 GREEN | `_COLLABORATION_EXPORT_DECLARATION` 收为 `const`／`let`／`var`／`function`／`type`／`interface`／`async`；新增 `_COLLABORATION_EXPORT_LOAD_TIME_DECLARATION` （`export (enum|class|namespace|abstract|declare|using|module)`）在**白名单之前**拒绝；`declare`／`abstract`／`async` 移出 `_COLLABORATION_MODULE_DECLARATIONS`（白名单条目是对「该形状不可能跑加载期代码」的承诺，而 `abstract class` 的静态字段初始式正好在加载期跑）。矩阵 **+3**（`export class` 静态初始式／`export enum` 成员／裸 `abstract class`）；真实树向量 A8-1…A8-5 （另含 `export namespace`、`export abstract class`）**全部 OLD=GREEN → NEW=REJECT**。鉴别力：两个模式同时回退翻 **2** 例、仅裸声明白名单回退翻 **1** 例（单独替换 `_COLLABORATION_EXPORT_DECLARATION` 而保留新规则时**零翻转**）。S1 |
| R51 | A⁸-S2-2（**S4**：据实性 ＋ 过严回归） | 第七轮把括号属性归一化从 `collaboration_flag_failures` 移出（改要求 `_blank_comments_and_strings` 保长）后，`props['showCollaborationPanel']` 由**接受**变**误拒**，而 §6 仍写「仍接受」——同一份文档里两处互相矛盾 | `body` 改为 `_computed_argument(_blank_string_literals(_normalize_bracket_property_access(_blank_comments(host))), "hasCollaboration")`：归一化前置、屏蔽仍保长；`props['…']` 恢复为**接受面**并进入矩阵（+1 例接受）。实测 A8-8 OLD=REJECT → NEW=GREEN；把该归一化去掉翻 **1** 例。S4 |
| R52 | B⁸-洞4（**S1**） | 插槽计数按**字面 `#collaboration` 文本**：`v-slot:collaboration` 是**同一个插槽**的另一种拼写，写成第二次声明时可顶掉已接线那个（B⁸ 用 Vue 编译器 ＋ `createSlots` 实测 `slots.collaboration() = []`）而守卫仍报「恰出现 1 次」 | 新增 `_slot_names(tag)`（`#x` ≡ `v-slot:x` ≡ 无参 `v-slot`）；`collaboration_consumption_failures` 改按**元素级插槽名**计数，协作区模板由 `slot_declarations` 派生（不再对模板文本做 `findall`）。矩阵 **+2**（`v-slot:collaboration` 单声明接受、同一插槽以 `v-slot:` 二次声明拒绝）。实测 B8-V30 GREEN → REJECT、单声明写法 REJECT → GREEN；把归一化换回字面计数翻 **2** 例。S1 |
| R53 | A⁸-S2-1（**S1**） | 插槽内面板只查**自身标签**的字面死门：`<div v-if="false"><NativeCollaborationPanel … /></div>` 的**祖先**未查，协作区恒灭而守卫 GREEN（载体／宿主侧第七轮已查祖先，唯独面板漏了） | 面板区间改为从**元素表**取（以 `tag_end`／`end` 边界过滤，不再对子树做起始标签扫描），并对面板追加 `_ancestor_dead_gate_failures(template, panel_start, panel_end, …)`。矩阵 **+1**（面板被字面假祖先包住）。实测 A8-6 GREEN → REJECT；去掉该检查共翻 **3** 例（载体祖先／面板祖先／宿主祖先）。S1 |
| R54 | B⁸-POST（**S4**：过严面） | 模板**文本**里的 `{{ '#collaboration' }}` 插值按字面计数被当成「第二次声明」而**误拒**——Vue 里它根本不是插槽声明 | 同 R52 的元素级插槽计数顺带关闭；转为**接受面**并进矩阵（+1 例）。实测 B8-V27 REJECT → GREEN。S4 |
| R55 | B⁸-S2 ×2（登记不修） | （a）字面死门按**有限枚举表**判（`_LITERAL_FALSY_GATES` 共 11 条拼写：`false`／`0`／`null`／`undefined`／`void0`／`!true`／`!1`／`!!false`／`!!0`／`''`／`""`，另在工具层去掉空白与外层括号并小写化），表外的等价写法（实测：`!!''`、`!''`、`0.0`、`NaN`、`Boolean(0)`、`1>2` 均判为**真实谓词**即不被拒）不在判据内；（b）`v-bind:[动态属性名]` 不会被属性表收集 | 如实登记为下一轮候选（§7 第 11 项①②），**不声称覆盖**。S2 |
| R56 | B⁸-洞2／洞3（**S1**） | （a）`_blank_comments` **不识别字符串**：`export type T = "a//b";` 里的 `//` 打开行注释、吞掉同行其后的顶层门控；`'x/*y'` 打开一个**永不闭合**的块注释、吞掉文件其余部分——两层都看不见那些语句；（b）`import { x } from './y'` 与副作用 `import './y'` 执行的是**同一段**第三方加载期代码，判据却只拒后者（只查 `\bfrom\b`） | （a）`_blank_comments` 增**引号不透明**处理（`'`／`"`／反引号整段跳过，含 `\` 转义）；（b）新增 `_COLLABORATION_MODULE_IMPORT_SPECIFIERS`（真实 VM 的两个运行时 import：`../../app/contracts/v2/store`、`./valueUtils`），`import` 分支从**原文**读回 specifier，`import type` 豁免、其余不在清单内即拒。矩阵 **+3**（字符串行注释屏蔽／字符串未闭合块注释／未复核 import）。实测：注释感知翻 **2** 例、把 `./collaborationPoison` 加入清单翻 **1** 例（清单空集化零翻转）。S1 |
| R57 | A⁹-S2／B⁹-S1b（**S1**） | **正则字面量不被识别为不透明 span**：`return /[']/g` 在字符类里的引号开启一个**幻影字符串**、闭合在下方某处，把这两点之间的**顶层门控**整段吞掉（B⁹ 用真实 VM ＋ SSR 实测 `region present = false`；A⁹ 另报**未闭合**块注释／字符串同样让「读窗其实不存在」却被当作存在继续读） | 新增 `_js_opaque_spans()`：把注释／字符串／模板／**正则**统一为 `(start, end, kind, terminated)` 四元组（正则由**前置字符表**（18 个字符） ＋ 13 个前置关键字 `await`／`case`／`delete`／`do`／`else`／`in`／`instanceof`／`new`／`of`／`return`／`typeof`／`void`／`yield` 判定，**同一行闭合**才算、否则回滚，故模板里的 `v-else />` 不再被误判），`_blank_comments`／`_blank_string_literals` 由它派生；`collaboration_module_scope_failures` 开头对**未闭合 span 直接失败**。矩阵 **+2**。实测：停用未闭合拒绝翻 **1** 例；停用正则识别在矩阵上 **0** 例（矩阵用例均**同一行**闭合），但**第十轮向量** `R57-1`／`R57-2` 在**真守卫**上实测 OLD=GREEN → NEW=REJECT——归因更正为「**同轮新增的未闭合 span 拒绝**顶住了它」，并非正则识别可在矩阵上直接翻转。S1 |
| R58 | A⁹-S1／B⁹-S2（**S1**） | import 的 specifier 取**读窗内最后一个字符串字面量**（在**原文**上取，故含注释里的引号）：`import { x } from './collaborationPoison' /* './valueUtils' */` 靠注释诱饵通过已复核清单；TS 丢弃注释，**真正加载**的是前者（B⁹ 挂真实产物：新模块在加载期改 `Array.prototype.includes`，浏览器域节点权威恒 false） | 新增 `_collaboration_import_failure()`：在**注释屏蔽后**的语句文本上、按 `\bfrom\b` 子句读 specifier；specifier 之后**还有非空文本即拒**（判不出加载哪一个）、无 `from` 的副作用 import 拒、`import type` 豁免。矩阵 **+3**（注释诱饵／specifier 后有文本／正向镜像入接受面）。实测：规则换回第八轮形状翻 **1** 例。S1 |
| R59 | B⁹-S1（**S1**） | **计算插槽名二次声明顶掉已接线插槽**：`#[collaborationRegionSlot]`（其值为 `'collaboration'`）编译器**取后者**，协作区空渲染，而守卫仍报「恰出现一次」（B⁹ 用真 `@vue/compiler-sfc@3.5.27` ＋ SSR 实测） | `_slot_names()` 对 `#[…]`／`v-slot:[…]` 报哨兵 `_SLOT_NAME_DYNAMIC`；`collaboration_consumption_failures` 增循环——计算名元素若其**最内层元素**落在已接线区间内即拒（不扫嵌套子元素）。矩阵 **+2**。实测：还原旧 `_slot_names` 翻 **2** 例。S1 |
| R60 | B⁹-S2（**S2**） | **面板自身 `v-if` 从未绑定任何权威**：`v-if="!hasCollaboration"`／`v-if="NaN"` 均 ACCEPT——插槽已接线而面板恒不渲染；此前只测**字面假值**表，真实谓词但恒假的写法全部漏过 | 新增 `_COLLABORATION_PANEL_GATE`；区域插槽内面板的 `v-if` 须**恰好等于** `["showCollaborationPanel"]`（`=` 两侧空白仍接受）。矩阵 **+2**。实测：停用该规则翻 **2** 例。S2 |
| R61 | A¹⁰-S2-1／B¹⁰-S1-1（**S1**） | **`_module_statements` 对 `(`／`{` 开头的顶层语句整体失明**：`(`／`[`／`{` 分支排在 `pending` 判定**之前**，故开括号只被压栈、从不被报出——顶层裸块 `{ poison() }`、顶层 IIFE `(() => { … })()`、**整式括号** `((Array.prototype as any).includes = () => true);` 与**逗号表达式** `((X.length = 0, 0));` 几类**加载期可执行**语句读完整个文件都「没有语句」，门禁 GREEN（**第十二轮据实更正**：第十一轮曾把**已修版** `305245f9` 当旧版、宣布「非整式括号赋值旧版即 REJECT」，该结论**不成立**——旧版 `47b9a631` 对**单层整式括号** `(X.includes = () => true);` 同样 **ACCEPT（不可见）**，旧版只报**完全不带括号**的裸赋值；不可见面是**整式括号（单层／双层）＋ 逗号表达式**三类，见 §8 R75 的可复现实测）；B¹⁰ 把载荷追到**真实 `contractRuntimeVm.ts` 末尾**后实测浏览器域规则真死（`[true,false,false,false,false]`）、TS 诊断 0、esbuild transform OK、prettier 不改动 ⇒ **可部署**。另一处是**ASI**：上一条无 `;` 时`if (typeof window !== 'undefined') { … }` 被判为**同一条语句的中段** | 重写 `_module_statements`：①在**同层无栈**时，`(`／`[`／`{` 若正处语句待起位置即**照报**（token 为括号字符，故不进声明白名单）；②**ASI 语句头**——行首标识符若前一有效字符**可结束语句**（标识符字符／`)`／`]`／`}`）即视为新语句，只有把声明续到下一行的词（`as`／`satisfies`／`extends`／`implements`／`from`／`is`）豁免；③顶层 `}` 之后改按**后随字符**判定是否续句（`_JS_STATEMENT_TAIL_CHARS`），顺带修掉 `export type X = Record<string, { … }>;` 被读成「多出一条 `>` 语句」的**假 REJECT**（store.ts 46 → 45 条）。矩阵 **+4**（裸块／IIFE／ASI／括号赋值）。实测（真文件影子）：载荷逐个追加到真实 VM 后门禁**全部 FAIL**，还原即 PASS；目录内 5 个相关文件的非声明语句数**均为 0**。S1 |
| R62 | B¹⁰-S1-2（**S1**） | **「已复核 import」是承诺而不是检查**：`_COLLABORATION_MODULE_IMPORT_SPECIFIERS` 只把 specifier **字符串**与清单比对，**从不打开被导入文件**；把 `if (typeof window !== 'undefined') { (Array.prototype as any).includes = () => true }` 放进 `pages/contractForm/valueUtils.ts`、`contractRuntimeVm.ts` **一字不改**，守卫 GREEN（`collaboration_authority_failures` 的三个输入里没有被导入文件的**内容**），B¹⁰ 用真双域执行实测浏览器域规则死掉 | 新增 `collaboration_import_closure_failures()` ＋ `_resolve_local_module()`：按 specifier **解析 → 读文件 → 走完整运行时 import 闭包**（`import type` 被擦除故跳过，仅相对 specifier），闭包内每个模块须**可读**、**可切分**（未闭合 span 即拒）且**不得出现任何环境全局或 `import.meta`**；规模上限 40 文件／深度 8，触顶 fail-closed。实测闭包为 **4** 个文件且全部环境纯净；`checks` **+1**，矩阵／自检 **+6**（含传递依赖、不可读、未闭合、类型导入四个反向用例）。**不**对被导入文件套用声明白名单（它们合法地持有模块级绑定；环境无关的加载期载荷由 `node` 域证明兜底），该分工已登记为下一轮候选。S1 |
| R63 | B¹⁰-S1-3（**S1**） | **载体／祖先死门只按「字面量假值」判**：`<div v-if="hasCollaboration && false">`（祖先）与 `<ObjectTaskPage v-if="!preserveAuthoritativeBusinessSections && false">`（载体）都是**真实谓词但恒假**——不是字面，故既不在 `_LITERAL_FALSY_GATES` 内，也不被任何判据看见；B¹⁰ 实测真 `compileTemplate` 编译通过、SSR `panel=ABSENT`／整块不渲染、`v-show="hasCollaboration && false"` 变体输出 `style="display:none"`，守卫均 GREEN。第九轮只把**面板自己的** `v-if` 升级为等值比较，**漏了祖先与载体这一层** | `_dead_gate_failures()` 改为**登记式等值清单**：载体／其**全部祖先**／面板的 `v-if`／`v-else-if` 只允许等于**已登记**的表达式（宿主侧 4 条：`!preserveAuthoritativeBusinessSections`、`renderModel.identity.presentationMode === 'task'`、`hasCollaboration`、`showCollaborationPanel`；页面侧 2 条：`!showCurrentFormFieldConfigScope` 与那条 page-section 表达式，均以 `_condense` 归一化登记），`v-show` 在整条路径上**一概**拒绝，`v-else` 只允许出现在**已登记的元素**上（`section`／`ScCard`）——`v-else` 的条件正是兄弟门取反，故登记兄弟门即登记它。矩阵 **+11**（宿主 6 ＋ 页面 5，含 **4 类接受形状／5 条条目**——第 4 类含 2 条）。实测（真文件影子）：载体死门／祖先死门／页面祖先死门三种真实改动**全部 FAIL**，还原即 PASS。**副作用据实登记**：新规则**包含**了第九轮的面板等值规则，故「停用面板等值」现在翻 **0** 例（二者构成纵深防御，见 §6 鉴别力）。S1 |
| R64 | B¹⁰-S2-1（**S2**，**假 REJECT**） | **`.vue` 模板文案里的撇号让 JS 词法器错配引号**：`<span>don't</span>` 开启一个跨到下一个引号的**幻影字符串**，`<script setup>` 里的 `hasCollaboration` 与 `import { resolveCollaborationVisibility }` 都被读成缺失（报 `the collaboration flag is no longer a computed`）；触发条件是**日常英文文案**，不是攻击；B¹⁰ 未能把它翻成绕过（奇撇号时脚本区可见仅 903/11146），故此前只 fail-closed，但仍是缺陷 | 新增 `_script_text()`：**先取出 `<script>` 区域**再做 JS 级屏蔽（含 `_authority_named_imports()` 与『宿主不得自声明权威』的正则），无 `<script` 块时原样返回；偏移照旧保长。矩阵 **+1**（该形状现在**接受**）。实测：移植用例由 REJECT 转 GREEN，真文件门禁仍 PASS。S2 |
| R65 | B¹¹-S1-1（**S1**，**回归**） | **`_JS_STATEMENT_TAIL_CHARS` 把「不能续接表达式」的字符也算成续句**：`!`／`~`／`@`／`#` 在 `}` 之后**不能**接续任何表达式（`{ … } !x` 不是表达式），故 ASI 生效、它们**开始一条新语句**；把它们列进续句表后，`function gate() { … }` 后面跟一行 `!gate()` 读完整个文件**没有语句**——B¹¹ 实测 **OLD(`47b9a631`)=REJECT → NEW(第十轮)=GREEN**（`,(function(){…})()` 同类首字符同样命中），同一载荷下 node 证明 PASS、浏览器域 DEAD（`COLLABORATION_SURFACE_KINDS` 被清空 ⇒ 协作区恒灭），esbuild／vite 可编、TS 合法 ⇒ **可部署**。这是第十轮新引入的 fail-open | 续句表只留**能作中缀**的运算符（`,)]}.>?:=+-*/%&|^<`），`!`／`~`／`@`／`#` 移出——一个尾字符是对「后面的文本仍属本语句」的承诺，一个不能接续表达式的字符给不出这个承诺。矩阵 **+1**（`!gate()` 藏在一个声明之后）。实测（真文件影子）：`!gate()`／`~f()` 追加到真实 VM 后**均 FAIL**，还原即 PASS；旧版对同载荷均 **REJECT**（回归闭合）。S1 |
| R66 | B¹¹-S2-1（**S2**） | **`\u2028`／`\u2029` 不算换行**：二者对 ASI 与 `\n` 等价，但 `_module_statements` 只在 `character == "\n"` 时置 `line_break`，故 `export type T = typeof KINDS`＋U+2028＋`if (typeof screen !== 'undefined') { … }` 里的 `if` 被读成上一条语句的中段（B¹¹ 实测同形 `\n` 版本 REJECT、`\u2028` 版本 GREEN，浏览器域 DEAD）。**非回归**（旧版同样 GREEN），但正是 R61 声称关闭的 ASI 空面残留 | `line_break` 改为对 `"\n"`＋`\u2028`＋`\u2029` 三者置位。矩阵 **+1**（U+2028 后的语句）。实测：该载荷追加到真实 VM 后 FAIL。S2 |
| R67 | A¹¹-S1-1（**S1**） | **语句位的模板字面量被整段抹平**：`_blank_spans` 对 `template` 整段抹平、插值 `${…}` 一并消失，于是 `` `${typeof window !== 'undefined' ? (…length = 0) : 0}`; `` 这种语句在 `_module_statements` 里**没有语句**、其中的 `window` 也不被 `_environment_reference_failures` 看见（未屏蔽时 `window` 是能被抓到的）；载荷 esbuild 打包通过、`node` 加载即求值 ⇒ **可部署**，且反证 `collaboration_module_scope_failures` 自己的不变式 | `_blank_spans` 对 `template` span **保留起始反引号**：反引号不是文本而是语句的首 token，保留它就让既有的「本层语句必须是声明」规则看得见该语句并拒绝，同时不放开任何被屏蔽的文本（插值内容仍被抹平，字符串诱饵不会复现）。矩阵 **+1**（语句位模板字面量）。实测：载荷追加到真实 VM 后 FAIL。S1 |
| R68 | B¹¹-S1-2／S1-3／S3-1（**S1**×2 ＋ **S3**×1） | **R62 的闭包有三个洞**：①闭包模块**不适用**「本层只能是声明」的形状规则，于是 `if (typeof screen !== 'undefined') { … }` 放在 `valueUtils.ts` 顶层无人读；②只跟**静态 `import`** 边，`export { x } from './y'` 与 `import('./y')` 到达的模块**从不被打开**，含被禁全局的 `collaborationPoison.ts` 整块漏读（B¹¹ 实测守卫 PASS／node PASS／浏览器域 DEAD）；③深度上限 8 **静默截断**（链长 9 起返回 `[]` 且无 failure），而 40 文件上限是 fail-closed | ①闭包模块新增「本层语句必须是声明」判定（模块级 `const` 绑定仍放行）；②边遍历扩到 `export … from`／`export * from`／动态 `import('…')`（re-export 用**锚定 export 子句**的模式，避免把初始化式里叫 `from` 的调用误判成边）；③深度触顶由「静默返回」改为**报 failure**（守卫不再声称读过它没读的闭包）。矩阵 **+5**（仅声明接受／顶层语句／re-export 边／动态 import 边／深度触顶）。实测：真文件注入 `valueUtils.ts` 顶层探针与 re-export 诱饵后守卫 FAIL，还原即 PASS；闭包实为 4 文件、顶层语句全为声明，收紧后仍 PASS。S1×2 ＋ S3 |
| R79 | A¹³-F3／B¹³-S3-1（**S3**×2，据实性） | **第十二轮登记的差分面不实**：文档写「**14** 例翻转 ＝ **11** 例 OLD=GREEN → NEW=REJECT ＋ **3** 例 OLD=REJECT → NEW=GREEN，其余 159 例不变」，但 11＋3＋159 ＝ 173 ≠ 174，第十四例无处安放（A¹³ 与 B¹³ 独立复算一致） | 就地更正 §8 第十二轮段：**15** 例翻转 ＝ **12** 例 OLD=GREEN → NEW=REJECT ＋ **3** 例 OLD=REJECT → NEW=GREEN，其余 **159** 例逐条不变（12＋3＋159 ＝ 174）。S3×2 |
| R80 | A¹³-F4（**S4**，据实性） | ①R71 行仍把 `(X.includes = () => true)` 列为「旧版即 REJECT」，与 R75 的实测更正**同文件自相矛盾**且无更正标记；②R75 行的交叉引用写成「R71-④」，而该条更正的对象是 **R71-②**（④ 是体量排名条） | ①R71 行加 **（第十三轮据实更正）** 标记并写明 ②／④ 已由 R75／R81 取代；②把交叉引用订正为 **R71-②**。S4 |
| R81 | A¹³-F5（**S4**，据实性） | **体量排名口径未钉死**：文中「第 N 大代码文件」在历轮里出现过第 3／第 4／第 5 三种说法，读数取决于是否把 `docs/` 与 lockfile 计入 | **钉死口径**：一律按 `scripts/ci/generate_complexity_budget_report.py` 的 `SCAN_ROOTS`（`Makefile`／`addons/`／`scripts/`／`frontend/apps/web/src/`／`.github/workflows/`）＋ 其 `BUDGETS` 扩展名统计，**排除 `docs/` 与 `frontend/pnpm-lock.yaml` 一类 lockfile**；本口径下守卫 5018 行为**全仓第 1**（Python 源码亦第 1，压过 `test_ui_contract_v2_boundaries.py` 的 5001 行）。§7 第 7 项与 §8 第十三轮段同步采用。S4 |
| R82 | A¹³-F6（**S2**，主张**不成立**） | A¹³ 主张 `<SCRIPT setup>`／模板内 `<SCRIPT>` 被拒是**假 REJECT**（「大小写不敏感才是对的」） | **实测不成立**：用真 `@vue/compiler-sfc@3.5.27` 复算——`<SCRIPT setup lang="ts">` 作为真实块 → `errors=["Element is missing end tag."]`、`script=null`；改为大写闭合 `</SCRIPT>` → `errors=[]`、`script` 正常。故**闭合标签**必须大小写不敏感（R70 已如此）、**起始标签**必须大小写敏感（守卫现状即如此），唯一被拒的「模板内裸 `<SCRIPT>` 文本元素」连真编译器也报错，**不是**假 REJECT、守卫不改。S2（据实驳回）。**第十六轮据实更正（见 R93-③）**：本行「起始标签大小写敏感 ⇒ 被拒」的措辞比实现宽——`_script_text()` 以**字面量小写 `<script`** 定位，未命中即原样返回（块体不被剥离），故 `<SCRIPT setup>` 起始标签实际**既不识别也不再拒绝**（实测守卫 GREEN）；真 `@vue/compiler-sfc@3.5.27` 自身拒绝大写起始标签，故**不可利用** |
| R83 | A¹³-S1／B¹³-S1-1／S1-2／S1-3（**S1**×3） | 闭包出口的**声明白名单**本身就是开口：①非导出模块级绑定（`export const dead = typeof Element !== 'undefined'`、`const box = new Image()` 等）的初始化式在加载期求值，而枚举清单只覆盖少数拼写（`customElements`／`URL`／`Element` 都漏网）；②`export default class` 被当合法声明放行，其**静态初始式**（`static x = (((Array.prototype as any).includes = () => true), 1)`）在加载期污染原型、权威在每个域都答 `true` 而守卫全绿；③类**表达式**的静态初始式同理 | **以形状规则取代出口白名单**（`run_failures()` 阶梯重写）：非声明 token 拒；`const`／`let`／`var` 模块级绑定拒；`import` 仅在运行时导入且非 `import type`／非相对 specifier 时拒；`export` 侧 `export const\|let\|var`／加载期声明（`enum`／`class`／`namespace`／`abstract class`／`declare`／`using`／`module`）／`export default`（**任意形态**，含 `export default class` 与 `export default abstract class`）／`export =` 一律拒；枚举式环境清单**降级为函数体内运行期探针的补充**。矩阵闭包层 20 → **26**（新增 7 条、改写 1 条同名夹具）。实测（`/tmp/r13` 影子树）：A（绑定）／C（`export default class` 静态初始式）／D（类表达式静态初始式）三类载荷在真 `valueUtils.ts` 上全部 FAIL，还原即 PASS。S1 |
| R84 | B¹³-S1-4／B¹³-S2-1（**S1**＋**S2**） | ①**动态 `import()` 的 fail-closed 判定可被第二实参绕过**：旧模式接受「字面量 ＋ 逗号或右括号」，故 `import('./__collabDeep', { with: {} })` 满足「字面量后跟逗号」而**不**触发拒绝、也不跟边（fail-open）；②`export enum` 被加载期声明规则拒绝（**第十四轮据实更正**：这**不是假 REJECT**——`esbuild` 实测其产加载期 IIFE，是真阳性；仅「合法 TypeScript 语法却被拒」这层属**过严面**） | ①收紧为**只接受「字面量后紧跟 `)`」**（`\s*(['"])([^'"]*)\1\s*\)`），第二实参即拒；②`export enum` 的处置为**方向 fail-closed、据实登记不改规则**——`esbuild` 实测 `export enum` 产出加载期 IIFE（**真阳性**，第十四轮据实更正上一轮「假 REJECT」的用词），真实闭包 4 文件无 `enum`，两轮复核（A¹³-S2-1／B¹³-S2-1）同源。S1＋S2 |
| R85 | B¹⁴-S1-1（**S1**） | **`type`／`interface` 是上下文关键字，不是保留字**：声明白名单按**拼写**放行，语句走查又只读首 token，于是 `type(typeof customElements !== 'undefined' && (Array.prototype.includes = () => false));` 被读成类型别名——它是**加载期执行的调用**，在守卫的 node 域不执行、在浏览器域真死（B¹⁴ 真 Chromium 实测 `ruleAlive=false`；对照把 `type` 换成 `probe` 即 REJECT），`vue-tsc`／`eslint` 均通过 ⇒ **可部署** | **把放行从拼写改为形状**（新增 `_COLLABORATION_DECLARATION_SHAPES`：`type X …=`／`interface X`／`function f(`）：**权威体层**（`collaboration_module_scope_failures`）与**闭包成员层**（`run_failures`）同时生效。矩阵 **+4**（权威体 1 拒 ＋ 1 接受；闭包 1 拒 ＋ 1 接受）。实测：两处真文件注入后守卫 FAIL，还原即 PASS；停用该形状规则时自检立刻点名这两条夹具。S1 |
| R86 | A¹⁴-S1／B¹⁴-S1-2（**S1**×2） | **打不开的再导出是既不被跟、也不被拒的加载期边**：`import { x } from 'pkg'` 早已拒绝（守卫打不开包），而 `export * from 'pkg'`／`export * as ns from 'pkg'`／`export { a } from 'pkg'` 同样在加载期求值目标模块，`relative_edges()` 却只跟 `.` 开头的 specifier ⇒ 既不拒绝也不跟边。A¹⁴ 用**真实别名** `@/`（`tsconfig.json` 的 `"@/*": ["src/*"]`）端到端复现：守卫 GREEN、`esbuild` 把探针打进产物、浏览器域规则在每个域都答 `true`；B¹⁴ 用真 Chromium 独立复现同一条缺口 | `export` 阶梯末尾补再导出判定：语句匹配 `_COLLABORATION_RE_EXPORT` 且 specifier **不以 `.` 开头**即拒（消息与 import 分支同构）。矩阵 **+4**（`export * from`／`export { a } from`／`export * as ns from` 三拒 ＋ 相对再导出到干净模块一接受）。实测：五条载荷（含别名与裸包两条路径）在真文件上全部 FAIL，还原即 PASS。S1×2。**第十五轮据实更正**：该「全部 FAIL」只对**有空白**拼写成立——`export*from'./x'` 一类无空白拼写当时仍放行，已由 R88 收口 |
| R87 | A¹⁴-P1／A¹⁴-P2／B¹⁴-S4（**S3**／**S4**，据实性） | ①上一轮把 **`export enum`** 标为「新增**假 REJECT**」，而同一行给出的理由（`esbuild` 实测产加载期 IIFE）恰恰说明拒绝是**真阳性**；②闭包夹具账目写「新增 **7** 条 ＋ 改写 **1** 条」，实测是「新增 **6** 条 ＋ 改写 **2** 条（净 +6）」——漏算 `whose declaration initializer reads the environment` → `whose module-level binding reads the environment` 这一处改名 | ①本文件 R83／R84 行与 `delivery_context_switch_log_v1.md` 第十三轮段 ③改写为「**真阳性／过严面**」，并保留「方向 fail-closed、据实登记不改规则」的处置；②账目改为「新增 6 ＋ 改写 2」，并在切换日志第十三轮段标注据实更正。另**新登记**两条非阻断面（见 §7 第 13 项 ⑬／⑭）：闭包顶层 `declare const` 的**既有假 REJECT**、闭包模块级绑定（含 `as const`）一律拒的**刻意取舍**。S3／S4 |
| R69 | B¹¹-S1-4（**S1**） | **登记式死门清单不含 `v-for`**：`v-for="n in 0"`／`v-for="n in []"` 与 `v-if="false"` 一样渲染不出任何东西，而清单只登记 `v-if`／`v-else-if`／`v-show`；B¹¹ 给载体、祖先与页面 driver host 各加一条空迭代，真 `compileTemplate` 编译通过、`@vue/server-renderer` SSR 判据 `panel=ABSENT`（基线 RENDERED）而守卫 GREEN | `_dead_gate_failures` 增加 `v-for` 分支：**整条已登记路径上没有任何元素迭代**，故登记清单为空、任何 `v-for` 一律拒绝（与 `v-show` 同向 fail-closed）；祖先检查由同一函数复用，故载体／祖先／面板／页面侧一次覆盖。矩阵 **+3**（载体／祖先／页面 host）。实测：三处注入后守卫 FAIL，还原即 PASS；真实两文件**无任何 `v-for`**，收紧后仍 PASS。S1 |
| R70 | B¹¹-S3-2／S3-3（**S3**×2，**假 REJECT**） | ①`_script_text()` 的闭合标签**大小写敏感**，而 SFC 解析器接受 `</SCRIPT>`——大小写不一致时整块脚本被判为空、报「flag is no longer a computed」；②`native_surface_bridge_errors()` 仍用 `source.split("<script", 1)[0]` 且**未先屏蔽 HTML 注释**，模板里一句 `<!-- <script> -->` 就让模板被判为空。两处都是**日常可写**的形状，不是攻击 | ①闭合分隔符改用作用域内联标志 `(?i:</script\s*>)`（起始标签仍大小写敏感，因为 Vue 本身不接受 `<SCRIPT>`）；②先屏蔽 HTML 注释、再按 `<script` 切分。矩阵 **+1**（`</SCRIPT>` 接受）。实测：两处真文件注入后由 FAIL 转 PASS，基线两版均 PASS。S3×2 |
| R71 | A¹¹-S3-1／S4-1／S4-2／S4-3（**S3**＋**S4**×3，据实性） | ①文档 4 处仍在**现在时**用第九轮口径（`120 例`／`107／13`），与同文件已改的 142／118／18／6 及切换日志⑩「以批次文档为准」**自相矛盾**；②R61 行把 `(X.includes = () => true)` 列为「旧版不可见」，实测旧版即 REJECT；③R63「含 4 例接受面」实为 **4 类形状／5 条条目**；④「全仓第 4 大文件」不成立（大于 4212 行的代码文件另有 4 个＝5001／4974／4841／4274，守卫为**第 5**，仅在 Python 源内第 4） | ①就地刷新 4 处（§1 交付结论、§5 矩阵口径、§6 鉴别力、§7 体量项）并补出接受／拒绝拆分；②改用整式括号与逗号表达式举例并标注「非整式括号赋值旧版即 REJECT」；③写作「4 类接受形状（5 条矩阵条目）」；④改「全仓代码文件第 5 大（Python 源码第 4）」。**（第十三轮据实更正）**本条 ② 的结论由 R75 推翻、④ 的排名口径由 R81 取代，两项均不再生效（见 R80）。S3＋S4×3 |
| R72 | B¹²-S1-2／A¹²-S2-1（**S1**×2） | ①闭包层在**注释屏蔽**（而非字符串感知屏蔽）的文本上切分语句：`export const OPEN_BRACE_HINT = '{'` 里的 `{` 被压栈不弹，**其后整个文件**读不到语句——把顶层探针放在闭包模块的一个字符串字面量之后即可全绿；②**深度触顶模块不被读**——边界分支只在边界模块**还有边**时报「deeper than bound」，链正好停在界上时该模块的加载期语句无人读（`m7` 的 `(Array.prototype as any).includes = () => false` 全绿） | 抽出 `read_module(path, text)`（未闭合 span 即拒 ＋ 语句检查），并让 `walk` 与**深度边界**分支**都**调用它——边界模块**先读、再报深度**；语句切分改用 `_blank_comments_and_strings`。矩阵 **+3**（字符串含 `{` 拒绝／模板插值接受／边界语句拒绝）。实测：`OPEN_BRACE_HINT = '{'` 载荷 REJECT、`` `p-${1}` `` ACCEPT、边界 `m7` 语句 REJECT（`/tmp/r512/probe.py`）。S1×2 |
| R73 | B¹²-S1-1／A¹²-S1-2（**S1**×2） | 顶层 `}` 的续句判定**只看后随 token 是否在续句表内**：`+`／`-`／`/` 既能作中缀、也能**起**一条语句（一元运算、正则字面量），把它们留在表里就意味着 `export function probe() { … }` 后接 `+gate()`／`-gate()`／`/^collect-/.test('')` 读完整个文件**没有语句**；`from(...)`／`as(...)`／`satisfies(...)`／`is(...)` 这类首词同样隐形 | ①`+`／`-`／`/` 移出 `_JS_STATEMENT_TAIL_CHARS`；②新增 `_JS_CLOSED_DECLARATION_HEADS`（function／class／interface／enum／namespace／declare／abstract）＋ `_closed_declaration_head()`：**声明体的 `}` 就是语句终点**（只读语句首个 `=` 之前的词，故 `export const f = function () { … }` 仍是变量声明），除非后随 `else`／`catch`／`finally`／`while`（结构续接）或 `>`／`|`／`&`（类型续接）。矩阵 **+7**（`+`／`-`／正则／`from`／`satisfies`／`as` 六条拒绝 ＋ 类型字面量续接一条接受）。实测：与旧树（`956dbcbd`）全量差分 **REGRESSIONS 0／NOW ACCEPTED 0**（`/tmp/r512/diff_all.py`，174 例逐条）。S1×2 |
| R74 | A¹²-S1-1／A¹²-S3-4／B¹²-S1-3／B¹²-S3-2（**S1**×3＋**S3**） | ①环境全局清单**不含 `screen`**，故 `export const dead = typeof screen !== 'undefined'` 这类**声明初始化式**里的探针两层同绿（⑨只判「这算不算一条语句」，初始化式内部由清单负责）；②闭包出口形状阶梯**缺 `class` 等合法声明**（假 REJECT 面）；③闭包层只判**首 token** 是否声明，`export default <表达式>` 的加载期求值没人管；④`export class P { static x = … }` 的静态初始式同样是加载期求值 | ①清单扩入 `screen`／`frames`／`devicePixelRatio`／`isSecureContext`／`crossOriginIsolated`／`visualViewport`／`speechSynthesis`／`crypto`／`queueMicrotask`／`structuredClone`／`atob`／`btoa`／`HTMLElement`／`CustomEvent`／`IntersectionObserver`／`PerformanceObserver`／`Notification`／`WebSocket`／`EventSource`／`Deno`／`Bun`／`Buffer`（**刻意不含** `fetch`——真实 `fieldUtils.ts` 命中它；也不含 `top`／`parent`／`name`／`status`／`origin`，理由写在守卫注释里，见 §7 第 13 项 ⑩）；②闭包出口新增形状阶梯：拒 `export default <表达式>`，放行 `export default class\|function\|interface`，`export class`／`enum` 静态初始式按 `_COLLABORATION_EXPORT_LOAD_TIME_DECLARATION` 拒。矩阵 **+4**（`typeof screen` 初始化式拒绝／表达式默认导出拒绝／类默认导出接受／静态初始式拒绝）。实测：`export default (Object.assign(Array.prototype, …))` REJECT、`export class P { static x = (Array.prototype as any) }` REJECT、`export default class Probe { read() { return 1; } }` ACCEPT、`export const dead = typeof screen !== 'undefined'` REJECT。S1×3＋S3 |
| R75 | A¹²-S3-3（**S3**，据实性） | **R61 行的「第十一轮据实更正」本身不实**：它把**已修版** `305245f9` 当成了旧版，据此宣布「`(X.includes = () => true)` 这种非整式括号赋值**旧版即 REJECT**」；按 `git archive 47b9a631`（第九轮收口）影子复测，**单层整式括号** `(COLLABORATION_SURFACE_KINDS.includes = () => true);` 在旧版同样是 **ACCEPT（不可见）**，旧版只报**完全不带括号**的裸赋值 `X.includes = …;`（REJECT） | 就地更正 R61 行与本 §8 第十一轮段：不可见面是**整式括号（单层与双层）＋ 逗号表达式**三类，`47b9a631`=ACCEPT／`305245f9`=REJECT 为可复现实证；R71-② 的同类更正文一并订正（**第十三轮订正交叉引用**：原文误写为 R71-④——④ 是体量排名条，与 R61 归因无关，见 R80）。S3 |
| R76 | A¹²-S4-1／A¹²-S4-2（**S4**×2，据实性） | ①§7 第 13 项 ⑦ 引用的 `_closure_relative_specifiers` **在守卫里不存在**（相对边实际由 `relative_edges()` 解析）；②§7 第 13 项 ⑨ 把开口写成「非语句位的模板字面量插值」，与实测不符——真开口是**声明初始化式里的自由环境引用**（`typeof screen`），与模板插值无关 | ①符号名改为 `relative_edges()`；②⑨ 改写为「声明初始化式里的自由环境引用由**枚举式**环境全局清单负责，清单漏项即整体失守」，并按同源登记 ⑩（`fetch` 类未枚举全局）／⑪（`v-once`／`v-memo` 未登记）／⑫（`require()`／`import.meta.resolve()` 等不可跟的边）。S4×2 |
| R77 | A¹²-S3-5（**S3**） | **非字面量动态 `import()` 不跟边**：`import('./' + 'deepModule')` 以引号开头，但 `relative_edges()` 的模式要求引号后紧跟 `)`，于是**匹配不到**它——既没有边、也不触发拒绝，其后模块的加载期代码落在**所有层之外**（fail-open） | `read_module()` 增判定：动态 `import(` 的**首个实参必须是单一字符串字面量**（`\s*(['"])([^'"]*)\1\s*(?:,\|\))`），否则 fail-closed 报「specifier 无法读取」。矩阵 **+1**。实测：`import('./' + 'deepModule')` REJECT、`import(p)` REJECT、`` import(`./deepModule`) `` REJECT、`import('./deepModule')` ACCEPT。S3 |
| R78 | A¹²-S4-3／B¹²-S2-2（**S3**＋**S2**，**假 REJECT**） | ①`_script_text()` **不先屏蔽 HTML 注释**：注释里的 `<script>`／`</script>` 会移动脚本边界（R70-② 只补了 `native_surface_bridge_errors()` 一处）；②`native_surface_bridge_errors()` 的模板边界旧实现仍是 `source.split("<script", 1)[0]`，**引号属性值** `data-note="<script"` 与 HTML 注释都把模板切短 ⇒ 真宿主被判「task and workspace surfaces must forward…」；③两个消费侧调用点（`collaboration_consumption_failures()`／`collaboration_page_wiring_failures()`）**同样**用裸 `template.find("<script")` | `_scan_tags()` ＋ `_HTML_VOID_ELEMENTS` 上移到文件头；`_script_text()` 改按 `_scan_tags()` 定位 script 块（跳过注释、起始标签引号感知、闭合分隔符 `</script\s*>` 仍大小写不敏感）；新增 `_template_before_script()` 并替换**全部三处**裸 `<script` 切分（含本轮新收口的两处消费侧调用点）。矩阵 **+4**（页面／宿主各 2：引号属性值与 HTML 注释）。实测：真宿主 ＋ `data-note="<script"` → ACCEPT、真宿主 ＋ `<!-- <script> -->` → ACCEPT、`</SCRIPT>` 大写闭合仍 PASS、`_script_text()` 两形状均保留 `hasCollaboration`；旧树（`956dbcbd`）对**引号属性值**两例误拒（`data-note` decoy 在宿主／页面各翻 1 例）。S2／S3 |
| R91 | A¹⁶-S1（**S1**） | **语句切分器的「续句首词」把下一条语句胶到上一条**：`type` 别名刻意不在「`}` 即语句终点」的声明头清单里（类型表达式确实会把 `}` 带到 `>`／`|`／`&`），而续句词表 `as`／`satisfies`／`is`／`extends`／`implements`／`from` 是**无条件**表——于是 `type gN3 = { a: number }` 后面一行 `from: { (Array.prototype as any).includes = () => true }`（**语句标签**）被读成**一条**类型别名，形状规则匹配到别名头即放行，标签块在加载期真跑：`node` 域（门禁自身）不执行、浏览器域执行 ⇒ 守卫 GREEN 而浏览器域规则真死。A¹⁶ 用真 `esbuild@0.21.5` 复算产物逐字含 `Array.prototype.includes = () => true;`；同族变体 `export type gM4 = number` ＋ `from: {…}`、`type X = 1 | 2` ＋ 标签、`from((Array.prototype as any).includes = () => true)` 全部放行（**既有缺口**：`0692078d` 上同样 PASS，非第十五轮引入），且权威体层与闭包层**同时**中招 | ①续句词改为**按语句头判定**（`_JS_CONTINUATION_HEADS`：`as`／`satisfies` 只接 `const|let|var`、`is` 接 `function|const|let|var`、`extends` 接 `class|interface|type|abstract|declare|default`、`implements` 接 `class|abstract|declare|default`），`from` 只接**模块子句**（`import`／`export` ＋ `*`／`{`，见 `_JS_MODULE_CLAUSE`）；②新增 `_statement_labels()`：后随冒号的词是**语句标签**而不是续句词（`extends:` 是标签，`T extends U` 不是）——单靠 ① 挡不住 `extends:`，因为 `extends` 确实能续 `type` 头；③删除无条件的 `_COLLABORATION_STATEMENT_CONTINUATIONS`／`_JS_STATEMENT_INVISIBLE_HEADS` 两张表。矩阵 **+5**（两拒 ＋ 一拒 ＋ 一拒 ＋ 一接受：三段合法续接 `export interface gShape` 换行 `extends …` 在两层各保留一条）。实测：12 条载荷在新树 12 拒／旧树 0 拒，还原即 PASS。S1 |
| R92 | B¹⁶-S1／S2（**S1**／**S2**） | **400 字符读窗被长具名列表击穿**：`export { exportedName000, …, exportedName059 } from './b16poison'` 把 `from` 子句顶到窗口之外 ⇒ 再导出正则失配、落进「`export {` 且窗口内找不到 `from`」的**放行**支，`relative_edges()` 也看不到边 ⇒ 目标模块的加载期代码在门禁眼皮下进包（B¹⁶ 用真 `vite build` ＋ 真 Chromium 复算：产物含 `customElements<"u"){const e=Array.prototype;e.includes=()=>!1}`、`browserDomain.ruleAlive=false`，且 `eslint` 0 error、`vue-tsc` 与 pristine 错误集一致 ⇒ **可部署**）；含无空白版、多行 prettier 版、45 组 `as alias` 版、`from 'somePackage'` 版；S2 指出既有夹具只证明「400 空格不再填满窗口」，未覆盖长文本这一成因面 | ①**读窗与截断**：`_statement_text` 拆成 `_statement_window()`，返回 `(文本, 是否耗尽窗口)`，窗口按**语句真实终点**结束（顶层 `;`，或后随 token 不能续接的换行——本仓**全无分号**，旧「读到下一个 `;`」永远读不到终点，导致长签名一律被读成截断）；②**耗尽即拒绝**：`export {` 打头的语句只有在**读到终点**时才允许走「本地具名导出」放行支，读不完则落到新增的专用拒绝（权威体层与闭包层各一条）；③窗口上限从 400 提到 **2000** 个折叠后字符（60 个导出名约 1.1k **仍可读并被跟边**，400 个约 7.2k 被拒——上限是**有限性**约束，不是内容约束）。矩阵 **+4**（两拒 ＋ 两接受：可读的长列表仍须被跟边，否则只是把 fail-open 换成一刀切）。实测：400 名载荷在新树 REJECT／旧树 ACCEPT，60 名干净目标两版均 ACCEPT。S1／S2 |
| R93 | A¹⁶-S3（**S3**×3，据实性） | ①文档 §6 现在时仍写「当前 **154** ＝ …（接受 26 ＋ 拒绝 128）」，与同文件 §4／§5 的 200 自相矛盾；②同段落把相对边解析写成 `_closure_relative_specifiers`——**该符号在守卫里不存在**（R76 只改了 §7 第 13 项 ⑦ 的同一笔误，此处漏改）；③文档称大写 `<SCRIPT` 起始标签**被拒**，实测**不被拒**（`_script_text()` 以字面量小写 `<script` 早退，块体不被剥离）——真 `@vue/compiler-sfc@3.5.27` 自身拒绝大写起始标签，故**不可利用**，属据实性 | ①§6 该处改为当前口径 `210 ＝ 143 ＋ 21 ＋ 46（45 接受 ＋ 165 拒绝）`，并把 §1／§3／§4／§5／§6／§7 第 7 项的现在时数字一并刷新为第十六轮口径（自检 210、守卫 5643 行）；②符号名改为 `relative_edges()` 并就地注明「原写符号不存在、此处漏改」；③R82 行就地补「据实更正」，写明大写起始标签**既不识别也不拒绝**、因真编译器同样拒绝而不可利用。**第十七轮据实更正**：本行登记的第十六轮口径已由 R98 取代（自检 **230**、守卫 **6065 行**）。**第十八轮据实更正**：本行登记的第十六轮口径已由 R103 取代（自检 **243 例**、守卫 **6531 行**）。S3×3 |
| R94 | B¹⁶-S3（**S3**，POST_MERGE_FOLLOWUP） | 四条**既有**过严面（本轮未引入、未收口）：跨行动态 `import(\n './valueUtils',\n)`、赋值式 `import fs = require('fs')`、闭包顶层 `declare const`、`export const K = [...] as const` | 逐条**复测**：四者在 `9e5402c3` 与本次修复树上**同样被拒**（CLOSED），与第十五轮一致；四者均不产生加载期执行、方向 fail-closed，按 B¹⁶ 建议登记为 **POST_MERGE_FOLLOWUP**（见 §6 第 13 项 ⑯／⑰），不在本轮扩围。S3 |
| R95 | A¹⁷-F1／B¹⁷-S1（**S1**） | **标签判定用定长十六字符看窗**：`_statement_labels()` 原写 `re.match(r"\s*:", source[end:end+16])`，只看得见冒号后（判定点后）的 16 个字符；垫 **≥16 个空白**（空格／制表／不换行空格 U+00A0／零宽空格 U+200B／字节序标记 U+FEFF）或一条**长注释**（注释先被抹平）即可把冒号顶出窗口 ⇒ 判定为「不是标签」⇒ 落到续句词路径（`as`／`extends` 确实能续类型头）⇒ `type` 别名与标签块胶成**一条**语句 ⇒ 出口阶梯只匹配语句头 ⇒ 放行，而标签块在加载期真跑（门禁自身的 `node` 域不执行、浏览器域执行）⇒ 守卫 GREEN 而浏览器域规则真死。B¹⁷ 独立复现为**可部署**（真 `esbuild@0.21.5 --bundle --platform=browser` 产物逐字含 `from: { Array.prototype.includes = () => true; }`），且**权威体层与闭包层同时**中招；与第十六轮 R91 的标签判定**同根因** | ①`_statement_labels()` 改为**跳过任意长度**的空白后判 `source[index:index+1] == ':'`，空白集合 ＝ `.isspace()` ∪ 新增的 `_JS_INVISIBLE_CHARACTERS`（`\u200b`／`\u200c`／`\u200d`／`\ufeff`／`\u2060`，经新增的 `_js_is_blank()` 统一判定）；定长窗口整个删除。②`_blank_spans()` 在**被擦字面量的末字符**写 `"0"`（只对 `string`／`template` span），使被擦掉的字面量**仍然能结束语句**。③矩阵 **+6**（五拒 ＋ 一对照：16 空格／16 制表／16 不换行空格／16 零宽空格／200 字符注释，外加 15 空格对照〔第十五轮前即拒〕）。实测：五种垫法在两层面均由 OLD=ACCEPT 变 NEW=REJECT。S1 |
| R96 | A¹⁷-F2（**S1**，语句吸收通道） | **`_can_end_statement()` 漏掉 `>` 与三个闭引号，且走查跑在字符串已抹的文本上**：`export type A = 'x'`（抹后行尾是空白）与 `export type A = Record<string, number>`（行尾 `>`）都**不能结束语句** ⇒ 下一行被**无条件吸收**进上一条语句 ⇒ 标签判定与续句词表**根本不参与**，形状阶梯只看语句头 ⇒ 放行；十个形状实测 ACCEPT，含 `'x'`／`"x"`／`` `x` `` ＋ 裸表达式、`(…)` 赋值、正则守卫、数字起句与 `Record<string, number>` 换行 `{ … }` 块。同族第二处：`_module_statements()` 的「非姓名」分支只报告词元，**行首的正则／模板／数字／`{` 一律不报告** | ①`_can_end_statement()` 改为 `character.isalnum() or character in "_$)]}>'\"`"`（新增 `>` 与 `'`／`"`／`` ` ``）；②块语句（`{` 开头且**不是**已闭合声明头）与行首非姓名语句（`word is None` ＋ 上一字符可结束语句 ＋ 不续接）纳入语句报告；③矩阵 **+5**（四拒 ＋ 一块语句拒）。实测：X／L 族 **13** 例 ACCEPT → REJECT、**0** 例 REJECT → ACCEPT，`export function f<T extends` 换行两版一致 REJECT（**既有缺口，未修**）。S1 |
| R97 | A¹⁷-F3（**S2**，**假 REJECT**） | **模块子句跨行被拒**：TypeScript 在 `import`／`export` 头与它的子句之间不设边界，`import\n  { read } from './peer'`、`export\n  { g }` 都是合法写法，而新版把行尾当作语句终点 ⇒ 语句切成 `import` ＋ `{ read } …` 两条 ⇒ 合法导入被判成「无法读取」而 REJECT（旧版 PASS，属**本轮新引入的回归**） | ①新增 `_JS_MODULE_CLAUSE_TOKENS`（`{`／`*`／`type`）与 `_statement_awaits_module_clause()`（`re.sub(r"\s+", " ", source[offset:index])` 匹配 `(?:import|export)\s*(?:type\s*)?$`），在 `_statement_continues()` 的标签判定**之前**判「仍是语句头 ＋ 下一词是模块子句令牌」⇒ 续接；②`_module_statements()` 的括号分支把 `{` 限定为「闭合头之后的声明体」才算续接（`character == "{" and closed_head is None` 另开一条），否则 `import\n{` 的 `{` 会被误报成独立语句；③矩阵 **+4**（三接受 ＋ 一对照）。实测：权威体与闭包层的 `import\n{…}`／`export\n{…}` 由 OLD=REJECT 变 NEW=ACCEPT，`import\n* as`／`import type\n{` 两版一致 ACCEPT。S2 |
| R98 | A¹⁷-F4（**S3**，据实性） | §1 表 `:18` 仍写「内建自检 **200/200**」、§5 仍写 `collaboration_self_check=200`，与同文件 §4／§6 的自相矛盾（第十六轮 R93 只刷新到 210，后又随本轮增长失效） | 按**本轮实跑**刷新为「自检 **230**、守卫 **6065 行**」：§1（`:8` 与 `:18`）、§3（`:60`／`:91`／`:97`）、§4（`:163`）、§5（`:186`／`:215`）、§6（`:518`／`:371`）、§7 第 7 项（`:561`／`564`）与 §8 归属段（`:849`／`:854`）一并改为 **230 例（49 接受 ＋ 181 拒绝）＝ 宿主／模块 159（26／133）＋ 页面 21（7／14）＋ import 闭包 50（16／34）**；R93 行就地补「第十七轮据实更正」交叉引用；**第十八轮据实更正**：本行登记的第十七轮口径已由 R103 取代（自检 **243 例**、守卫 **6531 行**）。S3 |
| R100 | A¹⁸-S1-1（**S1**） | **组合记号逃避标识符判定**：`_statement_labels()` 只判「跳过空白后是否 `:`」，而标识符正则用 Python `\w`（**不含** Mn／Mc 组合记号）⇒ `extends\u0301:` 被读成「续句词 `extends` ＋ 非空白」⇒ 标签块胶进上一条 `export type`、守卫 **GREEN** 而浏览器域规则真死；同族字符 U+0300／U+0301／U+093F／U+0E31／U+3099／U+FE20／U+00B7／U+0387／U+200C／U+200D | 新增 `unicodedata` 导入 ＋ `_JS_IDENTIFIER_MARK_CHARACTERS`（`·`／`·`）／`_JS_IDENTIFIER_JOINERS`（ZWNJ／ZWJ）＋ `_js_identifier_continue()`／`_js_identifier_start()`（**ASCII 起首**，避免把非 ASCII 起句的载荷吞进标识符）／`_js_identifier_at()`／`_js_identifier_words()`／`_js_word_may_extend()`／`_js_preceding_word()`／`_js_next_token()`；`_module_statements`／`_closed_declaration_head`／`_statement_carries`／`_statement_continues` 全部改用它们；`_statement_labels()` 加 fail-closed 兜底（跳过空白后既非 `:` 且当前字符 `_js_word_may_extend` ⇒ 判标签）。矩阵 +1（组合记号标签一拒）。**第十九轮据实更正**：本条原写 +2（另一条「对照一接」不在本轮增量内），实测本轮新增夹具为 1 条。S1 |
| R101 | A¹⁸-S1-2（**S1**） | **`<` 被无条件当续句字符**：`_JS_STATEMENT_TAIL_CHARS` 含 `<` ⇒ 合法旧式类型断言 `<unknown>(expr)();` 的起句被胶进上一条语句、隐形（守卫 PASS） | `_JS_STATEMENT_TAIL_CHARS` **移除 `<`**；新增 `_JS_TYPE_PARAMETER_HEADS` ＋ `_statement_awaits_type_parameters(source, offset, index)`——`<` 只在「语句头仍只剩类型形参表」时续接（末词 `function`，或倒数第二词 ∈ `{function,class,interface,type,enum,namespace,abstract,declare}`），否则按**新语句** fail-closed。矩阵 +6（角括号断言一拒、断言数组字面量一拒、完成类型后接类型实参一拒、类型形参续接**三**接）。**第十九轮据实更正**：本条原写 +5 且枚举为「两接」，实测新增夹具为 6 条。S1 |真 `tsc 5.9.3`／`esbuild 0.21.5` 实测五种拼写均续接、两种「完成类型」按新语句。S1 |
| R102 | B¹⁸-S1（**S1**） | **正则语境启发式漏 `=>` 与控制头 `)`** ⇒ `/` 被当除法、其后 `'` 开启**幻影字符串**、整段置空 ⇒ 加载期语句隐形；真 Chromium 实测 `nodeDomain.ruleAlive=true / browserDomain.ruleAlive=false / prototypeIncludesIsStub=true`，同时 `eslint` 0 error、`vue-tsc` 32（无新增）、`vite build` exit 0 ⇒ **可部署** | `_JS_REGEX_PRECEDING_WORDS` 增 `throw`；新增 `_JS_REGEX_PRECEDING_BLOCK_KEYWORDS = {if,for,while,switch,catch}` ＋ `_js_opaque_spans()` 内 `paren_heads` 栈（`(` 记「前一词是否控制关键字」，`)` 弹栈得 `regex_preceding`）；`=>` 识别（`char == ">" and previous == "="` ⇒ `regex_preceding=True`）；并把 `_js_opaque_spans()` 改为 **5 元组**（新增 `crossed`：`'`／`"` 字面量只在**原始换行之下**才闭合），新增 `_js_unsegmentable_spans()`，`collaboration_module_scope_failures()` 与 `collaboration_import_closure_failures()` 的「不能切分」判定改用它（未闭合／跨原始换行两种理由分别报错）。矩阵 +6（箭头体／循环头正则两接、调用后除法一接、闭包层正则幻影两拒、闭包「只有箭头体正则」对照一接）。**第十九轮据实更正**：本条原写 +4 而枚举已有 5 项，实测新增夹具为 6 条。真树零误判：`valueUtils.ts`／`fieldUtils.ts`／`contractRuntimeVm.ts` 正则 span 数与旧版逐条相同（2／1／1）。S1 |
| R103 | A¹⁸-S3-1（**S3**，据实性） | §5 `:184` 仍写 `collaboration_self_check=200`，与同文件 §4／§6 的自相矛盾 | 按**本轮实跑**刷新为「自检 **243 例**、守卫 **6531 行**」：§1（`:8`／`:18`）、§3（`:60`／`:91`／`:97`）、§4（`:163`）、§5（`:184`／`:186`／`:215`）、§6（`:371`／`:518`）、§7 第 7 项与 §8 归属段一并改为 **243 例（56 接受 ＋ 187 拒绝）＝ 宿主／模块 169（32／137）＋ 页面 21（7／14）＋ import 闭包 53（17／36）**；R93／R98 行就地补「第十八轮据实更正」交叉引用。S3 |
| R104 | A¹⁸-S3-2（**S3**，据实性） | 三条「过严面」的**机制描述错**：文档称跨行 `export type X = Foo<Bar>` 换行 `[];` 是「被切开的**数组类型**」，真 `tsc`／`esbuild` 实测第二行是**独立语句**（`[];` 真跑到产物）——真正的机制是「第二行是独立语句」而非「类型被切开」 | §6 第 13 项 ⑱ 行就地更正定性，并把本轮新登记的过严面／开口面（`<` 收窄为「语句头仍只剩类型形参表」、`crossed` 引号 span fail-closed）一并记入新增的 ⑲；R101 的 `<` 判定与 `crossed` 规则即本条的两处来源。S3 |
| R99 | A¹⁷-F5（**S3**，随仓交付） | 第十六轮段 ⑦ 引用的「**载荷矩阵（20 行）**」**从未随仓交付**——复核者无法复算那份清单，只能读结论 | ①本轮把**载荷矩阵逐条随仓交付**（`delivery_context_switch_log_v1.md` 第十七轮段 ⑩，含每条载荷的判据编号、形状与期望），并写明第十六轮段 ⑦ 的 20 行清单以**本轮清单 ＋ 矩阵内的具名夹具**取代（同名夹具已在守卫里，可逐条复算）；②本轮新增的三条**过严面**同时作为**对照夹具**钉进矩阵（名字后缀 `(registered over-strictness)`），不依赖文档单点声明。S3 |
| R105 | A¹⁹-S1-1／B¹⁹-S1（**S1**，同根因） | **类型形参判定被「名字与关键字撞名」击穿**：`_statement_awaits_type_parameters()` 只取语句头的**最后两个词**——`export type type = number` 换行 `<unknown>…();`、`export type abstract = number`、`export type A = { type: () => void }`／`{ namespace: string }`／`{ enum: string }`／`{ class: string }` 全部被读成「仍在等类型形参」⇒ 幻影行的加载期投毒语句隐形。真 `tsc 5.9.3`／`esbuild 0.21.5` 证明这些拼写均可部署，B¹⁹ 更在真 `vue-tsc`／真 `vite build`／真 Chromium 上实测 `ruleAlive=false` 而守卫 PASS | 新增 `_JS_HEAD_MODIFIERS`／`_JS_TYPE_PARAMETER_HEAD_KEYWORDS`／`_JS_HEAD_EXPRESSION_KEYWORDS`／`_JS_HEAD_SINGLE_CHARACTER_TOKENS` ＋ `_js_head_tokens()`，`_statement_awaits_type_parameters()` 改为**读语句头形状**（在注释／字符串屏蔽后的文本上切词）：修饰词之后，①声明关键字 ＋ 至多一个名字（仅 `default` ＋ function／class 允许匿名），或②`名字 =`（可带 `async`）＋ 恰一个 function／class。矩阵 **+3**（宿主两拒 ＋ 闭包一拒）。实测 7 条撞名载荷（权威体 3 ＋ 闭包 4）全部 OLD=ACCEPT → NEW=REJECT。S1 |
| R106 | A¹⁹-S1-2（**S1**） | **9 个 Unicode `Pc` 连接符漏出标识符判定**：`_js_identifier_continue()` 只认 `isalnum` ＋ `Mn`／`Mc` ＋ 两个 `Other_ID_Continue` 记号，而 `U+203F U+2040 U+2054 U+FE33 U+FE34 U+FE4D U+FE4E U+FE4F U+FF3F` 九个连接符既非字母数字也非组合记号 ⇒ `extends‿:` 一族把标签胶进上一条 `export type`（与 R100 同族复活） | 新增 `_JS_IDENTIFIER_CONNECTORS`（九个 `Pc`）与 `_JS_IDENTIFIER_CONTINUE_SYMBOLS`（`U+30FB`／`U+FF65`／`U+2118`／`U+212E`／`U+309B`／`U+309C`），`_js_identifier_continue()` 增加 `Pc` 类、`Mn`／`Mc` 与「`>U+007F` 且 `unicodedata.category == 'Cn'`（未分配）」的 fail-closed 兜底，`_js_word_may_extend()` 复用同一集合。矩阵 **+2**（宿主两拒）。实测 Pc／符号记号 **15** 条载荷（9 个 `Pc` ＋ 6 个符号记号）全部 OLD=ACCEPT → NEW=REJECT。S1 |
| R107 | A¹⁹-S1-3（**S1**） | **正则前置字符表缺 `>`**：`_JS_REGEX_PRECEDING_CHARS` 不含 `>`，`_js_opaque_spans()` 只对 `=>` 特判 ⇒ `export function pad(n) { return (n as any) > /[']/.test(String(n)); } ; (Array.prototype as any).includes = () => false; // '` **同一行**内，字符类里的 `'` 开启一个到行尾注释里才闭合的**幻影字符串**（不跨原始换行，`crossed` 规则看不见），整段投毒语句被擦除、守卫 PASS；同族还能把 `screen`／`window` 环境引用一并藏掉（击穿「环境盲」） | ①`<` 并入 `_JS_REGEX_PRECEDING_CHARS`（`<` 在任何读法下都不能结束表达式，`/` 必为正则）；②新增 `_JS_REGEX_AMBIGUOUS_PRECEDING_CHARS = {'>'}`——`>` 既可能是比较符也可能是类型实参收尾，两种读法隐藏**不同**语句，故 `_js_opaque_spans()` 对紧跟 `>`（且非 `=>`）的 `/` 追加一个 `ambiguous` span（`terminated=False`），两处「不能切分」格式化器各加一条具名理由，**拒绝而不猜**。矩阵 **+5**（三条 A→R ＋ 一对照接 ＋ 一条 `(registered over-strictness)`：`export function* gen` 换行 `<T>(): Iterable<T> {}` 真 `tsc`／`esbuild` 均 rc=0 但仍被拒，属注册在案的过严面）。S1 |
| R108 | A¹⁹-S3-2／S3-3／S3-4／S3-5（**S3**×4）＋ A¹⁹-S4-1（**S4**，据实性） | ①第十八轮那 13 行**载荷矩阵**逐行 OLD 列**错了 8 行**（`R105` 行 P18-05／06／07／08／09／11／12／13：把「新增即通过的接」「旧版即拒绝的闭包幻影串」写成别的方向；A¹⁹ 报 6 行，本轮逐行复算为 **8 行**，聚合数 6／3／4 本身正确）；②R100／R101／R102 的**每规则夹具增量**写成 2／5／4＝11，实测为 **1／6／6＝13**；③3 例 R→A 的**指名**错（实为「箭头体正则／循环头正则／闭包『只有箭头体正则』」，不是「三处类型形参续接」）；④§6 第 13 项 ⑲① 把**不编译**的 `export type A = Record` 换行 `<string, number>;`（真 `tsc` TS1005／TS1109）称作「跨行续写的真类型实参」；⑤§3 提交链仍是首批 10 笔的口径（实测 `de9a230d..e4435c77` 共 **46 笔**） | 逐条据实更正：①按 `/tmp/p19r/cross18truth.py`（`f944b313` × `e4435c77` 逐行求值）重写 13 行矩阵，切换日志同批更正；②改为 1／6／6＝13 并就地登记「原写 2／5／4」；③改为三条正则夹具的实名；④⑲① 改按真工具链结论重写，并把可复现的**真**过严面换成 `export function* gen` 换行 `<T>()`（`tsc`／`esbuild` rc=0，本轮为其新增 `(registered over-strictness)` 夹具）；⑤§3 补全逐轮提交清单并写明实测计数口径。S3×4＋S4 |
| R109 | A²⁰-S2-2（**S2**，过严面；本轮只登记了一类拼写） | **生成器头与非 ASCII 名字头的跨行类型形参表被读成新语句**：`_statement_awaits_type_parameters()` 的 tail 判定把 `*` 当单字符 token 计入（`function`＋`*`＋`name` 的 tail 长度是 2 而不是 1），`_js_identifier_start()` 又是有意 ASCII-only（非 ASCII 名字读不出 token、tail 变空）⇒ `export function* gen`⏎`<T>…`／`export async function* gen`⏎`<T>…`／局部 `function* gen`⏎`<T>…`／`export function 名`⏎`<T>…` 四类拼写全部被读成「下一行是独立语句」并拒绝；真 `tsc 5.9.3`／`esbuild 0.21.5` 对四类拼写**全部 rc=0**（A²⁰ 报四类，本轮逐条复算一致） | 新增 `_js_identifier_start_non_ascii()`（词法起名的**非 ASCII 半边**：字母／`Nl`／两个 `Other_ID_Start` 符号／未分配 `Cn` 兜底；**只在 head 形状判定里读**，`_js_identifier_start()` 的 ASCII-only 取值**不动**，以免 R100 的「非 ASCII 起句仍按首字符报告」漂移）＋ `_js_head_token_is_name()` ＋ `_js_head_declared_tail()`（把生成器记号 `*` **跳过而非计作第二个名字**），两处 tail 判定改用它们，`_js_head_tokens()` 读非 ASCII 名字串。矩阵 **+4 宿主 ＋ 3 闭包**（其中 1 条宿主是既有 `(registered over-strictness)` 夹具**转正**）。实测：新 260 例 × `309cec59` = **6** 例 R→A（4 宿主 ＋ 2 闭包，正是本轮修回的六类拼写），0 例 A→R；**变异鉴别**：停用「跳过 `*`」→ 自检点名 4 条生成器夹具，停用非 ASCII 名字判定 → 点名 2 条。S2 |
| R110 | A²⁰-S2-1（**S2**，过严面，本轮未登记） | **`>` 后紧跟 `/` 一律拒绝**，合法比较被一并拒掉：`(a as any) > /x/.test(b)`（真 `tsc`／`esbuild` 均 rc=0）在权威体层与闭包层**同时** REJECT，拒因是「cannot be segmented」 | **判定：保留拒绝，登记而不收窄**。①「按窗口是否含引号才拒」**不可落地**：投毒载荷 `(n as any) > /[']/…` 与合法的 `(a as any) > /[']/.test(b)` **共用同一个窗口**（`/[']/`），按窗口判据二者同判；②「把 `>` 后的 `/` 一律读作字面量」正是 R107 要堵的那条读法。**变异鉴别**：停用该拒绝 → 投毒载荷 P20-02 由 REJECT 翻 **ACCEPT**（规则承重）。故新增一条 `(registered over-strictness)` 夹具（宿主 ＋ 闭包各一条）钉住本过严面，并在代码注释里写明取舍；`a < b > /x/.test('y')` 由同一规则拒绝且**两工具均不编译**（TS1109／esbuild 报错），那部分零成本。S2 |
| R111 | A²⁰-S3-1／S3-2（**S3**×2，据实性） | ①第十八轮段 ⑦ 把**夹具层**聚合数（新增 13 条夹具 × `f944b313` → 6 A→R／3 R→A／4 A→A）写成「**载荷矩阵（⑨，13 行）** → 6 行／3 行／其余 4 行」，与 ⑨ 表自身互斥（⑨ 表按行清点为 **4** A→R／**3** R→A／**4** A→A／**2 R→R**，4＋3＋4＝11≠13）；②同段与 §8 第十八轮段末句写「**1** 例两版一致 ACCEPT（闭包「只有箭头体正则」）」，而该闭包夹具实测为 **R→A**（⑨ 表 P18-13 自己就标 `REJECT -> ACCEPT`），两版一致 ACCEPT 的是 **4** 条**宿主**夹具 | 两处均**据实更正**：把两个计数分开写明（夹具层 6／3／4；⑨ 表 4／3／4／2），末句改为「**4** 例新增宿主夹具两版一致 ACCEPT（function 头／interface 头／type-alias 头／除法对照）」。复算脚本 `/tmp/p20/r18fixtures.py`（13 条新增夹具逐条 × `f944b313`）。S3 |
| R112 | A²⁰-S4（**S4**，据实性） | 第十九轮段 §8 的归因括号「（R105 三条 ＋ R106 两条 ＋ R107 三条 ＋ 闭包一条）」**多算一条**：8 条宿主翻转实为 **R105 两拒 ＋ R106 两拒 ＋ R107 三拒 ＋ 生成器头一拒**（**第二十一轮按 A²¹-S4-1 改写**：该例不属 R105／R106／R107 **三者**的加固面——它是第十九轮把 `_statement_awaits_type_parameters()` 由「最后两个词」改为「读语句头形状」（R105 的改写）时**新引入**的过严面，本轮 R109 已判放行、夹具由 `expected=False` 改 `True`） | 括号改为「**R105 两拒 ＋ R106 两拒 ＋ R107 三拒 ＋ 生成器头一拒 ＋ 闭包一拒**」，与 R105／R106／R107 行自述的 `+3`（宿主两拒 ＋ 闭包一拒）／`+2`（宿主两拒）／`+5` 交叉一致。S4 |
| R113 | A²¹-S1（**S1**，等价绕过） | **`>` 后接 `/` 的歧义拒绝可被一个 `U+FEFF` 绕过**：`_js_opaque_spans()` 的空白判定用本解释器的 `str.isspace()`（对 `U+FEFF` 为 False），而 TypeScript 词法把 `U+FEFF` 读作空白 ⇒ `previous` 被该字符顶掉、`ambiguous` span 不产生 ⇒ `/` 被读成除号、紧随的 `'` 开启一个**同行闭合**的幻影字符串 ⇒ 整段投毒语句被擦除、守卫 **GREEN**；同载荷真 `esbuild --bundle` ＋ `node` 实测加载期投毒生效（`[1,2].includes(1)` 由 `true` 变 `false`），**权威体层与闭包层同时**；`U+200B`／`U+200C`／`U+200D`／`U+2060` 同族 | `_js_opaque_spans()` 的空白判定改用文件内**既有**的 `_js_is_blank()`（＝ `str.isspace()` ＋ `_JS_INVISIBLE_CHARACTERS`，与语句走查同一读法），宿主／闭包各补一条具名夹具（`expected=False`）。实测：12 行载荷矩阵中 10 例 `ACCEPT → REJECT`、2 例对照两版 `REJECT`；**262** 例 × 上一候选 `77d23382` 交叉求值**恰 2 例翻转**（即两条新增夹具），既有 260 例 **0 翻转**；真实树仍 PASS。见本段第二十一轮 |
| R114 | A²¹-S4-1（**S4**，据实性／措辞） | R112 行括号「生成器那条属 R107 的登记面」不准（R107 是**正则前置字符表**，与该例无关） | 按 A²¹ 判定改写为「不属 R105／R106／R107 **三者**的加固面；它是第十九轮 R105 改写时新引入的过严面，本轮 R109 已判放行」 |
| R115 | A²¹-S4-2（**S4**，据实性，**非阻断**） | `_js_head_declared_tail()` 无条件删掉 tail 里**所有** `*`，于是「删掉 `*` 后恰剩一个名字」比「合法生成器头」宽：`export function 名*`⏎`<T>()`／`export function * *`⏎`<T>()`／`export function*`⏎`<T>()`／`export function *`⏎`<T>()`／`export type gen*`⏎`<T> = T;` 五形在宿主层与闭包层**均 ACCEPT**，而真 `tsc 5.9.3`（`TS1003`／`TS1005`）与 `esbuild 0.21.5` **全部 rc≠0** ⇒ 不可编译 ⇒ 无加载期执行面（惰性） | **据实登记，本轮不改规则**；并**实测否证**「收紧为『只跳过紧邻关键字的一个 `*`』即可关闭」——该收紧对五形**逐一无影响**（仍 ACCEPT），说明五形由**另一条路径**放行，故留作后续轮次的定向项（见本段第二十一轮） |



R1／R2 产生候选 `23928265`（已重跑 L1／L5 并获 VERIFIED 回执）；R9／R10（绑定提交 `50faccf5`）把断言从
「标志表达式一个位点」扩到「表达式 ＋ 权威派生 ＋ 类型声明 ＋ 消费接线四个位点」、自检矩阵 13 例 → 22 例；
R15–R21（第三轮复核后的修订）按第三轮复核根因把协作区判定**下沉为单一权威 ＋ 可执行真值表**，守卫退化为只绑
**接线**，自检矩阵 22 例 → **26 例**，`checks` 改为运行时统计。

R28–R34（**第五轮**，第五轮复核后的收口）按两位复核者与自查的十项发现逐条收窄：块体委派**必须真 `return`**（V21，
真 bug）；证明目标**唯一定义**、`esbuild` 输入**字面路径**、outfile **独占**、执行行按 basename 锚定 `node`；
宿主 import 的 **specifier** 与宿主／证明的**模块同一性**被绑定；三个权威体改为**单一 `return` 表达式**并禁止
**运行期环境探针**（封 V01／V02／S2-F2）；区域插槽改为**直接子元素**，元素区间改由**引号感知扫描**一次算出、
未闭合元素**逐个收尾**（封 S3-F3／V06）；页面侧两个属性改为**元素级 ＋ 逐处表达式**绑定（封 V03／V04）。
矩阵 36 例 → **54 例（6 接受 ＋ 48 拒绝）**，`checks` 运行时统计 **127**；证明 51 例不变（`:27` 改 `strictEqual`）。
另更正两处**据实性**：R24 的「运行中的证明＝被复核的证明」过度声称（改为「源码层⑥ ＋ 配方层⑤」并登记残余面）、
R27 的「`surfaces` 逐条不变」实为「仅指纹字段变化」。据实登记：守卫 1420 → **1940 行**，越过阈值并被机器生成物登记为
`split_plan_queue.md` 的 P2 项（未上调任何锁），回收方案见 §7 第 7 项。

**一处跨轮更正**：R26 行末「本轮已把诱饵挪到元素**内**，矩阵遂对注释屏蔽**真有**鉴别力」是第四轮当时的复算结论，
按第六轮的 77 例矩阵**不再复现**（恒等化后零翻转），已按 R40 改登记为纵深防御——R26 行保留为当时记录。
**第六轮**（A⁶ 判 APPROVE 只列 S3×3／S4×2；B⁶ 判 REQUEST_CHANGES，S1×1 直指环境探针黑名单整族可绕）对冻结候选
`f2a94f614fc5be4b41903d3c44557202d2e68588`（第五轮收口提交）的七项发现逐条收窄（R35–R41，绑定提交
`45466b62`）：三个权威体由**黑名单禁探针**改为**整表达式等值**（`_expression_failures` 对归一化后的表达式做规范
等值比较，探针族结构性被拒）；权威体的**函数体定位**改为「注释＋字符串都屏蔽后定位、再从原文读回」（封字符串
decoy 顶替 body）；`_scan_tags` 跳过 `{{ … }}` 插值并对 14 个 void 元素视为自闭合（封假闭合与合法 void 误拒）；
import 绑定要求 `local == imported` 并拒绝解构（封 `as` 别名与命名空间解构）；⑤的扫描面扩到 `Makefile` ＋
`make/*.mk` 且拒绝变量名目标与含 `$(`／`${` 的配方行（封 `$(VAR)` 目标／outfile 覆盖）；页面侧改按**属性表**解析
并新增**页面层自检矩阵**（此前页面层无矩阵）。矩阵 54 例 → **77 例（10 接受 ＋ 67 拒绝）**；
证明真值表 51 例 → **102 例**（同一张表在 `node` 域与**浏览器域**各跑一遍，装／卸 `window`／`document`／
`navigator`／`self` 并断言全局被恢复）；`checks` 仍 **127**。据实登记：守卫 1940 → **2528 行**，仍在
`split_plan_queue.md` 的 P2 项（**未上调任何锁**）。另按 A⁶ 更正两处**据实性**：撤回「矩阵对 HTML 注释屏蔽有
鉴别力」的旧声明（77 例复算零翻转），并把 `--outfile=$(VAR)` 从「未覆盖」更正为「**已被拒**」。
**据实登记一处与复核报告不一致**：B⁶ 的 V18（命名空间导入 ＋ 解构）按报告是 LEAK，实测**修复前就已被**
「宿主不得自声明该权威」拒绝，故它不是本轮修复项。

**第七轮**（A⁷ 与 B⁷ 均判 **REQUEST_CHANGES**：A⁷ 报 F1 错位读窗／F2 模块级加载期门控／F3 载体—插槽—面板死门族，B⁷ 另以 Vue 编译器探针证实「后声明插槽胜出」与插槽内面板 `v-if` 的真实行为）对冻结候选
`5e3120dc`（第六轮收口提交）的八项发现逐条收窄（R42–R49，绑定提交为本次提交）：`_blank_comments_and_strings` 改**保长**、读窗定位
**自证对齐**（F1）；新增**模块纯净性**（整模块禁环境全局／`import.meta`、顶层语句白名单）与**顶层绑定形状白名单**（F2／R48）；`#collaboration`
**单插槽**、插槽内**面板存在式**与面板／载体／祖先的**字面死门**检查（F3 族）；宿主属性改按**属性表**读、单引号写法转为接受面（R46）。
矩阵 77 例 → **99 例（12 接受 ＋ 87 拒绝）**＝宿主／模块 86（10 接受 ＋ 76 拒绝）＋ 页面 13（2 接受 ＋ 11 拒绝）；`checks` **128**（自检 99）。
据实登记：守卫 2528 → **3136 行**，因越过 `lines >= 3000` 阈值由 `split_plan_queue.md` 的 P2 升为 **P1**（**未上调任何锁**），回收方案见 §7 第 7 项。

**第八轮**（A⁸ 与 B⁸ 均判 **REQUEST_CHANGES**：A⁸ 报 S1-1 导出加载期声明未扫描、S2-1 面板祖先死门未覆盖、S2-2 括号属性访问误拒〔据实性〕、S3-1 矩阵用例名实不符、S4-1 计数不符；B⁸ 另报注释屏蔽不识别字符串、具名 import 与副作用 import 不等价、`v-slot:` 二次声明可顶掉已接线插槽）对冻结候选 `4e9e2fc8`（第七轮收口提交）的发现逐条收窄（R50–R56，绑定提交为本次提交）：`_blank_comments` 增**引号不透明**（R56）；新增**导出加载期声明**拒绝并收窄顶层语句白名单（R50）；运行时 `import` 的 specifier 须落在**已复核清单**内（R56）；插槽计数改**元素级插槽名归一化**（R52／R54）、面板**祖先**死门纳入（R53）；委派实参的**括号属性访问**归一化恢复（R51）；另更正矩阵用例「ancestor」名实不符（S3-1）。
矩阵 99 例 → **111 例（15 接受 ＋ 96 拒绝）**＝宿主／模块 **98（13 接受 ＋ 85 拒绝）** ＋ 页面 13（2 接受 ＋ 11 拒绝）；`checks` 仍 **128**（自检 **111**）。据实登记：守卫 3136 → **3379 行**，`split_plan_queue.md` 仍在 **P1**（**未上调任何锁**），回收方案见 §7 第 7 项；第八轮实测 **13** 例翻转＝**10** 例 OLD=GREEN → NEW=REJECT ＋ **3** 例 OLD=REJECT → NEW=GREEN（对照组：类型导入、基线模块等仍按原判——见 §6 的鉴别力清单）。

**第九轮**（A⁹ 与 B⁹ 均判 **REQUEST_CHANGES**：A⁹ 报 S1 import specifier 取错字符串 ＋ 正则／未闭合 span 不可切分、S2 未闭合块注释吞掉其下语句、S4 §6 的 `declare const …` 与 R50 自相矛盾；B⁹ 另以**真 `@vue/compiler-sfc@3.5.27` ＋ SSR** 实测三例：注释诱饵可使新模块在**浏览器域加载期**改 `Array.prototype.includes` 而门禁恒绿、正则引号使 `region present = false`、计算插槽名二次声明使协作区空渲染）对冻结候选 `0faf569a`（第八轮收口提交）的发现逐条收窄（R57–R60，绑定提交为本次提交）：新增 `_js_opaque_spans()` 统一注释／字符串／模板／**正则**为带 `terminated` 的 span，`_blank_comments`／`_blank_string_literals` 由它派生，**未闭合即拒**（R57）；新增 `_collaboration_import_failure()` 只读 `from` 子句的 specifier 并拒尾随文本（R58）；`_slot_names()` 对**计算插槽名**报哨兵并新增消费侧拒绝循环（R59）；新增 `_COLLABORATION_PANEL_GATE` 使面板 `v-if` 与权威等值（R60）；另按 A⁹-S4 更正 §6 的 `declare const …` 登记。
矩阵 111 例 → **120 例（16 接受 ＋ 104 拒绝）**＝宿主／模块 **107（14 接受 ＋ 93 拒绝）** ＋ 页面 13（2 接受 ＋ 11 拒绝）；`checks` 仍 **128**（自检 **120**）。据实登记：守卫 3379 → **3629 行**，`split_plan_queue.md` 仍在 **P1**（**未上调任何锁**），回收方案见 §7 第 7 项；第九轮实测 **8** 例翻转＝**8** 例 OLD=GREEN → NEW=REJECT ＋ **0** 例 OLD=REJECT → NEW=GREEN（`/tmp/r59/vectors.py`，双进程影子 ＝ `git archive 0faf569a` vs 候选工作树；对照组：R58-3 镜像、R58-4 类型导入、基线模块仍 GREEN）。

**第十轮**（A¹⁰ 与 B¹⁰ 均判 **REQUEST_CHANGES**：A¹⁰ 报 S2-1 `_module_statements` 对 `(`／`{` 开头语句整体失明（fail-open）、并另报 6 条据实性问题——「14 个前置关键字」实测为 **13**、R57「矩阵 +3」多算一例**应为 +2**、§6 鉴别力 (i) 的**归因不成立**、§8 悬空引用「§5 向量 R57-1／R57-2」、§7 第 12 项 ⑥ 可关闭未关闭、R59 存在**域差异**；B¹⁰ 用真 `@vue/compiler-sfc@3.5.27` ＋ `@vue/server-renderer` ＋ TS 5.9.3 ＋ esbuild 0.21.5 ＋ prettier 3.8.1 另报三处**第九轮同一面墙未关的门**〔均为**第八轮即已存在**的旧洞，非 `db734ea5` 引入的回归〕：**语句切分三类盲点**（裸块／IIFE／ASI，追到真实文件末尾后浏览器域规则真死且**可部署**）、**已复核 import 的内容从不被读取**（门控放进 `valueUtils.ts` 即可一字不改绕过）、**载体／祖先只按字面假值判**（`&& false` 的祖先或载体使 `panel=ABSENT` 而 GREEN），另报一条**假 REJECT**（模板撇号）与两条无害项〔计算插槽名嵌套容器**不可部署**、`#Collaboration` **不同槽位**〕）对冻结候选 `47b9a631`（第九轮收口提交）的发现逐条收窄（R61–R64，绑定提交为本次提交）：`_module_statements` 补三类空洞并把顶层 `}` 的续句判定改为**后随字符**（R61）；新增 `collaboration_import_closure_failures()` 把「已复核 import」变成**真读文件 ＋ 环境纯净闭包**（R62）；`_dead_gate_failures()` 从**字面假值黑名单**改为**登记式等值清单**、`v-show` 一概拒绝、`v-else` 按元素登记（R63）；新增 `_script_text()` 把 JS 级屏蔽限定在 `<script>` 区域（R64）；另按 A¹⁰-S4 更正四处文档计数／归因（关键字 13、R57 +2、鉴别力 (i) 的**未闭合拒绝**归因、悬空引用），并关闭 §7 第 12 项 ⑥（`#Collaboration` **不是**同一槽位，一律 REJECT，方向安全）与登记 R59 的**客户端／SSR 域差异**（客户端编译把计算名放静态 slots、字面槽放动态数组，`createSlots` 先套静态后覆盖动态 ⇒ 客户端不顶掉；SSR 同数组后者胜 ⇒ 空渲染；矩阵用例在客户端域偏严，方向 fail-closed）。
矩阵 120 例 → **142 例**＝宿主／模块 **118**（新增 11）＋ 页面 **18**（新增 5）＋ **import 闭包 6**（新矩阵）；`checks` 128 → **129**（新增 import 闭包 `require`，自检仍由矩阵长度实时导出）。据实登记：守卫 3629 → **4212 行**（按同一口径为全仓第 5 大代码文件、Python 源码第 4），`split_plan_queue.md` 仍在 **P1**（**未上调任何锁**），回收方案见 §7 第 7 项；第十轮实测**翻转面**：真文件影子逐个注入 R61／R62／R63 的三类载荷**全部被拒**、还原即 PASS；停用未闭合 span 拒绝翻 **1** 例、import 规则换回第八轮形状翻 **1** 例、计算插槽名不再报哨兵翻 **2** 例、停用正则识别翻 **0** 例（归因见 §6 鉴别力 (i)）、停用面板等值规则翻 **0** 例（已被 R63 包含）。

**第十一轮**（A¹¹ 与 B¹¹ 均判 **REQUEST_CHANGES**：A¹¹ 独立复算全部聚合数字**对上**并另报 1 条 S1 门禁强度缺口——顶层**模板字面量语句**被整段抹平而 fail-open、1 条 S3 文档自相矛盾（仍在现在时用第九轮口径）与 3 条 S4 据实性（R61 举例写错、R63 接受面口径、第 4 大文件不成立）；B¹¹ 另报 **4 条 S1**：R61 的 `_JS_STATEMENT_TAIL_CHARS` 把 `!`／`~` 等不能续接表达式的字符也算续句，`!gate()` 藏在函数声明之后——**OLD(`47b9a631`)=REJECT → 第十轮=GREEN**，即第十轮引入的**回归**；闭包模块不适用「本层只能是声明」故顶层环境探针无人读；闭包只跟静态 `import` 边，re-export 与动态 `import()` 到达的模块从不被打开；登记式死门清单不含空 `v-for`。另有 2 条 S2／S3 与 2 条 S3 假 REJECT（`</SCRIPT>` 大小写、`<!-- <script> -->` 顶掉模板））对冻结候选 `305245f9`（第十轮收口提交）的发现逐条收窄（R65–R71）：续句表只留中缀运算符并把 `U+2028`／`U+2029` 当换行（R65／R66）；模板 span 保留起始反引号（R67）；闭包新增「本层语句必须是声明」＋ 边遍历扩到 re-export／动态 import ＋ 深度触顶改报 failure（R68）；`v-for` 纳入登记式死门（R69）；`</SCRIPT>` 与 HTML 注释两处假 REJECT 收口（R70）；四处文档口径就地刷新（R71）。
矩阵 142 例 → **154 例（26 接受 ＋ 128 拒绝）**＝宿主／模块 **124（18 接受 ＋ 106 拒绝）** ＋ 页面 **19（5 接受 ＋ 14 拒绝）** ＋ **import 闭包 11（3 接受 ＋ 8 拒绝）**；`checks` 仍 **129**（本轮未新增静态 `require` 调用点）。据实登记：守卫 4212 → **4433 行**（按同一口径为全仓第 4 大代码文件、Python 源码第 3），`split_plan_queue.md` 仍在 **P1**（**未上调任何锁**），回收方案见 §7 第 7 项；第十一轮实测**翻转面**：B11-1（`!gate()`）为 **OLD=REJECT → NEW=GREEN → 现值 REJECT** 的回归闭合，B11-3／B11-4／B11-5 为 GREEN → REJECT，A11-1／B11-2 为 GREEN → REJECT，B11-7／B11-8 为 REJECT → GREEN（假 REJECT 收口）；**据实登记（第十二轮再更正，见 R75）**：第十一轮写的「R61 举例里的非整式括号赋值在旧版即 REJECT」**不成立**——按 `git archive 47b9a631` 复测，旧版对**单层整式括号**同样不可见（只报完全无括号的裸赋值），故不可见面确为整式括号与逗号表达式。

**第十二轮**（A¹² 与 B¹² 均判 **REQUEST_CHANGES**：A¹² 报 S1-1 闭包**声明初始化式**藏环境探针（`export const dead = typeof screen !== 'undefined'`）、S1-2 `}` 后续句表仍留 `+`／`-`／`/`、S2-1 **深度触顶模块不被读**、S3-1 文档 6 处仍在现在时用第十轮口径（`142`／`4212 行`）、S3-2「全仓第 5 大」不成立（实测第 4 大、Python 第 3）、S3-3 R61 的「据实更正」本身不实、S3-4 闭包形状阶梯缺 `class` 等合法声明（假 REJECT）、S3-5 非字面量动态 `import()` 不跟边、S4-1 文档引用不存在的 `_closure_relative_specifiers`、S4-2 §7⑨ 机制描述错、S4-3 `_script_text()` 不先屏蔽 HTML 注释；B¹² 以真 `@vue/server-renderer` 实证浏览器域失效，另报 S1-1 同 A¹²-S1-2（`+`／`-`／`/`／`as`／`from`／`satisfies` 首词）、S1-2 闭包层用**非字符串感知**屏蔽（`export const OPEN = '{'` 令整文件隐形）、S1-3 闭包层只判首 token（`export default <表达式>` 加载期执行）、S2-1 闭包对**含插值的模板字面量**假 REJECT、S2-2 `data-note="<script"` 属性值假 REJECT、S3-1 非相对 specifier、S3-2 环境清单不含 `screen`）对冻结候选 `956dbcbd`（第十一轮收口提交）的发现逐条收窄（R72–R78，绑定提交为本次提交）：闭包读取抽出 `read_module()` 且**深度边界先读再报**（R72）；`+`／`-`／`/` 移出续句表 ＋ **声明体 `}` 即语句终点**（R73）；环境全局清单补入 `screen` 一族并给闭包出口加形状阶梯（R74）；更正 R61 行的**旧版归属**（R75）与 §7 第 13 项的符号名／机制描述并登记 ⑩⑪⑫（R76）；动态 `import()` 的非字面量 specifier fail-closed（R77）；`_scan_tags()` 上移并把 `_script_text()`／`_template_before_script()` ＋ **两处消费侧调用点**统一到标签扫描（R78）。另按 A¹²-S3-1／S3-2 更正文档中的**当下口径**（自检 `174`、守卫 `4849 行`、代码体量排名按 `git ls-files` 代码类扩展名口径重算）。
矩阵 154 例 → **174 例（34 接受 ＋ 140 拒绝）**＝宿主／模块 **133（21 接受 ＋ 112 拒绝）** ＋ 页面 **21（7 接受 ＋ 14 拒绝）** ＋ **import 闭包 20（6 接受 ＋ 14 拒绝）**；`checks` 仍 **129**（本轮未新增静态 `require` 调用点）。据实登记：守卫 4433 → **4849 行**（按同一口径为全仓第 3 大代码文件、Python 源码第 2——本轮首次**超过** `unified_page_contract_v2_assembler.py` 的 4841 行，§7 第 7 项的回收因此更紧迫），`split_plan_queue.md` 仍在 **P1**（**未上调任何锁**）；第十二轮实测**翻转面（第十三轮据实更正，见 R79）**：**15** 例翻转 ＝ **12** 例 OLD=GREEN → NEW=REJECT（闭包字符串含 `{`／边界语句／`export default` 表达式／类静态初始式／非字面量 `import()`／`screen` 初始化式 ＋ 六条 `}` 后续句）＋ **3** 例 OLD=REJECT → NEW=GREEN（模板插值、宿主与页面的引号属性值 decoy）；其余 **159** 例判定**逐条不变**（`/tmp/r512/diff_all.py`，旧树 ＝ `git archive 956dbcbd`）。

**第十三轮**（A¹³ 与 B¹³ 均判 **REQUEST_CHANGES**：A¹³ 报 S1 闭包出口的**声明白名单本身是开口**——非导出模块级绑定的初始化式（`const box = new Image()` 一类环境名不在枚举清单内的写法）与 `export default class` 的**静态初始式**（`static x = (((Array.prototype as any).includes = () => true), 1)` 在加载期污染原型，权威在每个域都答 `true`）、类**表达式**的静态初始式三类载荷全部放行；另报 S3 据实性（第十二轮差分数 11＋3＋159 ＝ 173 ≠ 174）、S4×2（R71-② 未挂更正标记且 R75 交叉引用写错、体量排名口径未钉死）与一条**不成立**的 S2（`<SCRIPT>` 大小写「假 REJECT」）；B¹³ 除同源 S1-1／S1-2／S1-3 外另报 S1-4 动态 `import(literal, { with: {} })` **fail-open**、S2-1 新增假 REJECT `export enum`、S2-2 枚举族无界、S3-1 同 A¹³ 的差分数、S4-1 `export =` 放行）对冻结候选 `379163ec`（第十二轮收口提交）的发现逐条收窄（R79–R84，绑定提交为本次提交）：闭包出口**由形状规则取代声明白名单**（模块级绑定／类体／`export =` 按形状拒绝、`export default` **任意形态**一律拒绝，R83）；动态 `import()` 收紧为「字面量后紧跟 `)`」（R84）；R61／R71 的归因与交叉引用就地更正（R80）；第十二轮差分数更正为 **15** 例（R79）；体量排名口径**钉死**（R81）；`<SCRIPT>` 大小写主张据真 `@vue/compiler-sfc` 复算**驳回**（R82）；另按 A¹³-F3／F5 更新文档中的**当下口径**（自检 `180`、守卫 `5018 行`、闭包 26 例）。
矩阵 174 例 → **180 例（34 接受 ＋ 146 拒绝）**＝宿主／模块 **133（21 接受 ＋ 112 拒绝）** ＋ 页面 **21（7 接受 ＋ 14 拒绝）** ＋ **import 闭包 26（6 接受 ＋ 20 拒绝）**；`checks` 仍 **129**（本轮未新增静态 `require` 调用点）。据实登记：守卫 4849 → **5018 行**（按 §7 第 7 项钉死的 `SCAN_ROOTS` 口径为**全仓第 1 大代码文件、Python 源码亦第 1**），`split_plan_queue.md` 仍在 **P1**（**未上调任何锁**）；第十三轮实测**翻转面**：**7** 例翻转，**全部**是**新增夹具名**的 OLD=ACCEPT → NEW=REJECT（`export default class` 声明／带静态初始式／带静态块、`export =` 赋值导出、非类型包导入、动态 `import()` 带第二实参、模块级绑定读环境），**0** 例 OLD=REJECT → NEW=ACCEPT，其余 **173** 例判定**逐条不变**（`/tmp/r13/diff.py`，旧树 ＝ `git archive 379163ec`）；另**据实登记**：`export enum` 仍被拒（**假 REJECT**，方向 fail-closed、真实闭包 4 文件无 `enum`，见 R84），`<SCRIPT>` 起始标签大小写敏感的拒绝经真编译器复算为**正确**（R82）；B¹³ 另据实登记：其复核期间候选工作树被本轮修复**并发写入**，故其结论绑定的是 `git archive 379163ec` 的提交树而非当时的磁盘状态。

**第十四轮**（A¹⁴ 与 B¹⁴ 均判 **REQUEST_CHANGES**：A¹⁴ 报 S1 闭包成员层的**非相对 `export … from` 再导出**既不跟边也不拒绝（用真实别名 `@/` 端到端复现：守卫 GREEN、`esbuild` 把探针带进产物、浏览器域规则真死），另报两条非阻断据实性（`export enum` 被标「假 REJECT」而实测是真阳性、闭包夹具账目「新增 7 ＋ 改写 1」实测应为「新增 6 ＋ 改写 2」）；B¹⁴ 用真 `@vue/compiler-sfc@3.5.27` ＋ 真 `esbuild@0.21.5` ＋ 真 Chromium 独立复现同一条再导出缺口，并另报 S1 **`type`／`interface` 上下文关键字**——`type(typeof customElements !== 'undefined' && (Array.prototype.includes = () => false));` 的首 token 在声明白名单上、被读成类型别名而放行（对照把 `type` 换成 `probe` 即 REJECT），同时**确认**上一轮 B¹³ 的四条载荷在本轮 head 上全部 REJECT）对冻结候选 `379829c4` 的发现逐条收窄（R85–R87）：**声明白名单改为形状规则**（`type`／`interface`／`function` 必须真的声明出名字，R85，权威体层与闭包成员层同时生效）；**打不开的再导出与打不开的 import 同规拒绝**（R86）；`export enum` 用词与夹具账目就地更正并新登记两条非阻断面（R87）。
矩阵 180 例 → **188 例（37 接受 ＋ 151 拒绝）**＝宿主／模块 **135（22 接受 ＋ 113 拒绝）** ＋ 页面 **21（7 接受 ＋ 14 拒绝）** ＋ **import 闭包 32（8 接受 ＋ 24 拒绝）**；`checks` 仍 **129**（本轮未新增静态 `require` 调用点）。据实登记：守卫 5018 → **5167 行**（按 §7 第 7 项钉死的 `SCAN_ROOTS` 口径仍为**全仓第 1 大代码文件、Python 源码亦第 1**），`split_plan_queue.md` 仍在 **P1**（**未上调任何锁**）；第十四轮实测**翻转面**：**5** 例翻转，**全部**是**新增夹具名**的 OLD=ACCEPT → NEW=REJECT（权威体 `type` 调用、闭包 `type` 调用、三条打不开的再导出），**0** 例 OLD=REJECT → NEW=ACCEPT，其余 **183** 例判定**逐条不变**（旧树 ＝ `git archive 379829c4`）。

**第十五轮**（A¹⁵ 与 B¹⁵ 均判 **REQUEST_CHANGES**：A¹⁵ 报 S1-1 无空白再导出租（`export*from'./x'`）整条链既不跟边也不拒——真浏览器域实测域规则真死，S1-2 读取窗口**先截断后折叠空白** ⇒ 垫 400+ 空格即可绕过刚收口的三条拒绝面，S2 新增形状规则对**嵌套泛型** `>>` 假 REJECT，S3 无空白副作用导入的**既有假 REJECT**；B¹⁵ 用真 `@vue/compiler-sfc@3.5.27`＋真 `esbuild@0.21.5`＋真 Chromium 独立复现同一 S1（含真 `@/` 别名，探针真进了浏览器 bundle）与同一 S2，另报 S4 据实性——R86 行「五条载荷全部 FAIL」只对**有空白**拼写成立）对冻结候选 `0692078d` 的发现逐条收窄（R88–R90）：**再导出族按 `\s*` 收口，并在闭包出口阶梯末尾补默认拒绝**（R88）；**读取窗口按折叠后的字符计数**（R89）；**形状规则容忍嵌套泛型、无空白副作用导入放行、R86 行就地更正**（R90）。
矩阵 188 例 → **200 例（42 接受 ＋ 158 拒绝）**＝宿主／模块 **137（23 接受 ＋ 114 拒绝）** ＋ 页面 **21（7 接受 ＋ 14 拒绝）** ＋ **import 闭包 42（12 接受 ＋ 30 拒绝）**；`checks` 仍 **129**（本轮未新增静态 `require` 调用点）。据实登记：守卫 5167 → **5358 行**（按 §7 第 7 项钉死的 `SCAN_ROOTS` 口径仍为**全仓第 1 大代码文件、Python 源码亦第 1**），`split_plan_queue.md` 仍在 **P1**（**未上调任何锁**）；第十五轮实测**翻转面**：新矩阵 200 例与旧守卫逐例交叉求值 → **6** 例 OLD=ACCEPT → NEW=REJECT（三条无空白再导出、两条垫空白载荷、`export @sealed class` 装饰器导出）、**3** 例 OLD=REJECT → NEW=ACCEPT（嵌套泛型两条、无空白副作用导入一条）、其余 **191** 例判定**逐条不变**；夹具**新增 12 条、删除 0 条、无改名**（旧树 ＝ `git archive 0692078d`）。
**第十六轮**（A¹⁶ 与 B¹⁶ 均判 **REQUEST_CHANGES**：A¹⁶ 报 S1 **语句切分器的续句首词把下一条语句胶到上一条**——`type` 别名不在「`}` 即语句终点」的声明头清单里，而无条件的续句词表让 `type gN3 = { a: number }` ＋ 下一行 `from: { (Array.prototype as any).includes = () => true }`（语句标签）读成**一条**类型别名，标签块在加载期真跑（`node` 域不跑、浏览器域跑）⇒ 守卫 GREEN 而浏览器域规则真死，同族 `export type` ＋ `from:`／`type X = 1 | 2` ＋ 标签／`from(…)` 全部放行，且为**既有缺口**（`0692078d` 上同样 PASS）；另报 S3×3 据实性——§6 仍用第十五轮前的 `154` 口径、引用守卫里**不存在**的 `_closure_relative_specifiers`、称大写 `<SCRIPT` 起始标签被拒实测不被拒。B¹⁶ 报 S1 **400 字符读窗被长具名列表击穿**——`export { …60 名… } from './b16poison'` 把 `from` 顶出窗口后落进「本地具名导出」放行支、边也不被跟，真 `vite build` ＋ 真 Chromium 实测产物进包、`browserDomain.ruleAlive=false`、`eslint`／`vue-tsc` 均通过 ⇒ 可部署，S2 指出既有夹具未覆盖长文本这一成因面，S3 另登记四条既有过严面为 POST_MERGE_FOLLOWUP）对冻结候选 `9e5402c3` 的发现逐条收窄（R91–R94）：**续句词改为按语句头判定 ＋ 新增「后随冒号即标签」判定，并删除两张无条件续句表**（R91）；**读窗改用 `_statement_window()`（按语句真实终点结束、返回是否耗尽），耗尽即拒绝，上限 400 → 2000 折叠字符**（R92）；**三处据实性就地更正**（R93）；**四条既有过严面复测并登记为 POST_MERGE_FOLLOWUP**（R94）。
矩阵 200 例 → **210 例（45 接受 ＋ 165 拒绝）**＝宿主／模块 **143（24 接受 ＋ 119 拒绝）** ＋ 页面 **21（7 接受 ＋ 14 拒绝）** ＋ **import 闭包 46（14 接受 ＋ 32 拒绝）**；`checks` 仍 **129**（本轮未新增静态 `require` 调用点）。据实登记：守卫 5358 → **5643 行**（按 §7 第 7 项钉死的 `SCAN_ROOTS` 口径仍为**全仓第 1 大代码文件、Python 源码亦第 1**），`split_plan_queue.md` 仍在 **P1**（**未上调任何锁**）；第十六轮实测**翻转面**：新矩阵 210 例与旧守卫逐例交叉求值 → **7** 例 OLD=ACCEPT → NEW=REJECT（全部是**新增夹具名**：`type` 别名 ＋ `from:` 标签（权威体／闭包各一）、`export type` ＋ `from:` 标签、`type` 别名 ＋ `from(...)` 调用、`type` 别名 ＋ `extends:` 标签、两层各自的「具名导出列表长于读窗」）、**0** 例 OLD=REJECT → NEW=ACCEPT，其余 **203** 例判定**逐条不变**；夹具**新增 10 条、删除 0 条、无改名**（`/tmp/r16/diff_all.py`，旧树 ＝ `git archive 9e5402c3`）。**变异鉴别力**（逐条停用本轮机制、看矩阵点名）：停用权威体层「耗尽即拒绝」→ 点名 1 例、停用闭包层同规则 → 1 例、停用标签判定（`_statement_labels` 恒假）→ 1 例、`from` 恢复无条件续接 → 1 例、`extends` 从 `type` 头移除 → 1 例、读窗回退 400 → 1 例。**独立复算**：A¹⁶／B¹⁶ 原始载荷在影子树上 12 拒／旧树 12 例中 11 例为 PASS（第 12 例是旧树本就拒绝的 `from(...)` 裸调用，已在夹具内保留为对照），全部对照（干净树、干净目标的长列表、合法续接 `extends`／条件类型）两版一致 ACCEPT；另用真 `esbuild@0.21.5` 复算 A¹⁶ 载荷产物含 `Array.prototype.includes = () => true;`、B¹⁶ 载荷产物含目标模块的 `proto.includes = () => false;`，即两处缺口在旧树上**确为可部署的真死**。
**第十七轮**（A¹⁷ 与 B¹⁷ 均判 **REQUEST_CHANGES**：A¹⁷ 报 F1 **标签判定用的是定长十六字符看窗**——`re.match(r"\s*:", source[end:end+16])` 只看得见 16 个字符，垫 ≥16 个空白（空格／制表／不换行空格／零宽空格／字节序标记）或一条长注释就能把冒号顶出窗口 ⇒ 续句词路径放过 ⇒ `type` 别名与标签块胶成**一条**语句、标签块在加载期执行，**与第十六轮同根因**，B¹⁷ 独立复现为**可部署**（真 `esbuild@0.21.5 --bundle --platform=browser` 产物逐字含 `from: { Array.prototype.includes = () => true; }`）；F2 **语句吸收通道**——`_can_end_statement()` 对 `'`／`"`／`` ` ``／`>` 返回 False，且走查跑在**字符串已抹**的文本上 ⇒ `export type A = 'x'`／`= Record<string, number>` 的行尾不能结束语句 ⇒ 下一行被**无条件吸收**，标签判定与续句词表根本不参与（十个形状实测 ACCEPT）；F3 是**本轮新引入的假 REJECT**——`import\n  { read } from './peer'` 与 `export\n  { g }` 旧版 PASS、新版 REJECT，而真编译器接受（TypeScript 在 `import`／`export` 头与它的子句之间不设边界）；B¹⁷ 另报据实性 F4（§1 与 §5 仍写「内建自检 200」）与 F5（第十六轮段 ⑦ 的 20 行载荷清单未随仓交付））对冻结候选 `0137b95b` 的发现逐条收窄（R95–R99）：**标签判定改为「跳过任意长度空白后判冒号」并让被擦字面量保留结束证据**（R95）；**`_can_end_statement()` 接受 `>` 与三个闭引号，行首非姓名语句（正则／模板／数字／`{`）纳入报告**（R96）；**新增模块子句令牌 ＋ `_statement_awaits_module_clause()`，使 `import`／`export` 的续接跨行成立**（R97）；**文档据实刷新**（R98）；**本轮载荷矩阵随仓交付**（R99）。
矩阵 210 例 → **230 例（49 接受 ＋ 181 拒绝）**＝宿主／模块 **159（26 接受 ＋ 133 拒绝）** ＋ 页面 **21（7 接受 ＋ 14 拒绝）** ＋ **import 闭包 50（16 接受 ＋ 34 拒绝）**；`checks` 仍 **129**（本轮未新增静态 `require` 调用点）。据实登记：守卫 5643 → **6065 行**（按 §7 第 7 项钉死的 `SCAN_ROOTS` 口径仍为**全仓第 1 大代码文件、Python 源码亦第 1**），`split_plan_queue.md` 仍在 **P1**（**未上调任何锁**）；第十七轮实测**翻转面**：新矩阵 230 例与旧守卫逐例交叉求值 → 既有 **210** 例**逐条不变（0 翻转）**，新增 **20** 条（宿主／模块 16 ＋ import 闭包 4）中 **14** 例 OLD=ACCEPT → NEW=REJECT——五条 F1 垫空白／注释族（16 空格／16 制表／16 不换行空格／16 零宽空格／200 字符注释）＋ 六条 F2 吸收通道族（字面量别名 ＋ 裸表达式、类型实参别名 ＋ 裸表达式、类型实参别名 ＋ 块语句、字面量别名 ＋ 正则守卫，闭包层同族两条）＋ **三条本轮登记的过严面**（跨行数组类型／跨行索引访问／类型别名后接合法语句标签）；**3** 例 OLD=REJECT → NEW=ACCEPT 全为 F3 假 REJECT 修正（权威体的 `import\n{` 与 `export\n{`、闭包层的 `import\n{`）；**3** 例两版一致（15 空格对照、`;` 结尾别名对照、`import type\n{` 对照）；夹具**新增 20 条、删除 0 条、无改名**（`/tmp/p17/diff_all.py`，旧版由 `git show HEAD:…` 的守卫源码加载）。

**第十八轮**（A¹⁸ 与 B¹⁸ 均判 **REQUEST_CHANGES**：A¹⁸ 报 **S1×2**——**①组合记号逃避标识符判定**：`_statement_labels()` 只判「跳过空白后是否 `:`」，而标识符正则用 Python `\w`（**不含** Mn／Mc 组合记号），故 `extends\u0301:` 被读成「续句词 `extends` ＋ 非空白」⇒ 标签块胶进上一条 `export type` ⇒ 守卫 **GREEN**、浏览器域规则**真死**；**②`<` 被无条件当续句字符**：`_JS_STATEMENT_TAIL_CHARS` 含 `<` ⇒ 合法旧式类型断言 `<unknown>(expr)();` 的起句被胶掉、隐形；另报 **S3×2** 据实性〔§5 `:184` 仍写 `collaboration_self_check=200`；三条「过严面」的**机制描述错**——真 `tsc`／`esbuild` 实测把 `export type X = Foo<Bar>` 换行 `[];` 的第二行解析为**独立语句**（`[];` 真跑到产物），不是「被切开的数组类型」〕。B¹⁸ 报 **S1**——**正则语境启发式漏 `=>` 与控制头 `)`**：`/` 被当除法、其后 `'` 开启**幻影字符串**、整段置空 ⇒ 加载期语句隐形；真 Chromium 实测 `nodeDomain.ruleAlive=true / browserDomain.ruleAlive=false / prototypeIncludesIsStub=true`，同时 `eslint` 0 error、`vue-tsc` 32（无新增）、`vite build` exit 0 ⇒ **可部署**）对冻结候选 `f944b313` 的发现逐条收窄（R100–R104）：**标识符判定改用组合记号感知的 `_js_identifier_*()` 族，并在 `_statement_labels()` 加 fail-closed 兜底**（R100）；**`<` 移出无条件续句表，改由 `_statement_awaits_type_parameters()` 仅在「语句头仍只剩类型形参表」时续接**（R101）；**正则前置语境补 `throw`／控制头 `)`／`=>`，并新增 `crossed` 规则使跨原始换行才闭合的引号 span 拒绝切分**（R102）；**文档据实刷新**（R103）；**过严面定性就地更正**（R104）。
矩阵 230 例 → **243 例（56 接受 ＋ 187 拒绝）**＝宿主／模块 **169（32 接受 ＋ 137 拒绝）** ＋ 页面 **21（7 接受 ＋ 14 拒绝）** ＋ **import 闭包 53（17 接受 ＋ 36 拒绝）**；`checks` 仍 **129**（本轮未新增静态 `require` 调用点）。据实登记：守卫 6065 → **6531 行**（按 §7 第 7 项钉死的 `SCAN_ROOTS` 口径仍为**全仓第 1 大代码文件、Python 源码亦第 1**），`split_plan_queue.md` 仍在 **P1**（**未上调任何锁**）；第十八轮实测**翻转面**：既有 **230** 例**逐条不变（0 翻转）**，新增 **13** 条中 **9** 例翻转——**4** 例新增夹具 OLD=ACCEPT → NEW=REJECT（组合记号标签、角括号断言、断言数组字面量、完成类型后接类型实参）＋ **3** 例新增夹具 OLD=REJECT → NEW=ACCEPT（**第十九轮据实更正**：这 3 例是「箭头体正则／循环头正则／闭包『只有箭头体正则』」——旧版对它们**假 REJECT**；本条原写「三处类型形参续接」，而那三条在旧版即 ACCEPT，见 R108）＋ **2** 例新增闭包夹具 OLD=ACCEPT → NEW=REJECT（闭包层正则幻影串）；**4** 例新增**宿主**夹具两版一致 ACCEPT（function 头／interface 头／type-alias 头／除法对照，属「新增即通过」）——**第二十轮据实更正**：本条原写「**1** 例两版一致 ACCEPT（闭包「只有箭头体正则」）」，该闭包夹具实测为 **R→A** 且已计入上列 3 例（⑨ 表 P18-13 自己就标 `REJECT -> ACCEPT`），与自身互斥；逐条复算 13 条新增夹具 × `f944b313`（`/tmp/p20/r18fixtures.py`）＝ **6** A→R ＋ **3** R→A ＋ **4** A→A，见 R111；夹具**新增 13 条、删除 0 条、无改名**（`/tmp/p18/cross18.py`，旧版由 `git show HEAD:…` 的守卫源码加载）。
**第十九轮**（A¹⁹ 与 B¹⁹ 均判 **REQUEST_CHANGES**：A¹⁹ 报 **S1×3**——**①类型形参判定被「名字与关键字撞名」击穿**（`_statement_awaits_type_parameters()` 只取语句头**最后两个词**，`export type type = number`／`{ type: () => void }` 一族遂被读成「仍在等类型形参」，幻影行的加载期投毒语句隐形；真 `tsc 5.9.3`／`esbuild 0.21.5` 证明可部署）；**②9 个 Unicode `Pc` 连接符漏出标识符判定**（`extends‿:` 一族把标签胶进上一条 `export type`，与第十八轮 R100 同族复活）；**③正则前置字符表缺 `>`**（字符类里的 `'` 在**同一行**内开启幻影字符串，`crossed` 看不见，投毒语句被擦除，同族还能藏 `screen`／`window`）；另报 **S3×4 ＋ S4×1** 据实性（第十八轮 13 行载荷矩阵 OLD 列错、R100／R101／R102 夹具增量写成 2／5／4、3 例 R→A 指名错、⑲① 把不编译的写法称作合法跨行类型实参、§3 提交链仍是首批口径）。B¹⁹ 报 **S1**——与 A¹⁹-S1-1 **同根因**：`export type CollaborationKindName = { type: string }` 换行 `<unknown>Object.defineProperty(Array.prototype, 'includes', { value: () => false });` 追加进 `valueUtils.ts` 后守卫 PASS、真 `eslint` 0 error、`vue-tsc` 与基线逐字节相同、真 `vite build` exit 0，真 Chromium 实测 `ruleAlive=false`）对冻结候选 `e4435c77` 的发现逐条收窄（R105–R108）：**语句头形状判定取代「最后两个词」**（R105）；**标识符判定补齐 `Pc`／`Mn`／`Mc`／未分配字符**（R106）；**`<` 入正则前置表 ＋ `>` 歧义拒绝**（R107）；**文档据实更正 ＋ 本轮载荷矩阵随仓交付**（R108）。
矩阵 243 例 → **253 例（57 接受 ＋ 196 拒绝）**＝宿主／模块 **178（33 接受 ＋ 145 拒绝）** ＋ 页面 **21（7 接受 ＋ 14 拒绝）** ＋ **import 闭包 54（17 接受 ＋ 37 拒绝）**；`checks` 仍 **129**（本轮未新增静态 `require` 调用点）。据实登记：守卫 6531 → **6794 行**（按 §7 第 7 项钉死的 `SCAN_ROOTS` 口径仍为**全仓第 1 大代码文件、Python 源码亦第 1**），`split_plan_queue.md` 仍在 **P1**（**未上调任何锁**）；第十九轮实测**翻转面**：既有 **243** 例**逐条不变（0 翻转）**，新增 **10** 条中 **9** 例翻转——**8** 例新增宿主夹具 ＋ **1** 例新增闭包夹具 OLD=ACCEPT → NEW=REJECT（**R105 两拒 ＋ R106 两拒 ＋ R107 三拒 ＋ 生成器头一拒 ＋ 闭包一拒**——**第二十轮据实更正**：本条原写「R105 三条 ＋ R106 两条 ＋ R107 三条 ＋ 闭包一条」，多算一条，见 R112），**0** 例 OLD=REJECT → NEW=ACCEPT，**1** 例两版一致 ACCEPT（`Math.round(value) / factor` 除法对照，属「新增即通过」）；夹具**新增 10 条、删除 0 条、无改名**（`/tmp/p19r/fixtureflips.py`，旧版由 `git show HEAD:…` 的守卫源码加载）。
**本轮载荷矩阵（随仓交付，12 行）**——记法同第十八轮：层面 `A` ＝ 权威体／模块、`C` ＝ import 闭包；`OLD` ＝ `e4435c77`，`NEW` ＝ 本轮工作树守卫。

```text
ID      族  载荷                                                                   层  OLD -> NEW
P19-01  S1-1  export type type = number⏎<unknown>(() => { …includes = () => false; })();      A  ACCEPT -> REJECT
P19-02  S1-1  export type abstract = number⏎<unknown>(…)();                                   A  ACCEPT -> REJECT
P19-03  S1-1  export type gA = { type: () => void }⏎<unknown>(…)();                           A  ACCEPT -> REJECT
P19-04  S1-2  export type gPC = (x: number) => void⏎extends+U+203F: { …includes = …; }         A  ACCEPT -> REJECT
P19-05  S1-2  export type gPC2 = (x: number) => void⏎extends+U+30FB: { …includes = …; }        A  ACCEPT -> REJECT
P19-06  S1-3  export function padEq(n) { return (n as any) > /[']/.test(String(n)); } ; … // ' A  ACCEPT -> REJECT
P19-07  S1-3  同上 ＋ /[']/.test(String(screen)) ＋ typeof window !== 'undefined'（藏环境）     A  ACCEPT -> REJECT
P19-08  S1-3  export function padLt(n) { return (n as any) < /[']/.test(String(n)); } ; … // ' A  ACCEPT -> REJECT
P19-09  S1-1  别名体属性撞关键字（闭包成员 pages/valueUtils.ts，B¹⁹ 载荷）                        C  ACCEPT -> REJECT
P19-10  S1-3  单行正则幻影串（闭包成员 pages/valueUtils.ts）                                     C  ACCEPT -> REJECT
P19-11  对照  export function halfRounded(value, factor) { return Math.round(value) / factor; } A  ACCEPT -> ACCEPT
P19-12  对照  export function rc(text) { return text.length > 0 && /[']/.test(text); }         A  ACCEPT -> ACCEPT
```

  复算方式：`/tmp/p19r/payloadmatrix19.py`（12 行逐条在两版守卫上求值）、`/tmp/p19r/fixtureflips.py`（**253** 例 × `e4435c77` 交叉求值）、`/tmp/p19r/cross18truth.py`（`f944b313` × `e4435c77` 复算第十八轮 13 行矩阵）、`/tmp/p19/tree3/`（整树影子 ＝ `git archive e4435c77` ＋ 新版守卫，逐载荷注入后跑真守卫）、`/tmp/p19r/lt/`（真 `tsc 5.9.3`／`esbuild 0.21.5`：五种类型形参拼写续接、`export type A = Record` 换行 `<string, number>;` 报 TS1005／TS1109、`export function* gen` 换行 `<T>()` 两工具 rc=0）、`/tmp/p19/probe2.py`（19 条 REJECT ＋ 12 条 ACCEPT 复测；其中五条 `class`／`const = function`／`declare function`／`export default function`／`abstract class` 由**模块纯净性**规则另行拒绝，经旧守卫复测同为 rc=1，**非本轮回归**）。**端到端实测**（`/tmp/p18/e2e.sh`／`e2e_a.sh`，影子树 ＝ `git archive f944b313` ＋ 追加载荷）：**旧守卫 rc=0 PASS / 新守卫 rc=1 FAIL**，B¹⁸-S1 两拼写与 A¹⁸-S1-1／S1-2 四类载荷全部由**隐形**变**点名**。**真工具链交叉验证**（`/tmp/p18/lt`）：`tsc 5.9.3`／`esbuild 0.21.5` 实测五种类型形参拼写**均续接**（`export function read`⏎`<T>(…)`／`export class Box`⏎`<T> {…}`／`export interface I`⏎`<T>`／`export type A`⏎`<T> = T`／`const f = function`⏎`<T>(x)`，应 ACCEPT），而 `export type A = B`⏎`<C>[];` 与 `export type A = Record`⏎`  <string, number>;` 的第二行是**独立语句**（应 REJECT）。**全仓幻影扫描**（`/tmp/p18/cross18.py` 第 (c) 段）：1156 个文件、8 个 `.vue` 命中跨行字符串 span，**全部是 SFC 模板属性**（`v-else-if="… ⏎ …"` 一类），**无 `.ts` 命中**；四份真实闭包文件 `unsegmentable=0`。
**第二十轮**（A²⁰ 判 **REQUEST_CHANGES**：**S2×2**——①**R107 的 `>` 歧义拒绝把合法比较一并拒掉**（`(a as any) > /x/.test(b)`，真 `tsc 5.9.3`／`esbuild 0.21.5` 均 rc=0，权威体层与闭包层**同时** REJECT，且该过严面**本轮未登记**）；②**R105 的形状判定仍读不出生成器头与非 ASCII 名字头**（`export async function* gen`⏎`<T>…`／局部 `function* gen`⏎`<T>…`／`export function 名`⏎`<T>…` 三类拼写**未登记**，只登记了 `export function* gen` 一类）；另报 **S3×2 ＋ S4×1** 据实性（第十八轮段 ⑦ 把夹具层聚合数写成载荷矩阵聚合数、同段与 §8 第十八轮段末句的「**1** 例两版一致 ACCEPT（闭包）」与 ⑨ 表 P18-13 自相矛盾、第十九轮段归因括号多算一条）。A²⁰ 同时**撤回**自己先前提出的 S2-1 修法：字符级 `<`／`>` 配对会被模块里**其它**内容左右（`a < b` 是比较、`=>` 是单箭头、`Record<a,b>` 是配平的），同一条载荷在不同模块文本下时而拒绝、时而放行，比「一律拒绝」更糟）。同轮独立复核 **B²⁰**（真工具链／对抗线）对同一冻结候选亦判 **REQUEST_CHANGES**：三条未登记假 REJECT 分别命中本条 R110（`>` 后接 `/` 的歧义拒绝误伤合法比较，权威体层＋闭包层同时）与 R109（`export async function* gen`⏎`<T>`／`export function 名`⏎`<T>`），**未找到任何 S0／S1 绕过**（真 Chromium 探针 PRISTINE `ruleAlive=True`／POISON `ruleAlive=False, stub=True`）；另两条观察按其实测登记，见本轮段末「据实登记的边界与既存拒绝」）。对冻结候选 `309cec59` 的发现逐条收窄（R109–R112）：**生成器记号跳过 ＋ 非 ASCII 名字读作 head 的一个名字**（R109）；**`>` 歧义拒绝保留并登记为过严面**（R110）；**第十八轮两处据实更正**（R111）；**第十九轮归因括号更正**（R112）。
矩阵 253 例 → **260 例（63 接受 ＋ 197 拒绝）**＝宿主／模块 **182（37 接受 ＋ 145 拒绝）** ＋ 页面 **21（7 接受 ＋ 14 拒绝）** ＋ **import 闭包 57（19 接受 ＋ 38 拒绝）**；`checks` 仍 **129**（本轮未新增静态 `require` 调用点）。据实登记：守卫 6794 → **6969 行**（按 §7 第 7 项钉死的 `SCAN_ROOTS` 口径仍为**全仓第 1 大代码文件、Python 源码亦第 1**），`split_plan_queue.md` 仍在 **P1**（**未上调任何锁**）；第二十轮实测**翻转面**（`/tmp/p20/fixtureflips.py`，旧版由 `git show <sha>:…` 的守卫源码加载）：新 **260** 例 × `309cec59` → **6** 例 R→ACCEPT（4 宿主 ＋ 2 闭包，**全部**是本轮修回的生成器／非 ASCII 名字拼写）、**0** 例 A→R；新 **260** 例 × `e4435c77` → **10** 例 A→R（8 宿主 ＋ 2 闭包：第十八／十九轮仍在承重的 8 条加固 ＋ 本轮新增的 2 条过严面登记）、**0** 例 R→A；夹具**新增 8 个名字（4 宿主 ＋ 3 闭包 ＋ 1 条宿主改名）、删除 0 条**，净增 **7** 条（原 `(registered over-strictness)` 的生成器头**转为接受**）。**变异鉴别**（逐条停用机制、看自检点名 ＋ 载荷翻转，`/tmp/p20/mutate.py`）：停用「跳过生成器记号」→ 自检点名 **4** 条生成器夹具；停用非 ASCII 名字判定 → 点名 **2** 条；停用 `>` 歧义拒绝 → 点名 **1** 条过严面夹具 ＋ **2** 条既有 `>` 载荷夹具，且投毒载荷 P20-02 由 REJECT 翻 **ACCEPT**（即该规则**承重**，收窄它会重开 R107 通道）。**真实树**（宿主／权威体 VM／页面／四个已复核闭包文件）两版均 **0 failures**；权威体 VM 与四个闭包文件中 `>`＋可选空白＋`/` 的出现次数为 **0**（`/tmp/p20/` 正则扫描），故本轮的登记过严面**不触及任何被复核模块**。
**本轮载荷矩阵（随仓交付，17 行）**——记法同前：层面 `A` ＝ 权威体／模块、`C` ＝ import 闭包；`OLD` ＝ `e4435c77`、`R19` ＝ `309cec59`、`NEW` ＝ 本轮工作树。

```text
ID      层  载荷（简写）                                                       OLD      R19      NEW
P20-01  A  (a as any) > /x/.test(b)  合法比较，tsc/esbuild rc=0               ACCEPT   REJECT   REJECT   ← 本轮登记过严面
P20-02  A  (n as any) > /[']/.test(…) ; (Array.prototype as any).includes=… ; // '   ACCEPT   REJECT   REJECT   ← R107 投毒载荷
P20-03  A  (a as any) > /[']/.test(b)  字符类含引号，tsc/esbuild rc=0         REJECT   REJECT   REJECT
P20-04  A  values.length / scale  类型实参收尾后的除法                     ACCEPT   ACCEPT   ACCEPT
P20-05  A  Math.round(v) / factor  除法对照                                ACCEPT   ACCEPT   ACCEPT
P20-06  A  a > b  纯比较对照                                              ACCEPT   ACCEPT   ACCEPT
P20-07  A  export function* gen⏎<T>(): Iterable<T> {}                       ACCEPT   REJECT   ACCEPT
P20-08  A  export async function* stream⏎<T>(values: readonly T[]): AsyncGenerator<T> {…}   ACCEPT   REJECT   ACCEPT
P20-09  A  function* walk⏎<T>(values: readonly T[]): Generator<T> {…}         ACCEPT   REJECT   ACCEPT
P20-10  A  export function 名⏎<T>(value: T): T { return value; }              ACCEPT   REJECT   ACCEPT
P20-11  A  export type CollaborationKindName = { type: string }⏎<unknown>Object.defineProperty(…)   ACCEPT   REJECT   REJECT   ← R105 撞名载荷
P20-12  A  a < b > /x/.test('y')  交叉角括号，两工具均不编译                 ACCEPT   REJECT   REJECT
P20-13  C  (a as any) > /x/.test(b)  闭包成员 pages/valueUtils.ts             ACCEPT   REJECT   REJECT   ← 登记过严面（闭包层）
P20-14  C  export function* walk⏎<T>(…)                                      ACCEPT   REJECT   ACCEPT
P20-15  C  export function 名⏎<T>(value: T): T { return value; }              ACCEPT   REJECT   ACCEPT
P20-16  C  values.length / scale                                          ACCEPT   ACCEPT   ACCEPT
P20-17  C  Math.round(v) / factor                                         ACCEPT   ACCEPT   ACCEPT
```

  复算方式：`/tmp/p20/spec.json` ＋ `/tmp/p20/mprobe.py`（17 行逐条在**三版**守卫上求值）、`/tmp/p20/fixtureflips.py`（**260** 例 × `e4435c77` 与 × `309cec59` 两次交叉求值）、`/tmp/p20/r18fixtures.py`（第十八轮 13 条新增夹具 × `f944b313` 复算，得 6／3／4）、`/tmp/p20/mutate.py`（三项变异鉴别：跳过生成器记号／非 ASCII 名字判定／`>` 歧义拒绝）、`/tmp/p20/lt/`（真 `tsc 5.9.3`／`esbuild 0.21.5`：P20-01／03／04／07／08／09／10／11／13／16 逐个 rc=0，P20-12 两工具均报错）。
  **据实登记的边界与既存拒绝**（第二十轮按独立复核 A²⁰／B²⁰ 的两条观察逐条实测后登记）：①**两个抽取路径的严格度不对称**——语句切分与 `>`／`<` 歧义拒绝只作用于**权威体模块正文**（`_js_unsegmentable_spans()` 的 `:2354` 调用点；第二十轮记为 `:2348`，第二十一轮的空白读法修法使其下移 6 行）与**被复核的 import 闭包成员文件**（同函数 `:2771` 调用点，`read_module()`；第二十轮记为 `:2765`），宿主的 `.vue` 文本只走声明／消费检查；故同一条载荷 `count > /x/.source.length` 注入 `ContractFormDriverHost.vue` 的 `<script setup>` 段**两版均 ACCEPT**、注入 `contractRuntimeVm.ts` 即 **REJECT**（本轮实测）。该不对称**系设计使然**（被复核的权威体才是模块），但按 B²⁰ 建议显式记入边界，不再只留在口头。②**两条既存拒绝不是本轮回归**——`export const f = function*<T>() {…}` 与 `export default function<T>() {…}` 在 OLD（`e4435c77`）与 NEW **两版均 REJECT**（分别命中「模块级值在加载期求值且被权威体链接」与「被复核闭包成员不得默认导出」两条既存 fail-closed 规则）；B²⁰ 亦据真 `tsc 5.9.3`／`esbuild 0.21.5` 复核并明示其「非本轮回归，可只在文档据实登记」，本轮据此**只登记、不改写**。
**第二十一轮**（A²¹ 判 **REQUEST_CHANGES**：**S1×1 ＋ S4×2**——①**S1 等价绕过**：`>` 后接 `/` 的歧义拒绝（R107 规则／第二十轮 R110 的登记面）可被**一个 `U+FEFF`**（以及 `U+200B`／`U+200C`／`U+200D`／`U+2060`）绕过：`_js_opaque_spans()` 的空白判定用本解释器的 `str.isspace()`（对 `U+FEFF` 为 False），而 TypeScript 词法把 `U+FEFF` 读作空白 ⇒ `previous` 被该字符顶掉、`ambiguous` span 不产生 ⇒ `/` 被读成除号、紧随的 `'` 开启一个**同行闭合**的幻影字符串 ⇒ 整段投毒语句被擦除、守卫 **GREEN**；同载荷真 `esbuild 0.21.5 --bundle` ＋ `node` 实测加载期投毒生效（`[1,2].includes(1)` 由 `true` 变 `false`），**权威体层与闭包层同时**；②**S4-1**：R112 行括号措辞不准；③**S4-2**：`_js_head_declared_tail()` 的「删掉所有 `*` 后恰剩一个名字」比「合法生成器头」宽，五形两层均 ACCEPT 而两工具全 rc≠0（不可编译 ⇒ 无加载期执行面）。B²¹（真工具链／对抗线）对同一冻结候选判 **APPROVE**：B²⁰ 的三条发现逐条收口（FR-1 保留登记、FR-2／FR-3 修回），11 条骑乘新接受面的投毒载荷**全 REJECT**，全仓 `src/`＋`addons/` 的 `ambiguous` span 计数为 **0**。主控线对冻结候选 `77d23382` 的发现逐条收窄（R113–R115）：**空白的读法与 TS 词法对齐**（R113）；**R112 措辞按实测改写**（R114）；**五形「宽头部」据实登记 ＋ 否证「收紧即关闭」**（R115）。

矩阵 260 例 → **262 例（63 接受 ＋ 199 拒绝）**＝宿主／模块 **183（37 接受 ＋ 146 拒绝）** ＋ 页面 **21（7 接受 ＋ 14 拒绝）** ＋ **import 闭包 58（19 接受 ＋ 39 拒绝）**；`checks` 仍 **129**（本轮未新增静态 `require` 调用点）。据实登记：守卫 6969 → **7007 行**（按 §7 第 7 项钉死的 `SCAN_ROOTS` 口径仍为**全仓第 1 大代码文件、Python 源码亦第 1**），`split_plan_queue.md` 仍在 **P1**（**未上调任何锁**）。

**本轮载荷矩阵（12 行）**——记法同前：层面 `A` ＝ 权威体／模块、`C` ＝ import 闭包；`R20` ＝ 上一冻结候选 `77d23382`、`NEW` ＝ 本轮工作树；载荷统一为「`>` ＋ 垫字 ＋ `/[']/.test(…)` ＋ 同行投毒 ＋ 行尾注释」的最小形态。

```text
ID      层  垫字（`>` 与 `/` 之间）      R20      NEW
P21-01  A  U+FEFF                      ACCEPT   REJECT   ← S1 绕过，本轮闭合
P21-02  A  U+200B 零宽空格             ACCEPT   REJECT
P21-03  A  U+200C 零宽不连字           ACCEPT   REJECT
P21-04  A  U+200D 零宽连字             ACCEPT   REJECT
P21-05  A  U+2060 词连接符             ACCEPT   REJECT
P21-06  A  无垫字（对照）               REJECT   REJECT
P21-07  C  U+FEFF                      ACCEPT   REJECT   ← 闭包层同族
P21-08  C  U+200B                      ACCEPT   REJECT
P21-09  C  U+200C                      ACCEPT   REJECT
P21-10  C  U+200D                      ACCEPT   REJECT
P21-11  C  U+2060                      ACCEPT   REJECT
P21-12  C  无垫字（对照）               REJECT   REJECT
```

  复算方式：`/tmp/p20b/m21.py`（12 行逐条在**两版**守卫上求值）、`/tmp/p20b/flips21.py`（**262** 例 × `e4435c77`／`309cec59`／`77d23382` 三次交叉求值：对上一候选**恰 2 例翻转**＝两条新增夹具，对第十九轮候选 8 例，对第十八轮基线 12 例）、`/tmp/p20b/s1check.py`（S1 闭合前后对照：四种垫字两层均 `ACCEPT → REJECT`）、`/tmp/p20b/battery.py`（合法拼法 `export function* gen`／`export async function* gen`／局部 `function* gen`／非 ASCII 名**仍 ACCEPT**；五形「宽头部」**不变**）、真 `esbuild 0.21.5` ＋ `node`（投毒真加载：`native includes(1) = false`）。
  **并入四种非 ES 空白字符的代价面**：`U+200B`／`U+200C`／`U+200D`／`U+2060` 本身不是 ES 空白（真工具链对其报 `TS1127`／`esbuild Unexpected`），本轮把它们一并读作空白是**取更严的一侧**；实测既有 **260** 例夹具 **0 翻转**、真实树仍 PASS，即该并入**只收紧、不放宽**。
  **S4-2 的否证记录**（供后续轮次定向）：把 `_js_head_declared_tail()` 收紧为「只跳过紧邻关键字的一个 `*`」在影子树实测对五形**逐一无影响**（仍 ACCEPT），故五形由**另一条路径**放行，不是该 helper 的宽度问题；本轮据此**只登记、不改规则**。

**独立复算**（`/tmp/p17/`，真守卫逐载荷注入 ＋ 两版对照）：F1 载荷族（15／16／100 空格、16 制表、16 不换行空格、16 零宽空格、16 字节序标记、16／200 注释）在**权威体层与闭包层同时**由 OLD=ACCEPT 变 NEW=REJECT，15 空格对照两版一致 REJECT；F3 的 `import\n{…}`／`export\n{…}` 由 OLD=REJECT 变 NEW=ACCEPT，`import\n* as`／`import type\n{` 两版一致 ACCEPT；X／L 族 13 例 ACCEPT → REJECT、0 例 REJECT → ACCEPT，`export function f<T extends\n…` 两版一致 REJECT（**既有缺口，本轮未修**，已登记）；**真实树**（宿主／权威体 VM／页面／四个已复核闭包文件）两版均 **0 failures**（修复不误报）。
R22–R27（第四轮复核后的收口）把「接线」本身从**令牌级**抬到**语义级**：委派从「含令牌」改为
**整表达式等值**（＋ 宿主不得自行声明该权威、必须导入），插槽从「存在 `v-if`」改为**绑定到承载标志的元素区间**，
证明从「路径出现在 Makefile 里」改为**配方块真的 `esbuild` ＋ `node` 执行**，并加 **sha256 内容绑定**使证明不可
静默改写；读模板时**丢弃 `<script setup>` 段**，关闭 JS 注释／字符串诱饵。自检矩阵 26 例 → **36 例
（4 接受 ＋ 32 拒绝）**，证明真值表 46 例 → **51 例**（全部 `strictEqual`），`checks` 运行时统计当时 **126**
（第五轮后矩阵 54 例、第六轮后 **77 例**、`checks=127` 不变，见下）。
**二十一次复核**后（**第二十一轮据实更正**：本轮按 R113–R115 一并刷新为「二十一次」） §1–§7 的**当前时口径**（行数、守卫口径、接受／拒绝面、提交链与归属说明）均已按修订同步更正——**范围限于 §1–§7**：§8 自身按轮次保留各轮当时数字，不随之改写（**第十九轮据实更正**：本条原写「§1–§7 的行数…均已按修订同步更正」，未限定口径，与 §8 保留历史数字的事实不符，见 R108）（**第十三轮据实更正**：本行计数在第十二轮收口时未同步，当时仍写「十一次」，见 R80 同族；**第十六轮据实更正**：本行计数在第十三～十五轮未再同步，本轮按 R93 一并刷新为「十六次」；**第十七轮据实更正**：本轮按 R98 一并刷新为「十七次」；**第十八轮据实更正**：本轮按 R103 一并刷新为「十八次」；**第十九轮据实更正**：本轮按 R108 一并刷新为「十九次」；**第二十轮据实更正**：本轮按 R111／R112 一并刷新为「二十次」，并把第十八轮那句聚合数与 §8 第十八轮段末句的闭包对照项一并更正）。本轮（整批）的四个
功能级改动为：`contractRuntimeVm.ts`（+4 权威）、`contract_form_collaboration_authority_test.ts`（新增）、
`frontend_scene_component_bridge_guard.py`（第七轮由八项扩到**十项**接线断言〔新增⑨模块纯净性／⑩偏移保长自证〕，第八轮把⑨补全为
**导出加载期声明 ＋ import 清单 ＋ 引号不透明** ＋ 内容绑定 ＋ 两张自检矩阵〔第八轮 **111 例**〕；第九轮再把⑨补成
**正则／字符串／模板／注释统一不透明 ＋ 未闭合即拒 ＋ import specifier 取 `from` 子句**，并新增**计算插槽名**与
**面板 `v-if` 等值**两条判据〔第九轮 **120 例**〕；第十轮再把⑨补成**语句切分三类空洞 ＋ 已复核 import 的**真实内容**读取（运行时闭包 4 文件）**，并把载体／祖先／面板的死门判定改为**登记式等值清单**〔第十轮 **142 例**〕；第十一轮再收口**续句表只留中缀运算符 ＋ U+2028/2029 当换行 ＋ 模板 span 保留起始反引号 ＋ 闭包「本层只能是声明」与 re-export／动态 import 边 ＋ 深度触顶报 failure ＋ `v-for` 纳入死门清单 ＋ `</SCRIPT>`／HTML 注释两处假 REJECT**〔第十一轮 **154 例**〕；第十二～十四轮再把⑨补成**闭包层字符串感知屏蔽 ＋ `type`／`interface` 形状规则 ＋ 闭包出口由声明白名单改为形状规则 ＋ 打不开的再导出与 import 同规拒绝**〔第十二轮 **174 例**、第十三轮 **180 例**、第十四轮 **188 例**〕；第十五轮把再导出族按 `\s*` 收口、读窗按**折叠后字符**计数、形状正则容忍嵌套泛型〔第十五轮 **200 例**〕；第十六轮把续句词改为**按语句头判定**＋新增「后随冒号即标签」判定＋读窗改为**按语句真实终点结束、耗尽即拒绝**〔第十六轮 **210 例**〕；第十七轮把**标签判定改为「跳过任意长度空白后判冒号」＋ 被擦字面量保留结束证据 ＋ `>` 与闭引号可结束语句 ＋ 行首非姓名语句与块语句纳入报告 ＋ 模块子句令牌跨行续接**〔第十七轮 **230 例**〕；第十八轮把**标识符判定改为组合记号感知 ＋ `<` 只在「语句头仍只剩类型形参表」时续接 ＋ 正则前置语境补 `throw`／控制头 `)`／`=>` ＋ 引号 span 的 `crossed` fail-closed**〔第十八轮 **243 例**〕；第十九轮把**语句头形状判定取代「最后两个词」＋ 标识符判定补齐 `Pc`／`Mn`／`Mc`／未分配字符 ＋ `<` 入正则前置表 ＋ `>` 歧义拒绝**〔第十九轮 **253 例**〕；第二十轮把**生成器记号跳过 ＋ 非 ASCII 名字头读作一个名字 ＋ `>` 歧义拒绝登记为过严面**〔第二十轮 **260 例**〕；第二十一轮把**空白的读法与 TS 词法对齐（`U+FEFF` 一族）**〔第二十一轮 **262 例**〕）与 `make/frontend.mk`
（证明接线）；四个生成物按注册目标重刷。
**未决**：本批发布仍受外部封禁阻塞，需用户先解除封禁并显式授权；协作区的**运行态**行为（浏览器里到底出不出）
仍无任何门禁覆盖，已登记为未覆盖边界（第四轮按实测更正：A³-V9 不构成运行态旁路；第六轮的「两域复跑」收窄了
门控面但仍跑纯函数，**不构成**运行态覆盖；第七轮起三个权威体的**加载期**门控由第二层⑨覆盖，**运行态**仍无覆盖）。
