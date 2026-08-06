# Formal Action Runtime Drift Root Fix — Batch-FA-RD

## 1. 本轮变更

- 目标：消除日常开发库正式业务 action 的运行时漂移，并把同类错误固化为可失败回归。
- 完成：施工合同 action 绑定用户确认树；补齐施工合同和工程进度收款关键列；移除
  `tender.guarantee` 上不存在字段的 domain；把材料历史列表的“必须有 fixture”断言改为
  历史源与正式投影数量一致断言；统一进项税额上报名称权威。
- 未完成：日常开发服务器升级与最终正式发布门禁结果将在部署批次后补录。

## 2. 影响范围

- 模块：`smart_construction_core`、`scripts/verify`。
- 启动链：否。
- contract/schema：不改变 public contract 或数据库 schema；改变 P1 action/view 数据记录。
- 路由：否；action XMLID 与菜单绑定保持兼容。

## 3. 风险

- P0：无。
- P1：后加载 XML 若再次改写 action 或列顺序会导致正式办理面漂移；运行时审计与源级测试阻断。
- P2：历史源和投影都为空的租户不再被误报为失败；两侧数量不一致仍严格失败。

## 4. 验证

- 源级：`python3 -m unittest scripts.verify.test_formal_action_runtime_drift_audit`。
- 代码：`python3 -m py_compile scripts/verify/formal_action_runtime_drift_audit.py`。
- 运行时：模块升级后执行 `make verify.formal_action.runtime_drift.audit DB_NAME=sc_demo`。
- 发布：最终执行 `make release.daily_dev.acceptance.publish DB_NAME=sc_demo`。

## 5. 产物

- 运行时报告：`artifacts/backend/formal_action_runtime_drift_audit_v1.json`（部署后生成）。
- 日常验收日志：部署批次保存到 `.runtime/final-acceptance/daily-deployed/`。

## 6. 回滚

- commit：以本批次最终提交 SHA 为准。
- 方法：恢复前一源码提交后，通过受控 `make mod.upgrade MODULE=smart_construction_core DB=sc_demo`
  重放上一版 XML；本批没有 schema 或业务数据写入。

## 7. 下一批次

- 目标：在配对备份后升级日常 `sc_demo`，复跑正式 action 漂移审计和日常发布验收。
- 前置条件：精确数据库过滤、filestore 身份、服务器源码 SHA 和备份证据全部确认。
