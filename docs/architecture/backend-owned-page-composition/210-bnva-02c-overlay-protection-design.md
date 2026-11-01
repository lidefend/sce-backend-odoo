# 210 · BNVA-02B-02C-02B-01 · 用户 Overlay 保护

## 保证

- tenant_lowcoding 是独立记录，migration runner 只锚定 external_id/module 的代码种子，
  不写用户覆盖记录。
- 种子升级只改变产品默认，用户覆盖按现有 layer/scope 规则继续解析（40 > 20）。
- 用户停用/删除覆盖自动回落产品默认。
- 种子迁移不重置用户覆盖的来源戳；不发生跨公司污染。
- 不新增第三套 Overlay 表达。

## Dry-run 结论

模拟 `tenant_overridden_seed` 升级：`outcome=migrated_new_version`，
`tenant_override_touched=False`。

