# 共享表单结构与阅读层次收口（2026-09-10）

## 1. 本轮变更

- 目标：在不推导业务语义、不改变契约和权限的前提下，用共享表单渲染能力统一查看态与录入态的信息结构。
- Formal Product Layer：P0 平台通用前端渲染；P4 仅承载只读验证和证据。
- Layer Target：`frontend/apps/web` 的共享 contract form renderer、native form bridge、关系明细和协作附件表达。
- Standard vs User-Specific：平台机制；不属于施工行业默认、客户偏好、低代码运行时配置或一次性修复。
- Why Here：章节角色、响应式字段网格、吸顶页头、明细桌面/移动投影和附件载体说明由共享渲染器统一负责。
- Why Not Elsewhere：未向 `smart_core` 或施工模块写入业务重要性、字段名特判、金额口径或客户偏好；未修改 backend contract、模型或数据。
- Blast Radius：contract-driven task forms、native workspace forms、readonly/editable x2many 明细、sticky form header、记录附件与协作附件的展示名称。
- 完成：
  - 页头保留身份、状态和操作；正文按既有 semantic role 形成概览、基本资料、关系明细、辅助信息和协作记录导航。
  - **原后端章节标题继续隐藏**。`CanonicalFormNodeRenderer` 的原章节标题及 group heading 没有恢复；新增标题只来自契约已有 semantic role，不按模型名或字段名猜测。
  - 付款详情将金额类型字段提升为视觉重点，并压缩当前任务正文；未更改金额字段、值或动作。
  - 材料入库新建将关系明细前置，辅助信息保持轻量折叠；1440/1088 桌面首屏均可见明细标题与添加入口。
  - 收入合同 readonly 明细在桌面使用共享 `ScTable` 横向比较，在移动端使用有标题的记录卡；新建和详情均获得可定位章节。
  - sticky 页头改用不透明公共主题表面、独立层叠上下文和阴影，正文滚动不再穿透标题区。
  - 单据字段中的 `ir.attachment` 与协作日志附件是两个不同载体，均予保留，分别命名为“单据附件”和“协作附件”。
  - P4 浏览器脚本增加 top/middle/bottom 滚动证据，并将实际滚动所有者绑定为 `.router-host`。
- 未完成：收入合同“未收款金额”和“未收款”的口径差异仅登记；本轮未改值、未合并口径、未补契约。键盘与查询优化仍为独立后续主题。

## 2. 影响范围

- 模块：`frontend/apps/web`、`scripts/verify`、前端生成清单、`.agent` 与本迭代记录。
- 启动链：否。
- contract/schema：否。
- default route：否。
- public intent：否。
- Odoo module/database：否；未升级模块、未 reset fixture、未保存业务数据。
- 代表样本：付款申请详情、材料入库新建、收入合同详情、收入合同新建。

## 3. 风险

- P0：无已知阻断。公开组件对齐清单为 0 个内部 vendor selector gap、0 个未知 token、0 个视觉字面量 gap、0 个孤立 appearance variant。
- P1：semantic role 缺失的历史表单不会获得同等章节标题；本轮选择保持契约边界，不通过字段名或模型名补猜测。
- P2：桌面 readonly 明细列数较多时仍依赖表格横向承载；移动端使用记录卡避免压缩为不可读窄列。
- 缓解：所有结构变化集中在共享渲染器，可按提交回退；契约、权限和数据库无需同步回滚。

## 4. 验证

