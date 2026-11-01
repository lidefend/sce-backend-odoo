# 371 · BNVA-04 Business Capability Map

Business Domain → Capability → Model → Process → Navigation → Product Page 的关联已建立：

- 项目管理：立项/台账/执行/变更 → project.project（继承）+ sc.general.contract / sc.construction.diary / sc.site.variation。
- 资金财务：付款/执行/收款/结算/成本 → account + sc.payment.execution / sc.receipt.income / sc.settlement.order。
- 采购：申请/询价/订单 → purchase + sc.material.purchase.request / sc.material.rfq。
- 材料设备：计划/出入库/设备 → stock/product + sc.material.inbound/outbound / sc.equipment.*。
- 劳务：计划/人员/考勤/结算 → hr + sc.labor.*。
- 合同分包：合同/申请/执行/结算 → project/account + sc.subcontract.*。
- 行政资料：资料/档案/质量/安全 → project/mail + sc.document.*。
- 经营分析：预算/成本/进度/指标 → account/analytic + sc.*.report/summary。
