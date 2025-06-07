<template>
  <div class="system-settings">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>系统设置</h2>
    </div>

    <el-row :gutter="20">
      <!-- 基础设置 -->
      <el-col :xs="24" :lg="12">
        <el-card class="settings-card">
          <template #header>
            <div class="card-header">
              <span>基础设置</span>
              <el-button type="primary" size="small" @click="saveBasicSettings">
                保存
              </el-button>
            </div>
          </template>
          
          <el-form :model="basicSettings" label-width="120px">
            <el-form-item label="系统名称">
              <el-input v-model="basicSettings.system_name" />
            </el-form-item>
            <el-form-item label="系统描述">
              <el-input 
                v-model="basicSettings.system_description" 
                type="textarea" 
                :rows="3"
              />
            </el-form-item>
            <el-form-item label="默认CA">
              <el-select v-model="basicSettings.default_ca">
                <el-option label="Let's Encrypt" value="letsencrypt" />
                <el-option label="ZeroSSL" value="zerossl" />
                <el-option label="Buypass" value="buypass" />
              </el-select>
            </el-form-item>
            <el-form-item label="证书续期天数">
              <el-input-number 
                v-model="basicSettings.renewal_days" 
                :min="1" 
                :max="90"
              />
              <span class="form-help">证书过期前多少天开始续期</span>
            </el-form-item>
            <el-form-item label="客户端心跳间隔">
              <el-input-number 
                v-model="basicSettings.heartbeat_interval" 
                :min="60" 
                :max="3600"
              />
              <span class="form-help">客户端发送心跳的间隔时间（秒）</span>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <!-- 邮件设置 -->
      <el-col :xs="24" :lg="12">
        <el-card class="settings-card">
          <template #header>
            <div class="card-header">
              <span>邮件设置</span>
              <div>
                <el-button size="small" @click="testEmail">测试</el-button>
                <el-button type="primary" size="small" @click="saveEmailSettings">
                  保存
                </el-button>
              </div>
            </div>
          </template>
          
          <el-form :model="emailSettings" label-width="120px">
            <el-form-item label="启用邮件通知">
              <el-switch v-model="emailSettings.enabled" />
            </el-form-item>
            <el-form-item label="SMTP服务器">
              <el-input v-model="emailSettings.smtp_server" />
            </el-form-item>
            <el-form-item label="SMTP端口">
              <el-input-number v-model="emailSettings.smtp_port" :min="1" :max="65535" />
            </el-form-item>
            <el-form-item label="用户名">
              <el-input v-model="emailSettings.username" />
            </el-form-item>
            <el-form-item label="密码">
              <el-input 
                v-model="emailSettings.password" 
                type="password" 
                show-password
              />
            </el-form-item>
            <el-form-item label="使用TLS">
              <el-switch v-model="emailSettings.use_tls" />
            </el-form-item>
            <el-form-item label="发件人邮箱">
              <el-input v-model="emailSettings.from_email" />
            </el-form-item>
            <el-form-item label="收件人邮箱">
              <el-input 
                v-model="emailSettings.to_emails" 
                placeholder="多个邮箱用逗号分隔"
              />
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20">
      <!-- 安全设置 -->
      <el-col :xs="24" :lg="12">
        <el-card class="settings-card">
          <template #header>
            <div class="card-header">
              <span>安全设置</span>
              <el-button type="primary" size="small" @click="saveSecuritySettings">
                保存
              </el-button>
            </div>
          </template>
          
          <el-form :model="securitySettings" label-width="120px">
            <el-form-item label="密码最小长度">
              <el-input-number 
                v-model="securitySettings.password_min_length" 
                :min="6" 
                :max="32"
              />
            </el-form-item>
            <el-form-item label="登录失败锁定">
              <el-switch v-model="securitySettings.login_lockout_enabled" />
            </el-form-item>
            <el-form-item label="最大失败次数">
              <el-input-number 
                v-model="securitySettings.max_login_attempts" 
                :min="3" 
                :max="10"
                :disabled="!securitySettings.login_lockout_enabled"
              />
            </el-form-item>
            <el-form-item label="锁定时间">
              <el-input-number 
                v-model="securitySettings.lockout_duration" 
                :min="5" 
                :max="60"
                :disabled="!securitySettings.login_lockout_enabled"
              />
              <span class="form-help">锁定时间（分钟）</span>
            </el-form-item>
            <el-form-item label="会话超时">
              <el-input-number 
                v-model="securitySettings.session_timeout" 
                :min="30" 
                :max="1440"
              />
              <span class="form-help">会话超时时间（分钟）</span>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <!-- 系统信息 -->
      <el-col :xs="24" :lg="12">
        <el-card class="settings-card">
          <template #header>
            <div class="card-header">
              <span>系统信息</span>
              <el-button size="small" :icon="Refresh" @click="refreshSystemInfo">
                刷新
              </el-button>
            </div>
          </template>
          
          <el-descriptions :column="1" border>
            <el-descriptions-item label="系统版本">
              {{ systemInfo.version }}
            </el-descriptions-item>
            <el-descriptions-item label="运行时间">
              {{ systemInfo.uptime }}
            </el-descriptions-item>
            <el-descriptions-item label="CPU使用率">
              <el-progress 
                :percentage="systemInfo.cpu_usage" 
                :color="getProgressColor(systemInfo.cpu_usage)"
              />
            </el-descriptions-item>
            <el-descriptions-item label="内存使用率">
              <el-progress 
                :percentage="systemInfo.memory_usage" 
                :color="getProgressColor(systemInfo.memory_usage)"
              />
            </el-descriptions-item>
            <el-descriptions-item label="磁盘使用率">
              <el-progress 
                :percentage="systemInfo.disk_usage" 
                :color="getProgressColor(systemInfo.disk_usage)"
              />
            </el-descriptions-item>
            <el-descriptions-item label="数据库大小">
              {{ systemInfo.database_size }}
            </el-descriptions-item>
            <el-descriptions-item label="证书总数">
              {{ systemInfo.total_certificates }}
            </el-descriptions-item>
            <el-descriptions-item label="服务器总数">
              {{ systemInfo.total_servers }}
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'

