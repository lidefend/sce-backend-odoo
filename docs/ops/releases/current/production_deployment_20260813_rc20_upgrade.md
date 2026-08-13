# Production Deployment Record — RC20 Upgrade Closeout

## 1. 基本信息

| 项目 | 值 |
| --- | --- |
| 部署编号 | `rc20-20260813T0019Z` |
| 部署窗口 | `2026-08-13 Asia/Shanghai` |
| 操作/审批 | `Codex 执行；用户会话统一授权` |
| 生产主机/数据库 | `sc-prod` / `sc_production`，dbfilter `^sc_production$` |
| 发布类型 | `RC20 产品独立发布 + P2 增量边界修复` |
| 产品版本 | `v1.0.0-rc.20` |
| 产品源 SHA | `bd5a6e6fd84b61922c3c93b3ad693a0bdd12f8a3` |
| 产品 registry digest | `sha256:043e82e4f49ed42f950976437593d0394ebe0805e1b0709ef559a51e10b142a1` |
| 产品运行 image ID | `sha256:2d3fdd313931678d6bc7a183a33e75bdd869c07d1442a9d242afeb11670e3bcf` |
| P2 SHA / 版本 | `4683ac95d9601362ae4d5ec1de08ad270e34db34` / `17.0.3.1.8` |
| 最终工具 SHA | `1129485ecec95cc1e04e8b313cdfa3c4dab0f4b3` |

## 2. 边界与范围

产品发布与用户模块独立。RC20 产品发布不依赖 P2 数据完整性；生产随后只对
`sce_customer_baosheng_legacy` 做增量升级，移除它误写入产品策略的一个客户菜单。

- 产品模块：`smart_core=17.0.1.1.9`、`smart_construction_core=17.0.0.129`。
- P2 模块：`sce_customer_baosheng_legacy=17.0.3.1.8`。
- 未导入租户 payload，未补用户字典数据，未用 demo seed，未升级产品模块。
- P2 原生历史入口仍由 P2 持有，但不进入标准版/预览版产品策略和快照。

## 3. 备份与回滚

用户明确说明没有实际有用数据变动并授权跳过本次新备份。保留的完整数据库与
filestore 配对回滚点为：

```text
/data/backups/sc_production/sc_production-20260812T183501Z-44ffdd06
```

运行配置原子回滚副本：

```text
/opt/sce/config/sc_production/runtime.env.pre-p2-4683ac95-20260813T022134Z
```

上一 P2 运行根：

```text
/opt/sce/customer-addons/v1.0.0-rc.19-p2.b62f3c3
```

## 4. 日常生产克隆先行验证

| 项目 | 结果 |
| --- | --- |
| restore ID | `sc_restore_20260810t093000z_352c22d4` |
| 隔离数据库 | `r10e_sc_restore_20260810t093000z_352c22d4` |
| 生产数据库连接 | `false` |
| 产品镜像 | 与生产 RC20 image ID 完全一致 |
| P2 升级 | `17.0.3.1.7 -> 17.0.3.1.8` PASS |
| 受保护计数 | `res_users=115`、`project_project=923`、`ir_attachment=44066`，前后不变 |
| 产品策略 | standard/preview 均 `89`，P2 残留 `0` |
| 归档投影 | `6413` / `841`，不变 |
| 模块 pending | `0` |
| 正式 HTTP 验收 | 连续两轮 PASS |

克隆验收证据：

```text
/home/lidefend/workspace/artifacts/rc20-daily-clone-acceptance-p2-318.json
```

## 5. 生产执行

P2 签名包与发布锁：

```text
package sha256=229caf5898b4068ea00e4fdfdd1c228c8c3ccc1c00de877c8f25c0611eda5dd8
/data/backups/production_acceptance/tenant-deliveries/baosheng-rc20-p2-318-20260813-v2/production-release-set.json
```

受控步骤：

```text
production.tenant.delivery.artifacts.sync: PASS
release.production.customer_package.prepare: PASS
release.production.customer_module.upgrade TARGET_MODULE=sce_customer_baosheng_legacy: PASS
release.production.customer_runtime.activate: PASS
release.production.platform.snapshot.initialize construction.standard: PASS
release.production.platform.snapshot.initialize construction.preview: PASS
verify.production_menu.release_gate.guard.prod: PASS
production.customer.runtime.config.promote: PASS
```

最终持久化运行根：

```text
/opt/sce/customer-addons/v1.0.0-rc.20-p2.4683ac9
```

配置提升证据：

```text
/data/backups/deployments/rc20-20260813T0019Z/customer-runtime-config-p2-318.json
```

## 6. 发布后验收

| 检查项 | 结果 |
| --- | --- |
| Odoo/Nginx/PostgreSQL/Redis | `healthy` |
| `verify.baseline` | `PASS` |
| `verify.p0` 产品范围 | `PASS`；P2 用户字典基线明确 SKIP |
| 产品菜单发布闸 | standard/preview 均 `PASS`，89 页 |
| 正式 HTTP acceptance | `PASS` |
| 模块 pending | `0` |
| Odoo `ERROR\|Traceback` | `0`（最终激活窗口） |
| 产品模块版本 | RC20 版本不变 |
| P2 版本 | `17.0.3.1.8` |
| 归档投影计数 | `6413` / `841`，不变 |
| 生产受保护计数 | `res_users=115`、`project_project=923`、`ir_attachment=52577` |

正式验收证据：

```text
/data/backups/deployments/rc20-20260813T0019Z/acceptance-postdeploy-final.json
/data/backups/deployments/rc20-20260813T0019Z/acceptance-p2-318-final.json
```

`smoke.business_full` 与 `smoke.role_matrix` 未在生产运行。代码检查确认这两个旧入口会
创建 demo 用户或业务记录，不符合本次不可变、只读验收边界；由正式 HTTP acceptance、
产品菜单发布闸、baseline/P0、只读数据库核对与日志检查替代。

## 7. 代码与远端收口

- P2 `main`: `4683ac95d9601362ae4d5ec1de08ad270e34db34`。
- 产品工具 PR #198 五项 required checks 全部 PASS，merge commit：
  `1129485ecec95cc1e04e8b313cdfa3c4dab0f4b3`。
- GitHub/Gitee 产品 `main` 均同步到该 SHA。
- 产品运行身份仍为冻结 RC20 源 SHA/digest/image ID；工具合并没有重发产品镜像。

## 8. 结论

RC20 产品独立发布、日常克隆先行验证、生产 P2 增量修复、两套产品快照恢复、运行配置
持久化和最终验收均已完成。用户模块数据缺口不再阻断产品发布，生产具备继续运行条件。
