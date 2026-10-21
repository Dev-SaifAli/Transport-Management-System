import { fileURLToPath, URL } from 'node:url'

import vue from '@vitejs/plugin-vue'
import { defineConfig, loadEnv } from 'vite'

// The base path is configurable so the built app can be served from a
// Frappe subpath such as /dispatch/ (see .env.example / .env).
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  return {
    // Production assets are served by Frappe from the app's public directory.
    // Keep the dev server convenient while using the canonical Frappe asset URL
    // for builds consumed by /dispatch.
    base: mode === 'production' ? '/assets/dispatch_portal/frontend/' : env.VITE_APP_BASE_PATH || '/dispatch/',
    server: {
      port: 5173,
      host: '127.0.0.1',
      proxy: {
        '/api': {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
          headers: {
            Host: 'tms.localhost',
          },
        },
      },
    },
    plugins: [vue()],
    build: {
      outDir: '../dispatch_portal/public/frontend',
      emptyOutDir: true,
    },
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
  }
})
