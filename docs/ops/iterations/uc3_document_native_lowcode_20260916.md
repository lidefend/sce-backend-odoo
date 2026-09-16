# U-C3 证照／制度默认结构迁移与低代码兼容

## 边界与承接

基线 `225a56bf9fa6ef3ff07a853450d11835ea973257`（#483 主线集成），分支 `feature/uc3-document-native-lowcode`，当前为开发态未提交修改。通过 `make main.sync` 快进主线后创建本批分支；从既有外部 `uc3-pending` 归档核对三份文件和补丁 SHA256，`git apply --check` 通过后恢复原文件，没有覆盖其他修改。原冻结低代码候选、证据及历史工作树保留。

Formal Product Layer=P1；Layer Target=资料证照原生默认与重复行业覆盖退役；Module=`smart_construction_core`。这是标准行业页面基线，不属于 P0 通用机制或 P2 客户偏好；P3 合法配置仍由既有后端编译器合成。P4 仅参数化既有 `local.dev.form_lowcode.browser` 的证照样板与观察，不增加环境、凭据、fixture 或配置写入器。

范围为 action 666／862，共用 `sc.document.admin.document` form view 1703。兼容台账沿用已有44项，仅核对本组。共用存档／借阅补有限契约反例，不计入迁移扣减。低代码机制、自定义字段、跨区域编排、业务规则不扩项。

## 结构来源前后对照

| 正式入口 | 迁移前（既有台账） | 本批默认结构 | 必须保留 |
|---|---|---|---|
| 证书管理 action666/menu356 | action配置191的章节、字段排序及模型级generated65 | `view_sc_document_admin_document_form` 原生分组／说明附件notebook，经后端最终树输出；配置191仅保留标题/原生模式 | 证照必填与日期、项目、办理人、四项来源、附件、原动作 |
| 制度文件 action862/menu708 | action配置178章节与字段排序，同一generated65 | 共用原生条件分组，制度名称标签；配置178保留fact权威、标题、action限定分类只读 | 专用列表、default/domain、密级/版本/有效期、附件、来源、管理员入口权限 |

精确退役 `business_config_contract_sc_document_admin_document_form_structure_generated`，其内容只有重复字段排序；存档／借阅各自action配置保留。初版恢复补丁把制度分类只读扩大到共享表单，已修正为862作用域内的语义字段策略，原生分类字段保持原可编辑范围。

## 验证与运行

L0：本批base+明确dirty范围，日常不生成完整冻结指纹。L1：`make ci.local.iteration` 16项通过；XML/Python/JS/shell语法通过。首次本机XML检查因无lxml未执行，改用标准库XML解析通过，非产品缺陷。

L2：`make local.dev.test MODULE=smart_construction_core TEST_TAGS='/smart_construction_core:TestDocumentNativeLowcode,/smart_construction_core:TestPolicyDocumentCapability'` 实际5项，1失败/0错误。原因是generated记录原始noupdate使普通record更新被忽略；改用既有精确ORM退役function。仅重验受影响的TestDocumentNativeLowcode三项，0失败/0错误；原有两项domain/日期业务测试复用。三项涵盖最终契约无旧路径、共享反例、配置预览发布回滚与另一action隔离及业务指纹不变。

受管目标：platform internal demo tenant / feature development，非控制库、非行业目录、非客户生产、非新演练库；project=`sc-local-dev`，db=`sc_dev_demo`，dbfilter=`^sc_dev_demo$`，filestore卷=`sc_local_dev_odoo_data`。复用既有账号和.env.dev凭据；不打印凭据、不创建数据或环境。不执行sync_demo，fixture/reset与全量快照跳过（不需要重置数据的定向检查）；主体迁移阶段未修改前端产品；复核后仅补通用空章节显示投影及定向验证，不重复UC1/UC2矩阵。

