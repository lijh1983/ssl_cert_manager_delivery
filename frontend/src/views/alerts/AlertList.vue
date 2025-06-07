<template>
  <div class="alert-list">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>告警管理</h2>
    </div>

    <!-- 搜索和筛选 -->
    <el-card class="search-card">
      <el-form :model="searchForm" inline>
        <el-form-item label="告警类型">
          <el-select v-model="searchForm.type" placeholder="选择类型" clearable>
            <el-option label="过期预警" value="expiry" />
            <el-option label="错误" value="error" />
            <el-option label="吊销" value="revoke" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="searchForm.status" placeholder="选择状态" clearable>
            <el-option label="待处理" value="pending" />
            <el-option label="已发送" value="sent" />
            <el-option label="已解决" value="resolved" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 告警列表 -->
    <el-card class="table-card">
      <div class="table-toolbar">
        <div class="left">
          <el-button 
            type="primary" 
            :disabled="selectedAlerts.length === 0"
            @click="batchResolve"
          >
            批量处理
          </el-button>
        </div>
        <div class="right">
          <el-button :icon="Refresh" @click="fetchAlertList">刷新</el-button>
        </div>
      </div>

      <el-table
        v-loading="loading"
        :data="alertList"
        style="width: 100%"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="type" label="类型" width="100">
          <template #default="scope">
            <el-tag :type="getTypeTagType(scope.row.type)" size="small">
              {{ getTypeText(scope.row.type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="message" label="告警消息" min-width="300" show-overflow-tooltip />
        <el-table-column prop="certificate" label="相关证书" width="200">
          <template #default="scope">
            <el-link 
              v-if="scope.row.certificate"
              type="primary" 
              @click="viewCertificate(scope.row.certificate_id)"
            >
              {{ scope.row.certificate.domain }}
            </el-link>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="scope">
            <el-tag :type="getStatusTagType(scope.row.status)" size="small">
              {{ getStatusText(scope.row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="160">
          <template #default="scope">
            {{ formatDate(scope.row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="scope">
            <el-button 
              v-if="scope.row.status !== 'resolved'"
              type="text" 
              size="small" 
              @click="resolveAlert(scope.row)"
            >
              处理
            </el-button>
            <el-button 
              type="text" 
              size="small" 
              style="color: #f56c6c"
              @click="deleteAlert(scope.row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.limit"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import type { Alert } from '@/types/alert'
import dayjs from 'dayjs'

const router = useRouter()

// 响应式数据
const loading = ref(false)
const alertList = ref<Alert[]>([])
const selectedAlerts = ref<Alert[]>([])

// 搜索表单
const searchForm = reactive({
  type: '',
  status: ''
})

// 分页
const pagination = reactive({
  page: 1,
  limit: 20,
  total: 0
})

// 模拟数据
const mockAlerts: Alert[] = [
  {
    id: 1,
    type: 'expiry',
    message: '证书 example.com 将在 3 天后过期',
    status: 'pending',
    certificate_id: 1,
    certificate: {
      domain: 'example.com',
      expires_at: '2025-06-08T00:00:00Z'
    },
    created_at: '2025-06-05T08:00:00Z',
    updated_at: '2025-06-05T08:00:00Z'
  },
  {
    id: 2,
    type: 'expiry',
    message: '证书 api.example.com 将在 5 天后过期',
    status: 'sent',
    certificate_id: 2,
    certificate: {
      domain: 'api.example.com',
      expires_at: '2025-06-10T00:00:00Z'
    },
    created_at: '2025-06-05T07:30:00Z',
    updated_at: '2025-06-05T07:30:00Z'
  },
  {
    id: 3,
    type: 'error',
    message: '证书 test.example.com 续期失败: DNS验证超时',
    status: 'pending',
    certificate_id: 3,
    certificate: {
      domain: 'test.example.com',
      expires_at: '2025-06-15T00:00:00Z'
    },
    created_at: '2025-06-04T15:20:00Z',
    updated_at: '2025-06-04T15:20:00Z'
  },
  {
    id: 4,
    type: 'expiry',
    message: '证书 blog.example.net 已过期',
    status: 'resolved',
    certificate_id: 4,
    certificate: {
      domain: 'blog.example.net',
      expires_at: '2025-06-01T00:00:00Z'
    },
    created_at: '2025-06-02T00:00:00Z',
    updated_at: '2025-06-03T10:30:00Z'
  }
]

// 获取告警列表
const fetchAlertList = async () => {
  try {
    loading.value = true
    
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 500))
    
    // 应用筛选
    let filteredAlerts = mockAlerts
    
    if (searchForm.type) {
      filteredAlerts = filteredAlerts.filter(alert => alert.type === searchForm.type)
    }
    
    if (searchForm.status) {
      filteredAlerts = filteredAlerts.filter(alert => alert.status === searchForm.status)
    }
    
    // 分页
    const start = (pagination.page - 1) * pagination.limit
    const end = start + pagination.limit
    
    alertList.value = filteredAlerts.slice(start, end)
    pagination.total = filteredAlerts.length
    
  } catch (error) {
    console.error('Failed to fetch alert list:', error)
    ElMessage.error('获取告警列表失败')
  } finally {
    loading.value = false
  }
}

// 获取类型标签类型
const getTypeTagType = (type: string) => {
  switch (type) {
    case 'expiry': return 'warning'
    case 'error': return 'danger'
    case 'revoke': return 'info'
    default: return 'info'
  }
}

// 获取类型文本
const getTypeText = (type: string) => {
  switch (type) {
    case 'expiry': return '过期预警'
    case 'error': return '错误'
    case 'revoke': return '吊销'
    default: return type
  }
}

// 获取状态标签类型
const getStatusTagType = (status: string) => {
  switch (status) {
    case 'pending': return 'warning'
    case 'sent': return 'info'
    case 'resolved': return 'success'
    default: return 'info'
  }
}

// 获取状态文本
const getStatusText = (status: string) => {
  switch (status) {
    case 'pending': return '待处理'
    case 'sent': return '已发送'
    case 'resolved': return '已解决'
    default: return status
  }
}

// 格式化日期
const formatDate = (dateString: string) => {
  return dayjs(dateString).format('MM-DD HH:mm')
}

// 搜索
const handleSearch = () => {
  pagination.page = 1
  fetchAlertList()
}

// 重置搜索
const handleReset = () => {
  searchForm.type = ''
  searchForm.status = ''
  pagination.page = 1
  fetchAlertList()
}

// 分页大小改变
const handleSizeChange = (size: number) => {
  pagination.limit = size
  pagination.page = 1
  fetchAlertList()
}

// 当前页改变
const handleCurrentChange = (page: number) => {
  pagination.page = page
  fetchAlertList()
}

// 选择改变
const handleSelectionChange = (selection: Alert[]) => {
  selectedAlerts.value = selection
}

// 查看证书
const viewCertificate = (certificateId: number) => {
  router.push(`/certificates/${certificateId}`)
}

// 处理告警
const resolveAlert = async (alert: Alert) => {
  try {
    await ElMessageBox.confirm(
      `确定要将此告警标记为已解决吗？`,
      '确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'info'
      }
    )
    
    // 模拟API调用
    alert.status = 'resolved'
    alert.updated_at = new Date().toISOString()
    
    ElMessage.success('告警已处理')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to resolve alert:', error)
    }
  }
}

// 删除告警
const deleteAlert = async (alert: Alert) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除此告警吗？此操作不可恢复。`,
      '警告',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    // 模拟API调用
    const index = alertList.value.findIndex(item => item.id === alert.id)
    if (index > -1) {
      alertList.value.splice(index, 1)
    }
    
    ElMessage.success('告警已删除')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to delete alert:', error)
    }
  }
}

// 批量处理
const batchResolve = async () => {
  try {
    await ElMessageBox.confirm(
      `确定要将选中的 ${selectedAlerts.value.length} 个告警标记为已解决吗？`,
      '确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'info'
      }
    )
    
    // 模拟API调用
    selectedAlerts.value.forEach(alert => {
      alert.status = 'resolved'
      alert.updated_at = new Date().toISOString()
    })
    
    ElMessage.success(`已处理 ${selectedAlerts.value.length} 个告警`)
    selectedAlerts.value = []
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to batch resolve alerts:', error)
    }
  }
}

onMounted(() => {
  fetchAlertList()
})
</script>

<style scoped>
.alert-list {
  padding: 0;
}

.page-header {
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  color: #303133;
}

.search-card {
  margin-bottom: 20px;
}

.table-card {
  margin-bottom: 20px;
}

.table-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.table-toolbar .left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.table-toolbar .right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.pagination-wrapper {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .table-toolbar {
    flex-direction: column;
    gap: 10px;
    align-items: stretch;
  }
  
  .table-toolbar .left,
  .table-toolbar .right {
    justify-content: center;
  }
}
</style>
