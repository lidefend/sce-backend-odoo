# 共享前端基础完整性收口报告

日期：2026-09-09

状态：开发候选验证通过；不是 PR、CI 或发布验收结论

## 1. 候选与范围

- 产品基线：`d4b66a8eca180bc640bad31285bb80021381251c`。
- 冻结产品候选：`10fdf6dcb4007be20ea7ba25a097a4d60a654aef`。
- 完整 tracked、staged、untracked 指纹：`694f36c9aafa0cb2db53866de587aa5cff6ac02910a0e69a66e836583919385f`，7344 路径；使用 `scripts/contract/complete_worktree_fingerprint.py` 和上述产品基线生成。
- 产品提交范围：40 个文件，新增 958 行、删除 130 行；其中包含共享实现、行为门禁、浏览器证据入口、生成清单及实施前审查文档。
- Formal Product Layer：P0 平台通用前端机制；P4 仅承载验证入口、生成清单和本报告。
- Layer Target：canonical form、relation/detail collection、design-system adapter、validation/focus lifecycle。
- 不含后端模型、契约字段、业务规则、fixture、数据库迁移、发布环境或 release gate 改动。

产品候选运行在受管 `local.dev`：前端 `5176`、数据库 `sc_dev_demo`、用户 `sc_test_admin`。报告提交会位于产品候选之后，因此服务绑定的是上述产品 SHA，而不是报告 HEAD。

## 2. 收口结果

### 字段校验与焦点

- canonical form 以字段 code 和明细单元格路径传递错误，不再根据标签或错误文案猜字段身份。
- 错误摘要携带明确目标；定位时展开其祖先分区，只选择当前页面中可见的匹配控件；无结构化目标时聚焦摘要并保留原错误。
- relation 字段通过既有 native-control projection 将 `required`、`invalid` 和 `describedby` 投影到真实输入控件。
- 明细错误采用 `field:row:column` 身份，修正对应单元格后只解除该错误。

### 关系明细表达与既有能力消费

- 明细桌面列显式显示契约列标题；320/390 使用同一数据和操作 authority 的移动卡片，不再依赖宽表格缩放。
- 桌面和移动复用 `One2ManyCellEditor`，去除了两套字段编辑、错误绑定和只读提示分支。
- many2one 明细编辑仅在 `inline_edit=true`、列非只读、子字段 `relation_entry.can_read=true` 三项 authority 同时成立时启用；缺失或加载失败均保持只读。
- 候选查询复用现有 relation runtime、行/父表 domain 和选择浮层；没有模型名、菜单 ID、记录 ID或中文字段标题特例，没有新增保存分支。
- 只读、加载、失败和空结果均使用面向用户的状态说明，不暴露“当前契约”等实现术语。

### 变更前后对照

| 基线缺口 | 候选结果 | 证据边界 |
| --- | --- | --- |
| 错误按标签文本匹配，可能误标同名或嵌套字段 | `project_id` 错误目标与实际聚焦字段一致；明细错误目标与活动控件路径一致 | 自动行为断言 + 最终浏览器截图 |
| relation 错误停留在组合控件外层 | 实际 input 获得 required/invalid/describedby | 定向 guard 与真实页面验证 |
| 明细列标题缺失，窄屏为拥挤宽表 | 桌面读取 12 个列标题；移动读取 10 个字段标签并采用逐行卡片 | 1440/1088、390/320 实测 |
| 桌面和移动维护重复单元格逻辑 | 两种布局消费同一编辑器和错误状态 | 代码结构 guard + 两种布局实测 |
| 关联列一律只读，已有完整 authority 未被消费 | 仅在三重 authority 完整时开放既有选择链；其他情况失败关闭 | 26 条真实候选、键盘选择、零提交写入 |

基线缺口来源为实施前代码审查及既有浏览器复核；本批没有伪造一套“前截图”。候选完成态截图保存在下列精确 SHA 证据目录。

## 3. 验收矩阵

| 范围 | 明色 1440 / 390 | 暗色 1088 / 320 | 结果 |
| --- | --- | --- | --- |
| 首页与系统外壳 | 加载完成、主题 token、顶栏动作边界 | 同项 | PASS |
| 冻结付款列表与记录 15 | 列表加载；详情显示 `SHOW-PR-04`、`¥50.00` 和现有主动作 | 同项 | PASS，只读回归 |
| 主表字段校验 | `project_id` 精确误差目标、可见控件聚焦、零写入 | 同项 | PASS |
| 明细校验与表达 | 桌面表格 12 标题；390 卡片 10 标签；单元格精确聚焦 | 桌面表格 12 标题；320 卡片 10 标签；单元格精确聚焦 | PASS |
| relation 搜索浮层 | 26 条真实候选；键盘选择；宽 920 / 366，未越界 | 26 条真实候选；键盘选择；宽 920 / 296，未越界 | PASS |
| 根文档与浏览器错误 | 无根级横向溢出；0 error；0 failure | 同项 | PASS |
| 数据修改 | `mutationCount=0` | `mutationCount=0` | PASS，本轮无保存 |

证据：

- `artifacts/playwright/frontend-shared-foundation-10fdf6dc-light/summary.json`
- `artifacts/playwright/frontend-shared-foundation-10fdf6dc-dark/summary.json`
- 同目录包含 home、payment list/detail、form validation、detail validation 和 relation dialog 的桌面/移动截图。

## 4. 验证结果

- `make verify.local.dev.frontend.quick.gate`：PASS，绑定产品候选；构建完成，所有执行的门禁为非零测试。
- `make verify.frontend.professional_detail_collection.unit`：PASS；20 项 Python guard 测试及 detail collection model 测试通过。
- `pnpm --dir frontend/apps/web typecheck:strict`：PASS。
- `node --check scripts/verify/local_dev_candidate_visual_smoke.mjs`：PASS。
- 两组受管候选浏览器旅程：PASS；候选 SHA、数据库、角色、视口、主题、错误和 mutation count 均写入 summary。
- 生成清单通过仓库现有生成器刷新；最终 Quick 对其执行 current/stale 检查通过。

本结论没有用“代码字符串存在”、测试数量或“控制台无错误”单独替代行为验证。

## 5. 剩余依赖与明确未覆盖

- 子字段缺少 relation model、`relation_entry` 或读取权限时继续只读；补充这些 authority 属于契约/业务层依赖，不在本批前端猜测。
- 当前 domain 解析器不支持的任意表达式保持失败关闭，登记为上游契约能力，不在浏览器执行字符串表达式。
- 后端只返回非结构化错误时只能展示并聚焦错误摘要，不能可靠定位字段；没有恢复标签猜测。
- 本批按约束没有执行新增单据保存，因此不宣称明细持久化写入通过；既有保存链由 Quick 中的单次写入/回读模型测试覆盖，真实写入验收仍是独立范围。
- 未验证多角色授权、审批、支付、fixture、独立移动端、PR/CI 或 release gate。

## 6. 退出判断

共享表单基础的已知消费断点已在同一 canonical 链路收敛：字段错误、真实控件属性、可见焦点、明细列信息、窄屏表达和已获授权的 relation 选择不再由样本页各自实现。付款样板只读回归未发现重开项。

因此本批达到“共享前端基础完整性收口”的开发阶段退出条件，可作为后续页面一致性验证的稳定产品候选；是否进入 PR、主线或发布阶段必须另行执行相应门禁，本文不作替代结论。
