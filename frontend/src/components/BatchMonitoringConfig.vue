<template>
  <el-dialog
    v-model="visible"
    title="批量监控配置"
    width="800px"
    @close="handleClose"
  >
    <div class="batch-monitoring-config">
      <div class="selected-certificates">
        <h4>选中的证书 ({{ selectedCertificates.length }})</h4>
        <el-table :data="selectedCertificates" border max-height="200">
          <el-table-column prop="domain" label="域名" min-width="150" />
          <el-table-column prop="status" label="状态" width="100">
            <template #default="scope">
              <el-tag :type="getStatusType(scope.row.status)" size="small">
                {{ getStatusText(scope.row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="当前监控状态" width="120">
            <template #default="scope">
              <el-tag :type="scope.row.monitoring_enabled ? 'success' : 'info'" size="small">
                {{ scope.row.monitoring_enabled ? '已启用' : '已禁用' }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="config-form">
        <h4>批量配置选项</h4>
        <el-form :model="batchConfig" label-width="140px" size="default">
          <!-- 基础监控配置 -->
          <div class="config-section">
            <h5>基础监控</h5>
            <el-form-item label="启用监控">
              <el-radio-group v-model="batchConfig.monitoring_enabled">
                <el-radio :label="true">启用</el-radio>
                <el-radio :label="false">禁用</el-radio>
                <el-radio :label="null">保持不变</el-radio>
              </el-radio-group>
            </el-form-item>

            <el-form-item label="检查频率">
              <el-select v-model="batchConfig.check_frequency" placeholder="选择频率">
                <el-option label="保持不变" :value="null" />
                <el-option label="每小时" value="hourly" />
                <el-option label="每6小时" value="6hourly" />
                <el-option label="每12小时" value="12hourly" />
                <el-option label="每天" value="daily" />
                <el-option label="每周" value="weekly" />
              </el-select>
            </el-form-item>

            <el-form-item label="告警阈值">
              <el-input-number
                v-model="batchConfig.alert_threshold_days"
                :min="1"
                :max="365"
                placeholder="天数"
              />
              <span style="margin-left: 8px">天（留空保持不变）</span>
            </el-form-item>
          </div>

          <!-- 域名监控配置 -->
          <div class="config-section">
            <h5>域名监控</h5>
            <el-form-item label="DNS检查">
              <el-radio-group v-model="batchConfig.dns_check_enabled">
                <el-radio :label="true">启用</el-radio>
                <el-radio :label="false">禁用</el-radio>
                <el-radio :label="null">保持不变</el-radio>
              </el-radio-group>
            </el-form-item>

            <el-form-item label="可达性检查">
              <el-radio-group v-model="batchConfig.reachability_check_enabled">
                <el-radio :label="true">启用</el-radio>
                <el-radio :label="false">禁用</el-radio>
                <el-radio :label="null">保持不变</el-radio>
              </el-radio-group>
            </el-form-item>

            <el-form-item label="检查超时">
              <el-input-number
                v-model="batchConfig.check_timeout"
                :min="5"
                :max="60"
                placeholder="秒"
              />
              <span style="margin-left: 8px">秒（留空保持不变）</span>
            </el-form-item>
          </div>

          <!-- 端口监控配置 -->
          <div class="config-section">
            <h5>端口监控</h5>
            <el-form-item label="SSL检查">
              <el-radio-group v-model="batchConfig.ssl_check_enabled">
                <el-radio :label="true">启用</el-radio>
                <el-radio :label="false">禁用</el-radio>
                <el-radio :label="null">保持不变</el-radio>
              </el-radio-group>
            </el-form-item>

            <el-form-item label="TLS版本检查">
              <el-radio-group v-model="batchConfig.tls_version_check_enabled">
                <el-radio :label="true">启用</el-radio>
                <el-radio :label="false">禁用</el-radio>
                <el-radio :label="null">保持不变</el-radio>
              </el-radio-group>
            </el-form-item>

            <el-form-item label="监控端口">
              <el-select
                v-model="batchConfig.monitored_ports"
                multiple
                filterable
                allow-create
                placeholder="选择端口（留空保持不变）"
                style="width: 100%"
              >
                <el-option label="80 (HTTP)" :value="80" />
                <el-option label="443 (HTTPS)" :value="443" />
                <el-option label="8080 (HTTP备用)" :value="8080" />
                <el-option label="8443 (HTTPS备用)" :value="8443" />
              </el-select>
            </el-form-item>
          </div>

          <!-- 告警配置 -->
          <div class="config-section">
            <h5>告警配置</h5>
            <el-form-item label="邮件告警">
              <el-radio-group v-model="batchConfig.email_alerts_enabled">
                <el-radio :label="true">启用</el-radio>
                <el-radio :label="false">禁用</el-radio>
                <el-radio :label="null">保持不变</el-radio>
              </el-radio-group>
            </el-form-item>

            <el-form-item label="告警邮箱">
              <el-input
                v-model="batchConfig.alert_email"
                placeholder="输入邮箱地址（留空保持不变）"
              />
            </el-form-item>

            <el-form-item label="告警级别">
              <el-select v-model="batchConfig.alert_level" placeholder="选择级别">
                <el-option label="保持不变" :value="null" />
                <el-option label="低" value="low" />
                <el-option label="中" value="medium" />
                <el-option label="高" value="high" />
                <el-option label="紧急" value="critical" />
              </el-select>
            </el-form-item>
          </div>
        </el-form>
      </div>

      <div class="config-preview">
        <h4>配置预览</h4>
        <el-alert
          title="将要应用的配置更改"
          type="info"
          :closable="false"
          show-icon
        >
          <div class="preview-content">
            <div v-for="(value, key) in effectiveChanges" :key="key" class="change-item">
              <strong>{{ getConfigLabel(key) }}:</strong>
              <span class="change-value">{{ formatConfigValue(key, value) }}</span>
            </div>
            <div v-if="Object.keys(effectiveChanges).length === 0" class="no-changes">
              没有配置更改
            </div>
          </div>
        </el-alert>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleClose">取消</el-button>
        <el-button
          type="primary"
          @click="applyBatchConfig"
          :loading="applying"
          :disabled="Object.keys(effectiveChanges).length === 0"
        >
          应用配置 ({{ selectedCertificates.length }} 个证书)
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { certificateApi } from '@/api/certificate'
import type { Certificate } from '@/types/certificate'

interface Props {
  modelValue: boolean
  selectedCertificates: Certificate[]
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  success: []
}>()

// 响应式数据
const applying = ref(false)

// 批量配置表单
const batchConfig = reactive({
  monitoring_enabled: null as boolean | null,
  check_frequency: null as string | null,
  alert_threshold_days: null as number | null,
  dns_check_enabled: null as boolean | null,
  reachability_check_enabled: null as boolean | null,
  ssl_check_enabled: null as boolean | null,
  tls_version_check_enabled: null as boolean | null,
  check_timeout: null as number | null,
  monitored_ports: [] as number[],
  email_alerts_enabled: null as boolean | null,
  alert_email: '',
  alert_level: null as string | null
})

// 计算属性
const visible = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value)
})

const effectiveChanges = computed(() => {
  const changes: Record<string, any> = {}
  
  Object.entries(batchConfig).forEach(([key, value]) => {
    if (value !== null && value !== '' && !(Array.isArray(value) && value.length === 0)) {
      changes[key] = value
    }
  })
  
  return changes
})

// 方法
const getStatusType = (status: string) => {
  switch (status) {
    case 'valid': return 'success'
    case 'expired': return 'danger'
    case 'pending': return 'warning'
    default: return 'info'
  }
}

const getStatusText = (status: string) => {
  switch (status) {
    case 'valid': return '有效'
    case 'expired': return '已过期'
    case 'pending': return '待处理'
    default: return status
  }
}

const getConfigLabel = (key: string) => {
  const labels: Record<string, string> = {
    monitoring_enabled: '启用监控',
    check_frequency: '检查频率',
    alert_threshold_days: '告警阈值',
    dns_check_enabled: 'DNS检查',
    reachability_check_enabled: '可达性检查',
    ssl_check_enabled: 'SSL检查',
    tls_version_check_enabled: 'TLS版本检查',
    check_timeout: '检查超时',
    monitored_ports: '监控端口',
    email_alerts_enabled: '邮件告警',
    alert_email: '告警邮箱',
    alert_level: '告警级别'
  }
  return labels[key] || key
}

const formatConfigValue = (key: string, value: any) => {
  if (typeof value === 'boolean') {
    return value ? '启用' : '禁用'
  }
  
  if (key === 'check_frequency') {
    const frequencies: Record<string, string> = {
      hourly: '每小时',
      '6hourly': '每6小时',
      '12hourly': '每12小时',
      daily: '每天',
      weekly: '每周'
    }
    return frequencies[value] || value
  }
  
  if (key === 'alert_threshold_days') {
    return `${value} 天`
  }
  
  if (key === 'check_timeout') {
    return `${value} 秒`
  }
  
  if (key === 'monitored_ports') {
    return Array.isArray(value) ? value.join(', ') : value
  }
  
  if (key === 'alert_level') {
    const levels: Record<string, string> = {
      low: '低',
      medium: '中',
      high: '高',
      critical: '紧急'
    }
    return levels[value] || value
  }
  
  return value
}

const applyBatchConfig = async () => {
  try {
    applying.value = true
    
    const certificateIds = props.selectedCertificates.map(cert => cert.id)
    
    await certificateApi.batchUpdateMonitoringConfig({
      certificate_ids: certificateIds,
      config: effectiveChanges.value
    })
    
    ElMessage.success(`成功更新 ${certificateIds.length} 个证书的监控配置`)
    emit('success')
    handleClose()
    
  } catch (error) {
    console.error('批量更新监控配置失败:', error)
    ElMessage.error('批量更新监控配置失败')
  } finally {
    applying.value = false
  }
}

const handleClose = () => {
  // 重置表单
  Object.assign(batchConfig, {
    monitoring_enabled: null,
    check_frequency: null,
    alert_threshold_days: null,
    dns_check_enabled: null,
    reachability_check_enabled: null,
    ssl_check_enabled: null,
    tls_version_check_enabled: null,
    check_timeout: null,
    monitored_ports: [],
    email_alerts_enabled: null,
    alert_email: '',
    alert_level: null
  })
  
  emit('update:modelValue', false)
}

// 监听对话框打开，重置表单
watch(() => props.modelValue, (newValue) => {
  if (newValue) {
    // 对话框打开时重置表单
    handleClose()
  }
})
</script>

<style scoped>
.batch-monitoring-config {
  max-height: 600px;
  overflow-y: auto;
}

.selected-certificates {
  margin-bottom: 20px;
}

.config-form {
  margin-bottom: 20px;
}

.config-section {
  margin-bottom: 20px;
  padding: 15px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
}

.config-section h5 {
  margin: 0 0 15px 0;
  color: #303133;
  font-size: 14px;
  font-weight: 600;
}

.config-preview {
  margin-bottom: 20px;
}

.preview-content {
  margin-top: 10px;
}

.change-item {
  margin: 5px 0;
  padding: 5px 0;
  border-bottom: 1px solid #f0f0f0;
}

.change-item:last-child {
  border-bottom: none;
}

.change-value {
  margin-left: 10px;
  color: #409eff;
  font-weight: 500;
}

.no-changes {
  color: #909399;
  font-style: italic;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>
