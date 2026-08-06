# M4 菜单治理运行时闭环

## 结论

M4 在隔离验收库 `sc_frontend_acceptance` 完成。最终产品代码锚点为
`a85740c453a01e167faeaaf59c9fad9d74cc3e81`，未使用日常开发库或生产库，未写入真实业务数据。

- 冻结资产：22 个 XMLID，运行时解析 22/22。
- 重复 `<menuitem>`：16 组降为 0；声明数与唯一 XMLID 数均为 304。
- 兼容性：22 个资产的 action、groups、sequence、名称、父级、角色/公司可见性前后不变。
- 浏览器：8 个夹具角色 × 1440/390 两个视口，共 16 组；真实 `system.init` SHA 精确匹配。
- 浏览器错误：console 0、pageerror 0、API 非预期错误 0、页面横向溢出 0。
- 前端、权限、路由和业务接口未修改。

## 未实施候选及裁决

以下 6 项继续作为静态启发式候选保留，不作为 P0/P1 产品缺陷：

- `menu_sc_leave_request`：名称属于已冻结正式产品术语；本轮不启动术语基线变更。
- `menu_sc_material_stock_statistics_report`、`menu_sc_project_manage`、`menu_sc_project_wbs_cost`：未进入当前角色的发布导航。
- `menu_sc_settlement_adjustment`、`menu_sc_settlement_order`：Odoo 原生树为四级，但正式发布导航已归一化为“财务中心 / 结算管理 / 页面”三级；不得反向修改业务父级制造漂移。

## 环境与证据

- 静态清单源：`6250dc64eeb67bdd5a5e6686e6ac7c8233e0d4ce`。
- exact-baseline 运行时：`0abb989a6df017e8bd1bd0ce41e09b29f5d27549`。
- 最终产品运行时：`a85740c453a01e167faeaaf59c9fad9d74cc3e81`。
- 专属前端/API：`127.0.0.1:18121` / `127.0.0.1:18120`。
- Compose project：`sc-menu-governance-m4`。
- 截图：`.runtime/menu-governance-m4/evidence/baseline-0abb989/browser/screenshots/` 与 `.runtime/menu-governance-m4/evidence/candidate-a85740c/browser/screenshots/`。
- 自动闭环报告：`.runtime/menu-governance-m4/evidence/menu-m4-closure.json`。

旧的 `menu-m4-runtime.REJECTED-wrong-sha.json` 仅保留为资源事实探针；它曾错误地把静态清单 SHA 当作服务 SHA，禁止单独作为 exact-baseline 证据。exact-baseline 仅由真实浏览器 `system.init` 报告证明。

## 验收

- `make verify.product.menu.governance.m4.closure`：PASS。
- 菜单治理单测：16/16 PASS。
- 清单生成与 `--check`：PASS。
- `make verify.frontend.typecheck.strict`：PASS。
- `make verify.frontend.style_system.guard`：PASS。
- `make verify.frontend.release.unit`：PASS。
- `make verify.baseline.freeze_guard`：PASS。
- 环境无关生产构建：PASS（显式 acceptance env、DB 和独立输出目录）。
- 隔离库模块升级与 release snapshot：PASS。

