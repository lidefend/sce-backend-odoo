# 363 · BNVA-04 Model Consumer & Lifecycle Matrix

## 消费者分布（187 sc.*）

| 桶 | 数量 | 生命周期判断 |
| --- | --- | --- |
| menu + contract | 50 | 已产品化，随产品版本演进 |
| menu only | 69 | 有入口，契约待产品化 |
| action only | 11 | 上下文/内部调用 |
| 无 action/menu/contract（abstract/transient） | 57 | 技术基础设施 |

## 生命周期归属

- 50 个核心对象：产品发布负责。
- 69 个 workflow：产品化补齐时明确所有权。
- 11 个 action-only：调用方确认后登记为内部能力。
