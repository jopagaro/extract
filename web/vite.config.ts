import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Tauri sets TAURI_PLATFORM during `tauri build`. Relative asset URLs are
// required so `/assets/*.js` chunks resolve under the custom protocol; broken
// chunk loads (e.g. dynamic import for `invoke`) break API discovery and the
// report view while other routes may appear fine.
const isTauriBuild = Boolean(process.env.TAURI_PLATFORM)

export default defineConfig({
  plugins: [react()],
  clearScreen: false,
  base: isTauriBuild ? './' : '/',
  build: {
    target: isTauriBuild ? 'chrome105' : undefined,
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        rewrite: (path) => path.replace(/^\/api/, ''),
        changeOrigin: true,
      },
    },
  },
})
