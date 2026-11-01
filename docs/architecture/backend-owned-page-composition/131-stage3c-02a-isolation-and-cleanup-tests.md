# 131 · BNVA-019 Stage 3C-02A · 隔离与清理测试

## 覆盖

| # | 场景 | 状态 |
| --- | --- | --- |
| 1 | 同请求同视图命中 | PASS |
| 2 | 不同 cursor 不共享 | PASS |
| 3 | cursor 关闭后拒绝命中 | PASS |
| 4 | 不同 uid 隔离 | PASS |
| 5 | 不同 su 状态隔离 | PASS |
| 6 | 不同 lang 隔离 | PASS |
| 7 | 不同 view 隔离 | PASS |
| 8 | close 清理条目并释放 cursor 引用 | PASS |
| 9 | 无 cursor 的 fake env 优雅降级 | PASS |
| 10 | 请求结束 carrier 清理（handler 级） | PASS |

## 说明

测试使用真实 cursor 对象（带 closed 属性）而非整数 ID，覆盖对象生命周期。

