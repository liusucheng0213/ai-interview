import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'

export default defineConfig({
    plugins: [
      vue(),
      // Element Plus 按需自动引入（tree-shaking 移除未使用组件）
      AutoImport({
        resolvers: [ElementPlusResolver()],
        // 自动导入 Vue Composition API（ref/reactive/computed 等），无需手动 import
        imports: ['vue', 'vue-router'],
        dts: false,
      }),
      Components({
        resolvers: [ElementPlusResolver()],
        dts: false,
      }),
    ],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
        '@avatar-digital-human-studio': fileURLToPath(
          new URL('./vendor/avatar_sdk', import.meta.url),
        ),
      },
    },
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: 'http://localhost:8000',
          changeOrigin: true,
        },
      },
    },
    build: {
      // 启用 CSS code splitting，按路由拆分 CSS
      cssCodeSplit: true,
      rollupOptions: {
        output: {
          // 手动分割 vendor chunk，避免单包过大
          manualChunks: {
            // Vue 核心运行时
            'vue-vendor': ['vue', 'vue-router'],
            // Element Plus 单独打包（体积最大）
            'element-plus': ['element-plus'],
            // HTTP 客户端
            'axios': ['axios'],
            'flv': ['flv.js'],
          },
        },
      },
      // 低于 10KB 的模块内联到 JS 中，减少请求数
      assetsInlineLimit: 10240,
      // 提高 chunk 大小警告阈值（Element Plus 本身较大）
      chunkSizeWarningLimit: 1000,
    },
})
