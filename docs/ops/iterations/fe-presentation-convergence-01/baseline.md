# FE-PRESENTATION-CONVERGENCE-01 基线

状态：只读基线核查，未修改产品代码、契约、配置或数据库。

## 权威身份

| 项 | 值 |
| --- | --- |
| 权威主线 | `f9a291ae7d00d0fbb82fef43bd0e3d3ced77028e` |
| GitHub main | `f9a291ae7d00d0fbb82fef43bd0e3d3ced77028e` |
| 本地 main | `f9a291ae7d00d0fbb82fef43bd0e3d3ced77028e` |
| Gitee main | `f9a291ae7d00d0fbb82fef43bd0e3d3ced77028e` |
| Demo 服务 source_revision | `3f46dd7eba9f351386fee446151ee9eb545d56a4` |
| Demo 前端构建指纹 | `5690cde92298c32cb9e5e2c578380fe17e07bd7af21944bf72a42dbe577b027a` |
| product_version | 见权威 VERSION 文件（runtime-version 返回） |
| database / environment | `sc_demo` / `demo` |
| 主仓库当前分支 / HEAD | `fix/fe-ux-entry-continuity-01` / `88b4c1609eb2802f95a0b367a44efffd985db173` |
| 主仓库工作区状态 | 干净（无已跟踪变更，无未跟踪文件） |

## 关键结论

- 主线 `f9a291ae` 与 Demo 服务 `3f46dd7e` **不相等**：`f9a291ae` 在 `3f46dd7e` 之上仅追加文档
  （#744-#751），产品代码一致。前端审计以 Demo 服务实际运行的 `3f46dd7e` 为运行基线。
- 三方 Git（GitHub / 本地 / Gitee）一致，无漂移。
- 工作区未发现未登记变更；未执行任何清理。

## 核查环境

- 服务：`http://1.95.85.92:18081/t/demo`
- 观察账号：`demo_full`（主）、`demo_role_project_manager`、`demo_role_project_a_member`、`demo_role_owner`
- 浏览器：Chromium headless，桌面 1440×960 / 移动 390×844
- 方式：只读页面访问与 DOM 测量，无写入、无业务动作

## 交付物

- [findings.json](findings.json)：逐项问题与证据
- [component-map.md](component-map.md)：页面、契约、运行时与公共组件映射
- [demo-data-gaps.md](demo-data-gaps.md)：影响展示的 Demo 数据缺口
- [evidence-index.md](evidence-index.md)：截图与证据索引
