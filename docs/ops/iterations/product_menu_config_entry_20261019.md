# 产品配置菜单入口修复

基线 86c03b7a3a502028e5ad656f7c8cb34fd3bedff4，复用已收口P1工作树。P1 owns industry entry declaration; P0 owns generic published navigation; P4 owns bounded diagnostics/deployment. No frontend hard-coded visibility or role-name authorization. Preserve unrelated dirty worktrees. First inspect actual menu/action/role/publication facts; select owning-layer fix only after attribution.

## 归因与范围

日常服务器86c03b7a3/sc_demo：wutao(uid39)、demo_full(uid60)拥有business_full及业务配置组，菜单432、父310/304均active，action111已声明/admin/menu-config。标准版快照6(page_count90)无此入口；预览版快照7(page_count129)包含正确入口。唯一P1源声明为preview，故修改为released并由contract.product_menu.generate生成五个投影资产。未修改角色、ACL、前端产品逻辑或业务事实。

P4验证补充现有发布守卫必需菜单集，以及复用daily环境、既有fixture_role_config_admin凭据的只读点击探针；实际business_full另以wutao的权威导航回读验证。只读浏览器允许已有导航遥测，不做配置保存或业务写入。

风险低：只将已经可用的配置入口纳入标准发布面，原权限仍生效。L1→L2→定向发布及L3/L4，不全量重跑页面。无需模块升级/seed/前端重建。恢复为旧源码并经同一发布工具重发旧声明，原快照6/7保留可审计。

定向RED确认标准缺入口、预览标记不符；修正后发布契约9、单调性6、原生清单2项通过。
