# 产品配置菜单入口修复

基线 86c03b7a3a502028e5ad656f7c8cb34fd3bedff4，复用已收口P1工作树。P1 owns industry entry declaration; P0 owns generic published navigation; P4 owns bounded diagnostics/deployment. No frontend hard-coded visibility or role-name authorization. Preserve unrelated dirty worktrees. First inspect actual menu/action/role/publication facts; select owning-layer fix only after attribution.

## 归因与范围

日常服务器86c03b7a3/sc_demo：wutao(uid39)、demo_full(uid60)拥有business_full及业务配置组，菜单432、父310/304均active，action111已声明/admin/menu-config。标准版快照6(page_count90)无此入口；预览版快照7(page_count129)包含正确入口。唯一P1源声明为preview，故修改为released并由contract.product_menu.generate生成五个投影资产。未修改角色、ACL、前端产品逻辑或业务事实。

P4验证补充现有发布守卫必需菜单集，以及复用daily环境、既有fixture_role_config_admin凭据的只读点击探针；实际business_full另以wutao的权威导航回读验证。只读浏览器允许已有导航遥测，不做配置保存或业务写入。

风险低：只将已经可用的配置入口纳入标准发布面，原权限仍生效。L1→L2→定向发布及L3/L4，不全量重跑页面。无需模块升级/seed/前端重建。恢复为旧源码并经同一发布工具重发旧声明，原快照6/7保留可审计。

定向RED确认标准缺入口、预览标记不符；修正后发布契约9、单调性6、原生清单2项通过。

## 日常运行验收

产品候选0f896044afe9364ad86266d829dbe4282905071b已通过受管bundle同步、仅demo职责refresh、published_face.converge。模块升级为空（没有模型/XML/Python变更），无seed、无前端重建、无业务数据改写。发布standard91、preview129。发布入口显式使用已登记/opt/projects/secure/daily-runtime-duties/sc-demo-dev.env。刷新摘要必须采用远端managed binding合并后的规范化声明摘要；前两次错误摘要均在写入前被拒绝。首次发布使用旧默认.env.dev未到达发布守卫，权威只读回读确认快照仍为6/7；修正为职责env后成功。

只读事务验证wutao(uid39)、demo_full(uid60)：标准导航含432菜单、目标/admin/menu-config，面板均110项；demo_readonly(uid58)无入口且AccessError拒绝读取。原始证据在.runtime/menu-entry/principal-readback.json及脚本、日志。直接handler回读不等同HTTP登录；浏览器另使用既有fixture_role_config_admin验证侧栏点击、面板HTTP200/ok=true/非空、刷新后同样成功，5项PASS，errors/blocked均空。

独立复核确认发布态变更无权限扩大、投影一致；要求补充面板响应断言，现已补齐并实测通过。浏览器定位由同名heading改为h1，仅探针变化。证据绑定0f896产品源码+未提交增强探针，不冒充原提交含增强断言。

批次产品检查：所报缺口已修复且日常部署验证通过；主线尚未集成。当前P4探针/文档变化不影响部署产品输入，复用上述运行证据。未执行全量浏览器矩阵或完整Quick（本次定向迭代验收，未声明冻结发布）。记录不覆盖用户其他产品反馈。
