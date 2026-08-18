# .agent 工程上下文

## 项目定位

这是施工企业 ERP 系统。

- Backend: Odoo
- Frontend: Vue (Contract-driven)
- Database: PostgreSQL

## AI 工作原则

1. Contract First
2. Small Change First
3. Evidence Required
4. Preserve History
5. No Unverified Change

## AI 修改规则

AI 修改代码前必须执行：

1. 找到相关 contract / 上下文依据
2. 明确对应 goal
3. 执行对应 verify
4. 输出 evidence 与变更结果

该目录用于记录：

- 当前上下文（.agent/context.yaml）
- 目标/任务（.agent/goals）
- 决策约束（.agent/decisions）
- 执行记录（.agent/runs）
