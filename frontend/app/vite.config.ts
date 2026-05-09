import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import basicSsl from '@vitejs/plugin-basic-ssl'

// Backend listens with TLS on 8000 (Docker / entrypoint). Plain http:// here breaks the proxy.
const apiProxyTarget = process.env.GUARDIAN_API_PROXY ?? 'https://127.0.0.1:8000'

const apiProxy = {
  '/api': { target: apiProxyTarget, changeOrigin: true, secure: false },
  '/sw': { target: apiProxyTarget, ws: true, changeOrigin: true, secure: false },
  '/consumer': { target: apiProxyTarget, changeOrigin: true, secure: false },
  '/health': { target: apiProxyTarget, changeOrigin: true, secure: false },
} as const

// https://vite.dev/config/
export default defineConfig({
  // Dev HTTPS (self-signed). Browser will warn once; accept to use camera APIs on LAN.
  plugins: [react(), basicSsl()],
  server: {
    host: true,
    port: 5173,
    strictPort: true,
    proxy: { ...apiProxy },
  },
  preview: {
    host: true,
    port: 4173,
    strictPort: true,
    proxy: { ...apiProxy },
  },
})
