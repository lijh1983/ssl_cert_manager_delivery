<template>
  <div class="alert-rules-container">
    <div class="page-header">
      <h1>告警规则管理</h1>
      <p class="page-description">配置和管理系统告警规则，确保及时收到重要通知</p>
    </div>

    <!-- 操作栏 -->
    <div class="action-bar">
      <el-button 
        type="primary" 
        icon="Plus" 
        @click="showCreateDialog = true"
        v-if="userStore.user?.role === 'admin'"
      >
        创建规则
      </el-button>
      
      <el-button 
        icon="Refresh" 
        @click="loadAlertRules"
        :loading="loading"
      >
        刷新
      </el-button>

      <el-button 
        icon="Bell" 
        @click="showTestDialog = true"
        v-if="userStore.user?.role === 'admin'"
      >
        测试通知
      </el-button>
    </div>

    <!-- 告警规则列表 -->
    <el-card class="rules-card">
      <el-table 
        :data="alertRules" 
        v-loading="loading"
        stripe
        style="width: 100%"
      >
        <el-table-column prop="name" label="规则名称" min-width="150">
          <template #default="{ row }">
            <div class="rule-name">
              <el-tag 
                :type="getSeverityTagType(row.severity)" 
                size="small"
                class="severity-tag"
              >
                {{ getSeverityText(row.severity) }}
              </el-tag>
              <span>{{ row.name }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="alert_type" label="告警类型" width="150">
          <template #default="{ row }">
            <el-tag size="small">{{ getAlertTypeText(row.alert_type) }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="enabled" label="状态" width="80">
          <template #default="{ row }">
            <el-switch
              v-model="row.enabled"
              @change="toggleRule(row)"
              :disabled="userStore.user?.role !== 'admin'"
            />
          </template>
        </el-table-column>

        <el-table-column prop="notification_providers" label="通知方式" width="150">
          <template #default="{ row }">
            <el-tag 
              v-for="provider in row.notification_providers" 
              :key="provider"
              size="small"
              class="provider-tag"
            >
              {{ getProviderText(provider) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="cooldown_minutes" label="冷却时间" width="100">
          <template #default="{ row }">
            {{ formatCooldown(row.cooldown_minutes) }}
          </template>
        </el-table-column>

        <el-table-column prop="conditions" label="条件" min-width="200">
          <template #default="{ row }">
            <div class="conditions">
              <div v-for="(value, key) in row.conditions" :key="key" class="condition-item">
                <span class="condition-key">{{ getConditionText(key) }}:</span>
                <span class="condition-value">{{ value }}</span>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button 
              type="primary" 
              size="small" 
              icon="Edit"
              @click="editRule(row)"
              v-if="userStore.user?.role === 'admin'"
            >
              编辑
            </el-button>
            <el-button 
              type="danger" 
              size="small" 
              icon="Delete"
              @click="deleteRule(row)"
              v-if="userStore.user?.role === 'admin'"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 创建/编辑规则对话框 -->
    <el-dialog
      v-model="showCreateDialog"
      :title="editingRule ? '编辑告警规则' : '创建告警规则'"
      width="600px"
      @close="resetForm"
    >
      <el-form
        ref="ruleFormRef"
        :model="ruleForm"
        :rules="ruleFormRules"
        label-width="120px"
      >
        <el-form-item label="规则名称" prop="name">
          <el-input v-model="ruleForm.name" placeholder="请输入规则名称" />
        </el-form-item>

        <el-form-item label="告警类型" prop="alert_type">
          <el-select v-model="ruleForm.alert_type" placeholder="请选择告警类型" style="width: 100%">
            <el-option
              v-for="type in alertTypes"
              :key="type.value"
              :label="type.label"
              :value="type.value"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="告警级别" prop="severity">
          <el-select v-model="ruleForm.severity" placeholder="请选择告警级别" style="width: 100%">
            <el-option
              v-for="severity in severityOptions"
              :key="severity.value"
              :label="severity.label"
              :value="severity.value"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="通知方式" prop="notification_providers">
          <el-select 
            v-model="ruleForm.notification_providers" 
            multiple 
            placeholder="请选择通知方式"
            style="width: 100%"
          >
            <el-option
              v-for="provider in availableProviders"
              :key="provider"
              :label="getProviderText(provider)"
              :value="provider"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="冷却时间" prop="cooldown_minutes">
          <el-input-number
            v-model="ruleForm.cooldown_minutes"
            :min="1"
            :max="10080"
            placeholder="分钟"
            style="width: 100%"
          />
          <div class="form-tip">防止重复告警的最小间隔时间</div>
        </el-form-item>

        <!-- 动态条件配置 -->
        <el-form-item label="告警条件">
          <div class="conditions-config">
            <div v-if="ruleForm.alert_type === 'certificate_expiring'" class="condition-group">
              <label>提前天数:</label>
              <el-input-number
                v-model="ruleForm.conditions.days_before_expiry"
                :min="1"
                :max="365"
                placeholder="天"
              />
            </div>
            
            <div v-if="ruleForm.alert_type === 'server_offline'" class="condition-group">
              <label>离线阈值:</label>
              <el-input-number
                v-model="ruleForm.conditions.offline_threshold_minutes"
                :min="1"
                :max="1440"
                placeholder="分钟"
              />
            </div>

            <div class="condition-group">
              <label>检查间隔:</label>
              <el-input-number
                v-model="ruleForm.conditions.check_interval_hours"
                :min="1"
                :max="168"
                placeholder="小时"
              />
            </div>
          </div>
        </el-form-item>

        <el-form-item label="启用规则">
          <el-switch v-model="ruleForm.enabled" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="saveRule" :loading="saving">
          {{ editingRule ? '更新' : '创建' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 测试通知对话框 -->
    <el-dialog
      v-model="showTestDialog"
      title="测试通知"
      width="500px"
    >
      <el-form
        ref="testFormRef"
        :model="testForm"
        label-width="100px"
      >
        <el-form-item label="通知方式" required>
          <el-select v-model="testForm.provider" placeholder="请选择通知方式" style="width: 100%">
            <el-option
              v-for="provider in availableProviders"
              :key="provider"
              :label="getProviderText(provider)"
              :value="provider"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="接收者" required>
          <el-input v-model="testForm.recipient" placeholder="邮箱地址或其他标识" />
        </el-form-item>

        <el-form-item label="测试消息">
          <el-input
            v-model="testForm.message"
            type="textarea"
            :rows="3"
            placeholder="可选，留空将发送默认测试消息"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showTestDialog = false">取消</el-button>
        <el-button type="primary" @click="sendTestNotification" :loading="testing">
          发送测试
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { alertApi } from '@/api/alert'

// 状态管理
const userStore = useUserStore()

// 响应式数据
const loading = ref(false)
const saving = ref(false)
const testing = ref(false)
const alertRules = ref([])
const availableProviders = ref([])

// 对话框状态
const showCreateDialog = ref(false)
const showTestDialog = ref(false)
const editingRule = ref(null)

// 表单数据
const ruleForm = reactive({
  name: '',
  alert_type: '',
  severity: 'medium',
  enabled: true,
  conditions: {},
  notification_providers: [],
  notification_template: '',
  cooldown_minutes: 60
})

const testForm = reactive({
  provider: '',
  recipient: '',
  message: ''
})

// 表单引用
const ruleFormRef = ref()
const testFormRef = ref()

// 选项数据
const alertTypes = [
  { value: 'certificate_expiring', label: '证书即将过期' },
  { value: 'certificate_expired', label: '证书已过期' },
  { value: 'certificate_renewal_failed', label: '证书续期失败' },
  { value: 'server_offline', label: '服务器离线' },
  { value: 'system_error', label: '系统错误' },
  { value: 'quota_exceeded', label: '配额超限' }
]

const severityOptions = [
  { value: 'low', label: '低' },
  { value: 'medium', label: '中' },
  { value: 'high', label: '高' },
  { value: 'critical', label: '严重' }
]

// 表单验证规则
const ruleFormRules = {
  name: [
    { required: true, message: '请输入规则名称', trigger: 'blur' },
    { min: 2, max: 100, message: '长度在 2 到 100 个字符', trigger: 'blur' }
  ],
  alert_type: [
    { required: true, message: '请选择告警类型', trigger: 'change' }
  ],
  severity: [
    { required: true, message: '请选择告警级别', trigger: 'change' }
  ],
  notification_providers: [
    { required: true, message: '请选择至少一种通知方式', trigger: 'change' }
  ]
}

// 方法
const loadAlertRules = async () => {
  loading.value = true
  try {
    const response = await alertApi.getRules()
    alertRules.value = response.data.rules
  } catch (error) {
    ElMessage.error('加载告警规则失败')
  } finally {
    loading.value = false
  }
}

const loadNotificationProviders = async () => {
  try {
    const response = await alertApi.getNotificationProviders()
    availableProviders.value = response.data.providers
  } catch (error) {
    console.error('加载通知提供商失败:', error)
  }
}

const toggleRule = async (rule: any) => {
  try {
    await alertApi.updateRule(rule.id, { enabled: rule.enabled })
    ElMessage.success(`规则已${rule.enabled ? '启用' : '禁用'}`)
  } catch (error) {
    rule.enabled = !rule.enabled // 回滚状态
    ElMessage.error('更新规则状态失败')
  }
}

const editRule = (rule: any) => {
  editingRule.value = rule
  Object.assign(ruleForm, {
    name: rule.name,
    alert_type: rule.alert_type,
    severity: rule.severity,
    enabled: rule.enabled,
    conditions: { ...rule.conditions },
    notification_providers: [...rule.notification_providers],
    notification_template: rule.notification_template,
    cooldown_minutes: rule.cooldown_minutes
  })
  showCreateDialog.value = true
}

const deleteRule = async (rule: any) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除告警规则"${rule.name}"吗？`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await alertApi.deleteRule(rule.id)
    ElMessage.success('删除成功')
    loadAlertRules()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const saveRule = async () => {
  if (!ruleFormRef.value) return

  try {
    await ruleFormRef.value.validate()
    saving.value = true

    // 设置默认模板
    if (!ruleForm.notification_template) {
      if (ruleForm.alert_type.includes('certificate')) {
        ruleForm.notification_template = ruleForm.alert_type
      } else {
        ruleForm.notification_template = 'system_alert'
      }
    }

    if (editingRule.value) {
      await alertApi.updateRule(editingRule.value.id, ruleForm)
      ElMessage.success('更新成功')
    } else {
      await alertApi.createRule(ruleForm)
      ElMessage.success('创建成功')
    }

    showCreateDialog.value = false
    loadAlertRules()
  } catch (error) {
    ElMessage.error(editingRule.value ? '更新失败' : '创建失败')
  } finally {
    saving.value = false
  }
}

const sendTestNotification = async () => {
  if (!testForm.provider || !testForm.recipient) {
    ElMessage.warning('请填写必要信息')
    return
  }

  testing.value = true
  try {
    await alertApi.testNotification(testForm)
    ElMessage.success('测试通知发送成功')
    showTestDialog.value = false
  } catch (error) {
    ElMessage.error('测试通知发送失败')
  } finally {
    testing.value = false
  }
}

const resetForm = () => {
  editingRule.value = null
  Object.assign(ruleForm, {
    name: '',
    alert_type: '',
    severity: 'medium',
    enabled: true,
    conditions: {},
    notification_providers: [],
    notification_template: '',
    cooldown_minutes: 60
  })
  ruleFormRef.value?.resetFields()
}

// 辅助方法
const getSeverityTagType = (severity: string) => {
  const types = {
    low: '',
    medium: 'warning',
    high: 'danger',
    critical: 'danger'
  }
  return types[severity] || ''
}

const getSeverityText = (severity: string) => {
  const texts = {
    low: '低',
    medium: '中',
    high: '高',
    critical: '严重'
  }
  return texts[severity] || severity
}

const getAlertTypeText = (type: string) => {
  const texts = {
    certificate_expiring: '证书即将过期',
    certificate_expired: '证书已过期',
    certificate_renewal_failed: '证书续期失败',
    server_offline: '服务器离线',
    system_error: '系统错误',
    quota_exceeded: '配额超限'
  }
  return texts[type] || type
}

const getProviderText = (provider: string) => {
  const texts = {
    email: '邮件',
    slack: 'Slack',
    dingtalk: '钉钉',
    webhook: 'Webhook'
  }
  return texts[provider] || provider
}

const getConditionText = (key: string) => {
  const texts = {
    days_before_expiry: '提前天数',
    check_interval_hours: '检查间隔(小时)',
    offline_threshold_minutes: '离线阈值(分钟)',
    max_retry_attempts: '最大重试次数'
  }
  return texts[key] || key
}

const formatCooldown = (minutes: number) => {
  if (minutes < 60) {
    return `${minutes}分钟`
  } else if (minutes < 1440) {
    return `${Math.floor(minutes / 60)}小时`
  } else {
    return `${Math.floor(minutes / 1440)}天`
  }
}

// 生命周期
onMounted(() => {
  loadAlertRules()
  loadNotificationProviders()
})
</script>

<style scoped>
.alert-rules-container {
  padding: 20px;
}

.page-header {
  margin-bottom: 20px;
}

.page-header h1 {
  margin: 0 0 8px 0;
  font-size: 24px;
  font-weight: 600;
}

.page-description {
  margin: 0;
  color: #666;
  font-size: 14px;
}

.action-bar {
  margin-bottom: 20px;
  display: flex;
  gap: 12px;
}

.rules-card {
  margin-bottom: 20px;
}

.rule-name {
  display: flex;
  align-items: center;
  gap: 8px;
}

.severity-tag {
  font-size: 12px;
}

.provider-tag {
  margin-right: 4px;
  margin-bottom: 4px;
}

.conditions {
  font-size: 12px;
}

.condition-item {
  margin-bottom: 4px;
}

.condition-key {
  color: #666;
  margin-right: 4px;
}

.condition-value {
  font-weight: 500;
}

.conditions-config {
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  padding: 12px;
  background: #fafafa;
}

.condition-group {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
  gap: 8px;
}

.condition-group:last-child {
  margin-bottom: 0;
}

.condition-group label {
  min-width: 80px;
  font-size: 14px;
  color: #606266;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}
</style>
