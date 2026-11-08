# Smart Core 分类投影 Token 失效回归测试

## 缺陷分类

- Owner：`validation_tool_defect`
- 文件：`addons/smart_core/tests/test_load_contract_response_cache.py`
- 原问题：变更记录缺少 `name`，生产 Token 构造抛错后被外层捕获为 `""`。
  原 `assertNotEqual` 只证明“正常 Token != 空字符串”，未证明目标字段变化生效。

## 修复

- 变更记录完整携带 `name`。
- `form_policy_json`、`required_fields_json`、`default_values_json` 分别独立测试。
- 每个用例断言 before/after Token 都非空且不相等。
- `name` 独立变化继续验证失效。
- `sequence`、`note` 非投影元数据继续验证 Token 稳定。

## 验证

- `python3 addons/smart_core/tests/test_load_contract_response_cache.py`：PASS，53 tests。
- `make verify.business_config.formal_list.unit`：PASS，283 tests。
- `make verify.agent.ledger.unit`：PASS，18 tests。
- `make ci.local.iteration`：PASS，2/2 required targets 非零执行。

三个投影字段测试都断言：

- 变更前 Token 非空；
- 变更后 Token 非空；
- 两个 Token 不相等。

因此不再把“Token 构造异常后返回空字符串”误判为目标字段失效。

## 边界

- 不修改生产缓存实现。
- 不修改 Contract V2、权限、前端或运行环境。
- 不部署。