// 响应式数据
const basicSettings = reactive({
  system_name: 'SSL证书自动化管理系统',
  system_description: '安全、高效的证书管理解决方案',
  default_ca: 'letsencrypt',
  renewal_days: 30,
  heartbeat_interval: 300
})

const emailSettings = reactive({
  enabled: false,
  smtp_server: 'smtp.gmail.com',
  smtp_port: 587,
  username: '',
  password: '',
  use_tls: true,
  from_email: '',
  to_emails: ''
})

const securitySettings = reactive({
  password_min_length: 6,
  login_lockout_enabled: true,
  max_login_attempts: 5,
  lockout_duration: 15,
  session_timeout: 120
})

const systemInfo = reactive({
  version: '1.0.0',
  uptime: '3天 12小时 45分钟',
  cpu_usage: 25,
  memory_usage: 45,
  disk_usage: 60,
  database_size: '12.5 MB',
  total_certificates: 24,
  total_servers: 8
})

// 获取进度条颜色
const getProgressColor = (percentage: number) => {
  if (percentage < 50) return '#67c23a'
  if (percentage < 80) return '#e6a23c'
  return '#f56c6c'
}

// 保存基础设置
const saveBasicSettings = async () => {
  try {
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 500))
    ElMessage.success('基础设置已保存')
  } catch (error) {
    console.error('Failed to save basic settings:', error)
    ElMessage.error('保存失败')
  }
}

// 保存邮件设置
const saveEmailSettings = async () => {
  try {
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 500))
    ElMessage.success('邮件设置已保存')
  } catch (error) {
    console.error('Failed to save email settings:', error)
    ElMessage.error('保存失败')
  }
}

// 测试邮件
const testEmail = async () => {
  try {
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 1000))
    ElMessage.success('测试邮件发送成功')
  } catch (error) {
    console.error('Failed to test email:', error)
    ElMessage.error('测试邮件发送失败')
  }
}

// 保存安全设置
const saveSecuritySettings = async () => {
  try {
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 500))
    ElMessage.success('安全设置已保存')
  } catch (error) {
    console.error('Failed to save security settings:', error)
    ElMessage.error('保存失败')
  }
}

// 刷新系统信息
const refreshSystemInfo = async () => {
  try {
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 500))
    
    // 模拟更新数据
    systemInfo.cpu_usage = Math.floor(Math.random() * 100)
    systemInfo.memory_usage = Math.floor(Math.random() * 100)
    systemInfo.disk_usage = Math.floor(Math.random() * 100)
    
    ElMessage.success('系统信息已刷新')
  } catch (error) {
    console.error('Failed to refresh system info:', error)
    ElMessage.error('刷新失败')
  }
}

// 加载设置
const loadSettings = async () => {
  try {
    // 模拟API调用加载设置
    await new Promise(resolve => setTimeout(resolve, 500))
  } catch (error) {
    console.error('Failed to load settings:', error)
  }
}

onMounted(() => {
  loadSettings()
})
</script>

<style scoped>
.system-settings {
  padding: 0;
}

.page-header {
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  color: #303133;
}

.settings-card {
  margin-bottom: 20px;
  height: fit-content;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.form-help {
  font-size: 12px;
  color: #909399;
  margin-left: 10px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .settings-card {
    margin-bottom: 15px;
  }
}
</style>
