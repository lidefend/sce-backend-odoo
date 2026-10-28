# FEPC-09 证据索引

## 已有证据复用

[reused-project-facts.json](reused-project-facts.json) 是API01已有脱敏证据的选择性投影，非本轮新API结果。包含project15实际契约来源view943/action0、字段定义及修饰、已确认值、关系和时间线。原始文件路径及SHA256、运行时源码blob见 [evidence-provenance.json](evidence-provenance.json)。原件在本地.git/codex-recovery/FEPC-07R/merge-closeout/files归档，未修改；在线审阅可检查本PR所提供投影，不能声称已独立读取本地原件。

FEPC-01：[历史发现](../findings.json)、[原索引](../evidence-index.md)。API02R仅复用账号/版本上下文，不把付款验证当项目详情证据。F1暂停后只引用既有运行身份和测量，不补测。

## 当前浏览器与补充响应

| 证据 | 内容 / 限制 |
| --- | --- |
| [presentation-observations.json](presentation-observations.json) | 首次补测5个页面样本，18条API响应元数据；started_at/completed_at、环境、每请求时间/http_status/application_ok、前后runtime-version齐备 |
| [initial-probe.mjs](initial-probe.mjs) | 首次真实执行探针；只访问项目15，读取/滚动/实际协作系统页签，不执行业务按钮 |
| [supplement-presentation-observations.json](supplement-presentation-observations.json) | 一次补测：关系空态DOM与时间线内容位置；18条自动加载请求元数据，未重复保存业务数据 |
| [probe.mjs](probe.mjs) | 该补测探针；未点击F1帮助 |
| [message-author-evidence.json](message-author-evidence.json) | 2026-10-28T09:11:54Z，POST /t/demo/api/v1/intent，chatter.timeline，project.project/15，offset0，HTTP200/ok=true；只保留四条既有消息作者/正文/类型/时间 |
| [collect_message_authors.py](collect_message_authors.py) | 复用既有客户端认证；仅补取历史省略的映射字段，无扩大范围 |
| [run_probe.py](run_probe.py) | 隐藏密码输入、内存token管道；没有密码文件或会话转储 |
| [01-basic.png](01-basic.png) | 首屏重复标题、字段布局、日期和责任矩阵 |
| [02-plan.png](02-plan.png) / [03-responsibility.png](03-responsibility.png) | 目标原已在视口，scrollIntoView没有额外位移；不是额外页签成功证据 |
| [04-collaborators.png](04-collaborators.png) | 实际协作/系统页签；两个无名关系空块 |
| [05-timeline.png](05-timeline.png) | 协作面板顶部，主要是19名关注者；时间线仍在视口外 |
| [06-timeline-content.png](06-timeline-content.png) | 滚到时间线，直接展示作者槽位、正文、顺序和活动 |

标准只读intent路径均为POST /t/demo/api/v1/intent；请求元数据逐条保留intent/op/model及成功状态。版本身份GET /t/demo/api/runtime-version返回200。请求白名单复用已核查只读链；global.message.conversations阻止产生的唯一console错误不作为产品缺陷。认证成功摘要无token/cookie。没有create/write/unlink/审批/状态切换/关注/上传/回复操作。

## 源码引用

运行时声明SHA `3f46dd7eba9f351386fee446151ee9eb545d56a4` 下13个相关文件与本轮main相同，逐文件blob见provenance。源码链：ContractFormPage→NativeFormTreeRenderer/FormSection→X2ManyRelationRenderer；NativeCollaborationPanel→ProfessionalFollowerManager/ScList、ProfessionalCollaborationTimeline→professionalCollaborationModel；后端chatter_timeline提供作者、正文、时间和权限声明。契约源project_overview_views.xml/project_core.py。版本匹配不证明当前数据库配置未变化，历史契约引用按历史证据标记。

可直接查看 [消息映射源码](https://github.com/lidefend/sce-backend-odoo/blob/3f46dd7eba9f351386fee446151ee9eb545d56a4/frontend/apps/web/src/pages/contractForm/professionalCollaborationModel.ts#L235)、[后端消息声明](https://github.com/lidefend/sce-backend-odoo/blob/3f46dd7eba9f351386fee446151ee9eb545d56a4/addons/smart_core/handlers/chatter_timeline.py#L212)、[关系空态源码](https://github.com/lidefend/sce-backend-odoo/blob/3f46dd7eba9f351386fee446151ee9eb545d56a4/frontend/apps/web/src/components/template/X2ManyRelationRenderer.vue#L71)。

## 验证与未知

源码事实、复用运行时事实、新API事实、截图/DOM观察分别标记在发现清单，不互相替代。没有检查其他项目、公司、角色、Windows、窄屏、写权限、附件下载或全量审计事件。所有样本只证明当前入口和账号下的展示。

文档/元数据校验与轻量入口结果见validation.json；未实施产品修复，不运行业务写入测试。PR只供GPT审查，发布不代表合并资格或产品验收。
