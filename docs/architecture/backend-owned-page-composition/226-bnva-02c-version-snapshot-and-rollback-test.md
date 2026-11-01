# 226 · BNVA-02B-02C-02B-03B · 版本快照与回滚测试

## 设计

复用 `ui.business.config.contract.version`（append-only）+ `restore_published_version`；
target digest 不匹配 → restore。离线测试覆盖；真实数据库恢复留待 03C。

## 状态

离线 PASS；真实 DB `not_run`。

