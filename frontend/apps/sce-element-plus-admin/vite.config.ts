import path from 'node:path'

import vue from '@vitejs/plugin-vue'
import { defineConfig, loadEnv } from 'vite'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const proxyTarget = env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:18081'

  return {
    plugins: [vue()],
    resolve: { alias: { '@': path.resolve(__dirname, 'src') } },
    server: {
      host: '0.0.0.0',
      port: 3010,
      strictPort: false,
      proxy: {
        '/api': { target: proxyTarget, changeOrigin: true },
        '/web': { target: proxyTarget, changeOrigin: true },
      },
    },
  }
})
