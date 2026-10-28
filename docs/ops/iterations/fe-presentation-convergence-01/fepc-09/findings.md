# FEPC-09 项目详情展示核查

结论：本轮找到4项展示修复候选，其中**协作消息作者/正文映射**证据最完整；未实施任何修复。其余已确认空值不误判为UI问题。等待GPT审查独立审计PR；不合并、不部署。

## 基线、证据边界

GitHub最新main核对结果及本轮HEAD基线为 `27de8c2769d4c02a6e1076ad3f60fb9aa9f77e17`，PR758已进入主线。分支 `audit/fepc-09-project-detail-review`。仅P4审计文档、脱敏证据、只读探针及任务元数据；无产品、契约、配置、数据库修改。

服务 `/t/demo`、sc_demo，运行时声明 `3f46dd7eba9f351386fee446151ee9eb545d56a4`、版本1.0.0-rc.20，构建指纹见 [观测](presentation-observations.json)。项目15、用户41、business_full、当前公司1；并非全角色/全公司/全项目验收。此次浏览器Linux Chromium147、1440×1000、DPR1；不代替Windows及窄屏体验验收。

复用API01已确认日期/关系/契约和API02R身份上下文，不重新采集首页指标或执行付款点击。新浏览器只补可见展示/布局，自动初始化的API只保存请求状态，不重复落盘业务响应。唯一补充业务投影为既有4条消息的作者/正文（历史证据已裁剪，无法判定作者映射），不扩展项目、分页或权限范围。

本页“基本信息、计划与责任、责任矩阵、协作记录”是核查范围。真实页面前三者是纵向卡片，关联业务内另有11个原生notebook页签，协作日志位于下方。不能凭任务文字把它们误当成4个已存在页签。前一轮F1探针选择器失败原样保留，未再复现F1。

## 分类清单

`visual_defect`是有可见证据的修复候选，不代表获得实施授权；`verification_pending`保留事实和未知。没有证据时不强行凑齐data_gap、contract_config_gap或interaction_defect数量。

| ID | 范围 | 分类 | 结论 / 下一步 |
| --- | --- | --- | --- |
| 09-01 | 协作记录作者/正文 | `visual_defect` | API m-672.author_name=项目审批岗，正文以“项目初始化已完成：”开头；页面作者位置却显示“项目初始化已完成”，正文前缀被截去。其余备注的作者位置显示“备注”。 独立修复消息显示映射；消费author_name并保留完整正文，不改消息记录。 |
| 09-02 | 协作/系统中的关系空状态 | `visual_defect` | task_ids与collaborator_ids都仅显示“暂无可展示记录”，没有可见关系名称，用户无法分辨两块空状态。 最小候选：空/加载/非空关系的标题职责一致，消费现有字段label；不能硬编码项目字段名。 |
| 09-03 | 协作阅读顺序与关注者 | `visual_defect` | 关注者19人，容器高914px；滚动到协作面板时，时间线顶部y1254，低于1000px视口。名单遮占主要阅读空间。 先确认紧凑展示/按需展开方案；限定关注者组件，不修改数量、关注权限或时间线数据。 |
| 09-04 | 标题层次 | `visual_defect` | 同名项目标题在y137和y295各显示一次，均高32px；主体开始前存在重复标题层。 独立标题职责收敛候选；保留原生名称、收藏、编辑和固定页头功能。 |
| 09-05 | 客户长名称与字段栅格 | `verification_pending` | 1440px下客户名称折三行，项目编号折两行，未观察到丢字、重叠或水平页面溢出。 不立即改宽度或字段顺序；若产品要求再限定测试视口。 |
| 09-06 | 计划日期展示 | `expected_behavior` | date_start/date/end_date=false；date_start/end_date显示“-”；start_date与initiation_date为2026-10-28且正常显示。 转DATA-01候选，先批准场景事实，禁止前端填日期。 |
| 09-07 | 责任矩阵 | `expected_behavior` | responsibility_ids=[]；区块标题“责任矩阵”和合法空态可见。负责人字段有值不意味着存在矩阵明细。 DATA-01先确认场景需求；不要制造记录以改善截图。 |
| 09-08 | 协作者、关注者与时间线 | `expected_behavior` | 合作者关系0；本轮DOM关注者19；历史timeline总6=4消息+1活动+1审计，当前普通时间线5。 保留集合语义，审计展示如需覆盖另行补证，不强制数量相等。 |
| 09-09 | 协作时间顺序与时间口径 | `verification_pending` | DOM四条消息顺序为04:06、03:40、03:40、03:40，活动截止10/26；API按at降序；ISO时间无时区，DOM显示同一钟面值。 不要先加8小时或前端重排序；先确认服务端时间契约。 |
| 09-10 | 附件与空正文 | `verification_pending` | 历史附件0；当前显示上传入口。m-1568.body为空，但页面显示“备注”；可能来自title fallback。 仅保留候选；DATA-01先定义附件示例需求，不点击写操作。 |
| 09-11 | 只读、必填与业务操作 | `expected_behavior` | effectiveRenderProfile=readonly；基础字段无编辑输入；name必填、sc_approval_state只读必填；date_start有条件required声明。页头删除、协作回复/上传仍可见。 本轮不动权限；若产品要求纯只读所有交互，需独立权限/模式契约审查。 |
| 09-12 | 客户与业主 | `expected_behavior` | 详情客户partner_id与既有台账owner_id均指向72；详情读请求未包含owner_id，不可当作空值。 不统一字段key或标签；按已批准业务口径独立核查。 |
| 09-13 | 归档项目日期与责任覆盖 | `verification_pending` | 归档阶段项目计划竣工/安排日期为空、责任矩阵0、进度口径有待确认。 DATA-01建立场景→事实→初始化→重建验收方案后再授权。 |
| 09-14 | F1帮助浮层 | `verification_pending` | Windows人工观察滚动错位；Linux72帧未复现持续错位；一次短暂滞后因果未确认。 不计入FEPC-09修复候选，不继续测试。 |

