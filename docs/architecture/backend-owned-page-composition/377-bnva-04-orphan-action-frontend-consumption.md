# 377 · BNVA-04 Orphan Action Frontend Consumption

17 个孤立 Action 均无菜单，因此无前端路由消费者，也不会被 Vue 直接导航。它们的业务用途需
结合其模型消费面判定：

- 项目预算/资料/人力薪资：对应模型已有统一入口或 productized contract，子 Action 是合并候选。
- 付款往来单位：被资金执行流程取代，退役候选。
- 成本/材料/关系/变更：模型多为汇总/事实/中间对象，非 Vue 主页面，NOT_VERIFIED。
