# 84 · Phase 4H-02A Acceptance

## Verdict

READY_WITH_CONSTRAINTS

## 证据获取能力总表

| 项目 | 能力状态 | 说明 |
| --- | --- | --- |
| 运行时 Contract 获取 | READY_WITH_CONSTRAINTS | 经前端 API Client 可获取；直连需入口注入头 |
| PC-007 DOM 观察 | READY_WITH_CONSTRAINTS | Playwright 运行时 + 项目详情脚本存在，需新增观察脚本 |
| PC-008 权限身份 | READY_WITH_CONSTRAINTS | 多角色 fixture 身份存在，含负样本，未执行测试 |
| PC-009 旧消费者回归 | NOT_VERIFIED | 无既有测试入口，需新增 |
| PC-010 历史身份 | NOT_VERIFIED | Git 历史可用，缺历史快照/映射 |

## 关键事实

- 本轮登录成功但契约抓取失败根因：`/api/` 路径缺少入口注入的
  `X-SC-Namespace` 头（`entry_guard.enforce_entry_namespace`）。
- 浏览器自动化与多角色 fixture 均已存在，具备补齐 PC-007/PC-008 的基础。
- `old_consumer_regression` 测试需新增，PC-010 需历史快照，均不在本轮解决。

## 下一批最小可执行任务（4H-02B，待授权）

1. P0：新增并运行旧消费者只读回归（PC-009）。
2. P1：新增项目详情 DOM 观察脚本，区分调用/消费/进 DOM 三阶段（PC-007）。
3. P1：用 pm 与 partner_manager/system_admin 身份执行只读权限对比（PC-008）。
4. P1：从 Git 历史提取 1776/944 身份演变，建立 before/after 映射（PC-010）。

## 边界

只读核查；未改业务代码、认证配置、ACL、用户角色、数据库、assembler、Guard；
未删 Legacy fallback、未迁移页面、未重建 Candidate。工作树未提交改动保留。
