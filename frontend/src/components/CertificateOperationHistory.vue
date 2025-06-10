<template>
  <div class="certificate-operation-history">
    <el-card class="history-card">
      <template #header>
        <div class="card-header">
          <span>操作历史</span>
          <div class="header-actions">
            <el-select
              v-model="filterType"
              @change="fetchHistory"
              size="small"
              placeholder="操作类型"
              style="width: 120px"
            >
              <el-option label="全部" value="" />
              <el-option label="手动检测" value="manual_check" />
              <el-option label="深度扫描" value="deep_scan" />
              <el-option label="证书续期" value="renewal" />
              <el-option label="导入操作" value="import" />
              <el-option label="导出操作" value="export" />
            </el-select>
            
            <el-button
              size="small"
              @click="refreshHistory"
              :loading="loading"
            >
              刷新
            </el-button>
          </div>
        </div>
      </template>

      <div class="history-content" v-loading="loading">
        <!-- 操作统计 -->
        <div class="operation-stats">
          <el-row :gutter="20">
            <el-col :span="6">
              <div class="stat-item">
                <div class="stat-value">{{ stats.total }}</div>
                <div class="stat-label">总操作数</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="stat-item">
                <div class="stat-value success">{{ stats.completed }}</div>
                <div class="stat-label">成功</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="stat-item">
                <div class="stat-value running">{{ stats.running }}</div>
                <div class="stat-label">进行中</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="stat-item">
                <div class="stat-value failed">{{ stats.failed }}</div>
                <div class="stat-label">失败</div>
              </div>
            </el-col>
          </el-row>
        </div>

        <!-- 操作历史列表 -->
        <div class="history-list">
          <el-table
            :data="operations"
            size="small"
            max-height="400"
          >
            <el-table-column prop="operation_type" label="操作类型" width="120">
              <template #default="scope">
                <el-tag :type="getOperationTypeColor(scope.row.operation_type)" size="small">
                  {{ getOperationTypeText(scope.row.operation_type) }}
                </el-tag>
              </template>
            </el-table-column>
            
            <el-table-column prop="status" label="状态" width="100">
              <template #default="scope">
                <el-tag :type="getStatusType(scope.row.status)" size="small">
                  {{ getStatusText(scope.row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            
            <el-table-column prop="created_at" label="开始时间" width="150">
              <template #default="scope">
                {{ formatTime(scope.row.created_at) }}
              </template>
            </el-table-column>
            
            <el-table-column prop="completed_at" label="完成时间" width="150">
              <template #default="scope">
                <span v-if="scope.row.completed_at">
                  {{ formatTime(scope.row.completed_at) }}
                </span>
                <span v-else class="not-completed">-</span>
              </template>
            </el-table-column>
            
            <el-table-column label="耗时" width="100">
              <template #default="scope">
                <span v-if="scope.row.completed_at">
                  {{ getDuration(scope.row.created_at, scope.row.completed_at) }}
                </span>
                <span v-else-if="scope.row.status === 'running'">
                  {{ getDuration(scope.row.created_at) }}
                </span>
                <span v-else>-</span>
              </template>
            </el-table-column>
            
            <el-table-column prop="details" label="详情" min-width="200">
              <template #default="scope">
                <div class="operation-details">
                  <div v-if="scope.row.details" class="details-summary">
                    {{ getDetailsSummary(scope.row.details) }}
                  </div>
                  <div v-if="scope.row.error_message" class="error-message">
                    {{ scope.row.error_message }}
                  </div>
                </div>
              </template>
            </el-table-column>
            
            <el-table-column label="操作" width="120">
              <template #default="scope">
                <el-button
                  size="small"
                  @click="viewOperationDetails(scope.row)"
                >
                  详情
                </el-button>
                
                <el-button
                  v-if="scope.row.status === 'running'"
                  size="small"
                  type="danger"
                  @click="cancelOperation(scope.row)"
                >
                  取消
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <!-- 分页 -->
          <div class="pagination-wrapper">
            <el-pagination
              v-model:current-page="pagination.page"
              v-model:page-size="pagination.size"
              :total="pagination.total"
              :page-sizes="[10, 20, 50, 100]"
              layout="total, sizes, prev, pager, next, jumper"
              @size-change="fetchHistory"
              @current-change="fetchHistory"
            />
          </div>
        </div>

        <!-- 空状态 -->
        <div v-if="operations.length === 0 && !loading" class="empty-state">
          <el-empty description="暂无操作记录" />
        </div>
      </div>
    </el-card>

    <!-- 操作详情对话框 -->
    <el-dialog
      v-model="detailsVisible"
      title="操作详情"
      width="70%"
      :close-on-click-modal="false"
    >
      <div v-if="selectedOperation" class="operation-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="操作ID">
            {{ selectedOperation.id }}
          </el-descriptions-item>
          <el-descriptions-item label="操作类型">
            <el-tag :type="getOperationTypeColor(selectedOperation.operation_type)" size="small">
              {{ getOperationTypeText(selectedOperation.operation_type) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusType(selectedOperation.status)" size="small">
              {{ getStatusText(selectedOperation.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="开始时间">
            {{ formatTime(selectedOperation.created_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="完成时间">
            {{ selectedOperation.completed_at ? formatTime(selectedOperation.completed_at) : '未完成' }}
          </el-descriptions-item>
          <el-descriptions-item label="耗时">
            {{ selectedOperation.completed_at ? getDuration(selectedOperation.created_at, selectedOperation.completed_at) : '进行中' }}
          </el-descriptions-item>
        </el-descriptions>

        <div v-if="selectedOperation.details" class="operation-details-full">
          <h4>操作详情</h4>
          <el-tabs v-model="activeTab">
            <el-tab-pane label="基本信息" name="basic">
              <pre>{{ formatDetails(selectedOperation.details) }}</pre>
            </el-tab-pane>
            
            <el-tab-pane v-if="selectedOperation.error_message" label="错误信息" name="error">
              <div class="error-details">
                <el-alert
                  :title="selectedOperation.error_message"
                  type="error"
                  :closable="false"
                  show-icon
                />
              </div>
            </el-tab-pane>
            
            <el-tab-pane label="原始数据" name="raw">
              <pre>{{ JSON.stringify(selectedOperation, null, 2) }}</pre>
            </el-tab-pane>
          </el-tabs>
        </div>
      </div>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="detailsVisible = false">关闭</el-button>
          <el-button
            v-if="selectedOperation?.status === 'running'"
            type="danger"
            @click="cancelOperation(selectedOperation)"
          >
            取消操作
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { certificateApi } from '@/api/certificate'
import type { Certificate } from '@/types/certificate'
import dayjs from 'dayjs'

interface Props {
  certificate: Certificate
}

const props = defineProps<Props>()

// 响应式数据
const loading = ref(false)
const detailsVisible = ref(false)
const activeTab = ref('basic')
const filterType = ref('')
const selectedOperation = ref(null)

// 分页
const pagination = reactive({
  page: 1,
  size: 20,
  total: 0
})

// 统计数据
const stats = reactive({
  total: 0,
  completed: 0,
  running: 0,
  failed: 0
})

// 操作列表
const operations = ref([])

// 方法
const getOperationTypeColor = (type: string): string => {
  switch (type) {
    case 'manual_check': return 'primary'
    case 'deep_scan': return 'success'
    case 'renewal': return 'warning'
    case 'import': return 'info'
    case 'export': return 'info'
    default: return ''
  }
}

const getOperationTypeText = (type: string): string => {
  switch (type) {
    case 'manual_check': return '手动检测'
    case 'deep_scan': return '深度扫描'
    case 'renewal': return '证书续期'
    case 'import': return '导入操作'
    case 'export': return '导出操作'
    case 'delete': return '删除操作'
    default: return type
  }
}

const getStatusType = (status: string): string => {
  switch (status) {
    case 'completed': return 'success'
    case 'running': return 'warning'
    case 'failed': return 'danger'
    case 'cancelled': return 'info'
    default: return ''
  }
}

const getStatusText = (status: string): string => {
  switch (status) {
    case 'pending': return '等待中'
    case 'running': return '进行中'
    case 'completed': return '已完成'
    case 'failed': return '失败'
    case 'cancelled': return '已取消'
    default: return status
  }
}

const formatTime = (time: string): string => {
  return dayjs(time).format('YYYY-MM-DD HH:mm:ss')
}

const getDuration = (startTime: string, endTime?: string): string => {
  const start = dayjs(startTime)
  const end = endTime ? dayjs(endTime) : dayjs()
  const duration = end.diff(start, 'second')
  
  if (duration < 60) {
    return `${duration}秒`
  } else if (duration < 3600) {
    return `${Math.floor(duration / 60)}分${duration % 60}秒`
  } else {
    const hours = Math.floor(duration / 3600)
    const minutes = Math.floor((duration % 3600) / 60)
    return `${hours}小时${minutes}分`
  }
}

const getDetailsSummary = (details: any): string => {
  if (typeof details === 'string') {
    return details.length > 100 ? details.substring(0, 100) + '...' : details
  }
  
  if (typeof details === 'object') {
    try {
      const parsed = typeof details === 'string' ? JSON.parse(details) : details
      if (parsed.summary) return parsed.summary
      if (parsed.message) return parsed.message
      if (parsed.description) return parsed.description
      return '查看详情'
    } catch {
      return '查看详情'
    }
  }
  
  return '查看详情'
}

const formatDetails = (details: any): string => {
  if (typeof details === 'string') {
    try {
      return JSON.stringify(JSON.parse(details), null, 2)
    } catch {
      return details
    }
  }
  return JSON.stringify(details, null, 2)
}

const fetchHistory = async () => {
  try {
    loading.value = true
    
    const response = await certificateApi.getOperationHistory(props.certificate.id, {
      page: pagination.page,
      size: pagination.size,
      operation_type: filterType.value
    })
    
    operations.value = response.data.operations || []
    pagination.total = response.data.pagination?.total || 0
    
    // 更新统计数据
    Object.assign(stats, response.data.stats || {
      total: 0,
      completed: 0,
      running: 0,
      failed: 0
    })
    
  } catch (error) {
    console.error('获取操作历史失败:', error)
    ElMessage.error('获取操作历史失败')
  } finally {
    loading.value = false
  }
}

const refreshHistory = () => {
  pagination.page = 1
  fetchHistory()
}

const viewOperationDetails = (operation: any) => {
  selectedOperation.value = operation
  detailsVisible.value = true
  activeTab.value = 'basic'
}

const cancelOperation = async (operation: any) => {
  try {
    await ElMessageBox.confirm(
      '确定要取消这个操作吗？',
      '确认取消',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await certificateApi.cancelOperation(operation.id)
    
    ElMessage.success('操作已取消')
    detailsVisible.value = false
    fetchHistory()
    
  } catch (error) {
    if (error !== 'cancel') {
      console.error('取消操作失败:', error)
      ElMessage.error('取消操作失败')
    }
  }
}

onMounted(() => {
  fetchHistory()
})
</script>

<style scoped>
.certificate-operation-history {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

.operation-stats {
  margin-bottom: 20px;
  padding: 15px;
  background-color: #f5f7fa;
  border-radius: 4px;
}

.stat-item {
  text-align: center;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  margin-bottom: 5px;
}

.stat-value.success { color: #67c23a; }
.stat-value.running { color: #e6a23c; }
.stat-value.failed { color: #f56c6c; }

.stat-label {
  font-size: 12px;
  color: #909399;
}

.operation-details {
  font-size: 12px;
}

.details-summary {
  color: #606266;
  margin-bottom: 5px;
}

.error-message {
  color: #f56c6c;
  font-style: italic;
}

.not-completed {
  color: #909399;
}

.pagination-wrapper {
  margin-top: 20px;
  text-align: center;
}

.empty-state {
  text-align: center;
  padding: 40px;
}

.operation-detail {
  padding: 10px;
}

.operation-details-full {
  margin-top: 20px;
}

.operation-details-full h4 {
  margin: 0 0 15px 0;
  color: #303133;
}

.operation-details-full pre {
  background-color: #f5f7fa;
  padding: 15px;
  border-radius: 4px;
  overflow-x: auto;
  font-size: 12px;
  max-height: 300px;
}

.error-details {
  padding: 10px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>
