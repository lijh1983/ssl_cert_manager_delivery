<template>
  <div class="domain-monitoring-status">
    <el-card class="status-card">
      <template #header>
        <div class="card-header">
          <span>域名监控状态</span>
          <el-button
            size="small"
            type="primary"
            @click="refreshStatus"
            :loading="refreshing"
          >
            刷新
          </el-button>
        </div>
      </template>

      <div class="status-content">
        <!-- DNS解析状态 -->
        <div class="status-item">
          <div class="status-label">DNS解析状态</div>
          <div class="status-value">
            <el-tag
              :type="getDnsStatusType(certificate.dns_status)"
              size="small"
            >
              {{ getDnsStatusText(certificate.dns_status) }}
            </el-tag>
            <span v-if="certificate.last_dns_check" class="last-check">
              最后检查: {{ formatTime(certificate.last_dns_check) }}
            </span>
          </div>
        </div>

        <!-- 域名可达性 -->
        <div class="status-item">
          <div class="status-label">域名可达性</div>
          <div class="status-value">
            <el-tag
              :type="certificate.domain_reachable ? 'success' : 'danger'"
              size="small"
            >
              {{ certificate.domain_reachable ? '可达' : '不可达' }}
            </el-tag>
            <span v-if="certificate.last_reachability_check" class="last-check">
              最后检查: {{ formatTime(certificate.last_reachability_check) }}
            </span>
          </div>
        </div>

        <!-- 监控配置 -->
        <div class="status-item">
          <div class="status-label">监控状态</div>
          <div class="status-value">
            <el-switch
              v-model="monitoringEnabled"
              @change="updateMonitoringStatus"
              :loading="updating"
              active-text="启用"
              inactive-text="禁用"
            />
          </div>
        </div>

        <!-- 检查频率 -->
        <div class="status-item">
          <div class="status-label">检查频率</div>
          <div class="status-value">
            <el-select
              v-model="checkFrequency"
              @change="updateCheckFrequency"
              size="small"
              style="width: 120px"
            >
              <el-option label="每小时" value="hourly" />
              <el-option label="每6小时" value="6hourly" />
              <el-option label="每12小时" value="12hourly" />
              <el-option label="每天" value="daily" />
              <el-option label="每周" value="weekly" />
            </el-select>
          </div>
        </div>

        <!-- 告警阈值 -->
        <div class="status-item">
          <div class="status-label">告警阈值</div>
          <div class="status-value">
            <el-input-number
              v-model="alertThreshold"
              @change="updateAlertThreshold"
              :min="1"
              :max="365"
              size="small"
              style="width: 120px"
            />
            <span style="margin-left: 5px">天</span>
          </div>
        </div>
      </div>

      <!-- 监控历史 -->
      <div class="monitoring-history">
        <h4>最近监控记录</h4>
        <el-table
          :data="monitoringHistory"
          size="small"
          max-height="200"
          v-loading="loadingHistory"
        >
          <el-table-column prop="check_type" label="检查类型" width="100">
            <template #default="scope">
              <el-tag size="small">
                {{ getCheckTypeText(scope.row.check_type) }}
              </el-tag>
            </template>
          </el-table-column>
          
          <el-table-column prop="status" label="状态" width="80">
            <template #default="scope">
              <el-tag
                :type="scope.row.status === 'success' ? 'success' : 'danger'"
                size="small"
              >
                {{ scope.row.status === 'success' ? '成功' : '失败' }}
              </el-tag>
            </template>
          </el-table-column>
          
          <el-table-column prop="response_time" label="响应时间" width="100">
            <template #default="scope">
              <span v-if="scope.row.response_time">
                {{ scope.row.response_time }}ms
              </span>
              <span v-else>-</span>
            </template>
          </el-table-column>
          
          <el-table-column prop="created_at" label="检查时间" min-width="150">
            <template #default="scope">
              {{ formatTime(scope.row.created_at) }}
            </template>
          </el-table-column>
          
          <el-table-column prop="error_message" label="错误信息" min-width="200">
            <template #default="scope">
              <span v-if="scope.row.error_message" class="error-message">
                {{ scope.row.error_message }}
              </span>
              <span v-else>-</span>
            </template>
          </el-table-column>
        </el-table>

        <div v-if="monitoringHistory.length === 0 && !loadingHistory" class="no-history">
          暂无监控记录
        </div>
      </div>

      <!-- 手动检查 -->
      <div class="manual-check">
        <h4>手动检查</h4>
        <div class="check-buttons">
          <el-button
            size="small"
            @click="manualCheck('dns')"
            :loading="checking.dns"
          >
            DNS检查
          </el-button>
          
          <el-button
            size="small"
            @click="manualCheck('reachability')"
            :loading="checking.reachability"
          >
            可达性检查
          </el-button>
          
          <el-button
            size="small"
            type="primary"
            @click="manualCheck('all')"
            :loading="checking.all"
          >
            全面检查
          </el-button>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { certificateApi } from '@/api/certificate'
import type { Certificate } from '@/types/certificate'
import dayjs from 'dayjs'

interface Props {
  certificate: Certificate
}

const props = defineProps<Props>()
const emit = defineEmits<{
  updated: [certificate: Certificate]
}>()

// 响应式数据
const refreshing = ref(false)
const updating = ref(false)
const loadingHistory = ref(false)
const monitoringHistory = ref([])