L3：`make local.dev.upgrade MODULE=smart_construction_core CODEX_NEED_UPGRADE=1` 首次通过且authority通过。首轮L4因脚本精确匹配必填标签而失败；现场同时发现缺少显式章节锚点，只有字段没有章节导航。P1展开匿名包装并补6个data-sc-anchor，说明页签含同源命名group；未修改P0。脚本改为稳定字段选择器，并对配置排序增加实际DOM坐标断言。仅受影响3项契约事务重验通过，二次视图升级及authority通过；原失败证据保留，未计通过。之后HTTP运行态仍返回旧节点路径/无锚点，先通过`local.dev.restart`及`local.dev.health`恢复运行前提，再继续定向观察。L5：待集中产品复核，当前不冻结、不运行Quick、不准备PR。

数据样本：证照记录id1／S85安全生产许可证登记，state=done；制度无可读样本。无合法草稿样本；零保存新建页内切换不能冒充已保存草稿编辑验收。制度查看态无样本明确记未覆盖，不造业务数据。

## 状态

本批自验通过，待集中产品复核｜本批未集成｜未部署｜89入口交付未完成。主线剩余44不变；本地已验证剩余42（666／862两个旧路径退出候选，尚未主线集成）。台账分别记录旧路径退出与低代码兼容，不把原生默认通过冒充所有配置能力验证。

原始结果：`artifacts/uc3-document-lowcode/`，只维护本记录并引用原日志；回退为本批三份XML恢复与受管升级，测试配置通过既有版本回滚并权威回读，不撤销业务记录。


## 本轮集中自验结果

| 入口／状态 | 页面结果 | 配置结果 |
|---|---|---|
| 666证照新建，1440×960 | 正式action列表可达；真实顶部、章节/来源导航、说明→附件→说明保留临时输入，未保存 | 正式“更多操作→表单设置”：改发证机构标签、同区域上移、加入配置发证信息组、隐藏办理结果；预览→发布→业务页刷新→回滚→页面恢复均通过 |
| 666已有id1，390×844 | 已完成查看态、分类字段可读；复核后空来源正文与导航同步省略，不伪造来源 | 低代码代表面为新建态，既有查看未另扩配置矩阵 |
| 862制度新建，390×844 | 分类锁定制度，证照/借阅/存档组不进导航；说明页签保留临时输入、来源及附件入口可用 | 同模型另一action的完整有效结构/字段策略/动作在666发布前后相同；桌面页面未出现配置标签 |
| 862已有查看／两入口合法草稿编辑 | 未覆盖：无可读制度样本、无合法草稿；未创建业务数据 | 不将隔离验证表述为862独立配置写入旅程通过 |

运行结果 `browser/designer-report.json`：ok=true、restored=true、browser_errors=[]。publication.published_content、final_contract、browser、isolation 分别passed。实际配置字段纵坐标为证照名称380、配置发证单位502、证照编号588，既验证树序，也验证视觉顺序。配置基线已恢复并回读，保留未发布草稿133供集中复核；不修改真实个人偏好。预览安全及编译器组合拒绝反例复用#483同机制证据，不重复注入。

首轮脚本的必填标签精确匹配问题、第二轮旧运行态问题及第三轮“只读空来源字段必须可见”的错误断言均保留原始日志。第三轮实际通过的证照新建页证据，在产品/契约/业务指纹未变情况下承接；只改观察器，继续未完成面。包装最终输出business fingerprints unchanged；升级前到最终回滚后的整模型write_date/state指纹也一致。

权限保留：`local.dev.test`精确执行共享反例方法1项通过，断言666仍允许发起人+配置管理员，862仅配置管理员；模型ACL发起人读/写/建、不可删，管理员读/写/建/删保持原值。未修改安全文件、动作定义、模型计算/日期/状态规则；未重新做低权限真实浏览器旅程，不把ACL核对称为全权限验收。

可打开现场（5174）：

- 证照正式入口：http://127.0.0.1:5174/a/666?menu_id=356
- 制度正式入口：http://127.0.0.1:5174/a/862?menu_id=708
- 证照样本：http://127.0.0.1:5174/f/sc.document.admin.document/1?action_id=666&menu_id=356
- 设计器草稿地址见`browser/designer-report.json.review.designer_url`；预览短时有效，过期可从该草稿重新签发，不必重新发布。

