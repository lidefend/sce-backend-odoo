# TDesign 设计体系对齐 Batch A 交付报告

English: [tdesign_system_alignment_batch_a_20260914.en.md](tdesign_system_alignment_batch_a_20260914.en.md)

## 范围与身份

- 分支：`codex/tdesign-system-alignment-v1`；基线：`origin/main@6885840fe57f1e00ae8ce78bc76687e8a4a66332`。
- 产品源候选：`85b051104f29934e84ffaf81aff4ec8827290e51`，Tree `cd2be7d220c89a907e04a5d9ae2a23a44412a3b2`，完整工作树指纹 `eb216c2897ffa47c9e45978a3dcdca3336b35a60e07f2eec5979786ac75063a7`。
- Formal Product Layer：P0 平台共享表现层；Layer Target：现有设计 token、TDesign 公开桥接、共享页头、Card appearance、通用表单章节/字段布局与章节导航。
- Standard vs User-Specific：平台通用规范；没有 P1/P2/P3 业务字段、客户偏好或运行时配置。
- Why Here：问题来自共享排版、表面和导航消费不一致，应由现有 P0 组件与 token 收口。
- Why Not Elsewhere：P1 XML、契约字段/章节、权限、动作和业务语义均正确保留，不通过逐页 CSS 或模型特判覆盖。
- Blast Radius：共享列表、表单和只读详情的排版/表面/字段边界，以及使用 `FormSectionNavigation` 的表单。代表列表、办理表单、只读详情和复合表单共同验证影响范围。

## 用户可见结果

- 页面标题、章节、正文/控件、标签/辅助文字统一消费 24/16/14/12 的项目语义层级；控件 widget、格式、校验和标题内容不变。
- 主工作面保留一个结构边界，业务章节使用连续表面和单一分隔，嵌套表格、浮层与特殊状态仍保留功能边界。
- 章节导航的前后浏览按钮拥有独立空间；末端标签不再被提示覆盖，桌面与触屏触达尺寸继续消费既有 token。
- 只读长中文、无空格编号和关系名称在自己的字段槽位内换行，不覆盖相邻字段，也不隐藏业务值。
- 新建页纵向增量来自文字行高和自然换行；检查未发现重复 section/card padding，没有用固定高度或缩小字号回压。

## 修改归属

| 层 | 修改内容 | 边界 |
| --- | --- | --- |
| P0 token / bridge | 统一产品标题、章节、正文、辅助文字及表单控件公开 CSS 变量 | 不升级 TDesign，不改色板或主题生命周期 |
| P0 shared components | `ProductPageHeader`、`ScCard`、`FormSection`、`ProfessionalBaseFieldControl` | 不读取模型名、字段名、XML ID 或业务值 |
| P0 form renderer | 连续章节表面、字段网格可收缩、只读长值槽位内换行 | 不改契约章节、字段顺序、widget 或保存链 |
| P0 navigation | 溢出控制独立占位并沿用既有 anchor/滚动算法 | 不替换为 TabPanel，不改路由或章节身份 |
| P4 | 聚焦守卫、只读浏览器证据、本文和 PR 草案 | 不写数据库，不扩展业务验收 |

四个产品提交可独立回滚：`67301212`（A1 排版）、`d63a1dbb`（A2 表面）、`244cf29d`（A3 导航）、`85b05110`（只读字段边界）。

## 验证与证据

| 层 | 入口或证据 | 结果 |
| --- | --- | --- |
| L0 | HEAD、Tree、完整 tracked/staged/untracked 指纹 | 产品源候选干净且身份固定 |
| L1 | `make ci.local.iteration` | PASS，16 tests |
| L2 | form canvas、product page header、professional base field、canonical presenter、native section navigation、primitive/page pattern 及严格类型检查 | 非零 PASS；字段收缩、标题 token、导航占位及既有结构消费均有聚焦覆盖 |
| L3 | `make local.dev.health` 与 exact-head candidate frontend | 既有 `sc-local-dev/sc_dev_demo` 健康；候选前端通过受管入口启动并停止。无模块/schema 变化，因此未做模块升级 |
| L4 light | `/home/lidefend/workspace/sce-offrepo/artifacts/playwright/tdesign-alignment-final-light-1440-390-85b05110-retry1/summary.json` | 1440×960、390×844 共 8 个页面/视口样本，`pass=true`、零写入、零错误；全部 root overflow=0、h1=1、token 已加载 |
| L4 dark | `/home/lidefend/workspace/sce-offrepo/artifacts/playwright/tdesign-alignment-final-dark-1440-390-85b05110/summary.json` | 同一 8 个样本 `pass=true`、零写入、零错误；长值、控件、表面、导航和横向内容可达 |
| L4 composite | 两组 summary 中的 `material-inbound-composite-form` | 日期、关系选择、文本域共 8 个适用控件在桌面/移动均零槽位或基线失败；仅展开查看，未保存 |
| L5 | `make ci.delivery.freeze.prepare`、最终一次 `make ci.local.quick`、独立复核 | 冻结后由仓外 exact-head receipt 和独立复核记录；本文不回填结果而再次改变候选 |

支出结算新建的五个导航目标在四组视口/主题中均唯一、按钮完整可见且定位在吸顶区下方。只读详情的实际可见导航目标也逐项通过；浅色桌面 12 项、其余样本 11 项的差异来自当前可见内容，未用固定数量冒充规范。收入合同移动端的表格横向浏览提示和前后控制可见，根页面没有横向溢出。

首次浅色矩阵在页面加载期间出现 `ERR_NETWORK_CHANGED` 和动态组件加载错误，摘要保留于 `tdesign-alignment-final-light-1440-390-85b05110`，归类为 `environment_defect`。随后同一 HEAD 的受管 health 恢复且候选服务可用，才执行一次 retry；通过证据没有覆盖或删除失败记录。

冻结准备前的聚焦自检还发现页头守卫仍要求 `.readonly-value` 的旧属性顺序，无法接受同一规则新增的可收缩槽位属性；归类为 `validation_tool_defect`。P4 仅将断言更新为同时要求 body token 和 `max-width/min-width` 槽位约束，并新增失败反例；11 项守卫测试及直接 guard 均通过，产品源文件没有因此变化。

## 保留边界与回滚

- 未执行保存、审批、权限、全角色、数据库、fixture、模块升级、发布或部署验收；所有浏览器样本为只读或未提交交互。
- 本批不改 P1 XML、业务章节、字段顺序、外壳、色板、活动页签、Dialog/Drawer 生命周期或低代码运行时。
- `ScFormField` 的帮助/错误关联仍是后续独立 P0 交互任务，不借视觉批次宣称完成。
- 若需回滚，按 `85b05110` → `244cf29d` → `d63a1dbb` → `67301212` 逆序回退；没有业务数据回滚。

## 冻结策略

本文、英文报告、PR 草案及生成证据在冻结前一次提交。冻结后只运行一次 Quick，并由独立复核证明最终候选相对 `85b05110…` 仅有 P4 文档/生成证据变化；不为回填 SHA 或测试结果再修改候选。