const checking = reactive({
  dns: false,
  reachability: false,
  all: false
})

// 计算属性
const monitoringEnabled = computed({
  get: () => props.certificate.monitoring_enabled || false,
  set: (value: boolean) => {
    // 这里会触发 updateMonitoringStatus 方法
  }
})

const checkFrequency = computed({
  get: () => props.certificate.check_frequency || 'daily',
  set: (value: string) => {
    // 这里会触发 updateCheckFrequency 方法
  }
})

const alertThreshold = computed({
  get: () => props.certificate.alert_threshold_days || 30,
  set: (value: number) => {
    // 这里会触发 updateAlertThreshold 方法
  }
})

// 方法
const getDnsStatusType = (status?: string): string => {
  switch (status) {
    case 'resolved': return 'success'
    case 'failed': return 'danger'
    case 'timeout': return 'warning'
    default: return 'info'
  }
}

const getDnsStatusText = (status?: string): string => {
  switch (status) {
    case 'resolved': return '解析成功'
    case 'failed': return '解析失败'
    case 'timeout': return '解析超时'
    case 'error': return '解析错误'
    default: return '未知'
  }
}

const getCheckTypeText = (type: string): string => {
  switch (type) {
    case 'dns': return 'DNS'
    case 'reachability': return '可达性'
    default: return type
  }
}

const formatTime = (time?: string): string => {
  if (!time) return '未知'
  return dayjs(time).format('YYYY-MM-DD HH:mm:ss')
}

const refreshStatus = async () => {
  try {
    refreshing.value = true
    // 重新获取证书信息
    const response = await certificateApi.getDetail(props.certificate.id)
    emit('updated', response.data)
    
    // 刷新监控历史
    await fetchMonitoringHistory()
    
  } catch (error) {
    console.error('刷新状态失败:', error)
    ElMessage.error('刷新状态失败')
  } finally {
    refreshing.value = false
  }
}

const updateMonitoringStatus = async (enabled: boolean) => {
  try {
    updating.value = true
    await certificateApi.updateMonitoringConfig(props.certificate.id, {
      monitoring_enabled: enabled
    })
    
    ElMessage.success(enabled ? '监控已启用' : '监控已禁用')
    emit('updated', { ...props.certificate, monitoring_enabled: enabled })
    
  } catch (error) {
    console.error('更新监控状态失败:', error)
    ElMessage.error('更新监控状态失败')
  } finally {
    updating.value = false
  }
}

const updateCheckFrequency = async (frequency: string) => {
  try {
    await certificateApi.updateMonitoringConfig(props.certificate.id, {
      check_frequency: frequency
    })
    
    ElMessage.success('检查频率已更新')
    emit('updated', { ...props.certificate, check_frequency: frequency })
    
  } catch (error) {
    console.error('更新检查频率失败:', error)
    ElMessage.error('更新检查频率失败')
  }
}

const updateAlertThreshold = async (threshold: number) => {
  try {
    await certificateApi.updateMonitoringConfig(props.certificate.id, {
      alert_threshold_days: threshold
    })
    
    ElMessage.success('告警阈值已更新')
    emit('updated', { ...props.certificate, alert_threshold_days: threshold })
    
  } catch (error) {
    console.error('更新告警阈值失败:', error)
    ElMessage.error('更新告警阈值失败')
  }
}

const fetchMonitoringHistory = async () => {
  try {
    loadingHistory.value = true
    const response = await certificateApi.getDomainMonitoringHistory(props.certificate.id)
    monitoringHistory.value = response.data.history || []
    
  } catch (error) {
    console.error('获取监控历史失败:', error)
  } finally {
    loadingHistory.value = false
  }
}

const manualCheck = async (type: 'dns' | 'reachability' | 'all') => {
  try {
    checking[type] = true
    
    let checkTypes = []
    if (type === 'dns') {
      checkTypes = ['dns']
    } else if (type === 'reachability') {
      checkTypes = ['reachability']
    } else {
      checkTypes = ['dns', 'reachability']
    }
    
    await certificateApi.manualDomainCheck(props.certificate.id, {
      check_types: checkTypes
    })
    
    ElMessage.success('检查任务已启动')
    
    // 延迟刷新状态
    setTimeout(() => {
      refreshStatus()
    }, 2000)
    
  } catch (error) {
    console.error('手动检查失败:', error)
    ElMessage.error('手动检查失败')
  } finally {
    checking[type] = false
  }
}

onMounted(() => {
  fetchMonitoringHistory()
})
</script>

<style scoped>
.domain-monitoring-status {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.status-content {
  margin-bottom: 20px;
}

.status-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid #f0f0f0;
}

.status-item:last-child {
  border-bottom: none;
}

.status-label {
  font-weight: 500;
  color: #303133;
  min-width: 100px;
}

.status-value {
  display: flex;
  align-items: center;
  gap: 10px;
}

.last-check {
  font-size: 12px;
  color: #909399;
}

.monitoring-history {
  margin: 20px 0;
}

.monitoring-history h4 {
  margin: 0 0 10px 0;
  color: #303133;
}

.no-history {
  text-align: center;
  color: #909399;
  padding: 20px;
}

.error-message {
  color: #f56c6c;
  font-size: 12px;
}

.manual-check {
  margin-top: 20px;
}

.manual-check h4 {
  margin: 0 0 10px 0;
  color: #303133;
}

.check-buttons {
  display: flex;
  gap: 10px;
}
</style>
