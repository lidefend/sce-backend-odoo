# 08 · Productization Recommendations

## Priorities for PC-01 R2

1. B1 身份收敛：
   - `project_code / user_id / manager_id` 在真实概览 DOM 中各出现 2 次。
   - 需要定位 B1 视图改动为何未消除重复展示。

2. C 协作体验：
   - 先确认通用 mail 渲染链的实际 DOM，再设计关注者折叠、附件分离和 Chatter 层级。

3. Native View Action：
   - 保持 SUSPENDED。
   - 恢复条件是验证 `ContractFormPage → ContractFormNativeCanvas → NativeFormTreeRenderer`
     的运行时 prop 传递，不重查已通过的上游环节。

## General principle

优先消费 Odoo 原生能力，只有原生能力确实无法满足建筑业务时，才扩展 SCE 专业能力。

