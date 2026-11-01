# 344 · BNVA-03 Unmenu Action Caller Inventory

## 总览

233 个无菜单 act_window：54 个已在 03-01/03-02 分类（31 上下文绑定、11 向导、9 报表、3 内嵌）。
剩余 179 个本轮做调用方第一轮扫描。

| 第一轮结果 | 数量 |
| --- | --- |
| 多文件引用（跨文件有调用方） | 45 |
| 单文件（定义与同文件引用未拆分） | 134 |

## 单文件 134 的组成

- Odoo 标准模块（account / stock / base / mail / sms / project / product / purchase / hr / resource 等）约 116 个：
  标准内部可调用动作（按钮、smart button、服务端动作、设置、报表目标），不属于 Smart Construction
  业务入口资产。
- Smart Construction 自有动作约 17 个：见 346。
