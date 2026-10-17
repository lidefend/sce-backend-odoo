# 前端静态产物与 Odoo 镜像解耦（2026-10-18）

## 职责边界

- 前端源码在主仓 `frontend/`。静态产物由 `Dockerfile.production-frontend-builder`
  独立构建，产物目录为 `/build/frontend/apps/web/dist`，通过 export-only stage
  `frontend-dist` 导出。
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

前端指纹统一算法（构建、CI、校验共用）：

```bash
cd <dist-dir> && find . -type f -print0 | LC_ALL=C sort -z \
  | xargs -0 sha256sum | sha256sum | awk '{print $1}'
```

外部 `FRONTEND_BUILD_SHA256`、前端镜像内 `.build-sha256` 与镜像标签
`io.sce.frontend.sha256` 三者必须相等。

## 构建与验收命令

```bash
# 1. 导出前端静态产物
docker build --file Dockerfile.production-frontend-builder \
  --target frontend-dist --output type=local,dest=/tmp/frontend-dist .

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

## 当前未闭合项（阻断，需镜像/编排责任人处理）

- `Dockerfile.production-frontend` 目前写入的指纹标签是
  `com.sce.frontend.sha256`，与契约要求的 `io.sce.frontend.sha256` 不一致；
  `verify.production_blocker.image` 会以 fail-closed 方式失败。
- 该 Dockerfile 从构建上下文复制 `frontend/apps/web/dist-production-candidate/`，
  而 builder 导出目录是 `dist`；构建前端镜像前必须先把导出产物放入该路径
  （`scripts/release/immutable_candidate_build.sh` 采用同样方式）。
- `docker-compose.production-candidate.yml` 尚未把
  `EXPECTED_FRONTEND_IMAGE_DIGEST` 传入前端服务，前端镜像摘要目前无编排层断言。
- builder 不生成 `.build-sha256`，指纹由外部计算后作为构建参数注入；镜像内文件
  由 `Dockerfile.production-frontend` 写入。

## 验证状态说明

本文档与配套脚本改动只做了静态语法/契约校验（`bash -n`、`py_compile`、YAML 解析、
dispatch contract 单测）。本轮未执行任何 `docker build`、镜像扫描或运行时验收，
上述命令的实际结果需由 CI 或责任人复跑确认，不得据此宣称镜像验收完成。
