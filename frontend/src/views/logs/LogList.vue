<template>
  <div class="log-list">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>操作日志</h2>
    </div>

    <!-- 搜索和筛选 -->
    <el-card class="search-card">
      <el-form :model="searchForm" inline>
        <el-form-item label="操作类型">
          <el-select v-model="searchForm.action" placeholder="选择操作类型" clearable>
            <el-option label="用户登录" value="login" />
            <el-option label="证书申请" value="cert_create" />
            <el-option label="证书续期" value="cert_renew" />
            <el-option label="证书删除" value="cert_delete" />
            <el-option label="服务器注册" value="server_register" />
            <el-option label="服务器删除" value="server_delete" />
          </el-select>
        </el-form-item>
        <el-form-item label="用户">
          <el-input
            v-model="searchForm.username"
            placeholder="输入用户名"
            clearable
          />
        </el-form-item>
        <el-form-item label="时间范围">
          <el-date-picker
            v-model="searchForm.dateRange"
            type="datetimerange"
            range-separator="至"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
            format="YYYY-MM-DD HH:mm:ss"
            value-format="YYYY-MM-DD HH:mm:ss"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 日志列表 -->
    <el-card class="table-card">
      <div class="table-toolbar">
        <div class="left">
          <el-button :icon="Download" @click="exportLogs">导出日志</el-button>
        </div>
        <div class="right">
          <el-button :icon="Refresh" @click="fetchLogList">刷新</el-button>
        </div>
      </div>

      <el-table
        v-loading="loading"
        :data="logList"
        style="width: 100%"
      >
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="action" label="操作类型" width="120">
          <template #default="scope">
            <el-tag :type="getActionTagType(scope.row.action)" size="small">
              {{ getActionText(scope.row.action) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="操作描述" min-width="300" show-overflow-tooltip />
        <el-table-column prop="username" label="操作用户" width="120" />
        <el-table-column prop="ip_address" label="IP地址" width="140" />
        <el-table-column prop="user_agent" label="用户代理" width="200" show-overflow-tooltip />
        <el-table-column prop="created_at" label="操作时间" width="160">
          <template #default="scope">
            {{ formatDate(scope.row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="scope">
            <el-button type="text" size="small" @click="viewDetail(scope.row)">
              详情
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

    <!-- 日志详情对话框 -->
    <el-dialog
      v-model="detailDialogVisible"
      title="日志详情"
      width="600px"
    >
      <el-descriptions v-if="currentLog" :column="1" border>
        <el-descriptions-item label="操作ID">
          {{ currentLog.id }}
        </el-descriptions-item>
        <el-descriptions-item label="操作类型">
          <el-tag :type="getActionTagType(currentLog.action)">
            {{ getActionText(currentLog.action) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="操作描述">
          {{ currentLog.description }}
        </el-descriptions-item>
        <el-descriptions-item label="操作用户">
          {{ currentLog.username }}
        </el-descriptions-item>
        <el-descriptions-item label="IP地址">
          {{ currentLog.ip_address }}
        </el-descriptions-item>
        <el-descriptions-item label="用户代理">
          {{ currentLog.user_agent }}
        </el-descriptions-item>
        <el-descriptions-item label="操作时间">
          {{ formatDate(currentLog.created_at) }}
        </el-descriptions-item>
        <el-descriptions-item v-if="currentLog.details" label="详细信息">
          <pre>{{ JSON.stringify(currentLog.details, null, 2) }}</pre>
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Download, Refresh } from '@element-plus/icons-vue'
import dayjs from 'dayjs'

// 响应式数据
const loading = ref(false)
const detailDialogVisible = ref(false)
const logList = ref<any[]>([])
const currentLog = ref<any>(null)

// 搜索表单
const searchForm = reactive({
  action: '',
  username: '',
  dateRange: null as [string, string] | null
})

// 分页
const pagination = reactive({
  page: 1,
  limit: 20,
  total: 0
})

// 模拟数据
const mockLogs = [
  {
    id: 1,
    action: 'login',
    description: '用户登录系统',
    username: 'admin',
    ip_address: '192.168.1.100',
    user_agent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    created_at: '2025-06-05T09:00:00Z',
    details: { success: true }
  },
  {
    id: 2,
    action: 'cert_create',
    description: '申请证书: example.com',
    username: 'admin',
    ip_address: '192.168.1.100',
    user_agent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    created_at: '2025-06-05T09:15:00Z',
    details: { domain: 'example.com', ca_type: 'letsencrypt' }
  },
  {
    id: 3,
    action: 'server_register',
    description: '服务器注册: web-server-01',
    username: 'system',
    ip_address: '192.168.1.200',
    user_agent: 'SSL-Cert-Manager-Client/1.0',
    created_at: '2025-06-05T08:30:00Z',
    details: { hostname: 'web-server-01', os_type: 'Ubuntu 20.04' }
  },
  {
    id: 4,
    action: 'cert_renew',
    description: '证书续期: api.example.com',
    username: 'system',
    ip_address: '192.168.1.200',
    user_agent: 'SSL-Cert-Manager-Client/1.0',
    created_at: '2025-06-05T08:00:00Z',
    details: { domain: 'api.example.com', auto_renew: true }
  }
]

// 获取日志列表
const fetchLogList = async () => {
  try {
    loading.value = true
    
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 500))
    
    // 应用筛选
    let filteredLogs = mockLogs
    
    if (searchForm.action) {
      filteredLogs = filteredLogs.filter(log => log.action === searchForm.action)
    }
    
    if (searchForm.username) {
      filteredLogs = filteredLogs.filter(log => 
        log.username.toLowerCase().includes(searchForm.username.toLowerCase())
      )
    }
    
    if (searchForm.dateRange) {
      const [start, end] = searchForm.dateRange
      filteredLogs = filteredLogs.filter(log => {
        const logDate = dayjs(log.created_at)
        return logDate.isAfter(dayjs(start)) && logDate.isBefore(dayjs(end))
      })
    }
    
    // 分页
    const start = (pagination.page - 1) * pagination.limit
    const end = start + pagination.limit
    
    logList.value = filteredLogs.slice(start, end)
    pagination.total = filteredLogs.length
    
  } catch (error) {
    console.error('Failed to fetch log list:', error)
    ElMessage.error('获取日志列表失败')
  } finally {
    loading.value = false
  }
}

// 获取操作类型标签类型
const getActionTagType = (action: string) => {
  switch (action) {
    case 'login': return 'success'
    case 'cert_create': return 'primary'
    case 'cert_renew': return 'info'
    case 'cert_delete': return 'warning'
    case 'server_register': return 'success'
    case 'server_delete': return 'danger'
    default: return 'info'
  }
}

// 获取操作类型文本
const getActionText = (action: string) => {
  switch (action) {
    case 'login': return '用户登录'
    case 'cert_create': return '证书申请'
    case 'cert_renew': return '证书续期'
    case 'cert_delete': return '证书删除'
    case 'server_register': return '服务器注册'
    case 'server_delete': return '服务器删除'
    default: return action
  }
}

// 格式化日期
const formatDate = (dateString: string) => {
  return dayjs(dateString).format('YYYY-MM-DD HH:mm:ss')
}

// 搜索
const handleSearch = () => {
  pagination.page = 1
  fetchLogList()
}

// 重置搜索
const handleReset = () => {
  searchForm.action = ''
  searchForm.username = ''
  searchForm.dateRange = null
  pagination.page = 1
  fetchLogList()
}

// 分页大小改变
const handleSizeChange = (size: number) => {
  pagination.limit = size
  pagination.page = 1
  fetchLogList()
}

// 当前页改变
const handleCurrentChange = (page: number) => {
  pagination.page = page
  fetchLogList()
}

// 查看详情
const viewDetail = (log: any) => {
  currentLog.value = log
  detailDialogVisible.value = true
}

// 导出日志
const exportLogs = () => {
  ElMessage.info('导出功能开发中...')
}

onMounted(() => {
  fetchLogList()
})
</script>

<style scoped>
.log-list {
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

pre {
  background-color: #f5f7fa;
  padding: 10px;
  border-radius: 4px;
  font-size: 12px;
  max-height: 200px;
  overflow-y: auto;
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
