# 前端静态产物与 Odoo 镜像解耦（2026-10-18）

## 职责边界

- 前端源码在主仓 `frontend/`。静态产物由 `Dockerfile.production-frontend-builder`
  内的 pnpm/vite 构建到镜像内 `/build/frontend/apps/web/dist`，并由 export-only
  stage `frontend-dist` 导出。**宿主机落点由
  `--output type=local,dest=<dir>` 决定**：命令里传哪个 `<dir>`，产物就落在
  哪里，不存在固定的“导出目录”。`Dockerfile.production-frontend` 的 `COPY`
  源必须与该落点一致（当前为
  `frontend/apps/web/dist-production-candidate/`）。
- Odoo 镜像（`Dockerfile` / `Dockerfile.production-candidate`）只包含后端运行时。
  它不得包含 `/opt/sce/frontend`、`/usr/share/nginx/html/index.html`、`nginx`
  可执行文件或 Node 工具链。
- 前端运行载体是独立的 nginx 静态镜像（`Dockerfile.production-frontend`），
  由 `FRONTEND_IMAGE_REF` 指定，负责静态资源与反向代理。
- local-dev 的 nginx 不做镜像内静态构建，直接挂载主仓静态目录：
  `make local.dev` 设置 `FRONTEND_DIST_DIR=frontend/apps/web/dist-dev`，
  未显式设置时 `docker-compose.yml` 回退到 `frontend/apps/web/dist`。

## 镜像契约

| 载体 | 引用变量 | 期望摘要变量 | 必须存在 | 必须不存在 |
| --- | --- | --- | --- | --- |
| Odoo 后端 | `ODOO_IMAGE_REF` | `EXPECTED_IMAGE_DIGEST` | 后端运行时 | `/opt/sce/frontend`、nginx、Node |
| 前端静态 | `FRONTEND_IMAGE_REF` | `EXPECTED_FRONTEND_IMAGE_DIGEST` | `index.html`、`.build-sha256`、nginx | Node 构建链 |

## 指纹口径（三套，互不可比）

`sha256sum` 的输出包含文件路径，因此不同遍历根或路径前缀会得到不同摘要。
以下三套口径**互不可比**，不得跨口径断言相等：

| 口径 | 计算方式 | 消费方 |
| --- | --- | --- |
| F1（CI 规范口径） | `cd <dist-dir> && find . -type f -print0 \| LC_ALL=C sort -z \| xargs -0 sha256sum \| sha256sum` | `.github/workflows/backend_test_suite.yml`、`.github/workflows/demo-ci.yml`，产出 `FRONTEND_BUILD_SHA256` |
| 脚本变体（相对根，无 `LC_ALL=C`） | `find "$dist" -type f -print0 \| sort -z \| xargs -0 sha256sum \| sha256sum` | `scripts/release/immutable_candidate_build.sh`（候选 `frontend-build.sha256`）、`scripts/release/production_acceptance.sh`、`make/release.mk` 的 release artifacts |
| 契约镜像验收变体（绝对路径前缀） | `find "$context_dir/frontend/apps/web/dist-production-candidate" -type f -print0 \| sort -z \| xargs -0 sha256sum \| sha256sum` | `scripts/release/production_contract_image_acceptance.sh`，校验镜像 label 与 `.build-sha256` |

同一口径内，外部 `FRONTEND_BUILD_SHA256`、前端镜像内 `.build-sha256` 与镜像标签
`io.sce.frontend.sha256` 三者必须相等。

## 构建与验收命令

