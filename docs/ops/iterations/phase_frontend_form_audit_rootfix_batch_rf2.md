# 表单跨状态几何与可见性根因修复 — Batch-RF2

## 1. 本轮变更

- 目标：关闭 Batch-RF1 真实浏览器审计遗留的文字裁切、流程裁切、sticky 锚点和 loading 状态问题，并补齐同一记录“只读 → 继续办理 → 编辑”的跨状态页面尺寸审计。
- 通用产品修复：
  - 状态流程步骤按内容扩展，长状态不再被固定宽度截断。
  - 只读字段值和设计器搜索结果允许在容器内安全换行。
  - 章节定位改为确定性滚动，避免平滑动画采样到错误 sticky 位置。
  - 仅在权威迁移前缀位于字段值开头时隐藏内部迁移元数据，业务正文保持不变。
  - 有真实章节的编辑表单不再重复插入“编辑业务信息”说明区。
  - 同一记录在查看和编辑模式使用稳定记录身份；模式由命令栏表达，不再通过标题前缀造成窄屏换行和整体下移。
- 审计修复：loading 观测与被延迟的真实 `ui.contract` 请求同步；跨状态审计从运行时可编辑路由反推同记录只读路由并真实点击“继续办理”，不固定 model、record、action 或 menu ID。

## 2. 架构边界

- Formal Product Layer：P0 平台共享前端。
- Layer Target：通用表单渲染、页面身份、可见文本容纳和真实浏览器验收。
- Module：`frontend/apps/web` 与 `scripts/verify`。
- Standard vs User-Specific：平台通用行为，不固化 `sc_demo` 或 `wutao` 的业务语义与偏好。
- Why Here：缺陷来自所有契约表单共享的渲染几何和审计采样机制。
- Why Not Elsewhere：不修改权限、工作流、接口语义、数据库记录或客户配置来掩盖前端问题。
- Blast Radius：详情/编辑/新建表单、表单设计器、字段只读展示和表单验收脚本；启动链、公共 intent、contract/schema 与 default route 均不变。

## 3. 跨状态几何合同

- 深度视口：1440×900、390×844。
- 运行路径：当前角色运行时发现可编辑记录 → 同记录只读页 → 点击“继续办理” → 编辑页。
- 采集容器：viewport、document、`#main-content`、表单 page、命令栏、主内容卡和表单 canvas。
- 采集字段：bounding box、clientWidth/clientHeight、scrollWidth/scrollHeight、overflow、position 和 sticky top。
- 断言：记录身份稳定；核心容器 x/width/clientWidth 差异不超过 1px；命令栏、内容卡和画布 y 差异不超过 1px；document 与核心容器无横向溢出。
- 本轮实测：1440 与 390 的命令栏、内容卡、画布 x/y/width/clientWidth/scrollWidth 差异均为 0px。编辑控件导致的自然文档内容高度变化被记录但不伪装成外框几何失败。

## 4. 验证与证据

- 完整表单真实浏览器审计：PASS，129/129，issues=0，运行时错误 0。
- “继续办理”跨状态断言：8/8 PASS（1440 与 390 各 4 项）。
- `make ... verify.frontend.quick.gate`：PASS，包含页面宽度/表单画布契约、页面身份、关系字段、onchange、x2many、严格类型检查与 Vite 构建。
- `pnpm -C frontend/apps/web lint:src`：PASS。
- `make verify.frontend.localized_display.unit`：PASS。
- `make verify.frontend.detail_form_productization.guard`：PASS。
- `make verify.frontend.acceptance.environment.guard`：PASS。
- `git diff --check`：PASS。
- 截图经执行者肉眼复核，最终视觉结论仍由监督者裁决。

## 5. 产物

- `.runtime/final-acceptance/form-audit.json`
- `.runtime/final-acceptance/form-audit.html`
- `.runtime/final-acceptance/form-continue-readonly-1440.png`
- `.runtime/final-acceptance/form-continue-edit-1440.png`
- `.runtime/final-acceptance/form-continue-readonly-390.png`
- `.runtime/final-acceptance/form-continue-edit-390.png`

## 6. 状态与回滚

- 本批次代码和本地真实浏览器门禁已形成候选；未部署生产、未合并主分支、未写入业务数据库。
- 回滚：回退本批次提交即可，无数据库、模块升级或数据恢复动作。
- 状态：等待监督者最终视觉验收；不得仅凭自动化结果关闭“自定义前端专业成品收敛”专题。
