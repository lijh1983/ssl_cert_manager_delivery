<template>
  <div class="monitoring-detail">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>监控详情</h2>
      <div class="header-actions">
        <el-button @click="goBack">返回</el-button>
      </div>
    </div>

    <div v-loading="loading">
      <!-- 监控基本信息 -->
      <el-card class="info-card" v-if="monitoringItem">
        <template #header>
          <div class="card-header">
            <span>基本信息</span>
            <el-button type="text" @click="editMonitoring">编辑</el-button>
          </div>
        </template>
        
        <el-descriptions :column="2" border>
          <el-descriptions-item label="主机域名">{{ monitoringItem.domain }}</el-descriptions-item>
          <el-descriptions-item label="证书等级">{{ monitoringItem.cert_level || 'DV' }}</el-descriptions-item>
          <el-descriptions-item label="加密方式">{{ monitoringItem.encryption_type || 'RSA' }}</el-descriptions-item>
          <el-descriptions-item label="端口">{{ monitoringItem.port || 443 }}</el-descriptions-item>
          <el-descriptions-item label="IP类型">{{ monitoringItem.ip_type || 'IPv4' }}</el-descriptions-item>
          <el-descriptions-item label="IP地址">{{ monitoringItem.ip_address || '-' }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusTagType(monitoringItem.status)" size="small">
              {{ getStatusText(monitoringItem.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="有效期">
            <el-tag :type="getDaysLeftTagType(monitoringItem.days_left)" size="small">
              {{ monitoringItem.days_left }}天
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="检测开关">
            <el-switch
              v-model="monitoringItem.monitoring_enabled"
              @change="toggleMonitoring"
            />
          </el-descriptions-item>
          <el-descriptions-item label="备注" :span="2">{{ monitoringItem.description || '-' }}</el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- 监控历史 -->
      <el-card class="history-card">
        <template #header>
          <div class="card-header">
            <span>监控历史</span>
            <el-button type="primary" size="small" @click="checkNow">
              立即检测
            </el-button>
          </div>
        </template>
        
        <el-table :data="historyData" style="width: 100%">
          <el-table-column prop="check_time" label="检测时间" width="160">
            <template #default="scope">
              {{ formatDate(scope.row.check_time) }}
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="100">
            <template #default="scope">
              <el-tag :type="getStatusTagType(scope.row.status)" size="small">
                {{ getStatusText(scope.row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="days_left" label="剩余天数" width="100">
            <template #default="scope">
              <el-tag :type="getDaysLeftTagType(scope.row.days_left)" size="small">
                {{ scope.row.days_left }}天
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="response_time" label="响应时间" width="100">
            <template #default="scope">
              {{ scope.row.response_time }}ms
            </template>
          </el-table-column>
          <el-table-column prop="ssl_version" label="SSL版本" width="100" />
          <el-table-column prop="message" label="检测结果" min-width="200" />
        </el-table>
      </el-card>
    </div>

    <!-- 编辑监控弹窗 -->
    <el-dialog
      v-model="editDialogVisible"
      title="编辑监控"
      width="500px"
      @close="resetEditForm"
    >
      <el-form
        ref="editFormRef"
        :model="editForm"
        :rules="editFormRules"
        label-width="100px"
      >
        <el-form-item label="主机域名">
          <el-input v-model="editForm.domain" disabled />
        </el-form-item>
        <el-form-item label="检测开关">
          <el-switch v-model="editForm.monitoring_enabled" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input 
            v-model="editForm.description" 
            type="textarea" 
            :rows="3"
            placeholder="请输入备注信息"
          />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="editDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="editSubmitting" @click="handleEditSubmit">
            保存
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import dayjs from 'dayjs'

const route = useRoute()
const router = useRouter()

const monitoringId = computed(() => parseInt(route.params.id as string))

// 监控项接口定义
interface MonitoringItem {
  id: number
  domain: string
  cert_level?: string
  encryption_type?: string
  port: number
  ip_type: string
  ip_address?: string
  status: string
  days_left: number
  monitoring_enabled: boolean
  description?: string
  created_at?: string
  updated_at?: string
}

interface HistoryItem {
  id: number
  check_time: string
  status: string
  days_left: number
  response_time: number
  ssl_version: string
  message: string
}

// 响应式数据
const loading = ref(false)
const editSubmitting = ref(false)
const editDialogVisible = ref(false)
const monitoringItem = ref<MonitoringItem | null>(null)
const historyData = ref<HistoryItem[]>([])

// 表单引用
const editFormRef = ref<FormInstance>()

// 编辑表单
const editForm = reactive({
  domain: '',
  monitoring_enabled: true,
  description: ''
})

// 编辑表单验证规则
const editFormRules: FormRules = {}

// 模拟数据
const mockMonitoringItem: MonitoringItem = {
  id: 1,
  domain: 'example.com',
  cert_level: 'DV',
  encryption_type: 'RSA',
  port: 443,
  ip_type: 'IPv4',
  ip_address: '192.168.1.100',
  status: 'normal',
  days_left: 45,
  monitoring_enabled: true,
  description: '主站点监控'
}

const mockHistoryData: HistoryItem[] = [
  {
    id: 1,
    check_time: '2025-01-10 10:00:00',
    status: 'normal',
    days_left: 45,
    response_time: 120,
    ssl_version: 'TLSv1.3',
    message: '证书正常'
  },
  {
    id: 2,
    check_time: '2025-01-09 10:00:00',
    status: 'normal',
    days_left: 46,
    response_time: 115,
    ssl_version: 'TLSv1.3',
    message: '证书正常'
  },
  {
    id: 3,
    check_time: '2025-01-08 10:00:00',
    status: 'warning',
    days_left: 47,
    response_time: 200,
    ssl_version: 'TLSv1.2',
    message: '响应时间较慢'
  }
]

// 获取监控详情
const fetchMonitoringDetail = async () => {
  try {
    loading.value = true
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 500))
    
    monitoringItem.value = mockMonitoringItem
    historyData.value = mockHistoryData
  } catch (error) {
    console.error('Failed to fetch monitoring detail:', error)
  } finally {
    loading.value = false
  }
}

// 获取状态标签类型
const getStatusTagType = (status: string) => {
  switch (status) {
    case 'normal': return 'success'
    case 'warning': return 'warning'
    case 'error': return 'danger'
    default: return 'info'
  }
}

// 获取状态文本
const getStatusText = (status: string) => {
  switch (status) {
    case 'normal': return '正常'
    case 'warning': return '警告'
    case 'error': return '错误'
    default: return '未知'
  }
}

// 获取剩余天数标签类型
const getDaysLeftTagType = (days: number) => {
  if (days <= 7) return 'danger'
  if (days <= 15) return 'warning'
  return 'success'
}

// 格式化日期
const formatDate = (dateString?: string) => {
  if (!dateString) return '-'
  return dayjs(dateString).format('YYYY-MM-DD HH:mm')
}

// 返回
const goBack = () => {
  router.push('/monitoring')
}

// 编辑监控
const editMonitoring = () => {
  if (!monitoringItem.value) return
  
  editForm.domain = monitoringItem.value.domain
  editForm.monitoring_enabled = monitoringItem.value.monitoring_enabled
  editForm.description = monitoringItem.value.description || ''
  editDialogVisible.value = true
}

// 切换监控状态
const toggleMonitoring = async () => {
  if (!monitoringItem.value) return
  
  try {
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 200))
    ElMessage.success('监控状态已更新')
  } catch (error) {
    // 恢复原状态
    monitoringItem.value.monitoring_enabled = !monitoringItem.value.monitoring_enabled
    console.error('Failed to toggle monitoring:', error)
    ElMessage.error('更新监控状态失败')
  }
}

// 立即检测
const checkNow = async () => {
  try {
    ElMessage.info('正在检测证书...')
    // 模拟检测
    await new Promise(resolve => setTimeout(resolve, 2000))
    ElMessage.success('证书检测完成')
    fetchMonitoringDetail()
  } catch (error) {
    console.error('Failed to check certificate:', error)
    ElMessage.error('证书检测失败')
  }
}

// 提交编辑表单
const handleEditSubmit = async () => {
  if (!editFormRef.value || !monitoringItem.value) return
  
  try {
    editSubmitting.value = true
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    ElMessage.success('监控已更新')
    editDialogVisible.value = false
    fetchMonitoringDetail()
  } catch (error) {
    console.error('Failed to update monitoring:', error)
    ElMessage.error('更新监控失败')
  } finally {
    editSubmitting.value = false
  }
}

// 重置编辑表单
const resetEditForm = () => {
  if (editFormRef.value) {
    editFormRef.value.resetFields()
  }
  editForm.domain = ''
  editForm.monitoring_enabled = true
  editForm.description = ''
}

onMounted(() => {
  fetchMonitoringDetail()
})
</script>

<style scoped>
.monitoring-detail {
  padding: 0;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  color: #303133;
}

.info-card {
  margin-bottom: 20px;
}

.history-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
