/**
 * Playwright全局设置
 * 在所有测试运行前执行的设置操作
 */

import { chromium, FullConfig } from '@playwright/test'

async function globalSetup(config: FullConfig) {
  console.log('🚀 开始E2E测试全局设置...')
  
  // 等待服务启动
  await waitForServices()
  
  // 创建测试数据
  await setupTestData()
  
  // 创建认证状态
  await setupAuthState()
  
  console.log('✅ E2E测试全局设置完成')
}

/**
 * 等待服务启动
 */
async function waitForServices() {
  console.log('⏳ 等待服务启动...')
  
  const maxRetries = 30
  const retryInterval = 2000
  
  // 等待前端服务
  for (let i = 0; i < maxRetries; i++) {
    try {
      const response = await fetch('http://localhost:3000')
      if (response.ok) {
        console.log('✅ 前端服务已启动')
        break
      }
    } catch (error) {
      if (i === maxRetries - 1) {
        throw new Error('前端服务启动超时')
      }
      await new Promise(resolve => setTimeout(resolve, retryInterval))
    }
  }
  
  // 等待后端服务
  for (let i = 0; i < maxRetries; i++) {
    try {
      const response = await fetch('http://localhost:5000/api/v1/health')
      if (response.ok) {
        console.log('✅ 后端服务已启动')
        break
      }
    } catch (error) {
      if (i === maxRetries - 1) {
        throw new Error('后端服务启动超时')
      }
      await new Promise(resolve => setTimeout(resolve, retryInterval))
    }
  }
}

/**
 * 创建测试数据
 */
async function setupTestData() {
  console.log('📝 创建测试数据...')
  
  try {
    // 创建测试用户
    const createUserResponse = await fetch('http://localhost:5000/api/v1/auth/register', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        username: 'testuser',
        email: 'test@example.com',
        password: 'testpass123',
        role: 'user'
      })
    })
    
    if (createUserResponse.ok) {
      console.log('✅ 测试用户创建成功')
    }
    
    // 创建管理员用户（如果不存在）
    const createAdminResponse = await fetch('http://localhost:5000/api/v1/auth/register', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        username: 'admin',
        email: 'admin@example.com',
        password: 'admin123',
        role: 'admin'
      })
    })
    
    if (createAdminResponse.ok) {
      console.log('✅ 管理员用户创建成功')
    }
    
  } catch (error) {
    console.warn('⚠️ 测试数据创建失败（可能已存在）:', error.message)
  }
}

/**
 * 创建认证状态
 */
async function setupAuthState() {
  console.log('🔐 设置认证状态...')
  
  const browser = await chromium.launch()
  const context = await browser.newContext()
  const page = await context.newPage()
  
  try {
    // 访问登录页面
    await page.goto('http://localhost:3000/login')
    
    // 登录管理员账户
    await page.fill('input[placeholder*="用户名"]', 'admin')
    await page.fill('input[placeholder*="密码"]', 'admin123')
    await page.click('button:has-text("登录")')
    
    // 等待登录成功
    await page.waitForURL('**/dashboard')
    
    // 保存认证状态
    await context.storageState({ path: 'tests/e2e/auth-state.json' })
    
    console.log('✅ 管理员认证状态已保存')
    
    // 创建普通用户认证状态
    await page.goto('http://localhost:3000/login')
    await page.fill('input[placeholder*="用户名"]', 'testuser')
    await page.fill('input[placeholder*="密码"]', 'testpass123')
    await page.click('button:has-text("登录")')
    
    await page.waitForURL('**/dashboard')
    await context.storageState({ path: 'tests/e2e/user-auth-state.json' })
    
    console.log('✅ 普通用户认证状态已保存')
    
  } catch (error) {
    console.warn('⚠️ 认证状态设置失败:', error.message)
  } finally {
    await browser.close()
  }
}

export default globalSetup
