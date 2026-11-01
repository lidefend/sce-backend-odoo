# 273 · BNVA-02C-02E-P4 · 凭证状态与停止报告

## 凭证存储方式（已核实，未输出明文）

受管脚本 `scripts/dev/local_clean_env_prepare.sh`：

- 源 `.env.dev`，生成独立随机密钥（db/admin/jwt/bootstrap），`umask 077` 写
  `.env.local.clean`（600 权限）。
- 有防覆盖守卫：若 `sc_local_clean_*` 卷已存在且未带重建确认，则拒绝生成新凭证。

## 当前状态（不一致）

- `.env.local.clean` **缺失**。
- `sc-local-clean` 容器（odoo/db/redis/nginx）与 `sc_local_clean_*` 卷**仍在运行/存在**。

这属于“凭证需要覆盖现有受管秘密 + 数据库目标存在历史卷”的停止条件，不能直接
生成新凭证（会造成运行容器与凭证文件不一致）。

## 建议的受管恢复路径（需你确认后执行）

`make local.clean.rebuild CONFIRM_LOCAL_CLEAN_REBUILD=REBUILD_ISOLATED_REHEARSAL`

该入口会在重建确认下：重新生成 clean 凭证 → 只重建 `sc_clean` + `sc_local_clean_*`
→ 安装正式模块（`MODULE=sc_norm_engine --without-demo=all`）。不触碰 dev/test/
acceptance/production。

## 停止原因

未经你逐字确认重建命令，不执行破坏性重建与凭证覆盖。

