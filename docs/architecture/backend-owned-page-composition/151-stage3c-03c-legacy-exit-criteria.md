# 151 · BNVA-019 Stage 3C-03C-01 · 兼容退出条件

## 退出旧 ownership 兜底的条件

1. 原生字段位置完整（get_view 正常返回合并 arch）。
2. 原生投影不再在正常路径抛异常（观测零 fallback）。
3. 或：回退路径不再产生 `primary_facts`（改为最小结构/显式 NOT_VERIFIED）。
4. 历史消费者兼容已验证。
5. Guard 对正式页面不依赖旧兜底产生 PASS。

## 原则

- 按页面迁移，不按代码删除。
- 历史页面不强制升级 Formal。
- 只有零依赖证据 + Guard + 真实页面回归通过，才移除旧逻辑。

