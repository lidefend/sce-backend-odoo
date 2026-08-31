import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import path from 'path';

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

export default defineConfig({
  plugins: [vue()],
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
      },
    },
  },
  build: {
    outDir: buildOutDir,
    emptyOutDir: true,
  },
});
