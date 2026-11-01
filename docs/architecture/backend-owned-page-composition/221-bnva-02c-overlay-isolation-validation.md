# 221 · BNVA-02B-02C-02B-03A · 租户覆盖隔离验证

## 验证点

- tenant_lowcoding payload digest。
- user_preference payload digest。
- company_id / action_id / view_id / role_key。
- Resolver 最终选择结果。

## 结论

- `run_migration` 只锚定 module+external_id 种子，不写租户覆盖。
- 离线测试覆盖 tenant_lowcoding / user_preference / 退役跳过。
- 真实前后实测留待 03B/03C（隔离库 + 升级模拟）。

