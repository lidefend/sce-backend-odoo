# Demo 集团多公司结构（2026-10-19）

## 目标

Demo 是标准平台租户，不再使用“Demo/演示”可见标记。主公司收敛为正式集团名称，并在
同一租户内增加第二工程子公司，供真实多公司使用路径展示。

## 实现事实

| 项目 | 事实 |
| --- | --- |
| 主公司 | `四川智汇某某建设集团有限公司`，XMLID `base.main_company` |
| 第二公司 | `四川智汇某某建设集团第二工程有限公司`，XMLID `smart_construction_demo.demo_company_second` |
| 层级 | 第二公司 `parent_id = base.main_company` |
| 币种/国家 | 两家公司均为 CNY / 中国 |
| 数据空间 | 第二公司登记为 `data_purpose=demo`，租户键 `sc-demo-main` |
| 集团级成员 | `admin`、`wutao`、`demo_full`、`demo_role_owner`、`demo_role_executive`、`fin_mgr`、`fin1`、`demo_finance`、`demo_audit`、`sc_demo_accounting_manager`、`sc_demo_business_config`、`sc_demo_operation` |
| 重建步骤 | `demo_company_secondary`、`demo_company_membership` |

`FE Company A/B` 属于验收夹具，不是 Demo 公司，不参与本结构。

## 幂等与边界

- 第二公司先按 XMLID 查找；XMLID 缺失时按正式名称收敛；只有都找不到才创建。
- 名称、父公司、币种、国家、联系方式均只在值变化时写入。
- 数据空间登记先按 `company_id` 检查，已登记则跳过。
- 用户允许公司范围只追加第二公司，不覆盖既有公司，也不改变默认公司。
- 成员范围只在 `demo_10_users` 之后收敛，避免用户步骤的 `(6,0,[main])` 覆盖。
- 项目岗位不加入第二公司，保留真实的多公司数据边界。

## 验证

| 命令 | 结果 |
| --- | --- |
| `python3 demo_addons/smart_construction_demo/tests/test_demo_organization_baseline.py` | PASS，26 tests |
| `python3 demo_addons/smart_construction_demo/tests/test_demo_supplemental_flows.py` | PASS，80 tests |
| `make verify.demo.lifecycle.unit` | PASS，141 tests |

本记录是离线实现证据。既有 `sc_demo` 库仍需执行一次受管 seed，之后只读回读公司名称、
第二公司 XMLID/登记、集团级成员 `company_ids`、公司切换与 `/t/demo` 入口；在完成该回读前，
不宣称日常环境已经收敛。
