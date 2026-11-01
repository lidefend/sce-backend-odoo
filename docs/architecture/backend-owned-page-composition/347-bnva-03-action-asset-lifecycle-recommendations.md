# 347 · BNVA-03 Action Asset Lifecycle Recommendations

## 原则

一个 Action 可以没有独立菜单，但必须有可解释的存在理由、调用来源与权限边界。
区分 Navigation Entry（主动进入）与 Invocation Entry（按钮/上下文/向导触发）。

## 建议

- 对 Odoo 标准模块动作：不纳入 Smart Construction 导航治理，保持 Odoo 原生调用语义。
- 对 17 个 smart_construction_core 动作：做同文件引用核对；确认上下文调用的保留，确认真正孤立的
  在 BNVA-03-05 登记为生命周期待清理，不立即删除。
