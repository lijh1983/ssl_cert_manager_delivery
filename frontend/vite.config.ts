import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

// https://vitejs.dev/config/
export default defineConfig(({ command, mode }) => {
  // 加载环境变量
  const env = loadEnv(mode, process.cwd(), '')

  return {
    plugins: [vue()],
    resolve: {
      alias: {
        '@': resolve(__dirname, 'src')
      }
    },
    build: {
      target: 'es2015',
      outDir: 'dist',
      assetsDir: 'assets',
      minify: env.VITE_BUILD_MINIFY !== 'false' ? 'terser' : false,
      sourcemap: env.VITE_BUILD_SOURCEMAP === 'true',
      terserOptions: {
        compress: {
          drop_console: mode === 'production',
          drop_debugger: mode === 'production'
        }
      },
      rollupOptions: {
        output: {
          manualChunks: {
            'vendor': ['vue', 'vue-router', 'pinia'],
            'element-plus': ['element-plus'],
            'echarts': ['echarts']
          }
        }
      }
    },
    server: {
      host: env.VITE_DEV_SERVER_HOST || '0.0.0.0',
      port: parseInt(env.VITE_DEV_SERVER_PORT) || 3000,
      open: env.VITE_DEV_SERVER_OPEN === 'true',
      cors: env.VITE_DEV_SERVER_CORS !== 'false',
      proxy: env.VITE_PROXY_ENABLED !== 'false' ? {
        '/api': {
          target: env.VITE_PROXY_TARGET || 'http://localhost:5000',
          changeOrigin: true,
          secure: false,
          rewrite: (path) => path.replace(/^\/api/, '/api')
        }
      } : undefined
    },
    preview: {
      port: parseInt(env.VITE_DEV_SERVER_PORT) || 3000
    },
    define: {
      __APP_VERSION__: JSON.stringify(env.VITE_APP_VERSION || '1.0.0'),
      __BUILD_TIME__: JSON.stringify(new Date().toISOString())
    }
  }
})
