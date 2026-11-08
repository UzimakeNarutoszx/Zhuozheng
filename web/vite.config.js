import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
// apiUrl() prefixes requests with BASE_URL ('/garden/'), so dev needs the same prefix proxied.
const proxy = { '/garden/api': { target: 'http://127.0.0.1:8011', changeOrigin: true, rewrite: p => p.replace(/^\/garden/, '') }, '/garden/health': { target: 'http://127.0.0.1:8011', changeOrigin: true, rewrite: p => p.replace(/^\/garden/, '') }, '/api': { target: 'http://127.0.0.1:8011', changeOrigin: true }, '/health': { target: 'http://127.0.0.1:8011', changeOrigin: true } }
export default defineConfig({ base: '/garden/', plugins: [vue()], server: { proxy } })
