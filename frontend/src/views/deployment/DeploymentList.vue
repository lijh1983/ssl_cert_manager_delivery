<template>
  <div class="deployment-list">
    <!-- 页面标题和操作栏 -->
    <div class="page-header">
      <h2>自动部署</h2>
      <div class="header-actions">
        <el-button type="primary" :icon="Plus" @click="goToCreatePage">
          添加服务器
        </el-button>
      </div>
    </div>

    <!-- 搜索和筛选 -->
    <el-card class="search-card">
      <el-form :model="searchForm" inline>
        <el-form-item label="关键词">
          <el-input
            v-model="searchForm.keyword"
            placeholder="搜索服务器名称或IP"
            clearable
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="searchForm.status" placeholder="选择状态" clearable>
            <el-option label="在线" value="online" />
            <el-option label="离线" value="offline" />
            <el-option label="未知" value="unknown" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 服务器列表 -->
    <el-card class="table-card">
      <el-table
        v-loading="loading"
        :data="serverList"
        style="width: 100%"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="type" label="类型" width="100">
          <template #default="scope">
            <el-tag size="small">{{ scope.row.type || 'nginx' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="名称" min-width="150">
          <template #default="scope">
            <el-link type="primary" @click="viewDetail(scope.row.id)">
              {{ scope.row.name }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column prop="os_type" label="系统" width="200">
          <template #default="scope">
            {{ scope.row.os_type || 'CentOS Linux 7 (Core)' }}
          </template>
        </el-table-column>
        <el-table-column prop="ip" label="IP地址" width="140" />
        <el-table-column prop="version" label="版本" width="100">
          <template #default="scope">
            {{ scope.row.version || '1.17.0' }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="scope">
            <el-tag :type="getStatusTagType(scope.row.status)" size="small">
              <span class="status-dot" :class="getStatusDotClass(scope.row.status)"></span>
              {{ getStatusText(scope.row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="last_seen" label="最后更新时间" width="160">
          <template #default="scope">
            {{ formatDate(scope.row.last_seen) }}
          </template>
        </el-table-column>
        <el-table-column prop="auto_renew" label="自动部署" width="100">
          <template #default="scope">
            <el-switch
              v-model="scope.row.auto_renew"
              @change="toggleAutoRenew(scope.row)"
            />
          </template>
        </el-table-column>
        <el-table-column prop="description" label="备注" min-width="150" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="scope">
            <el-button type="text" size="small" @click="editServer(scope.row)">
              编辑
            </el-button>
            <el-button 
              type="text" 
              size="small" 
              style="color: #f56c6c"
              @click="deleteServer(scope.row)"
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

    <!-- 编辑服务器对话框 -->
    <el-dialog
      v-model="dialogVisible"
      title="服务器详情/编辑"
      width="500px"
      @close="resetForm"
    >
      <el-form
        ref="formRef"
        :model="serverForm"
        :rules="formRules"
        label-width="100px"
      >
        <el-form-item label="服务器名称" prop="name">
          <el-input v-model="serverForm.name" placeholder="请输入服务器名称" />
        </el-form-item>
        <el-form-item label="自动部署">
          <el-switch v-model="serverForm.auto_renew" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input 
            v-model="serverForm.description" 
            type="textarea" 
            :rows="3"
            placeholder="请输入备注信息"
          />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="submitting" @click="handleSubmit">
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
import { serverApi } from '@/api/server'
import type { Server, UpdateServerRequest } from '@/types/server'
import dayjs from 'dayjs'

const router = useRouter()

// 响应式数据
const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const serverList = ref<Server[]>([])
const selectedServers = ref<Server[]>([])
const currentServer = ref<Server | null>(null)

// 表单引用
const formRef = ref<FormInstance>()

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

// 服务器表单
const serverForm = reactive<UpdateServerRequest>({
  name: '',
  auto_renew: true,
  description: ''
})

// 表单验证规则
const formRules: FormRules = {
  name: [
    { required: true, message: '请输入服务器名称', trigger: 'blur' },
    { min: 2, max: 50, message: '长度在 2 到 50 个字符', trigger: 'blur' }
  ]
}

// 获取服务器列表
const fetchServerList = async () => {
  try {
    loading.value = true
    const params = {
      page: pagination.page,
      limit: pagination.limit,
      keyword: searchForm.keyword || undefined
    }
    
    const response = await serverApi.getList(params)
    serverList.value = response.data.items
    pagination.total = response.data.total
  } catch (error) {
    console.error('Failed to fetch server list:', error)
  } finally {
    loading.value = false
  }
}

// 获取状态标签类型
const getStatusTagType = (status: string) => {
  switch (status) {
    case 'online': return 'success'
    case 'offline': return 'danger'
    default: return 'info'
  }
}

// 获取状态点样式
const getStatusDotClass = (status: string) => {
  switch (status) {
    case 'online': return 'status-dot-success'
    case 'offline': return 'status-dot-danger'
    default: return 'status-dot-info'
  }
}

// 获取状态文本
const getStatusText = (status: string) => {
  switch (status) {
    case 'online': return '正常'
    case 'offline': return '离线'
    default: return '未知'
  }
}

// 格式化日期
const formatDate = (dateString?: string) => {
  if (!dateString) return '-'
  return dayjs(dateString).format('YYYY-MM-DD HH:mm')
}

// 搜索
const handleSearch = () => {
  pagination.page = 1
  fetchServerList()
}

// 重置搜索
const handleReset = () => {
  searchForm.keyword = ''
  searchForm.status = ''
  pagination.page = 1
  fetchServerList()
}

// 分页大小改变
const handleSizeChange = (size: number) => {
  pagination.limit = size
  pagination.page = 1
  fetchServerList()
}

// 当前页改变
const handleCurrentChange = (page: number) => {
  pagination.page = page
  fetchServerList()
}

// 选择改变
const handleSelectionChange = (selection: Server[]) => {
  selectedServers.value = selection
}

// 跳转到创建服务器页面
const goToCreatePage = () => {
  router.push('/deployment/create')
}

// 编辑服务器
const editServer = (server: Server) => {
  currentServer.value = server
  serverForm.name = server.name
  serverForm.auto_renew = server.auto_renew
  serverForm.description = server.description || ''
  dialogVisible.value = true
}

// 查看详情
const viewDetail = (id: number) => {
  router.push(`/deployment/${id}`)
}

// 切换自动部署
const toggleAutoRenew = async (server: Server) => {
  try {
    await serverApi.update(server.id, { auto_renew: server.auto_renew })
    ElMessage.success('设置已更新')
  } catch (error) {
    // 恢复原状态
    server.auto_renew = !server.auto_renew
    console.error('Failed to update auto renew:', error)
  }
}

// 删除服务器
const deleteServer = async (server: Server) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除服务器 "${server.name}" 吗？此操作不可恢复。`,
      '警告',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await serverApi.delete(server.id)
    ElMessage.success('服务器已删除')
    fetchServerList()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to delete server:', error)
    }
  }
}

// 提交表单
const handleSubmit = async () => {
  if (!formRef.value || !currentServer.value) return
  
  try {
    const valid = await formRef.value.validate()
    if (!valid) return
    
    submitting.value = true
    await serverApi.update(currentServer.value.id, serverForm)
    ElMessage.success('服务器已更新')
    
    dialogVisible.value = false
    fetchServerList()
  } catch (error) {
    console.error('Failed to submit form:', error)
  } finally {
    submitting.value = false
  }
}

// 重置表单
const resetForm = () => {
  if (formRef.value) {
    formRef.value.resetFields()
  }
  serverForm.name = ''
  serverForm.auto_renew = true
  serverForm.description = ''
  currentServer.value = null
}

onMounted(() => {
  fetchServerList()
})
</script>

<style scoped>
.deployment-list {
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

.status-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 6px;
}

.status-dot-success {
  background-color: #67c23a;
}

.status-dot-danger {
  background-color: #f56c6c;
}

.status-dot-info {
  background-color: #909399;
}
</style>
