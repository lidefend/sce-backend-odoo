# 表单视觉层级与首屏效率收口（2026-09-10）

## 1. 本轮变更

- 目标：在既有表单结构成果上，收口容器层级、长表单密度、移动概览顺序与章节导航；等待产品复核后再决定是否退出表单主题。
- Formal Product Layer：P0 平台通用前端渲染；P4 仅承载守卫、清单和只读浏览器证据。
- Layer Target：`frontend/apps/web` 共享表单 renderer、`FormSection`、`ScButton` 适配层及章节导航。
- Standard vs User-Specific：平台机制，不是施工行业规则、客户偏好、低代码配置或一次性数据修复。
- Why Here：容器层级、类型语义的视觉排序、字段节奏、语义锚点与当前章节状态均由共享 renderer 负责。
- Why Not Elsewhere：没有修改 contract/schema、模型、权限、动作或金额口径；没有按模型名或字段名推断重要性；没有把客户偏好写入 P0/P1。
- Blast Radius：contract-driven task form 与 native workspace form 的章节外壳、字段网格、关系明细边界、移动摘要和章节定位。

完成内容：

- 新增共享 `FormSectionNavigation`，任务表单和工作区表单共用同一实现；横向溢出时显示“滑动”提示，当前项通过 `aria-current="location"` 暴露，并逐项定位到契约已有 semantic role。
- `FormSection` 继续消费字段类型、span 和 semantic role；native 表单不再把普通孤立字段强制撑满整行，长文本仍按已有类型/span 跨列。
- 材料新建移除“关系明细”外层通用卡框，只保留具体“入库明细”自身所需边界和标题；基本信息后直接进入明细，附件归属仍分别显示为“单据附件”和“协作附件”。
- 付款详情在 390/320 移动端按已有 monetary 类型语义将关键金额放在摘要首项；未按字段名猜测，也未改金额值。
- 收入合同查看/新建统一字段行距和组间距，状态字段不再独占整行；桌面明细继续使用可横向比较的表格，移动端继续使用有标题卡片。
- 字段、校验、权限、动作和隐藏规则均保留。**原后端隐藏章节是有意设计，本轮没有恢复，也没有用导航把隐藏标题重新显示。**

## 2. 影响与边界

- 产品代码：P0 共享前端渲染与公开组件适配层。
- P4：扩展既有 form visual smoke，验证视觉顺序、语义锚点、当前章节、横向提示、桌面首屏明细和吸顶遮挡；刷新既有清单。
- contract/schema、启动链、default route、public intent、Odoo module/database：均无变化。
- 未执行模块升级、fixture reset、acceptance、业务保存、发布或远程写入。
- 收入合同“未收款金额/未收款”口径问题继续仅登记，不合并、不改值、不补契约。

## 3. 可见结果

- 材料 1440/1088 桌面首屏同时可见“入库明细”和“添加入库明细”；正文、关系区和具体明细不再形成连续三层套框。
- 收入合同详情桌面底部最大滚动量：1440 从 1143 降为 1104，1088 从 1135 降为 1096；新建页分别从 1513 降为 1400、从 1505 降为 1392。字号和字段数量未减少。
- 付款详情移动端首屏可同时识别单据标题/编号、状态、主操作与申请金额；390 的最大滚动量从 1581 降为 1381，320 从 1673 降为 1630。
- 四个样本的所有章节入口均存在、可点击、可获得当前态；定位后的具体语义锚点位于吸顶表面下方。末端入口可通过横向提示发现。
- 明暗主题下页头背景均为不透明主题表面，正文未穿过标题与导航。

## 4. 验证

- `make verify.frontend.quick.gate`：PASS（产品及清单 HEAD `45531f9c58fbc6506d326e48a9861397030ffd49`）。之后仅将 P4 的“明细首屏”断言限定到产品要求的 desktop viewport；`python3 -m unittest scripts.verify.test_local_dev_candidate_frontend` 9 tests PASS。
- 定向：strict typecheck、form canvas wide-grid、primitive adapter、professional detail collection、product page pattern、rendering detail state 均 PASS，且均为非零测试。
- 最终 exact-head：`121f63540a982eb35a36655fc2847e4a73e93fa3`。
- exact fingerprint：`artifacts/fingerprints/form_visual_hierarchy_candidate_121f6354.json`，digest `779479790a59bbc3035e0ca4a9de57aec836def94a92a602ca79fc3c742bad03`，7354 paths。
- 浏览器矩阵：
  - light：1440×960 / 390×844，四个样本全部 PASS。
  - dark：1088×960 / 320×844，四个样本全部 PASS。
  - 共 16 个路由视口、48 张首屏/中段/底部截图；`mutationCount=0`、`errors=[]`、`failures=[]`。
  - 每个视口均验证唯一当前章节、横向提示、全部入口逐项可达、目标不被吸顶区域遮挡；材料明细首屏断言按产品要求仅应用于 desktop。
- 人工截图复核：材料无重复通用章节标题；付款金额位于移动摘要首项；暗色合同首屏、移动长表单和底部协作/审计均可读。

## 5. 证据索引

- before（上一轮冻结候选）：
  - `artifacts/playwright/form-structure-final-exact-f1943462-1440-390/summary.json`
  - `artifacts/playwright/form-structure-final-exact-f1943462-1088-320/summary.json`
- final light：`artifacts/playwright/form-visual-hierarchy-light-1440-390-121f6354/summary.json`
- final dark：`artifacts/playwright/form-visual-hierarchy-dark-1088-320-121f6354/summary.json`
- 代表截图：
  - `artifacts/playwright/form-visual-hierarchy-light-1440-390-121f6354/desktop-material-create-after.png`
  - `artifacts/playwright/form-visual-hierarchy-light-1440-390-121f6354/mobile-payment-detail-after.png`
  - `artifacts/playwright/form-visual-hierarchy-dark-1088-320-121f6354/desktop-income-detail-after.png`
  - `artifacts/playwright/form-visual-hierarchy-dark-1088-320-121f6354/mobile-income-create-after.png`
- contract snapshot：N/A，本轮无 contract/schema 变化。
- 历史失败证据不作为最终通过依据：早期矩阵分别暴露并关闭了 DOM/视觉顺序判定、字段 semantic role 锚点投影及 desktop-only 断言范围问题。

## 6. 风险与回滚

- 已知限制：缺少 semantic role 的历史表单仍只能优化排版，不会获得推断式章节；这是契约边界，不以字段名补猜测。
- 本地证据不代表多角色、真实写入、旧版本升级兼容、acceptance 或发布验收。
- 产品回滚边界：在受管修复分支逆序回退 `067cf58c` 之后本批 P0 提交；P4 脚本与清单可独立回退。无需数据库、fixture 或 contract snapshot 回滚。

## 7. 下一步

- 当前状态：本地实现和证据已完成，等待产品复核“表单视觉层级与首屏效率收口”。
- 产品复核前不继续美化、不新增功能，也不自动恢复键盘与查询专题。
- 是否退出表单表达阶段、是否另行启动键盘与查询优化，由后续明确调度决定。

## 结论

本批已在共享前端范围完成可复核的表单层级和首屏效率改进，且保留了有意隐藏的章节、全部字段与业务边界。结论限于四个代表样本的本地只读候选，不扩张为全系统交互、写入、升级或发布通过。
