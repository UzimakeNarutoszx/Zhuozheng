import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
// apiUrl() prefixes requests with BASE_URL ('/zhuozheng/'), so dev needs the same prefix proxied.
const proxy = { '/zhuozheng/api': { target: 'http://127.0.0.1:8011', changeOrigin: true, rewrite: p => p.replace(/^\/zhuozheng/, '') }, '/zhuozheng/health': { target: 'http://127.0.0.1:8011', changeOrigin: true, rewrite: p => p.replace(/^\/zhuozheng/, '') }, '/api': { target: 'http://127.0.0.1:8011', changeOrigin: true }, '/health': { target: 'http://127.0.0.1:8011', changeOrigin: true } }
export default defineConfig({ base: '/zhuozheng/', plugins: [vue()], server: { proxy } })