```bash
# 1. 导出前端静态产物
docker build --file Dockerfile.production-frontend-builder \
  --target frontend-dist --output type=local,dest=/tmp/frontend-dist .

# 1b. 把导出产物放到 Dockerfile.production-frontend 的 COPY 源目录
mkdir -p frontend/apps/web/dist-production-candidate
cp -a /tmp/frontend-dist/. frontend/apps/web/dist-production-candidate/

# 2. 构建前端静态镜像（上下文需包含 dist-production-candidate）
docker build --file Dockerfile.production-frontend \
  --build-arg FRONTEND_BUILD_SHA256="$FRONTEND_BUILD_SHA256" \
  -t "$FRONTEND_IMAGE_REF" .

# 3. 后端/前端边界与指纹断言（该目标会重建两个载体，再执行断言）
make verify.production_blocker.image \
  BLOCKER_RUNTIME_IMAGE="$ODOO_IMAGE_REF" \
  BLOCKER_FRONTEND_IMAGE="$FRONTEND_IMAGE_REF" \
  EXPECTED_IMAGE_DIGEST="$EXPECTED_IMAGE_DIGEST" \
  EXPECTED_FRONTEND_IMAGE_DIGEST="$EXPECTED_FRONTEND_IMAGE_DIGEST"

# 4. 运行时资产刷新验证（Odoo 镜像反向断言，前端镜像可选正向断言）
make verify.production_blocker.runtime_assets \
  BLOCKER_RUNTIME_IMAGE="$ODOO_IMAGE_REF" \
  BLOCKER_FRONTEND_IMAGE="$FRONTEND_IMAGE_REF"
```

CI 中 `backend_test_suite.yml` 与 `demo-ci.yml` 均使用
`Dockerfile.production-frontend-builder` + `--target frontend-dist` 导出静态产物，
计算指纹后通过 `FRONTEND_BUILD_SHA256` 与 `FRONTEND_DIST_DIR` 向下游传递；
不再依赖 `Dockerfile` 的 `frontend-artifact` / `frontend-verified` stage。

## 契约核对（2026-10-18 R2 只读复核）

- `Dockerfile.production-frontend` 写入的指纹标签为
  `io.sce.frontend.sha256`，与镜像内 `.build-sha256` 及外部
  `FRONTEND_BUILD_SHA256` 保持一致；不再使用历史 `com.` 前缀命名空间，
  `verify.production_blocker.image` 按 `io.` 前缀做 fail-closed 断言。
- `EXPECTED_FRONTEND_IMAGE_DIGEST` 的归属是编排层契约：
  `release.production.compose.preflight`（依赖
  `release.production.identity.preflight`）检验其非空，并与
  `FRONTEND_IMAGE_REF` 一并传给
  `scripts/release/production_compose_contract.py`，要求与 release manifest 的
  `frontend_image_digest` 及 Odoo/前端 release revision 集合一致。
- `docker-compose.production-candidate.yml` 的 nginx 服务只消费
  `FRONTEND_IMAGE_REF`。不得向该服务注入未被消费的
  `EXPECTED_FRONTEND_IMAGE_DIGEST` 环境变量；该摘要已在 preflight 阶段完成校验。

## dist-production-candidate 状态

- `frontend/apps/web/dist-production-candidate/` 被 `.gitignore:87` 忽略：
  它不在版本库中，可能来自任意历史构建而**陈旧**，且**自身不带版本标识**。
- 因此构建前端镜像前必须由固定 `SOURCE_SHA` 重新导出并整体覆盖该目录：

```bash
SOURCE_SHA=<pinned-sha>
rm -rf frontend/apps/web/dist-production-candidate
mkdir -p frontend/apps/web/dist-production-candidate
docker build --file Dockerfile.production-frontend-builder \
  --target frontend-dist \
  --output type=local,dest=frontend/apps/web/dist-production-candidate .
```

## 当前未闭合项（阻断，需镜像/编排责任人处理）

- builder 不生成 `.build-sha256`，指纹由外部计算后作为构建参数注入；镜像内文件
  由 `Dockerfile.production-frontend` 写入。

## 验证状态说明

本文档与配套脚本改动只做了静态语法/契约校验（`bash -n`、`py_compile`、YAML 解析、
dispatch contract 单测）。本轮未执行任何 `docker build`、镜像扫描或运行时验收，
上述命令的实际结果需由 CI 或责任人复跑确认，不得据此宣称镜像验收完成。
