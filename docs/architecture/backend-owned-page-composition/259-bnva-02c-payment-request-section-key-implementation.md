# 259 · BNVA-02C-02B-03 · payment.request Section Key 实施

为 `payment_request_receive_productized_form_v1` 的 7 个 section 补充稳定 key：
processing_main / project_contract / request_amount / payment_account /
settlement_match / note_attachment / source_audit。

未改变 fields 与业务分组；保持 `identity_fields=['name']`。结构完整性校验零诊断。

