import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import path from 'path';
import fs from 'fs';
import { execFileSync } from 'child_process';

function readNumberEnv(name: string, fallback: number): number {
  const value = Number(process.env[name] ?? fallback);
  return Number.isFinite(value) && value > 0 ? Math.trunc(value) : fallback;
}

function readBooleanEnv(name: string, fallback: boolean): boolean {
  const value = String(process.env[name] ?? '').trim().toLowerCase();
  if (!value) return fallback;
  if (['1', 'true', 'yes', 'on'].includes(value)) return true;
  if (['0', 'false', 'no', 'off'].includes(value)) return false;
  return fallback;
}

const port = readNumberEnv('VITE_DEV_PORT', 5174);
const host = process.env.VITE_DEV_HOST ?? '127.0.0.1';
const backendPort = readNumberEnv('ODOO_PORT', 8070);
const apiProxyTarget = process.env.VITE_API_PROXY_TARGET ?? `http://127.0.0.1:${backendPort}`;
const entryNamespace = (process.env.SC_ENTRY_NAMESPACE ?? '').trim();
const entryHeaders = entryNamespace
  ? {
      'X-SC-Namespace': entryNamespace,
      'X-SC-Audience': (process.env.SC_ENTRY_AUDIENCE ?? 'tenant').trim(),
      'X-SC-Entry-Secret': (process.env.SC_ENTRY_SHARED_SECRET ?? '').trim(),
      'X-SC-Route-Version': (process.env.SC_ENTRY_ROUTE_VERSION ?? '').trim(),
    }
  : {};
const buildOutDir = process.env.VITE_BUILD_OUT_DIR || 'dist';
const hmrHost = process.env.VITE_HMR_HOST || (host === '0.0.0.0' ? '127.0.0.1' : host);
const hmrClientPort = readNumberEnv('VITE_HMR_CLIENT_PORT', port);
const hmrProtocol = process.env.VITE_HMR_PROTOCOL || 'ws';
const watchUsePolling = readBooleanEnv('VITE_WATCH_USE_POLLING', false);
const watchInterval = readNumberEnv('VITE_WATCH_INTERVAL', 100);
const watchBinaryInterval = readNumberEnv('VITE_WATCH_BINARY_INTERVAL', 300);
const rootDir = __dirname;
const workspaceRoot = path.resolve(__dirname, '../..');
const cacheDir = path.resolve(workspaceRoot, 'node_modules/.vite/web');
const fullSha = /^[0-9a-f]{40}$/;
const isoTime = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z$/;

function readBuildIdentity() {
  const firstNonEmpty = (...values: Array<string | undefined>) => (
    values.map((value) => String(value ?? '').trim()).find(Boolean) ?? ''
  );
  const configuredSha = firstNonEmpty(process.env.SC_SOURCE_REVISION, process.env.SC_BUILD_SHA).toLowerCase();
  let buildSha = fullSha.test(configuredSha) ? configuredSha : '';
  if (!buildSha) {
    try {
      buildSha = execFileSync('git', ['rev-parse', 'HEAD'], {
        cwd: workspaceRoot,
        encoding: 'utf8',
        stdio: ['ignore', 'pipe', 'ignore'],
      }).trim().toLowerCase();
    } catch {
      buildSha = '';
    }
  }
  const configuredTime = firstNonEmpty(process.env.SC_BUILD_TIME);
  const builtAt = isoTime.test(configuredTime) ? configuredTime : new Date().toISOString();
  const environment = firstNonEmpty(
    process.env.SC_DEPLOY_ENV
    , process.env.SC_ENVIRONMENT
    , process.env.VITE_APP_ENV
    , 'unknown',
  );
  let version = firstNonEmpty(process.env.SC_PRODUCT_VERSION);
  if (!version) {
    try {
      version = fs.readFileSync(path.resolve(workspaceRoot, '../VERSION'), 'utf8').trim();
    } catch {
      version = 'unknown';
    }
  }
  return {
    sha: fullSha.test(buildSha) ? buildSha : 'unknown',
    builtAt,
    environment,
    version: version || 'unknown',
  };
}

const buildIdentity = readBuildIdentity();

function buildInfoPlugin() {
  return {
    name: 'sc-build-info',
    apply: 'build' as const,
    generateBundle() {
      this.emitFile({
        type: 'asset' as const,
        fileName: 'build-info.json',
        source: `${JSON.stringify({
          schema: 'frontend.build_info.v1',
          sha: buildIdentity.sha,
          built_at: buildIdentity.builtAt,
          environment: buildIdentity.environment,
          version: buildIdentity.version,
        }, null, 2)}\n`,
      });
    },
  };
}

export default defineConfig({
  plugins: [vue(), buildInfoPlugin()],
  define: {
    __SC_BUILD_SHA__: JSON.stringify(buildIdentity.sha),
    __SC_BUILD_TIME__: JSON.stringify(buildIdentity.builtAt),
    __SC_BUILD_ENV__: JSON.stringify(buildIdentity.environment),
    __SC_BUILD_VERSION__: JSON.stringify(buildIdentity.version),
  },
  cacheDir,
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
      '@sc/schema': path.resolve(__dirname, '../../packages/schema/src/index.ts'),
    },
  },
  server: {
    host,
    port,
    strictPort: true,
    open: false,
    cors: false,
    hmr: {
      host: hmrHost,
      clientPort: hmrClientPort,
      protocol: hmrProtocol as 'ws' | 'wss',
      overlay: true,
    },
    watch: {
      usePolling: watchUsePolling,
      interval: watchInterval,
      binaryInterval: watchBinaryInterval,
      ignored: [
        '**/.git/**',
        '**/dist/**',
        '**/dist-dev/**',
        '**/artifacts/**',
        '**/.codex/**',
      ],
    },
    fs: {
      allow: [workspaceRoot, rootDir],
    },
    proxy: {
      '/api': {
        target: apiProxyTarget,
        changeOrigin: true,
        ws: true,
        headers: entryHeaders,
      },
    },
  },
  build: {
    outDir: buildOutDir,
    emptyOutDir: true,
  },
});
