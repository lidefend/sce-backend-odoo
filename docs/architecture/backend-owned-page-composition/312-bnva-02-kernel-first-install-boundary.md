# 312 · BNVA-02 Kernel First-install Boundary

| 检查 | 结果 |
| --- | --- |
| sc_clean 全新安装 `sc_norm_engine` | PASS（exit 0） |
| product_release 配置 | 140 条 |
| 预置用户低代码配置 | 0 条 |
| clean namespace → sc_clean | PASS（`ns_c6fed472e939`） |
| demo/platform 命名空间 | 未回归（demo→404，绑定不变） |
| fixture_role_finance 登录 | PASS（uid 6，非管理员） |
| 发布门禁修复后重新安装 | PASS |

## 结论

首次安装不依赖预置用户低代码配置，产品默认配置独立成立。
