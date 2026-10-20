# 产品配置能力长任务 Bootstrap（2026-10-20）

## 0. 身份与边界

- 分支：`feature/product-configuration-capability-20261020`
- 基线：`82dbd9134288576ede315370179858c5ba70ce87`（`main`）
- Formal Product Layer：P1（施工行业标准产品）
- Supporting Layers：P0（通用契约/能力目录）、P3（配置工作台）
- 长任务原则：总体目标达成前不合并 main。

## 1. 本批目标

锁定“业务全功能账号、业务配置管理员、平台管理员、支持/运维”四类账号的可见能力，
并把产品配置、系统参数、登录首屏、平台管理和支持诊断拆成可验证的能力目录。

## 2. 交付物

- `config/product_configuration_capability_v1.json`：4 类账号、6 个登录首屏区块、
  8 张配置卡、6 类系统参数、25 项能力。
- `docs/product/product_configuration_capability_v1.md`：产品能力说明与分批计划。
- `scripts/verify/product_configuration_capability_guard.py`：结构、边界与秘密泄漏守卫。
- `scripts/verify/test_product_configuration_capability_guard.py`：7 个反例/正例测试。
- `make verify.product_configuration.capability`：离线能力目录门禁。

## 3. 能力边界

- 业务全功能用户：今日工作、风险、我的对象、快捷办理、最近访问、我的能力、业务中心、
  全局搜索、我的设置；不得自动获得平台管理或支持诊断。
- 业务配置管理员：8 张配置卡；系统参数走受控目录，不暴露原始 `ir.config_parameter`、
  密钥或部署身份。
- 平台管理员：租户/公司、用户角色、发布健康、定时任务、集成。
- 支持/运维：只读诊断。

## 4. 验证

```bash
make verify.product_configuration.capability
```

结果：

- 7 tests PASS
- `[product_configuration_capability_guard] PASS audiences=4 cards=8 categories=6 capabilities=25`
- `git diff --check` PASS

## 5. 后续批次

- Batch 2：后端 `product.configuration.capability.catalog` 契约与测试。
- Batch 3：配置工作台 8 张卡与登录首屏能力发现。
- Batch 4：系统参数目录、影响预览、变更集发布/回滚。
- Batch 5：业务全功能角色浏览器验收。

## 6. 回滚

回退本批 commit；不涉及数据库、服务或产品运行时。
