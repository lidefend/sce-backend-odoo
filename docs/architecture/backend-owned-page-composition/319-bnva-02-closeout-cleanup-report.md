# 319 · BNVA-02 Closeout Cleanup Report

## 临时角色撤销（uid 7）

- login：`fixture_role_finance_dependency_creator`。
- 撤销前权限：project.project read+create、res.partner read+create、project.task.type read+create。
- 撤销后：project.project / res.partner create=false；账号 active=false；已移出临时组，仅保留 base 隐含组；is_admin=false。
- 未删除账号、联系人、组或 ACL。

## Fixture 密码轮换

- uid 6 `fixture_role_finance`：密码已轮换并重新验证登录通过。
- `SC_DEPENDENCY_FIXTURE_PASSWORD`：已从 `.env.local.clean` 移除（uid 7 已停用）。
- `.env.local.clean` 保持 mode 600，不输出明文。

## 环境保留

- sc_clean 保留，业务记录仍为 0（project.project / project.task.type / 三个财务模型）。
- P4 artifacts 保留。
