# 318 · BNVA-02 Closeout Final Plan

## 结论

CLOSEOUT-01 只读审计完成：变更边界清晰，临时环境未污染业务数据。

## 提交准备顺序（待授权后执行）

1. A · P0 发布门禁修复及测试。
2. B · P4 local.clean 环境/入口工具。
3. C · P4 验收证据。
4. D · 内核收口文档 + run record。

## 临时环境处置顺序（待授权后执行）

1. 撤销 uid 7 create 授权（revoke，不删角色/数据）。
2. 核验 fixture_role_finance 权限回退。
3. 轮换/撤销 fixture 密码，保留 SC_SOURCE_REVISION 与 clean 入口变量。
4. 保留 artifacts 与 sc_clean。

## 禁止

不提交秘密、临时产物或非版本控制文件；不 reset/clean/stash 丢弃证据。