- `make verify.frontend.quick.gate`：PASS。包含 strict typecheck、Vite build、组件公开适配、页面模式、关系明细、协作区、主题和生成清单门禁；所有目标测试均为非零执行。
- 定向门禁：form canvas wide-grid、professional detail collection、page pattern parity、professional collaboration、primitive adapter、product page pattern 均 PASS。
- `python3 -m unittest scripts.verify.test_local_dev_candidate_frontend`：PASS，9 tests。
- exact-head 浏览器矩阵：
  - `f1943462e6640224c4bac867edf0b5e167495be3`，light，1440×960 / 390×844：PASS。
  - 同一 HEAD，light，1088×960 / 320×844：PASS。
  - 两轮均覆盖四个样本的首屏、中段和底部，`mutationCount=0`、`errors=[]`、`failures=[]`。
  - 四个宽度下 sticky header 均为不透明表面；材料桌面首屏关系明细和添加入口均为 true。
  - exact-head 收入合同详情底部截图确认桌面为 2 行同列表格；390/320 摘要确认移动端使用 titled cards。
- 人工复核：桌面收入合同明细可横向比较；材料首屏可直接进入明细；两个附件入口的归属说明同时可见；未发现页头覆盖正文或主要操作。
- 非门禁说明：全工作区非 strict `npm run typecheck` 仍包含本轮之前已存在的 HierarchicalWorksheet、BlockRichTextOverview 等错误；本轮改动文件无新增错误，受管 strict typecheck 已通过。

## 5. 产物

- baseline 产品：`3c3c7bdef2dac3dfdfa06488c7e731ce1e565ce9`。
- baseline 指纹：`artifacts/fingerprints/form_structure_a_baseline_3c3c7bde.json`，SHA-256 `7e851d79b087fe43e4d5306608ed4fd4ef6ef373cd8970d4668d8c2aa7529f50`，7350 paths。
- before 浏览器证据：`artifacts/playwright/form-structure-before-final-59bcba6f/summary.json`。其中产品树仍为 baseline，`59bcba6f` 只包含生成 before 证据所需的 P4 验证工具；baseline sticky background 为透明。
- final 浏览器证据：
  - `artifacts/playwright/form-structure-final-exact-f1943462-1440-390/summary.json`
  - `artifacts/playwright/form-structure-final-exact-f1943462-1088-320/summary.json`
- 关键截图：
  - `artifacts/playwright/form-structure-final-exact-f1943462-1440-390/desktop-material-create-after.png`
  - `artifacts/playwright/form-structure-final-exact-f1943462-1440-390/desktop-income-contract-detail-after-bottom.png`
- 生成清单：
  - `docs/frontend_productization/rendering-detail/component-professionalization-inventory-v1.json`
  - `docs/frontend_productization/rendering-detail/visual-projection-inventory-v1.json`
  - `docs/frontend_productization/rendering-detail/official-design-alignment-inventory-v1.json`
- contract snapshot：N/A，本轮没有 contract/schema 变化。

## 6. 回滚

- 基线：`3c3c7bdef2dac3dfdfa06488c7e731ce1e565ce9`。
- 产品提交从 `52815581` 到 `383aaaa2`；P4 验证与文档提交保持独立。
- 方法：在受管修复分支按提交逆序回退共享 renderer/style 变更，再运行 `make verify.frontend.quick.gate` 和只读 exact-head 浏览器矩阵。
- 不需要数据库、fixture、contract snapshot 或模块升级回滚。

## 7. 下一批次

- 已按产品复核继续执行“表单视觉层级与首屏效率收口”，结果与证据见 `frontend_form_visual_hierarchy_first_view_closure_20260910.md`。
- 键盘与查询体验优化继续后置；先由产品复核本次表单表达结果，再决定是否退出表单主题，不自动切换专题。
- 后续若恢复键盘与查询专题，须另行明确影响页面与非写入验收样本；不得沿用本批金额口径问题作为前端推导依据。
- 当前不启动：旧版本升级兼容、acceptance 重建、多角色、真实写入、发布与收入合同金额口径仍分别管理。

## 结论

共享表单结构与阅读层次批次已在本地受管范围验证完成。结论只覆盖 P0 共享渲染实现和四个代表表单的只读/无保存浏览器证据，不等同于全业务、多角色、真实写入、升级兼容或发布验收完成。