完整逐项来源、观察、解释、未知见 [findings.json](findings.json)。

## 优先证据

1. **消息映射**：[实际API补证](message-author-evidence.json) 中m-672的author_name是“项目审批岗”，正文以“项目初始化已完成：”开头；[真实展示](06-timeline-content.png) 把这个前缀放在作者位置。运行时同版本 `professionalCollaborationModel.ts:235–252` 用正则拆正文，而没有读取message.author_name。其余消息在作者位置显示“备注”。属于消费者映射错误候选，不应修改演示消息或作者数据。
2. **无名关系空态**：[截图](04-collaborators.png) 两个相同空块；[DOM](supplement-presentation-observations.json) 识别为task_ids和collaborator_ids，均field--label-free。父FormSection转移标题职责，而X2ManyRelationRenderer只在非空分支输出标题。历史契约确认合作者label；task_ids标签及hideLabel还须在实施前对齐声明，不可硬编码名称。
3. **关注者占位**：[截图](05-timeline.png) 和DOM确认关注者19、高914px，时间线被推到视口以下。是阅读层次候选；不能把19当成应删人数，不能擅定折叠阈值。
4. **重复标题**：[首屏](01-basic.png) 同名标题两次，分别来自页头和原生标题投影。最小设计需要决定标题/收藏/编辑职责，不能未经裁定删除原生结构。

## 数据、模式与关系

date_start/date的安排日期范围，与start_date/end_date计划范围不是同一组字段。API false与页面“-”对应；date独立字段被声明隐藏，以范围控件消费。名称必填、审批只读等字段定义与页面readonly模式独立，不能因为只读页面没有星号或编辑框就判定必填丢失。

责任矩阵0是既有记录事实，页面标题和空态正常。负责人字段有值不等于矩阵有明细。合作者0、关注者19、timeline6属于不同模型/集合；普通时间线过滤audit后5条与源码一致，独立审计展示仍未验全。附件0、空日期、归档项目进度等是否需要补齐，须先有Demo演示场景规则，本轮不冒充已经批准的数据缺口。

时间线当前四条消息按返回时间降序，活动按其截止时间参与排序。无时区ISO到用户时区的口径、同秒稳定顺序及审核事件可见性保留未知，不自动加时差/重排。基础表单readonly不等于禁止独立协作动作：回复、关注、上传、删除入口存在，未执行这些动作，也不据按钮存在宣称实际权限正确。

## 执行与状态

[证据索引](evidence-index.md) 连接原始来源、当前截图/DOM、源码身份和失败限制；[最小实施建议](minimal-implementation-proposals.md) 是待批准候选。浏览器启动时global.message.conversations因只读白名单被阻止，产生ERR_BLOCKED_BY_CLIENT，属于探针限制，不记为产品故障；无其他pageerror。DOM的visible是CSS可见，不保证在视口内，必须结合rect与截图阅读。首轮名为05-timeline的截图实际主要展示关注者，06才是时间线内容，不混用。

F1以 [正式暂停记录](../fepc-08/f1-reproduction.md) 随审计交接保留：待核实、暂不修复、不标记解决。原始探针和测量不删除。本轮没有再次打开帮助或测试滚动浮层。

批次：事实整理完成，等待审查。主线：未集成。部署：未执行。用户验收：未通过，需GPT裁定。回退只涉及本审计文档，不需要产品或数据回滚。下一步是GPT选择独立最小修复任务或DATA-01业务定义；不自动进入实施。
