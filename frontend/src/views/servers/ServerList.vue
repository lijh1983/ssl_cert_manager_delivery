<template>
  <div class="server-list">
    <!-- 页面标题和操作栏 -->
    <div class="page-header">
      <h2>服务器管理</h2>
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
        <el-table-column prop="name" label="服务器名称" min-width="150">
          <template #default="scope">
            <el-link type="primary" @click="viewDetail(scope.row.id)">
              {{ scope.row.name }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column prop="ip" label="IP地址" width="140" />
        <el-table-column prop="os_type" label="操作系统" width="150" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="scope">
            <el-tag :type="getStatusTagType(scope.row.status)">
              {{ getStatusText(scope.row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="certificates_count" label="证书数量" width="100" />
        <el-table-column prop="last_seen" label="最后在线" width="160">
          <template #default="scope">
            {{ formatDate(scope.row.last_seen) }}
          </template>
        </el-table-column>
        <el-table-column prop="auto_renew" label="自动续期" width="100">
          <template #default="scope">
            <el-switch
              v-model="scope.row.auto_renew"
              @change="toggleAutoRenew(scope.row)"
            />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="scope">
            <el-button type="text" size="small" @click="viewDetail(scope.row.id)">
              查看
            </el-button>
            <el-button type="text" size="small" @click="editServer(scope.row)">
              编辑
            </el-button>
            <el-button type="text" size="small" @click="showInstallCommand(scope.row)">
              安装
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

    <!-- 创建/编辑服务器对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
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
        <el-form-item label="自动续期">
          <el-switch v-model="serverForm.auto_renew" />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="submitting" @click="handleSubmit">
            确定
          </el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 安装命令对话框 -->
    <el-dialog
      v-model="installDialogVisible"
      title="客户端安装命令"
      width="600px"
    >
      <div class="install-content">
        <p class="install-description">
          请在目标服务器上执行以下命令来安装SSL证书管理客户端：
        </p>
        <el-input
          v-model="installCommand"
          type="textarea"
          :rows="3"
          readonly
          class="install-command"
        />
        <div class="install-actions">
          <el-button type="primary" @click="copyInstallCommand">
            复制命令
          </el-button>
          <el-button @click="regenerateToken">
            重新生成令牌
          </el-button>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { serverApi } from '@/api/server'
import type { Server, CreateServerRequest, UpdateServerRequest } from '@/types/server'
import dayjs from 'dayjs'

const router = useRouter()

// 响应式数据
const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const installDialogVisible = ref(false)
const serverList = ref<Server[]>([])
const selectedServers = ref<Server[]>([])
const currentServer = ref<Server | null>(null)
const installCommand = ref('')

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
const serverForm = reactive<CreateServerRequest>({
  name: '',
  auto_renew: true
})

// 表单验证规则
const formRules: FormRules = {
  name: [
    { required: true, message: '请输入服务器名称', trigger: 'blur' },
    { min: 2, max: 50, message: '长度在 2 到 50 个字符', trigger: 'blur' }
  ]
}

// 计算属性
const dialogTitle = computed(() => {
  return currentServer.value ? '编辑服务器' : '添加服务器'
})

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

// 获取状态文本
const getStatusText = (status: string) => {
  switch (status) {
    case 'online': return '在线'
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
  router.push('/servers/create')
}

// 显示创建对话框（保留用于兼容性）
const showCreateDialog = () => {
  currentServer.value = null
  dialogVisible.value = true
}

// 编辑服务器
const editServer = (server: Server) => {
  currentServer.value = server
  serverForm.name = server.name
  serverForm.auto_renew = server.auto_renew
  dialogVisible.value = true
}

// 查看详情
const viewDetail = (id: number) => {
  router.push(`/servers/${id}`)
}

// 显示安装命令
const showInstallCommand = (server: Server) => {
  currentServer.value = server
  installCommand.value = server.install_command || ''
  installDialogVisible.value = true
}

// 复制安装命令
const copyInstallCommand = async () => {
  try {
    await navigator.clipboard.writeText(installCommand.value)
    ElMessage.success('命令已复制到剪贴板')
  } catch (error) {
    ElMessage.error('复制失败，请手动复制')
  }
}

// 重新生成令牌
const regenerateToken = async () => {
  if (!currentServer.value) return
  
  try {
    await ElMessageBox.confirm(
      '重新生成令牌后，旧令牌将失效，需要重新安装客户端。确定继续吗？',
      '警告',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    const response = await serverApi.regenerateToken(currentServer.value.id)
    installCommand.value = response.data.install_command
    ElMessage.success('令牌已重新生成')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to regenerate token:', error)
    }
  }
}

// 切换自动续期
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
  if (!formRef.value) return
  
  try {
    const valid = await formRef.value.validate()
    if (!valid) return
    
    submitting.value = true
    
    if (currentServer.value) {
      // 编辑
      await serverApi.update(currentServer.value.id, serverForm)
      ElMessage.success('服务器已更新')
    } else {
      // 创建
      await serverApi.create(serverForm)
      ElMessage.success('服务器已创建')
    }
    
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
  currentServer.value = null
}

onMounted(() => {
  fetchServerList()
})
</script>

<style scoped>
.server-list {
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

.install-content {
  padding: 10px 0;
}

.install-description {
  margin-bottom: 15px;
  color: #606266;
  line-height: 1.5;
}

.install-command {
  margin-bottom: 15px;
}

.install-actions {
  display: flex;
  gap: 10px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: stretch;
    gap: 15px;
  }
  
  .header-actions {
    display: flex;
    justify-content: center;
  }
}
</style>
