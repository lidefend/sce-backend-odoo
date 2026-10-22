# Daily Runtime 首版部署记录（2026-10-22）

## 1. 身份

- 部署目标：`sc-root` 日常开发服务器
- 服务面：`/t/demo`，database `sc_demo`，duty `demo`
- Candidate：`9734b5c6a687e3d1f2e3e6351d28de36d709f143`
- 基线：`74063688e928d25c8e65037ac3306956c954244d`
- 平台控制面：`sc_platform_control`

## 2. 变更

- 同步日常服务器代码树到 main `9734b5c6a`。
- 刷新 source revision、前端构建、demo/platform-control duty 环境和发布面。
- 前端构建：
  - fingerprint：`eebec2bfc2888c3248dda7e0b49a5a759a68e3c293711c758b3afc8ebb39035a`
  - entry asset：`index-B4UeQRQJ.js`
- 发布面：
  - `construction.standard` snapshot 11
  - `construction.preview` snapshot 12
- P4 修复：
  `daily_runtime_published_face_converge.py` 在父 Make 环境中移除由裸 `export`
  冻结的三项递归变量，避免子 Make 丢失 duty、entry digest 与 expected SHA 参数。

## 3. 验证

| 层 | 命令/检查 | 结果 |
|---|---|---|
| L4 | `daily.runtime.main.bundle_sync` | PASS |
| L4 | `daily.runtime.frontend.build` | PASS |
| L4 | `daily.runtime.database.duty.refresh`（demo + platform_control） | PASS |
| L4 | `daily.runtime.published_face.converge` | PASS |
| L4 | `daily.runtime.entry.verify` | PASS |
| L4 | `/t/demo/api/runtime-version` | PASS，`git_sha=9734b5c6a`，前端 fingerprint 已刷新 |
| L4 | 业务全功能账号 `wutao` startup smoke | PASS |
| L4 | 财务角色 `demo_finance` startup smoke | PASS |

两个角色均通过 `login → system.init → my.work.summary`，`role_surface`、
`default_route`、`capabilities`、`navigation` 均存在。

## 4. 证据

- `.runtime/final-acceptance/daily-deployed/bundle-sync.json`
- `.runtime/final-acceptance/daily-deployed/frontend-build.json`
- `.runtime/final-acceptance/daily-deployed/database-duty-refresh.json`
- `.runtime/final-acceptance/daily-deployed/published-face-converge.json`
- `.runtime/final-acceptance/daily-deployed/entry-verify.json`
- `.runtime/final-acceptance/daily-deployed/database-duty-plan-9734.json`

## 5. 回滚

- 代码：恢复上一 main/deployed SHA `74063688e`。
- 数据库恢复点：
  `/data/backups/daily-demo-dev/sc_demo-20261021T141845Z-3acc5f5b/database.dump`
  已由升级入口验证。
- 前端：恢复上一构建指纹 `c3350f412cabdfb7afeeaf26bf70dccdd3aab05e30b69828132eea99d3e69bbb`。
- duty env 在刷新前保留受管备份，并由入口在失败时自动恢复。

## 6. 未完成边界

- Preview 激活已完成（2026-10-22 收口）：
  - `smart_construction_bundle` startup hook 改为读取 carrier 参数
    `smart_construction_bundle.product_key`（XML 种子默认 `construction.standard`）。
  - 受管 `daily.runtime.duty.edition_release.remote_select` 将 demo duty 的
    startup edition 切换为 `construction.preview` 并回读验证。
  - `wutao` 导航权威 `primary_actions` 90 → 130；三个 preview 财务入口
    （收付款台账 / 资金台账 / 结算单）全部 `READY`，`demo_readonly` 仍
    `PERMISSION_DENIED`。
- 远端产品树当前为 detached candidate `dbeb09cf6`，待 fix 分支合入 main 后切回 main。

## 7. 结论

- 批次验收：不适用
- 首版部署：完成（`9734b5c6a` 已服务）
- 主线上仍保持 `9734b5c6a`
- 用户验收：启动链通过；preview-only 财务入口已激活并通过角色允许/拒绝冒烟
- 回滚：可用
