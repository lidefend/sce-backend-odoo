# SCENE-PRODUCT-02：企业配置管理员办理旅程与可用性收口

Base/main: `f2f7fd02f0f28f84e6190102f3bf559db0c28457`

Branch: `feature/scene-product-02-enterprise-config-journey-20261120`

Carried post-merge bookkeeping commit: `74dae16496222bdba07ea67f0fbd5fac550213be`

## 产品结果

企业配置管理员在现有企业初始化入口中，按业务依赖顺序完成企业资料、部门、岗位、人员与账号、同一用户的业务权限及企业场景选择。每条旅程必须有真实对象、提交结果、拒绝或成功反馈、权威回读、返回同一企业和重新诊断。

## 层级与边界

| 项目 | 声明 |
| --- | --- |
| Formal Product Layer | P1/P4 |
| Layer Target | 原生企业配置事实、五类维护入口、企业场景选择及自定义前端消费 |
| Standard vs User-Specific | 施工产品标准与企业运行时配置 |
| Why Here | 组织人事、账号权限和场景选择事实属于 P1 模型；前端只消费其声明 |
| Why Not Elsewhere | 平台只负责建企业和产品发布；P4 不成为业务事实来源，也不扩大权限 |
| Blast Radius | 六个配置入口的输入、拒绝、保存、回读、返回与重新诊断 |

## 运行环境与身份

开工检查结果：

- `make local.dev.health`：PASS，`sc-local-dev / sc_dev_demo`。
- `make local.dev.entry_identity.verify`：PASS，`/t/demo` 与 `ns_000000000002` 绑定 `sc_dev_demo`。
- `make local.dev.verify_authority`：PASS，演示环境模块、财务身份、本位币和税率事实成立。
- `make local.dev.write_lease.status`：`LOCAL_DEV_WRITE_LEASE_FREE`。
- `local.env.status` 的 sample 未启动和主静态入口 404 不影响 persistent local.dev；本批使用候选前端 5176。

待补记：后端运行 revision、候选前端构建 revision、配置管理员用户/公司/允许公司、六条旅程创建或修改的对象及恢复结果。

## 执行顺序

1. C02-01 企业信息：修改、保存、权威回读并返回初始化。
2. C02-02 部门：创建/维护并核对公司、上级和负责人。
3. C02-03 岗位：选择已保存部门并核对唯一编码与关系。
4. C02-04 人员与账号：创建普通内部用户、员工关联、部门和岗位，再修改同一对象并补部门负责人。
5. C02-05 业务权限：对同一用户授予和调整角色/允许公司，使用目标用户核对访问结果。
6. C02-06 企业场景：启用、回读、刷新、撤销/恢复，并区分企业选择、产品可用性和用户访问。

## 当前状态

- 运行环境健康、入口身份和写租约已通过。
- 所有实际保存、拒绝、回读和用户可用性结论仍为 `not_run`。
- 尚未修改产品代码。
