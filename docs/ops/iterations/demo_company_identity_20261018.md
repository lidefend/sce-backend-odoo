# Demo 公司身份种子收口（2026-10-18）

## 目标

日常 demo 的公司名固定为 `demo演示公司`。该身份属于 `smart_construction_demo`
正式种子链，而不是一次性的库内修改；重建或重跑种子不得回到 Odoo 默认的
`My Company`。

## 层级与载体

- 正式产品层：P4 demo 交付载体
- 模块：`demo_addons/smart_construction_demo`
- 数据职责：`sc_demo`（`sc-demo-dev`）

## 变更

- 新增种子步骤 `demo_company_identity`，同时修正公司和公司往来单位名称。
- 将步骤放在 `demo_full` profile 首位，先于项目与业务数据。
- `demo_90_verify` 增加公司身份断言，种子末尾自检不通过即失败。
- 离线测试覆盖 profile 顺序与步骤幂等。

## 验证

- `make verify.demo.supplemental.unit`：32 项 PASS。
- 候选 SHA 同步后执行受管 demo seed，回读 `res_company.name` 与
  `res_partner.name` 均为 `demo演示公司`。

## 边界

- 仅操作 demo 职责；未触碰历史保护库、生产库、租户库或用户模块。
