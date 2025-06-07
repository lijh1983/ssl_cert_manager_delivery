<template>
  <div class="server-detail">
    <!-- 页面标题 -->
    <div class="page-header">
      <el-breadcrumb separator="/">
        <el-breadcrumb-item :to="{ path: '/servers' }">服务器管理</el-breadcrumb-item>
        <el-breadcrumb-item>{{ server?.name || '服务器详情' }}</el-breadcrumb-item>
      </el-breadcrumb>
    </div>

    <div v-if="loading" class="loading-container">
      <el-skeleton :rows="8" animated />
    </div>

    <div v-else-if="server" class="server-content">
      <!-- 服务器基本信息 -->
      <el-card class="info-card">
        <template #header>
          <div class="card-header">
            <span>基本信息</span>
            <el-button type="primary" size="small" @click="editServer">
              编辑
            </el-button>
          </div>
        </template>
        
        <el-descriptions :column="2" border>
          <el-descriptions-item label="服务器名称">
            {{ server.name }}
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusTagType(server.status)">
              {{ getStatusText(server.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="IP地址">
            {{ server.ip || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="主机名">
            {{ server.hostname || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="操作系统">
            {{ server.os_type || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="客户端版本">
            {{ server.version || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="自动续期">
            <el-switch
              v-model="server.auto_renew"
              @change="toggleAutoRenew"
            />
          </el-descriptions-item>
          <el-descriptions-item label="最后在线">
            {{ formatDate(server.last_seen) }}
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">
            {{ formatDate(server.created_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="更新时间">
            {{ formatDate(server.updated_at) }}
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- 证书列表 -->
      <el-card class="certificates-card">
        <template #header>
          <div class="card-header">
            <span>证书列表 ({{ certificates.length }})</span>
            <el-button type="primary" size="small" @click="addCertificate">
              添加证书
            </el-button>
          </div>
        </template>
        
        <el-table :data="certificates" style="width: 100%">
          <el-table-column prop="domain" label="域名" min-width="200" />
          <el-table-column prop="type" label="类型" width="100">
            <template #default="scope">
              <el-tag size="small">{{ getCertTypeText(scope.row.type) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="100">
            <template #default="scope">
              <el-tag :type="getCertStatusTagType(scope.row.status)" size="small">
                {{ getCertStatusText(scope.row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="expires_at" label="过期时间" width="160">
            <template #default="scope">
              {{ formatDate(scope.row.expires_at) }}
            </template>
          </el-table-column>
          <el-table-column prop="ca_type" label="CA类型" width="120" />
          <el-table-column label="操作" width="200">
            <template #default="scope">
              <el-button type="text" size="small" @click="viewCertificate(scope.row.id)">
                查看
              </el-button>
              <el-button type="text" size="small" @click="renewCertificate(scope.row.id)">
                续期
              </el-button>
              <el-button 
                type="text" 
                size="small" 
                style="color: #f56c6c"
                @click="deleteCertificate(scope.row)"
              >
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- 操作日志 -->
      <el-card class="logs-card">
        <template #header>
          <div class="card-header">
            <span>操作日志</span>
          </div>
        </template>
        
        <el-timeline>
          <el-timeline-item
            v-for="log in operationLogs"
            :key="log.id"
            :timestamp="formatDate(log.created_at)"
            placement="top"
          >
            <el-card>
              <h4>{{ log.action }}</h4>
              <p>{{ log.description }}</p>
            </el-card>
          </el-timeline-item>
        </el-timeline>
      </el-card>
    </div>

    <div v-else class="error-container">
      <el-result
        icon="error"
        title="服务器不存在"
        sub-title="请检查服务器ID是否正确"
      >
        <template #extra>
          <el-button type="primary" @click="$router.push('/servers')">
            返回服务器列表
          </el-button>
        </template>
      </el-result>
    </div>

    <!-- 编辑服务器对话框 -->
    <el-dialog
      v-model="editDialogVisible"
      title="编辑服务器"
      width="500px"
      @close="resetEditForm"
    >
      <el-form
        ref="editFormRef"
        :model="editForm"
        :rules="editFormRules"
        label-width="100px"
      >
        <el-form-item label="服务器名称" prop="name">
          <el-input v-model="editForm.name" placeholder="请输入服务器名称" />
        </el-form-item>
        <el-form-item label="自动续期">
          <el-switch v-model="editForm.auto_renew" />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="editDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="submitting" @click="handleEditSubmit">
            确定
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { serverApi } from '@/api/server'
import { certificateApi } from '@/api/certificate'
import type { Server, UpdateServerRequest } from '@/types/server'
import type { Certificate } from '@/types/certificate'
import dayjs from 'dayjs'

const route = useRoute()
const router = useRouter()

// 响应式数据
const loading = ref(true)
const submitting = ref(false)
const editDialogVisible = ref(false)
const server = ref<Server | null>(null)
const certificates = ref<Certificate[]>([])
const operationLogs = ref<any[]>([])

// 表单引用
const editFormRef = ref<FormInstance>()

// 编辑表单
const editForm = reactive<UpdateServerRequest>({
  name: '',
  auto_renew: true
})

// 表单验证规则
const editFormRules: FormRules = {
  name: [
    { required: true, message: '请输入服务器名称', trigger: 'blur' },
    { min: 2, max: 50, message: '长度在 2 到 50 个字符', trigger: 'blur' }
  ]
}

// 服务器ID
const serverId = computed(() => {
  return parseInt(route.params.id as string)
})

// 获取服务器详情
const fetchServerDetail = async () => {
  try {
    loading.value = true
    const response = await serverApi.getDetail(serverId.value)
    server.value = response.data
    
    // 获取服务器上的证书
    if (response.data.certificates) {
      certificates.value = response.data.certificates
    }
    
    // 模拟操作日志
    operationLogs.value = [
      {
        id: 1,
        action: '服务器注册',
        description: '客户端首次注册到系统',
        created_at: response.data.created_at
      },
      {
        id: 2,
        action: '心跳检测',
        description: '客户端发送心跳信号',
        created_at: response.data.last_seen
      }
    ]
  } catch (error) {
    console.error('Failed to fetch server detail:', error)
    server.value = null
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

// 获取证书类型文本
const getCertTypeText = (type: string) => {
  switch (type) {
    case 'single': return '单域名'
    case 'wildcard': return '通配符'
    case 'multi': return '多域名'
    default: return type
  }
}

// 获取证书状态标签类型
const getCertStatusTagType = (status: string) => {
  switch (status) {
    case 'valid': return 'success'
    case 'expired': return 'danger'
    case 'pending': return 'warning'
    default: return 'info'
  }
}

// 获取证书状态文本
const getCertStatusText = (status: string) => {
  switch (status) {
    case 'valid': return '有效'
    case 'expired': return '已过期'
    case 'pending': return '待处理'
    case 'revoked': return '已吊销'
    default: return status
  }
}

// 格式化日期
const formatDate = (dateString?: string) => {
  if (!dateString) return '-'
  return dayjs(dateString).format('YYYY-MM-DD HH:mm:ss')
}

// 编辑服务器
const editServer = () => {
  if (!server.value) return
  
  editForm.name = server.value.name
  editForm.auto_renew = server.value.auto_renew
  editDialogVisible.value = true
}

// 切换自动续期
const toggleAutoRenew = async () => {
  if (!server.value) return
  
  try {
    await serverApi.update(server.value.id, { auto_renew: server.value.auto_renew })
    ElMessage.success('设置已更新')
  } catch (error) {
    // 恢复原状态
    server.value.auto_renew = !server.value.auto_renew
    console.error('Failed to update auto renew:', error)
  }
}

// 添加证书
const addCertificate = () => {
  router.push(`/certificates?server_id=${serverId.value}`)
}

// 查看证书
const viewCertificate = (id: number) => {
  router.push(`/certificates/${id}`)
}

// 续期证书
const renewCertificate = async (id: number) => {
  try {
    await certificateApi.renew(id)
    ElMessage.success('证书续期任务已提交')
  } catch (error) {
    console.error('Failed to renew certificate:', error)
  }
}

// 删除证书
const deleteCertificate = async (certificate: Certificate) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除证书 "${certificate.domain}" 吗？此操作不可恢复。`,
      '警告',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await certificateApi.delete(certificate.id)
    ElMessage.success('证书已删除')
    fetchServerDetail()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to delete certificate:', error)
    }
  }
}

// 提交编辑表单
const handleEditSubmit = async () => {
  if (!editFormRef.value || !server.value) return
  
  try {
    const valid = await editFormRef.value.validate()
    if (!valid) return
    
    submitting.value = true
    await serverApi.update(server.value.id, editForm)
    
    // 更新本地数据
    server.value.name = editForm.name
    server.value.auto_renew = editForm.auto_renew
    
    ElMessage.success('服务器已更新')
    editDialogVisible.value = false
  } catch (error) {
    console.error('Failed to update server:', error)
  } finally {
    submitting.value = false
  }
}

// 重置编辑表单
const resetEditForm = () => {
  if (editFormRef.value) {
    editFormRef.value.resetFields()
  }
}

onMounted(() => {
  fetchServerDetail()
})
</script>

<style scoped>
.server-detail {
  padding: 0;
}

.page-header {
  margin-bottom: 20px;
}

.loading-container,
.error-container {
  padding: 40px;
}

.server-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.info-card,
.certificates-card,
.logs-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .server-content {
    gap: 15px;
  }
  
  .info-card,
  .certificates-card,
  .logs-card {
    margin-bottom: 15px;
  }
}
</style>
