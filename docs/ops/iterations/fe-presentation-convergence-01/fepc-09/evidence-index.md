# FEPC-09 最终证据索引

本索引区分历史完整原件与最终选择性投影，不重新采集业务数据。

| 载体 | 内容与边界 |
| --- | --- |
| [原始证据索引](original-evidence-index.json) | 原始提交1214b9ce88c42875436a71340f7dd6d2eea3a126的47个文件：固定GitHub链接、SHA256、字节数及本地恢复目录。原探针、认证摘要、重复测量、失败和截图可回查，不在最终树重复承载 |
| [历史运行身份](runtime-identity.json) | 单一版本观测，含真实GET状态、时间、源revision、构建指纹与原件摘要；不是当前发布声明，不要求与未来VERSION一致 |
| [项目事实复用投影](reused-project-facts.json) | API01既有字段/契约/关系/时间线投影，不是本轮新响应；view943/action0、公司1、项目15 |
| [源码和历史来源](evidence-provenance.json) | 运行时SHA源码blob、与审计main一致性、此前API01/02R原件摘要；API02R只用于身份上下文 |
| [最终DOM与网络状态投影](presentation-observations.json) | 两次浏览器run的时间、18+18条API请求状态、阻断原因；保留有区别的4个页面样本及关系标题DOM，省略重复字段快照。visible表示CSS可见，需结合坐标/截图判断视口 |
| [作者补证](message-author-evidence.json) | 仅补取历史省略的4条既有消息作者/正文；POST /t/demo/api/v1/intent，chatter.timeline，project.project/15，offset0，HTTP200/ok=true；未分页或扩大权限 |
| [01-basic.png](01-basic.png) | 重复标题、字段布局、日期和责任矩阵 |
| [04-collaborators.png](04-collaborators.png) | 实际协作/系统页签中的两个无名关系空块 |
| [05-timeline.png](05-timeline.png) | 协作面板顶部主要是关注者，时间线仍在视口外；文件名不代表时间线已可见 |
| [06-timeline-content.png](06-timeline-content.png) | 时间线内容的实际作者位置、正文和活动 |
| [F1最终测量](../fepc-08/f1-measurements.json) | 尝试失败/跳过状态、关键坐标与连续72帧；F1暂停、根因未知、暂不修复，完整attempt原件在原始证据索引 |

FEPC-01继续引用[原发现](../findings.json)和[原索引](../evidence-index.md)。此前API原件位于.git/codex-recovery/FEPC-07R/merge-closeout/files；PR在线提供选择性投影，不能冒称读过本地归档即独立核实完整响应。

首次浏览器5个样本中02-plan/03-responsibility目标原已在视口，滚动未改变布局；精简后不重复提交相同截图/测量，完整原件仍可追溯。补测1个样本用于真正显示时间线及确认空关系标题。截图仅为Linux147、1440×1000样本，不外推Windows/窄屏/全角色。

所有业务请求只读。必要的自动页面加载只保存状态，未重复保存业务响应；global.message.conversations被白名单阻止引发ERR_BLOCKED_BY_CLIENT，已明确为探针限制。原认证仅隐藏输入和内存管道，无凭据/会话/HTML落盘。没有付款、关注、回复、上传、删除或状态转换。

运行时源码链：ContractFormPage→NativeFormTreeRenderer/FormSection→X2ManyRelationRenderer；NativeCollaborationPanel→ProfessionalFollowerManager/ScList与ProfessionalCollaborationTimeline→professionalCollaborationModel；chatter_timeline提供作者/正文/权限。13个相关源文件与审计main相同，但不据此推断数据库配置冻结。

[消息解析源码](https://github.com/lidefend/sce-backend-odoo/blob/3f46dd7eba9f351386fee446151ee9eb545d56a4/frontend/apps/web/src/pages/contractForm/professionalCollaborationModel.ts#L235)；[后端作者声明](https://github.com/lidefend/sce-backend-odoo/blob/3f46dd7eba9f351386fee446151ee9eb545d56a4/addons/smart_core/handlers/chatter_timeline.py#L212)；[关系空态源码](https://github.com/lidefend/sce-backend-odoo/blob/3f46dd7eba9f351386fee446151ee9eb545d56a4/frontend/apps/web/src/components/template/X2ManyRelationRenderer.vue#L71)。

检查见[原始审计验证](validation.json)及[本次CI收敛](ci-closeout.md)。本轮不改产品、不部署；审计PR需最新HEAD门禁通过后收口。FEPC-10另立分支和PR，仅修复作者/正文。
