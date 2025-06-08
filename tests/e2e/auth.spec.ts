/**
 * 端到端认证测试
 * 使用Playwright测试完整的用户认证流程
 */

import { test, expect } from '@playwright/test'

test.describe('用户认证流程', () => {
  test.beforeEach(async ({ page }) => {
    // 访问登录页面
    await page.goto('/login')
  })

  test('应该显示登录页面', async ({ page }) => {
    // 验证页面标题
    await expect(page).toHaveTitle(/SSL证书管理系统/)
    
    // 验证登录表单元素
    await expect(page.locator('.login-container')).toBeVisible()
    await expect(page.locator('input[placeholder*="用户名"]')).toBeVisible()
    await expect(page.locator('input[placeholder*="密码"]')).toBeVisible()
    await expect(page.locator('button:has-text("登录")')).toBeVisible()
  })

  test('应该验证必填字段', async ({ page }) => {
    // 点击登录按钮而不填写任何字段
    await page.click('button:has-text("登录")')
    
    // 验证错误消息
    await expect(page.locator('.el-form-item__error')).toBeVisible()
  })

  test('应该在输入无效凭据时显示错误', async ({ page }) => {
    // 输入无效凭据
    await page.fill('input[placeholder*="用户名"]', 'invaliduser')
    await page.fill('input[placeholder*="密码"]', 'invalidpass')
    
    // 点击登录
    await page.click('button:has-text("登录")')
    
    // 验证错误消息
    await expect(page.locator('.el-message--error')).toBeVisible()
  })

  test('应该成功登录并跳转到仪表板', async ({ page }) => {
    // 输入有效凭据（需要先创建测试用户或使用默认管理员账户）
    await page.fill('input[placeholder*="用户名"]', 'admin')
    await page.fill('input[placeholder*="密码"]', 'admin123')
    
    // 点击登录
    await page.click('button:has-text("登录")')
    
    // 等待跳转到仪表板
    await page.waitForURL('/dashboard')
    
    // 验证仪表板页面元素
    await expect(page.locator('.layout-container')).toBeVisible()
    await expect(page.locator('.sidebar-menu')).toBeVisible()
    await expect(page.locator('text=仪表盘')).toBeVisible()
  })

  test('应该在登录后显示用户信息', async ({ page }) => {
    // 登录
    await page.fill('input[placeholder*="用户名"]', 'admin')
    await page.fill('input[placeholder*="密码"]', 'admin123')
    await page.click('button:has-text("登录")')
    
    // 等待跳转
    await page.waitForURL('/dashboard')
    
    // 验证用户下拉菜单
    await expect(page.locator('.user-dropdown')).toBeVisible()
    await expect(page.locator('.username')).toContainText('admin')
  })

  test('应该支持登出功能', async ({ page }) => {
    // 先登录
    await page.fill('input[placeholder*="用户名"]', 'admin')
    await page.fill('input[placeholder*="密码"]', 'admin123')
    await page.click('button:has-text("登录")')
    await page.waitForURL('/dashboard')
    
    // 点击用户下拉菜单
    await page.click('.user-dropdown')
    
    // 点击退出登录
    await page.click('text=退出登录')
    
    // 确认退出
    await page.click('button:has-text("确定")')
    
    // 验证跳转回登录页面
    await page.waitForURL('/login')
    await expect(page.locator('.login-container')).toBeVisible()
  })

  test('应该在未登录时重定向到登录页面', async ({ page }) => {
    // 直接访问需要认证的页面
    await page.goto('/dashboard')
    
    // 应该被重定向到登录页面
    await page.waitForURL('/login')
    await expect(page.locator('.login-container')).toBeVisible()
  })

  test('应该记住登录状态', async ({ page, context }) => {
    // 登录
    await page.fill('input[placeholder*="用户名"]', 'admin')
    await page.fill('input[placeholder*="密码"]', 'admin123')
    await page.click('button:has-text("登录")')
    await page.waitForURL('/dashboard')
    
    // 创建新页面（模拟新标签页）
    const newPage = await context.newPage()
    await newPage.goto('/dashboard')
    
    // 应该直接显示仪表板，而不是重定向到登录页面
    await expect(newPage.locator('.layout-container')).toBeVisible()
  })

  test('应该在令牌过期时重新登录', async ({ page }) => {
    // 这个测试需要模拟令牌过期的情况
    // 可以通过修改本地存储中的令牌来模拟
    
    // 先登录
    await page.fill('input[placeholder*="用户名"]', 'admin')
    await page.fill('input[placeholder*="密码"]', 'admin123')
    await page.click('button:has-text("登录")')
    await page.waitForURL('/dashboard')
    
    // 模拟令牌过期（设置一个无效的令牌）
    await page.evaluate(() => {
      localStorage.setItem('ssl_cert_manager_token', 'invalid_token')
    })
    
    // 刷新页面
    await page.reload()
    
    // 应该被重定向到登录页面
    await page.waitForURL('/login')
    await expect(page.locator('.login-container')).toBeVisible()
  })

  test('应该防止SQL注入攻击', async ({ page }) => {
    // 尝试SQL注入攻击
    const maliciousInput = "'; DROP TABLE users; --"
    
    await page.fill('input[placeholder*="用户名"]', maliciousInput)
    await page.fill('input[placeholder*="密码"]', 'testpass')
    await page.click('button:has-text("登录")')
    
    // 应该显示登录失败，而不是系统错误
    await expect(page.locator('.el-message--error')).toBeVisible()
    
    // 页面应该仍然可用
    await expect(page.locator('.login-container')).toBeVisible()
  })

  test('应该防止XSS攻击', async ({ page }) => {
    // 尝试XSS攻击
    const maliciousInput = '<script>alert("xss")</script>'
    
    await page.fill('input[placeholder*="用户名"]', maliciousInput)
    
    // 验证脚本没有被执行
    // 如果XSS攻击成功，会弹出alert对话框
    const alertPromise = page.waitForEvent('dialog', { timeout: 1000 }).catch(() => null)
    const alert = await alertPromise
    
    // 不应该有alert对话框
    expect(alert).toBeNull()
  })

  test('应该限制登录尝试次数', async ({ page }) => {
    // 多次尝试错误登录
    for (let i = 0; i < 6; i++) {
      await page.fill('input[placeholder*="用户名"]', 'testuser')
      await page.fill('input[placeholder*="密码"]', 'wrongpass')
      await page.click('button:has-text("登录")')
      
      // 等待响应
      await page.waitForTimeout(500)
    }
    
    // 第6次尝试应该被限流
    await expect(page.locator('text=请求过于频繁')).toBeVisible()
  })

  test('应该在移动设备上正确显示', async ({ page }) => {
    // 设置移动设备视口
    await page.setViewportSize({ width: 375, height: 667 })
    
    // 验证移动端布局
    await expect(page.locator('.login-container')).toBeVisible()
    
    // 验证表单在移动端的可用性
    await page.fill('input[placeholder*="用户名"]', 'admin')
    await page.fill('input[placeholder*="密码"]', 'admin123')
    await page.click('button:has-text("登录")')
    
    await page.waitForURL('/dashboard')
    
    // 验证移动端导航
    await expect(page.locator('.menu-toggle')).toBeVisible()
  })
})
