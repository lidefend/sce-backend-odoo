import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

export default defineConfig({
  plugins: [
    vue({
      template: {
        compilerOptions: {
          isCustomElement: (tag) => tag.startsWith('ui5-'),
        },
      },
    }),
  ],
  server: {
    host: '127.0.0.1',
    port: 5186,
    strictPort: true,
  },
  preview: {
    host: '127.0.0.1',
    port: 5186,
    strictPort: true,
  },
});
