<template>
  <div class="monitoring-list">
    <!-- 页面标题和操作栏 -->
    <div class="page-header">
      <h2>证书监控</h2>
      <div class="header-actions">
        <el-button type="primary" :icon="Plus" @click="showAddDialog">
          添加监控
        </el-button>
      </div>
    </div>

    <!-- 搜索和筛选 -->
    <el-card class="search-card">
      <el-form :model="searchForm" inline>
        <el-form-item label="关键词">
          <el-input
            v-model="searchForm.keyword"
            placeholder="搜索主机域名"
            clearable
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="searchForm.status" placeholder="选择状态" clearable>
            <el-option label="正常" value="normal" />
            <el-option label="警告" value="warning" />
            <el-option label="错误" value="error" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 监控列表 -->
    <el-card class="table-card">
      <el-table
        v-loading="loading"
        :data="monitoringList"
        style="width: 100%"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="domain" label="主机域名" min-width="200">
          <template #default="scope">
            <el-link type="primary" @click="viewDetail(scope.row.id)">
              {{ scope.row.domain }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column prop="cert_level" label="证书等级" width="100">
          <template #default="scope">
            <el-tag size="small">{{ scope.row.cert_level || 'DV' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="encryption_type" label="加密方式" width="100">
          <template #default="scope">
            {{ scope.row.encryption_type || 'RSA' }}
          </template>
        </el-table-column>
        <el-table-column prop="port" label="端口" width="80">
          <template #default="scope">
            {{ scope.row.port || 443 }}
          </template>
        </el-table-column>
        <el-table-column prop="ip_type" label="IP类型" width="80">
          <template #default="scope">
            {{ scope.row.ip_type || 'IPv4' }}
          </template>
        </el-table-column>
        <el-table-column prop="ip_address" label="IP地址" width="140">
          <template #default="scope">
            {{ scope.row.ip_address || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="scope">
            <el-tag :type="getStatusTagType(scope.row.status)" size="small">
              {{ getStatusText(scope.row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="days_left" label="有效期（天）" width="120" sortable>
          <template #default="scope">
            <el-tag :type="getDaysLeftTagType(scope.row.days_left)" size="small">
              {{ scope.row.days_left }}天
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="monitoring_enabled" label="检测开关" width="100">
          <template #default="scope">
            <el-switch
              v-model="scope.row.monitoring_enabled"
              @change="toggleMonitoring(scope.row)"
            />
          </template>
        </el-table-column>
        <el-table-column prop="description" label="备注" min-width="150" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="scope">
            <el-button type="text" size="small" @click="checkCertificate(scope.row)">
              检测
            </el-button>
            <el-button type="text" size="small" @click="editMonitoring(scope.row)">
              编辑备注
            </el-button>
            <el-button 
              type="text" 
              size="small" 
              style="color: #f56c6c"
              @click="deleteMonitoring(scope.row)"
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

    <!-- 添加监控弹窗 -->
    <el-dialog
      v-model="addDialogVisible"
      title="添加监控"
      width="500px"
      @close="resetAddForm"
    >
      <el-form
        ref="addFormRef"
        :model="addForm"
        :rules="addFormRules"
        label-width="100px"
      >
        <el-form-item label="主机域名" prop="domain">
          <el-input v-model="addForm.domain" placeholder="请输入主机域名" />
        </el-form-item>
        <el-form-item label="端口" prop="port">
          <el-input-number v-model="addForm.port" :min="1" :max="65535" />
        </el-form-item>
        <el-form-item label="IP类型" prop="ip_type">
          <el-select v-model="addForm.ip_type" placeholder="选择IP类型">
            <el-option label="IPv4" value="ipv4" />
            <el-option label="IPv6" value="ipv6" />
          </el-select>
        </el-form-item>
        <el-form-item label="IP地址" prop="ip_address">
          <el-input v-model="addForm.ip_address" placeholder="请输入IP地址" />
        </el-form-item>
        <el-form-item label="检测开关">
          <el-switch v-model="addForm.monitoring_enabled" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input 
            v-model="addForm.description" 
            type="textarea" 
            :rows="3"
            placeholder="请输入备注信息"
          />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="addDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="addSubmitting" @click="handleAddSubmit">
            保存
          </el-button>
        </span>
      </template>
    </el-dialog>

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
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import dayjs from 'dayjs'

const router = useRouter()

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

// 响应式数据
const loading = ref(false)
const addSubmitting = ref(false)
const editSubmitting = ref(false)
const addDialogVisible = ref(false)
const editDialogVisible = ref(false)
const monitoringList = ref<MonitoringItem[]>([])
const selectedItems = ref<MonitoringItem[]>([])
const currentItem = ref<MonitoringItem | null>(null)

// 表单引用
const addFormRef = ref<FormInstance>()
const editFormRef = ref<FormInstance>()

// 搜索表单
const searchForm = reactive({
  keyword: '',
  status: ''
})

// 分页
const pagination = reactive({
  page: 1,
  limit: 20,
  total: 0
})

// 添加表单
const addForm = reactive({
  domain: '',
  port: 443,
  ip_type: 'ipv4',
  ip_address: '',
  monitoring_enabled: true,
  description: ''
})

// 编辑表单
const editForm = reactive({
  domain: '',
  monitoring_enabled: true,
  description: ''
})

// 表单验证规则
const addFormRules: FormRules = {
  domain: [
    { required: true, message: '请输入主机域名', trigger: 'blur' },
    { 
      pattern: /^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$/,
      message: '请输入有效的域名',
      trigger: 'blur'
    }
  ],
  port: [
    { required: true, message: '请输入端口', trigger: 'blur' }
  ],
  ip_type: [
    { required: true, message: '请选择IP类型', trigger: 'change' }
  ]
}

const editFormRules: FormRules = {}

// 模拟数据
const mockData: MonitoringItem[] = [
  {
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
  },
  {
    id: 2,
    domain: 'api.example.com',
    cert_level: 'OV',
    encryption_type: 'ECC',
    port: 443,
    ip_type: 'IPv4',
    ip_address: '192.168.1.101',
    status: 'warning',
    days_left: 10,
    monitoring_enabled: true,
    description: 'API接口监控'
  }
]

// 获取监控列表
const fetchMonitoringList = async () => {
  try {
    loading.value = true
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 500))
    
    // 过滤数据
    let filteredData = mockData
    if (searchForm.keyword) {
      filteredData = filteredData.filter(item => 
        item.domain.toLowerCase().includes(searchForm.keyword.toLowerCase())
      )
    }
    if (searchForm.status) {
      filteredData = filteredData.filter(item => item.status === searchForm.status)
    }
    
    monitoringList.value = filteredData
    pagination.total = filteredData.length
  } catch (error) {
    console.error('Failed to fetch monitoring list:', error)
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

// 搜索
const handleSearch = () => {
  pagination.page = 1
  fetchMonitoringList()
}

// 重置搜索
const handleReset = () => {
  searchForm.keyword = ''
  searchForm.status = ''
  pagination.page = 1
  fetchMonitoringList()
}

// 分页大小改变
const handleSizeChange = (size: number) => {
  pagination.limit = size
  pagination.page = 1
  fetchMonitoringList()
}

// 当前页改变
const handleCurrentChange = (page: number) => {
  pagination.page = page
  fetchMonitoringList()
}

// 选择改变
const handleSelectionChange = (selection: MonitoringItem[]) => {
  selectedItems.value = selection
}

// 显示添加对话框
const showAddDialog = () => {
  addDialogVisible.value = true
}

// 查看详情
const viewDetail = (id: number) => {
  router.push(`/monitoring/${id}`)
}

// 检测证书
const checkCertificate = async (item: MonitoringItem) => {
  try {
    ElMessage.info('正在检测证书...')
    // 模拟检测
    await new Promise(resolve => setTimeout(resolve, 1000))
    ElMessage.success('证书检测完成')
    fetchMonitoringList()
  } catch (error) {
    console.error('Failed to check certificate:', error)
    ElMessage.error('证书检测失败')
  }
}

// 编辑监控
const editMonitoring = (item: MonitoringItem) => {
  currentItem.value = item
  editForm.domain = item.domain
  editForm.monitoring_enabled = item.monitoring_enabled
  editForm.description = item.description || ''
  editDialogVisible.value = true
}

// 切换监控状态
const toggleMonitoring = async (item: MonitoringItem) => {
  try {
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 200))
    ElMessage.success('监控状态已更新')
  } catch (error) {
    // 恢复原状态
    item.monitoring_enabled = !item.monitoring_enabled
    console.error('Failed to toggle monitoring:', error)
    ElMessage.error('更新监控状态失败')
  }
}

// 删除监控
const deleteMonitoring = async (item: MonitoringItem) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除监控 "${item.domain}" 吗？此操作不可恢复。`,
      '警告',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 500))
    ElMessage.success('监控已删除')
    fetchMonitoringList()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to delete monitoring:', error)
    }
  }
}

// 提交添加表单
const handleAddSubmit = async () => {
  if (!addFormRef.value) return
  
  try {
    const valid = await addFormRef.value.validate()
    if (!valid) return
    
    addSubmitting.value = true
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    ElMessage.success('监控已添加')
    addDialogVisible.value = false
    fetchMonitoringList()
  } catch (error) {
    console.error('Failed to add monitoring:', error)
    ElMessage.error('添加监控失败')
  } finally {
    addSubmitting.value = false
  }
}

// 提交编辑表单
const handleEditSubmit = async () => {
  if (!editFormRef.value || !currentItem.value) return
  
  try {
    editSubmitting.value = true
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    ElMessage.success('监控已更新')
    editDialogVisible.value = false
    fetchMonitoringList()
  } catch (error) {
    console.error('Failed to update monitoring:', error)
    ElMessage.error('更新监控失败')
  } finally {
    editSubmitting.value = false
  }
}

// 重置添加表单
const resetAddForm = () => {
  if (addFormRef.value) {
    addFormRef.value.resetFields()
  }
  addForm.domain = ''
  addForm.port = 443
  addForm.ip_type = 'ipv4'
  addForm.ip_address = ''
  addForm.monitoring_enabled = true
  addForm.description = ''
}

// 重置编辑表单
const resetEditForm = () => {
  if (editFormRef.value) {
    editFormRef.value.resetFields()
  }
  editForm.domain = ''
  editForm.monitoring_enabled = true
  editForm.description = ''
  currentItem.value = null
}

onMounted(() => {
  fetchMonitoringList()
})
</script>

<style scoped>
.monitoring-list {
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

.search-card {
  margin-bottom: 20px;
}

.table-card {
  margin-bottom: 20px;
}

.pagination-wrapper {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}
</style>
