import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  build: {
    target: 'esnext',
    cssCodeSplit: true,
  },
  css: {
    preprocessorOptions: {
      scss: {
        additionalData: '/* 覆盖vuetify样式 */',
      },
    },
    postcss: {
      plugins: [
        {
          postcssPlugin: 'internal:charset-removal',
          AtRule: {
            charset: (atRule) => {
              if (atRule.name === 'charset') {
                atRule.remove()
              }
            },
          },
        },
      ],
    },
  },
  server: {
    port: 8017,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8021',
        changeOrigin: true,
      },
    },
  },
})
