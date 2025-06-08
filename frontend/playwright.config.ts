import { defineConfig, devices } from '@playwright/test'

/**
 * Playwright端到端测试配置
 * 配置浏览器、测试环境和报告选项
 */
export default defineConfig({
  // 测试目录
  testDir: '../tests/e2e',
  
  // 全局设置
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  
  // 报告配置
  reporter: [
    ['html', { outputFolder: '../tests/reports/e2e_report' }],
    ['json', { outputFile: '../tests/reports/e2e_results.json' }],
    ['junit', { outputFile: '../tests/reports/e2e_junit.xml' }]
  ],
  
  // 全局测试配置
  use: {
    // 基础URL
    baseURL: 'http://localhost:3000',
    
    // 浏览器配置
    headless: true,
    viewport: { width: 1280, height: 720 },
    ignoreHTTPSErrors: true,
    
    // 截图和视频
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    
    // 追踪
    trace: 'on-first-retry',
    
    // 等待配置
    actionTimeout: 10000,
    navigationTimeout: 30000,
    
    // 存储状态
    storageState: undefined
  },

  // 项目配置（不同浏览器）
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] }
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] }
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] }
    },
    
    // 移动端测试
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] }
    },
    {
      name: 'Mobile Safari',
      use: { ...devices['iPhone 12'] }
    },
    
    // 平板测试
    {
      name: 'Tablet',
      use: { ...devices['iPad Pro'] }
    }
  ],

  // Web服务器配置
  webServer: [
    {
      command: 'npm run dev',
      port: 3000,
      reuseExistingServer: !process.env.CI,
      timeout: 120000
    },
    {
      command: 'cd ../backend && source venv/bin/activate && python src/app.py',
      port: 5000,
      reuseExistingServer: !process.env.CI,
      timeout: 120000,
      env: {
        FLASK_ENV: 'testing'
      }
    }
  ],

  // 输出目录
  outputDir: '../tests/reports/e2e_artifacts',
  
  // 超时配置
  timeout: 30000,
  expect: {
    timeout: 5000
  },
  
  // 全局设置和清理
  globalSetup: require.resolve('../tests/e2e/global-setup.ts'),
  globalTeardown: require.resolve('../tests/e2e/global-teardown.ts')
})
