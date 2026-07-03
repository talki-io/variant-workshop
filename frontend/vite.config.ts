import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        // 供应商分包：把体积大头（图表/antd/react）拆成独立 chunk，
        // 提升缓存命中与首屏加载（图表仅在打开看板时才请求对应 chunk）。
        manualChunks(id) {
          if (!id.includes('node_modules')) return
          if (id.includes('@ant-design/charts') || id.includes('@antv')) return 'charts'
          if (id.includes('@ant-design/x')) return 'antx'
          if (id.includes('antd') || id.includes('@ant-design/icons') || id.includes('rc-'))
            return 'antd'
          if (id.includes('react')) return 'react'
          return 'vendor'
        },
      },
    },
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    host: true,
    // 前端 fetch 走同源相对 /api，由 Vite 代理到 FastAPI，免 CORS、免硬编域名。
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
