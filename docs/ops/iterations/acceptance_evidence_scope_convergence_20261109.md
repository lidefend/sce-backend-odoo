# ACCEPTANCE-EVIDENCE-SCOPE-20261109

状态：verification_pending

## 目标

把迭代、取证、集成、发布四段流程统一为：

1. 迭代：只运行受影响静态检查和定向测试。
2. 取证：只有契约语义或实际消费代码变化，才选择对应 runtime suite。
3. 集成：普通 PR 使用当前 exact-head 远端门禁。
4. 发布：deployment-only suite 只在部署阶段执行。

代码绑定证据以 suite 输入指纹、证据字节和受管环境身份复用，不以自然时间过期。

## 调整

- 通用 `frontend/**` 由 `frontend_contract` 承接，不再默认要求 list-surface 浏览器证据。
- 通用 `smart_construction_core/**` 由 `backend_contract` 承接，不再默认要求 list/relation 浏览器证据。
- 新增真实消费面规则：
  - Contract Form consumer -> `frontend_contract` + `frontend_presentation`
  - list consumer -> `frontend_contract` + `list_surface_structure`
  - relation consumer -> `frontend_contract` + `relation_roundtrip`
- 验收工具、schema、harness 和普通配置只要求其契约检查。
- 产品 runtime config、显式 list/relation probe 和实际消费者仍保留相应 runtime suite。
- `daily_runtime_entry`、`path_namespace_identity` 继续只在 deployment stage 要求。
- 删除 `evidence_max_age_hours=72`；旧证据只要输入和证据字节未变即可复用。

## 不变边界

- exact-head、PR base/head、suite input fingerprint、证据文件哈希和 adapter 断言不变。
- contract/consumer 输入变化仍使对应 suite 失效。
- 普通 PR 不继承旧 SHA 的远端成功。
- 合并不等于部署，部署不等于产品交付。

## 验证

- `make verify.acceptance.evolution.binding`：PASS，71 tests
- `make verify.validation.delivery.unit`：PASS，89 tests
- `make verify.frontend.dev.incremental.unit`：PASS，94 tests
- `make verify.agent.resume.unit`：PASS，56 tests
- `make verify.agent.ledger.unit`：PASS，18 tests
- `make ci.local.iteration`：PASS，affected exact set executed 5/5

## 下一步

审查并提交 P4 候选；随后清理已合并工作树，仅保留主线/产品主工作树和必要的环境 lane。
