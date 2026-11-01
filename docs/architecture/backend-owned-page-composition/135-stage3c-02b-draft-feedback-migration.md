# 135 · BNVA-019 Stage 3C-02B-03 · draft_feedback 迁移

## 判定

`draft_feedback._native_layout`（get_view + fromstring）只由 `evaluate` →
`_assemble_contract` 触发，`evaluate` 是反馈评估的独立请求，不共享页面装载
请求的 Carrier。

页面装载期间创建的 `ControlledDraftProof` 只调用 `native_advisory.validate_binding`
（消费已组装契约），不调用 `_native_layout`，无重复 get_view。

## 处理

不迁移到 Carrier。保持当前用户 get_view；保留 View 身份校验与字段访问控制。

## 结论

独立请求的合法解析，非重复；无需代码改动。

