# Draft PR：明细操作与追溯职责收口

## Summary

本 PR 收口付款申请的主编辑/追溯字段职责，并统一共享 x2many 操作表达：O2M 子记录删除显示“删除”，M2M 关系移除显示“解除关联”，未保存新行只取消本地草稿，原生 `delete="0"` 继续禁止删除。

同时修复正式收款申请入口在后端治理来源中遗漏 `formPresentationMode`、以及原生 create/edit/delete 能力没有完整收紧到 relation policies 的通用缺口。前端 Schema 继续 fail-closed；没有全局 task 默认、付款模型特判或协议改写。

## User-visible results

- 付款依据只有一处主编辑入口；已付/未付金额只在履约追溯查看，明细来源列保留。
- 持久化 O2M 删除、撤销及未保存新行取消使用与实际命令一致的文案。
- M2M 附件可在桌面和移动端“解除关联”；放弃恢复关系，保存不删除附件对象。
- 原生 `delete="0"` 入口不再出现删除或新增入口，仍保留权威允许的内联编辑。
- action 690/menu 360 收款申请不再因空的 presentation mode 在渲染前失败。

## Architecture and scope

- P1：付款申请原生 occurrence 与字段业务归属。
- P0：通用 form presentation 归一、native x2many capability 保真及共享 relation operation 表达。
- P4：在既有 local.dev payment fixture 生命周期中增加明确拥有的合成 M2M 关系及一次受管保存/回读/复位。
- 不改金额、权限、审批、保存协议、付款登记或会计写入；不创建新数据库/环境/通用 fixture 平台。

## Verification

- `make ci.local.iteration`：PASS，16 tests。
- P0 presentation、native capabilities、共享 detail collection 与 adapter guard：非零 PASS。
- 新增 P4 生命周期守卫：选择并实际执行 1 个测试方法，失败/错误 0。
- 冻结前责任预算 guard 首次准确阻止 4317 行 handler；复用既有 projection helper 后恢复为 4312 行，guard、精确 1 个 presentation 方法及 L1 16 项通过，没有抬高预算。错误的宿主包调用在收集期执行 0 个方法，不计入覆盖。
- action 690/menu 360、记录 10：1088×791 与 390×844 零写入检查；权威 XML 为 inline edit=true、create=false、delete=false，页面保持该能力组合。
- M2M：action 809/menu 559、`payment.request.attachment_ids`；1088×791 与 390×844 的解除关联/放弃均零 write 且恢复。
- 唯一一次真实保存协议为 `[[3, 16878]]`；权威回读确认附件 16878 仍存在，fixture reset 后关系恢复。证据绑定产品源候选 `ca5a2e0f685cc3584390b5ff0d962810befbf116`、Tree `64c2c512ad1507f0cf5ca7313d795cb1a650c40f`、完整指纹 `5227b6dd75077795a25c0b8ee9f6c4721d0e4da6f05477b76ddfa406ca047cf3`。
- 最终生成证据、Quick receipt 与交付 HEAD 在冻结后登记，不为回填结果再次修改产品候选。

## Evidence and limits

- 迭代报告：[detail_trace_responsibility_normalization_20260915.md](detail_trace_responsibility_normalization_20260915.md)。
- M2M exact-head：`artifacts/playwright/local-dev-payment-attachment-m2m-journey/`。
- delete=0 旧摘要误取同页最后一个关系契约，因此只复用截图、零写入与控件结果，不用其 sourceAuthority 字段证明主表单契约。
- 621/O2M 已通过证据按未受影响实现复用，不重复运行。
- 未执行审批、付款登记、会计写入、全角色、生产数据或完整业务矩阵。

## Delivery status

`READY_FOR_FREEZE_PREP`。独立只读复核未发现 S0/S1/S2 阻断；完成生成证据刷新并提交后冻结最终 HEAD，只运行一次 exact-head Quick。远端 push、PR、Ready、合并、部署、发布和历史分支清理不在当前授权范围。
