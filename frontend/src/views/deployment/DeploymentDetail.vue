<template>
  <div class="deployment-detail">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>服务器详情</h2>
      <div class="header-actions">
        <el-button @click="goBack">返回</el-button>
      </div>
    </div>

    <div v-loading="loading">
      <!-- 服务器基本信息 -->
      <el-card class="info-card" v-if="server">
        <template #header>
          <div class="card-header">
            <span>基本信息</span>
            <el-button type="text" @click="editServer">编辑</el-button>
          </div>
        </template>
        
        <el-descriptions :column="2" border>
          <el-descriptions-item label="服务器名称">{{ server.name }}</el-descriptions-item>
          <el-descriptions-item label="类型">{{ server.type || 'nginx' }}</el-descriptions-item>
          <el-descriptions-item label="IP地址">{{ server.ip || '-' }}</el-descriptions-item>
          <el-descriptions-item label="系统">{{ server.os_type || '-' }}</el-descriptions-item>
          <el-descriptions-item label="版本">{{ server.version || '-' }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusTagType(server.status)" size="small">
              <span class="status-dot" :class="getStatusDotClass(server.status)"></span>
              {{ getStatusText(server.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="最后更新时间">{{ formatDate(server.last_seen) }}</el-descriptions-item>
          <el-descriptions-item label="自动部署">
            <el-switch
              v-model="server.auto_renew"
              @change="toggleAutoRenew"
            />
          </el-descriptions-item>
          <el-descriptions-item label="备注" :span="2">{{ server.description || '-' }}</el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- 证书列表 -->
      <el-card class="certificates-card">
        <template #header>
          <div class="card-header">
            <span>部署的证书</span>
            <el-button type="primary" size="small" @click="addCertificate">
              添加证书
            </el-button>
          </div>
        </template>
        
        <el-table :data="certificates" style="width: 100%">
          <el-table-column prop="domain" label="域名" min-width="200">
            <template #default="scope">
              <el-link type="primary" @click="viewCertificate(scope.row.id)">
                {{ scope.row.domain }}
              </el-link>
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
          <el-table-column prop="days_left" label="剩余天数" width="100">
            <template #default="scope">
              <el-tag :type="getDaysLeftTagType(scope.row.days_left)" size="small">
                {{ scope.row.days_left }}天
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="150">
            <template #default="scope">
              <el-button type="text" size="small" @click="viewCertificate(scope.row.id)">
                查看
              </el-button>
              <el-button type="text" size="small" @click="renewCertificate(scope.row.id)">
                续期
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
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
        <el-form-item label="自动部署">
          <el-switch v-model="editForm.auto_renew" />
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
import { serverApi } from '@/api/server'
import { certificateApi } from '@/api/certificate'
import type { Server, UpdateServerRequest } from '@/types/server'
import type { Certificate } from '@/types/certificate'
import dayjs from 'dayjs'

const route = useRoute()
const router = useRouter()

const serverId = computed(() => parseInt(route.params.id as string))

// 响应式数据
const loading = ref(false)
const editSubmitting = ref(false)
const editDialogVisible = ref(false)
const server = ref<Server | null>(null)
const certificates = ref<Certificate[]>([])

// 表单引用
const editFormRef = ref<FormInstance>()

// 编辑表单
const editForm = reactive<UpdateServerRequest>({
  name: '',
  auto_renew: true,
  description: ''
})

// 编辑表单验证规则
const editFormRules: FormRules = {
  name: [
    { required: true, message: '请输入服务器名称', trigger: 'blur' },
    { min: 2, max: 50, message: '长度在 2 到 50 个字符', trigger: 'blur' }
  ]
}

// 获取服务器详情
const fetchServerDetail = async () => {
  try {
    loading.value = true
    const response = await serverApi.getDetail(serverId.value)
    server.value = response.data
    
    // 获取服务器的证书列表
    const certResponse = await certificateApi.getList({ server_id: serverId.value })
    certificates.value = certResponse.data.items.map(cert => ({
      ...cert,
      days_left: calculateDaysLeft(cert.expires_at)
    }))
  } catch (error) {
    console.error('Failed to fetch server detail:', error)
  } finally {
    loading.value = false
  }
}

// 计算剩余天数
const calculateDaysLeft = (expiresAt: string) => {
  const now = dayjs()
  const expiry = dayjs(expiresAt)
  return expiry.diff(now, 'day')
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
    case 'pending': return '处理中'
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
  router.push('/deployment')
}

// 编辑服务器
const editServer = () => {
  if (!server.value) return
  
  editForm.name = server.value.name
  editForm.auto_renew = server.value.auto_renew
  editForm.description = server.value.description || ''
  editDialogVisible.value = true
}

// 切换自动部署
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
  router.push(`/certificates/create?server_id=${serverId.value}`)
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
    fetchServerDetail()
  } catch (error) {
    console.error('Failed to renew certificate:', error)
  }
}

// 提交编辑表单
const handleEditSubmit = async () => {
  if (!editFormRef.value || !server.value) return
  
  try {
    const valid = await editFormRef.value.validate()
    if (!valid) return
    
    editSubmitting.value = true
    await serverApi.update(server.value.id, editForm)
    ElMessage.success('服务器已更新')
    
    editDialogVisible.value = false
    fetchServerDetail()
  } catch (error) {
    console.error('Failed to update server:', error)
  } finally {
    editSubmitting.value = false
  }
}

// 重置编辑表单
const resetEditForm = () => {
  if (editFormRef.value) {
    editFormRef.value.resetFields()
  }
  editForm.name = ''
  editForm.auto_renew = true
  editForm.description = ''
}

onMounted(() => {
  fetchServerDetail()
})
</script>

<style scoped>
.deployment-detail {
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

.certificates-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
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
