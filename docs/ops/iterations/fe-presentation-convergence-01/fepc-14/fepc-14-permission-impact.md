# FEPC-14R：权限影响与实施边界

推荐 A，不新增角色、不改变公司范围，不改 ACL/record rule。依据及基线见 [只读路径评估](fepc-14-readonly-path-assessment.md)。

## A 的权限要求

- 项目必须存在且对当前用户/公司可读；遵守正常 business scope、ACL 和 record rules，不用 su_env/sudo。
- `sc_get_stage_requirements` 已显式检查项目 read 权限和记录规则；要求项 search/字段访问继续使用当前 env 权限。
- `sc.project.stage.requirement.item` 的 project_read ACL 为只读；管理员、业务配置管理员和项目经理还有各自权限。不能通过隐藏按钮取代后端拒绝，也不能把这些管理权限赠给阅读用户。
- 要求项是按阶段定义的配置，不是 project_id 外键关系。必须先取得已授权项目再由服务端派生阶段；不能让任意阶段参数替代项目访问控制。
- 要求项模型未声明 company_id；不能杜撰“按公司分配要求项”的现有规则。公司限制首先来自项目访问上下文，后续仍需负向测试实际部署的记录规则。
- 当前数据库所有规则及字段 groups 未做全库盘点；未知不视为已验证。字段不可读须沿原机制拒绝，不换管理员读取完成度依赖字段。
- 当前 execute_button 对未登记为只读导航的方法默认检查 write；该方法未在项目类登记只读导航。若仍复用该 intent，必须明确采用既有只读方法登记还是薄查询入口，不能为解决 wizard create 拒绝而全局改默认权限。

## B 后备，不申请执行

只有 A 无法满足经批准的查看职责、且临时快照被证明必需时，才重新提出 B。
潜在最小对象为 `sc.project.stage.requirement.wizard` 的 create/read，**不是** project.project 或要求项配置模型的写权限。
项目阅读能力组是否适用必须另行批准，不能自动把 business_full 当成 ACL 组。

B 还须同时证明：

1. 创建只接受当前用户可读项目，阶段从项目取得，拒绝伪造 project/company/stage 与明细；UI readonly 不是服务端约束。
2. TransientModel 的创建者隔离、项目 record rules、跨公司与跨用户访问均经实际测试，不假定“临时模型天然安全”。
3. 父向导只读与明细当前已有 CRUD ACL 分开评估，禁止借明细直接创建/修改绕过父级限制。
4. default_get 能正确建立明细，不用放权掩盖初始化缺口；异常不能返回空成功。
5. action_go 的目标访问权限继续由既有链校验；不对任意 action_xmlid 开放执行。

本轮没有证明必须采用 B，也没有建议具体新增 ACL 行。未来若选择 B，需先提交明确角色、公司和字段约束后的权限差异再审批。

## 本轮实际影响

仅 GET runtime-version；未登录、重放 execute_button、创建临时记录或运行 SQL/初始化。
只新增决策文档、更新现有任务元数据。产品代码、业务配置、权限和业务数据均未修改。
FEPC-13、F1、DATA-01、CFG-01B、PFL-035 不在本轮范围内；未执行付款能力或写流程测试。
