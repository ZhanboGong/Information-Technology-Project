import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue' // 确保这里是 @vitejs/plugin-vue
import path from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      // 设置 @ 符号指向 src 目录，方便导入
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    proxy: {
      // 解决你之前的 404 问题
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        secure: false,
      }
    }
  }
})