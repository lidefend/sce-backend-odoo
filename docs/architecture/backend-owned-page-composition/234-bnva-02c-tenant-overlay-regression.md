# 234 · BNVA-02B-02C-02C-01 · 租户覆盖回归

离线验证成立：Runner 只锚定 module+external_id 种子，不写 tenant_lowcoding /
user_preference。真实前后 payload_sha256 / Resolver 对比留待隔离库（`not_run`）。

