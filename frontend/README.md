# Frontend (0 → 1)

This workspace is the independent frontend for the Smart Construction Platform.

## Layout

- `apps/web`: primary web app (Vue 3 + Vite)
- `packages/ui`: shared UI components (future)
- `packages/sdk`: API/intent client (future)
- `packages/schema`: contract types (future)
- `packages/tools`: codegen/validation tools (future)

## Quick Start

```bash
make fe.install.cached
make local.dev.frontend.watch
```

## Environment

The governed local development authority is the repository `.env.dev`.
Use `make local.dev.up` for backend services and `make local.dev.frontend.watch`
for the Vite HMR server. `make local.dev.frontend` remains the static build entry.

Copy the example env file only for isolated experiments outside the governed
`local.dev` lifecycle:

```bash
cp frontend/.env.example frontend/apps/web/.env
```

Key vars (Vite uses `VITE_*`):

- `VITE_API_BASE_URL`
- `VITE_APP_ENV`
- `VITE_TENANT`
- `VITE_FEATURE_FLAGS`

## Scripts

From repo root:

```bash
make local.dev.frontend.watch
make frontend.logs
make frontend.stop
pnpm -C frontend build
pnpm -C frontend lint
pnpm -C frontend typecheck
```
