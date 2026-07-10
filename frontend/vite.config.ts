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
        //
        // ⚠️ 必须按「包名」精确分组，不能用 id.includes() 子串匹配。
        // 曾经的写法把 @ant-design/cssinjs、@ant-design/colors 这类既不含 "antd"
        // 也不含 "rc-" 的包漏进 vendor，而它们反过来依赖 antd 和 react，于是
        // react → vendor → antd → react 形成跨 chunk 循环引用。运行时 antd 会在
        // React 初始化完成前读 React.version，报
        // "Cannot read properties of undefined (reading 'version')" 并白屏。
        // 开发模式不走分包，所以只有生产构建会炸。
        manualChunks(id) {
          if (!id.includes('node_modules')) return
          const seg = id.split('node_modules/').pop()!.split('/')
          const pkg = seg[0].startsWith('@') ? `${seg[0]}/${seg[1]}` : seg[0]

          // React 运行时整体一个 chunk：拆散 scheduler / react-is 会让
          // 依赖它们的 chunk 在初始化前读到 undefined。
          if (['react', 'react-dom', 'scheduler', 'react-is'].includes(pkg)) return 'react'

          // 图表是体积大头（~977KB），只有看板用到。
          // 必须排在下面 @ant-design/* 兜底之前，且要连 charts-util 一起收——
          // 它依赖 @antv，落进 antd chunk 会造成 antd ↔ charts 循环。
          if (
            pkg.startsWith('@antv/') ||
            pkg.startsWith('@ant-design/charts') ||
            pkg === '@ant-design/plots' ||
            pkg === '@ant-design/graphs'
          )
            return 'charts'

          if (pkg === '@ant-design/x') return 'antx'

          // antd 生态整体收在一起：antd 本体 + 其余 @ant-design/* + rc-* + @rc-component/*
          // （@rc-component 是 rc 组件的新 scope，漏掉它会掉进 vendor 而形成循环）
          if (
            pkg === 'antd' ||
            pkg.startsWith('@ant-design/') ||
            pkg.startsWith('rc-') ||
            pkg.startsWith('@rc-component/')
          )
            return 'antd'

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
