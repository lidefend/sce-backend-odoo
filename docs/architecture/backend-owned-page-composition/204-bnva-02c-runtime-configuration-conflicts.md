# 204 · BNVA-02B-02C-02A · 运行时配置冲突

## 冲突类别

- 同一精确作用域多条 active：合法（不同 priority/version 由 apply_order 解析），
  但缺可追溯记录。
- 同层竞争（同为 industry_standard 或同为 tenant_lowcoding）：由 priority/version/id
  定序，后应用者覆盖先应用者。
- generated_baseline(10) vs industry_standard(20)：industry 覆盖 generated。
- user_preference(30) vs tenant_lowcoding(40)：lowcode 覆盖 preference。
- 同版本不同 payload：definition_sha256 不同则生成新版本，不会同版本并存。

## 治理建议

- 不新增唯一约束（不同作用域多条合法）。
- 对“同一精确作用域重复 active”产生可追溯诊断；合法覆盖记录 apply_order 结果，
  非法竞争（同层同作用域同 priority 但不同 payload）产生诊断。

