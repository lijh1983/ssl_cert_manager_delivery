<template>
  <div class="active-alerts-container">
    <div class="page-header">
      <h1>活跃告警</h1>
      <p class="page-description">查看和处理当前系统中的活跃告警</p>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-cards">
      <el-card class="stat-card critical">
        <div class="stat-content">
          <div class="stat-number">{{ criticalCount }}</div>
          <div class="stat-label">严重告警</div>
        </div>
        <el-icon class="stat-icon"><Warning /></el-icon>
      </el-card>

      <el-card class="stat-card high">
        <div class="stat-content">
          <div class="stat-number">{{ highCount }}</div>
          <div class="stat-label">高级告警</div>
        </div>
        <el-icon class="stat-icon"><InfoFilled /></el-icon>
      </el-card>

      <el-card class="stat-card medium">
        <div class="stat-content">
          <div class="stat-number">{{ mediumCount }}</div>
          <div class="stat-label">中级告警</div>
        </div>
        <el-icon class="stat-icon"><QuestionFilled /></el-icon>
      </el-card>

      <el-card class="stat-card low">
        <div class="stat-content">
          <div class="stat-number">{{ lowCount }}</div>
          <div class="stat-label">低级告警</div>
        </div>
        <el-icon class="stat-icon"><CircleCheck /></el-icon>
      </el-card>
    </div>

    <!-- 操作栏 -->
    <div class="action-bar">
      <el-button 
        icon="Refresh" 
        @click="loadActiveAlerts"
        :loading="loading"
      >
        刷新
      </el-button>

      <el-button 
        type="success" 
        icon="Check"
        @click="batchResolve"
        :disabled="selectedAlerts.length === 0"
        v-if="userStore.user?.role === 'admin'"
      >
        批量解决 ({{ selectedAlerts.length }})
      </el-button>

      <div class="filter-controls">
        <el-select 
          v-model="severityFilter" 
          placeholder="按级别筛选" 
          clearable
          style="width: 120px"
          @change="filterAlerts"
        >
          <el-option label="严重" value="critical" />
          <el-option label="高" value="high" />
          <el-option label="中" value="medium" />
          <el-option label="低" value="low" />
        </el-select>

        <el-select 
          v-model="typeFilter" 
          placeholder="按类型筛选" 
          clearable
          style="width: 150px"
          @change="filterAlerts"
        >
          <el-option label="证书即将过期" value="certificate_expiring" />
          <el-option label="证书已过期" value="certificate_expired" />
          <el-option label="服务器离线" value="server_offline" />
          <el-option label="续期失败" value="certificate_renewal_failed" />
          <el-option label="系统错误" value="system_error" />
        </el-select>
      </div>
    </div>

    <!-- 告警列表 -->
    <el-card class="alerts-card">
      <el-table 
        :data="filteredAlerts" 
        v-loading="loading"
        @selection-change="handleSelectionChange"
        stripe
        style="width: 100%"
      >
        <el-table-column 
          type="selection" 
          width="55"
          v-if="userStore.user?.role === 'admin'"
        />

        <el-table-column prop="severity" label="级别" width="80">
          <template #default="{ row }">
            <el-tag 
              :type="getSeverityTagType(row.severity)" 
              size="small"
            >
              {{ getSeverityText(row.severity) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="title" label="告警标题" min-width="200">
          <template #default="{ row }">
            <div class="alert-title">
              <el-icon class="alert-icon" :class="getSeverityClass(row.severity)">
                <component :is="getSeverityIcon(row.severity)" />
              </el-icon>
              <span>{{ row.title }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="alert_type" label="类型" width="120">
          <template #default="{ row }">
            <el-tag size="small" type="info">{{ getAlertTypeText(row.alert_type) }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="description" label="描述" min-width="250">
          <template #default="{ row }">
            <div class="alert-description">
              {{ row.description }}
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="created_at" label="创建时间" width="160">
          <template #default="{ row }">
            <div class="time-info">
              <div>{{ formatDateTime(row.created_at) }}</div>
              <div class="time-ago">{{ getTimeAgo(row.created_at) }}</div>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="context" label="相关信息" width="200">
          <template #default="{ row }">
            <div class="context-info">
              <div v-if="row.context.domain" class="context-item">
                <span class="context-label">域名:</span>
                <span class="context-value">{{ row.context.domain }}</span>
              </div>
              <div v-if="row.context.server_name" class="context-item">
                <span class="context-label">服务器:</span>
                <span class="context-value">{{ row.context.server_name }}</span>
              </div>
              <div v-if="row.context.days_remaining !== undefined" class="context-item">
                <span class="context-label">剩余:</span>
                <span class="context-value">{{ row.context.days_remaining }}天</span>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button 
              type="success" 
              size="small" 
              icon="Check"
              @click="resolveAlert(row)"
              v-if="userStore.user?.role === 'admin'"
            >
              解决
            </el-button>
            <el-button 
              type="primary" 
              size="small" 
              icon="View"
              @click="viewAlertDetail(row)"
            >
              详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 空状态 -->
      <div v-if="!loading && filteredAlerts.length === 0" class="empty-state">
        <el-empty description="暂无活跃告警">
          <el-button type="primary" @click="loadActiveAlerts">刷新数据</el-button>
        </el-empty>
      </div>
    </el-card>

    <!-- 告警详情对话框 -->
    <el-dialog
      v-model="showDetailDialog"
      title="告警详情"
      width="600px"
    >
      <div v-if="selectedAlert" class="alert-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="告警标题">
            {{ selectedAlert.title }}
          </el-descriptions-item>
          <el-descriptions-item label="告警级别">
            <el-tag :type="getSeverityTagType(selectedAlert.severity)">
              {{ getSeverityText(selectedAlert.severity) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="告警类型">
            {{ getAlertTypeText(selectedAlert.alert_type) }}
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="selectedAlert.status === 'active' ? 'danger' : 'success'">
              {{ selectedAlert.status === 'active' ? '活跃' : '已解决' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">
            {{ formatDateTime(selectedAlert.created_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="最后发送">
            {{ selectedAlert.last_sent_at ? formatDateTime(selectedAlert.last_sent_at) : '未发送' }}
          </el-descriptions-item>
        </el-descriptions>

        <div class="detail-section">
          <h4>告警描述</h4>
          <p>{{ selectedAlert.description }}</p>
        </div>

        <div class="detail-section" v-if="Object.keys(selectedAlert.context).length > 0">
          <h4>上下文信息</h4>
          <el-table :data="contextTableData" size="small">
            <el-table-column prop="key" label="属性" width="150" />
            <el-table-column prop="value" label="值" />
          </el-table>
        </div>
      </div>

      <template #footer>
        <el-button @click="showDetailDialog = false">关闭</el-button>
        <el-button 
          type="success" 
          @click="resolveAlert(selectedAlert)"
          v-if="userStore.user?.role === 'admin' && selectedAlert?.status === 'active'"
        >
          解决告警
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Warning, InfoFilled, QuestionFilled, CircleCheck } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import { alertApi, type Alert } from '@/api/alert'
import { formatDateTime, getTimeAgo } from '@/utils/date'

// 状态管理
const userStore = useUserStore()

// 响应式数据
const loading = ref(false)
const activeAlerts = ref<Alert[]>([])
const selectedAlerts = ref<Alert[]>([])
const severityFilter = ref('')
const typeFilter = ref('')

// 对话框状态
const showDetailDialog = ref(false)
const selectedAlert = ref<Alert | null>(null)

// 自动刷新
let refreshTimer: NodeJS.Timeout | null = null

// 计算属性
const filteredAlerts = computed(() => {
  let alerts = activeAlerts.value

  if (severityFilter.value) {
    alerts = alerts.filter(alert => alert.severity === severityFilter.value)
  }

  if (typeFilter.value) {
    alerts = alerts.filter(alert => alert.alert_type === typeFilter.value)
  }

  return alerts.sort((a, b) => {
    // 按严重程度排序
    const severityOrder = { critical: 4, high: 3, medium: 2, low: 1 }
    const aSeverity = severityOrder[a.severity] || 0
    const bSeverity = severityOrder[b.severity] || 0
    
    if (aSeverity !== bSeverity) {
      return bSeverity - aSeverity
    }
    
    // 按创建时间排序
    return new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime()
  })
})

const criticalCount = computed(() => 
  activeAlerts.value.filter(alert => alert.severity === 'critical').length
)

const highCount = computed(() => 
  activeAlerts.value.filter(alert => alert.severity === 'high').length
)

const mediumCount = computed(() => 
  activeAlerts.value.filter(alert => alert.severity === 'medium').length
)

const lowCount = computed(() => 
  activeAlerts.value.filter(alert => alert.severity === 'low').length
)

const contextTableData = computed(() => {
  if (!selectedAlert.value) return []
  
  return Object.entries(selectedAlert.value.context).map(([key, value]) => ({
    key: getContextKeyText(key),
    value: String(value)
  }))
})

// 方法
const loadActiveAlerts = async () => {
  loading.value = true
  try {
    const response = await alertApi.getActiveAlerts()
    activeAlerts.value = response.data.alerts
  } catch (error) {
    ElMessage.error('加载活跃告警失败')
  } finally {
    loading.value = false
  }
}

const handleSelectionChange = (selection: Alert[]) => {
  selectedAlerts.value = selection
}

const resolveAlert = async (alert: Alert) => {
  try {
    await ElMessageBox.confirm(
      `确定要解决告警"${alert.title}"吗？`,
      '确认解决',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await alertApi.resolveAlert(alert.id)
    ElMessage.success('告警已解决')
    loadActiveAlerts()
    
    if (showDetailDialog.value) {
      showDetailDialog.value = false
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('解决告警失败')
    }
  }
}

const batchResolve = async () => {
  if (selectedAlerts.value.length === 0) return

  try {
    await ElMessageBox.confirm(
      `确定要解决选中的 ${selectedAlerts.value.length} 个告警吗？`,
      '批量解决',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    // 批量解决告警
    const promises = selectedAlerts.value.map(alert => alertApi.resolveAlert(alert.id))
    await Promise.all(promises)
    
    ElMessage.success(`已解决 ${selectedAlerts.value.length} 个告警`)
    selectedAlerts.value = []
    loadActiveAlerts()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('批量解决告警失败')
    }
  }
}

const viewAlertDetail = (alert: Alert) => {
  selectedAlert.value = alert
  showDetailDialog.value = true
}

const filterAlerts = () => {
  // 筛选逻辑在计算属性中处理
}

// 辅助方法
const getSeverityTagType = (severity: string) => {
  const types = {
    low: 'info',
    medium: 'warning',
    high: 'danger',
    critical: 'danger'
  }
  return types[severity] || 'info'
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

const getSeverityClass = (severity: string) => {
  return `severity-${severity}`
}

const getSeverityIcon = (severity: string) => {
  const icons = {
    low: 'CircleCheck',
    medium: 'QuestionFilled',
    high: 'InfoFilled',
    critical: 'Warning'
  }
  return icons[severity] || 'InfoFilled'
}

const getAlertTypeText = (type: string) => {
  const texts = {
    certificate_expiring: '证书即将过期',
    certificate_expired: '证书已过期',
    certificate_renewal_failed: '续期失败',
    server_offline: '服务器离线',
    system_error: '系统错误',
    quota_exceeded: '配额超限'
  }
  return texts[type] || type
}

const getContextKeyText = (key: string) => {
  const texts = {
    domain: '域名',
    server_name: '服务器',
    days_remaining: '剩余天数',
    days_expired: '已过期天数',
    expires_at: '过期时间',
    ca_type: 'CA类型',
    offline_minutes: '离线时长(分钟)',
    last_heartbeat: '最后心跳'
  }
  return texts[key] || key
}

// 启动自动刷新
const startAutoRefresh = () => {
  refreshTimer = setInterval(() => {
    loadActiveAlerts()
  }, 30000) // 每30秒刷新一次
}

// 停止自动刷新
const stopAutoRefresh = () => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
}

// 生命周期
onMounted(() => {
  loadActiveAlerts()
  startAutoRefresh()
})

onUnmounted(() => {
  stopAutoRefresh()
})
</script>

<style scoped>
.active-alerts-container {
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

.stats-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

.stat-card {
  position: relative;
  overflow: hidden;
}

.stat-card.critical {
  border-left: 4px solid #f56c6c;
}

.stat-card.high {
  border-left: 4px solid #e6a23c;
}

.stat-card.medium {
  border-left: 4px solid #409eff;
}

.stat-card.low {
  border-left: 4px solid #67c23a;
}

.stat-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-number {
  font-size: 28px;
  font-weight: 600;
  color: #303133;
}

.stat-label {
  font-size: 14px;
  color: #606266;
}

.stat-icon {
  position: absolute;
  right: 16px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 32px;
  opacity: 0.3;
}

.action-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.filter-controls {
  display: flex;
  gap: 12px;
}

.alerts-card {
  margin-bottom: 20px;
}

.alert-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.alert-icon {
  font-size: 16px;
}

.alert-icon.severity-critical {
  color: #f56c6c;
}

.alert-icon.severity-high {
  color: #e6a23c;
}

.alert-icon.severity-medium {
  color: #409eff;
}

.alert-icon.severity-low {
  color: #67c23a;
}

.alert-description {
  font-size: 14px;
  color: #606266;
  line-height: 1.4;
}

.time-info {
  font-size: 12px;
}

.time-ago {
  color: #909399;
  margin-top: 2px;
}

.context-info {
  font-size: 12px;
}

.context-item {
  margin-bottom: 4px;
}

.context-label {
  color: #909399;
  margin-right: 4px;
}

.context-value {
  color: #303133;
  font-weight: 500;
}

.empty-state {
  padding: 40px;
  text-align: center;
}

.alert-detail {
  padding: 16px 0;
}

.detail-section {
  margin-top: 20px;
}

.detail-section h4 {
  margin: 0 0 12px 0;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.detail-section p {
  margin: 0;
  color: #606266;
  line-height: 1.6;
}
</style>
