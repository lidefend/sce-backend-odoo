# 123 · BNVA-019 Stage 3B · 验收

## 结论

READY_WITH_CONSTRAINTS

## 通过项

- 唯一 form 主 arch 解析入口已建立（LDP 写入、NCP 复用的请求级共享）。
- 同请求 form get_view / fromstring 各 1 次。
- 两个 Adapter 职责边界保持，未合并。
- V2 契约输出兼容（project 590 / payment 880 不变）。
- 权限上下文按 cursor + uid + context 隔离。

## 约束

- 精确 HEAD Quick 需在提交后执行。
- 请求缓存有界 LRU，跨请求复用仅在 cursor 对象 id 被复用的极端情况下可能发生，
  已通过 uid + context digest 压缩碰撞面；正式发布前需结合 CI 观察。
- 旧 Parser 接口保留，Stage 3C 再收敛。