尚未覆盖：制度现有查看、合法草稿编辑、真实业务保存、自定义字段、跨区域编排。action777、退库能力、结算demo金额问题维持原独立状态。下一步仅集中产品复核；通过后才整理提交、生成预检、冻结、Quick、独立最终复核和下一PR。

B线只读复核：证据与本批`225a56bf… + dirty`一致，可交集中产品复核；不是最终验收批准。未要求或运行Quick。

[恢复设计器草稿133](http://127.0.0.1:5174/f/sc.document.admin.document/new?menu_id=356&action_id=666&activity_page_id=ap_mu3ox71y_tyl71o&config_mode=form_field_configuration&change_set_token=pjqAHmYdfOTV7FUY-daAevBwnPR6BBqU)，重新签发预览不需要发布配置。


## 产品复核后：空来源章节收口

用户已确认666既有窄屏、862新建分类及草稿133配置预览符合预期；仅要求修复空来源，未重复发布回滚。旧截图中空来源标题保留的问题明确作废，由本节定向结果替代。

归属P0 / 通用前端契约消费 / `canonicalNativeFormBridge`与`FormSection`：把既有只读事实空值判断提取为共用谓词，在推导正文及导航前应用同一显示投影。仅消除已被字段组件省略的空内容，不改变后端业务显隐或配置合成，不添加模型/字段名特判。关系组件、合法动作、notebook说明/附件保留，新建/编辑不走只读投影。P1/P2配置不能补偿通用容器空态，因此修复归P0；影响范围为只读原生表单的空字段容器。

验证边界：L1 `ci.local.iteration`通过；L2 `verify.frontend.canonical_form_presenter.unit`、`verify.frontend.native_section_navigation.unit`、`verify.frontend.typecheck.strict`通过，覆盖空/有值、0、false、动作、嵌套字段容器、新建及说明附件保留。L3复用既有运行环境，新增修复仅前端，无模块升级/数据重置需要。L4 `FORM_LOWCODE_TOPIC=document FORM_LOWCODE_DOCUMENT_EMPTY=1 make local.dev.form_lowcode.browser`通过：390×844证照id1空来源正文与导航均不可见，说明有内容，附件可切换，零浏览器错误、无横向溢出、真实顶部滚动位置为空。没有配置或业务写入，包装回读业务指纹未变。有来源值采用非模型特定单测反例；当前实库样本无来源值，不宣称做过有值浏览器验收。

原始日志：`empty-section-static.log`、`empty-section-targeted.log`、`empty-section-browser.log`；结果与三张完整视口截图：`browser/empty-section-report.json`、`empty-source-narrow-{top,notes,attachments}.png`。主体默认/配置新建旅程的XML、后端与运行输入未变，新的显示投影仅readonly；沿用`designer-report.json`，不重跑A→B→A。此前后台测试、动作ACL核对及升级结果继续有效；证照旧空来源截图库不承接。

本批状态：主体产品复核通过，空章节修复定向自验通过，进入最终集成准备；未主线集成、未部署、89入口交付未完成。主线44、本地42保持。制度查看、合法草稿编辑、多角色浏览器、实际保存、自定义字段/跨区域编排仍未覆盖。


### 冻结准备与承接

`make ci.delivery.freeze.prepare`已通过，更新组件接管清单的inputDigest及复杂度报告中FormSection行数1353→1347；生成证据预检与7项守卫通过。计划提交按P0显示机制、P1默认迁移、P4观察工具与本记录划分，保持同一分支/产品批次。最终完整HEAD、Quick receipt、独立复核及归档哈希保存在既有外部证据目录，不为写入回执再改冻结代码。

影响承接：主体浏览器证据绑定`225a56bf… + dirty`，不能冒称冻结HEAD直接运行。与最终候选相比，后端XML/模型/低代码机制/新建态产品输入不变；补丁只改变readonly空内容投影（已补空/有值单测与现有窄屏），其余差异为测试观察器、记录和生成摘要。旧来源空标题画面不复用。最终Quick和独立复核绑定冻结完整指纹；原结果、受影响补验、最终身份分别保留。
