# FE-PROJECT-DETAIL-01 项目台账身份摘要布局

## 身份与范围

- 起始：main@8ff4cad7f3eb38152e74ec9222297bd692612c07，干净。
- 分支：feature/project-detail-productization-01；运行：FE-PROJECT-DETAIL-01。
- P0 标准原生模板的既有声明样式消费；P4 定向验证。只修改 NativeFormTreeRenderer.vue 的样式，不增加模型判断、模板或运行时。
- 原生节点及顺序、字段 occurrence、native locator、表单绑定、客户/业主数据来源、日期、业务动作、权限、配置均不修改。
- 复用现有 Chromium 启动器和日常 demo 登录能力；UID 39、company 1、project 7、sc_demo。没有部署或业务写入。

## 根因与改动

源码声明：addons/smart_construction_core/views/core/project_overview_views.xml:17-42 的身份区；:61-67 的完成度区。
浏览器实际契约 action 588 / view 1772，native_form_layout；businessConfigContracts 为空、legacyFieldPolicyOverlay=false。

原生身份区为 d-flex / justify-content-between，正文子项 flex:0 1 auto；其内部的 FormSection 开启 inline-size containment。实测父宽1111px，正文宽112px，摘要高908px。名称和主体信息只能挤在左侧。
完成度文本、数值和斜杠经过 FormSection/递归树块级包装，单值仍占维护网格，导致分行。

在现有声明 token 对应样式内分配正文剩余空间，摘要只读字段批次取消尺寸容器并按内容同行排列，递归包装透明；保留标签与字段身份；窄屏主体换行。完成度的数值、斜杠居中同行。
影响范围只到 sc-project-overview__header 与 sc-project-stage__desc 的声明区域；维护区和看板不匹配这些选择器。

## 定向验证

- make verify.frontend.form_canvas_layout.unit：通过，80项布局用例、29项真实Vue组件挂载检查。日志 .runtime/agent-runs/FE-PROJECT-DETAIL-01/layout.log。
- make verify.frontend.project_detail_summary.browser：通过，320/390/768/1440四个宽度、32项几何/身份/控件状态检查。生产SFC样式，离线DOM夹具，无服务访问。日志同目录 geometry.log。
- node scripts/verify/frontend_project_detail_summary_browser.mjs --baseline：预期失败，原始基线在320px下正文70/288px，完成度分行；证明回归用例能检出旧问题。正常测试不依赖历史Git对象。
- make ci.local.iteration：通过，仅L1/推荐计划，不等于完整验收。日志 iteration.log；其中交付计划因未提交输入标记blocked，未运行交付车道。
- canonical_form_presenter、dev.incremental、page_pattern_reference_parity、primitive_adapter、product_page_pattern、style_system：全部通过。原始结果 remaining-gates.log。
- git diff --check：通过。

## 既有门禁阻塞

make verify.form_container_presentation.guard 失败，affected-gates.log：
1. frameless inline-size containment 自测试未检出其变异；
2. alert/alert-danger/alert-info/alert-link/alert-warning vocabulary 检查缺失；
3. 未声明布局的基线期望与实际span=12不符。

只读加载起始HEAD的完整原始渲染器、保持其余未改输入运行同一guard，完全复现上述三项。属于既有门禁/契约问题，本批未改guard、未放宽条件、未扩展修复。整体状态verification_pending，不能称全部门禁通过。

## 浏览器观察与证明范围

日常环境仍为原始构建。本轮将编译后的候选CSS仅加入当前浏览器，用于样式对照，不替换服务资源、脚本或契约；不是已部署新构建的端到端验收。

- 1440px：正文112px → 1023px；摘要高度908px → 228px。
- 390px：摘要宽325px、高402px，无页面横向溢出；长主体名称自然换行。
- 完成度两个值同一行，斜杠位于中间。
- 全部已渲染字段key、native locator、state与原页面一致；保存草稿仍可见且未禁用；没有输入、保存或动作执行。
- 看板view1518：候选CSS前后文本、所有测量字段/容器几何、按钮状态完全一致。
- 下方基本信息、计划责任、责任矩阵保留；样式未触及这些区域。
- 几何及字段身份原始记录：.runtime/agent-runs/FE-PROJECT-DETAIL-01/browser-preview.json。
- 同目录截图：ledger-baseline-desktop.png、ledger-candidate-desktop.png、ledger-candidate-narrow.png。
- 离线夹具首次缺doctype导致quirks模式form默认margin，已修正夹具；未因此追加产品CSS或放宽断言。

## 主展示职责与保留重复

|字段|摘要职责|维护职责|本批处理|
|---|---|---|---|
|名称、编号|身份识别|名称维护、编号只读|全部保留，压缩布局|
|项目类型、经营方式|背景信息|基本信息维护|保留；隐藏需另案证明配置兼容|
|负责人、项目经理|责任提示|计划与责任维护|保留；可选补充的取舍待下一批|
|客户/业主|同一业务概念|现有partner_id/owner_id依赖分别保留|不映射、不同步、不删字段|

重复标签（如项目经理、业主）及摘要/维护区重复尚未删除；本批没有隐藏计划的实施授权。经营摘要卡片内部密度未扩展处理。

## 交付边界与下一步

批次：本地实现及定向验证完成，既有门禁阻塞/正式构建浏览器验收待完成；主线：未合并；部署：未部署；用户验收：待人工审阅。
回滚：撤销本专题提交，无数据或配置回滚。
下一项最小任务：单独核验并处理上述已有presentation门禁与当前契约口径的差异；通过后再安排候选构建验收。本批不自动继续或部署。
