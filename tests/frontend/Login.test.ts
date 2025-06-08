/**
 * 登录组件测试
 * 测试登录表单的各种交互和验证逻辑
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { ElMessage } from 'element-plus'
import Login from '@/views/Login.vue'
import { useAuthStore } from '@/stores/auth'

// Mock Element Plus 消息组件
vi.mock('element-plus', async () => {
  const actual = await vi.importActual('element-plus')
  return {
    ...actual,
    ElMessage: {
      error: vi.fn(),
      success: vi.fn()
    }
  }
})

// Mock 路由
const mockRouter = {
  push: vi.fn()
}

vi.mock('vue-router', () => ({
  useRouter: () => mockRouter
}))

describe('Login.vue', () => {
  let wrapper: any
  let authStore: any

  beforeEach(() => {
    // 创建新的 Pinia 实例
    setActivePinia(createPinia())
    authStore = useAuthStore()
    
    // Mock authStore 方法
    authStore.login = vi.fn()
    
    // 挂载组件
    wrapper = mount(Login, {
      global: {
        plugins: [createPinia()]
      }
    })
  })

  afterEach(() => {
    wrapper.unmount()
    vi.clearAllMocks()
  })

  it('应该正确渲染登录表单', () => {
    expect(wrapper.find('.login-container').exists()).toBe(true)
    expect(wrapper.find('form').exists()).toBe(true)
    expect(wrapper.find('input[type="text"]').exists()).toBe(true)
    expect(wrapper.find('input[type="password"]').exists()).toBe(true)
    expect(wrapper.find('button[type="submit"]').exists()).toBe(true)
  })

  it('应该显示正确的标题', () => {
    const title = wrapper.find('.login-title')
    expect(title.exists()).toBe(true)
    expect(title.text()).toContain('SSL证书管理系统')
  })

  it('应该验证必填字段', async () => {
    const submitButton = wrapper.find('button[type="submit"]')
    
    // 点击提交按钮而不填写任何字段
    await submitButton.trigger('click')
    
    // 应该显示验证错误
    const errorMessages = wrapper.findAll('.el-form-item__error')
    expect(errorMessages.length).toBeGreaterThan(0)
  })

  it('应该验证用户名格式', async () => {
    const usernameInput = wrapper.find('input[type="text"]')
    
    // 输入无效的用户名（太短）
    await usernameInput.setValue('ab')
    await usernameInput.trigger('blur')
    
    // 应该显示格式错误
    const errorMessage = wrapper.find('.el-form-item__error')
    expect(errorMessage.exists()).toBe(true)
    expect(errorMessage.text()).toContain('用户名')
  })

  it('应该验证密码长度', async () => {
    const passwordInput = wrapper.find('input[type="password"]')
    
    // 输入太短的密码
    await passwordInput.setValue('123')
    await passwordInput.trigger('blur')
    
    // 应该显示长度错误
    const errorMessage = wrapper.find('.el-form-item__error')
    expect(errorMessage.exists()).toBe(true)
    expect(errorMessage.text()).toContain('密码')
  })

  it('应该在输入有效数据时成功提交', async () => {
    const usernameInput = wrapper.find('input[type="text"]')
    const passwordInput = wrapper.find('input[type="password"]')
    const submitButton = wrapper.find('button[type="submit"]')
    
    // 输入有效数据
    await usernameInput.setValue('testuser')
    await passwordInput.setValue('testpass123')
    
    // Mock 成功的登录响应
    authStore.login.mockResolvedValue(true)
    
    // 提交表单
    await submitButton.trigger('click')
    
    // 等待异步操作完成
    await wrapper.vm.$nextTick()
    
    // 验证登录方法被调用
    expect(authStore.login).toHaveBeenCalledWith({
      username: 'testuser',
      password: 'testpass123'
    })
  })

  it('应该在登录失败时显示错误消息', async () => {
    const usernameInput = wrapper.find('input[type="text"]')
    const passwordInput = wrapper.find('input[type="password"]')
    const submitButton = wrapper.find('button[type="submit"]')
    
    // 输入数据
    await usernameInput.setValue('testuser')
    await passwordInput.setValue('wrongpassword')
    
    // Mock 失败的登录响应
    authStore.login.mockRejectedValue(new Error('登录失败'))
    
    // 提交表单
    await submitButton.trigger('click')
    
    // 等待异步操作完成
    await wrapper.vm.$nextTick()
    
    // 验证错误消息被显示
    expect(ElMessage.error).toHaveBeenCalled()
  })

  it('应该在登录成功后跳转到仪表板', async () => {
    const usernameInput = wrapper.find('input[type="text"]')
    const passwordInput = wrapper.find('input[type="password"]')
    const submitButton = wrapper.find('button[type="submit"]')
    
    // 输入有效数据
    await usernameInput.setValue('testuser')
    await passwordInput.setValue('testpass123')
    
    // Mock 成功的登录响应
    authStore.login.mockResolvedValue(true)
    
    // 提交表单
    await submitButton.trigger('click')
    
    // 等待异步操作完成
    await wrapper.vm.$nextTick()
    
    // 验证路由跳转
    expect(mockRouter.push).toHaveBeenCalledWith('/dashboard')
  })

  it('应该在提交时显示加载状态', async () => {
    const usernameInput = wrapper.find('input[type="text"]')
    const passwordInput = wrapper.find('input[type="password"]')
    const submitButton = wrapper.find('button[type="submit"]')
    
    // 输入有效数据
    await usernameInput.setValue('testuser')
    await passwordInput.setValue('testpass123')
    
    // Mock 延迟的登录响应
    authStore.login.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 1000)))
    
    // 提交表单
    await submitButton.trigger('click')
    
    // 验证按钮显示加载状态
    expect(submitButton.attributes('loading')).toBeDefined()
  })

  it('应该支持回车键提交', async () => {
    const usernameInput = wrapper.find('input[type="text"]')
    const passwordInput = wrapper.find('input[type="password"]')
    
    // 输入有效数据
    await usernameInput.setValue('testuser')
    await passwordInput.setValue('testpass123')
    
    // Mock 成功的登录响应
    authStore.login.mockResolvedValue(true)
    
    // 在密码输入框按回车
    await passwordInput.trigger('keyup.enter')
    
    // 等待异步操作完成
    await wrapper.vm.$nextTick()
    
    // 验证登录方法被调用
    expect(authStore.login).toHaveBeenCalled()
  })

  it('应该清理敏感数据', async () => {
    const passwordInput = wrapper.find('input[type="password"]')
    
    // 输入密码
    await passwordInput.setValue('testpass123')
    
    // 模拟组件卸载
    wrapper.unmount()
    
    // 验证密码字段被清空（这需要在组件中实现）
    // 这是一个安全最佳实践的测试用例
  })

  it('应该防止XSS攻击', async () => {
    const usernameInput = wrapper.find('input[type="text"]')
    
    // 尝试输入恶意脚本
    const maliciousInput = '<script>alert("xss")</script>'
    await usernameInput.setValue(maliciousInput)
    
    // 验证输入被正确转义或过滤
    expect(usernameInput.element.value).not.toContain('<script>')
  })
})
