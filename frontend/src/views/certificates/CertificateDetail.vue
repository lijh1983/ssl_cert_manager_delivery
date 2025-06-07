<template>
  <div class="certificate-detail">
    <!-- 页面标题 -->
    <div class="page-header">
      <el-breadcrumb separator="/">
        <el-breadcrumb-item :to="{ path: '/certificates' }">证书管理</el-breadcrumb-item>
        <el-breadcrumb-item>{{ certificate?.domain || '证书详情' }}</el-breadcrumb-item>
      </el-breadcrumb>
    </div>

    <div v-if="loading" class="loading-container">
      <el-skeleton :rows="8" animated />
    </div>

    <div v-else-if="certificate" class="certificate-content">
      <!-- 证书基本信息 -->
      <el-card class="info-card">
        <template #header>
          <div class="card-header">
            <span>证书信息</span>
            <div class="header-actions">
              <el-button size="small" @click="renewCertificate">续期</el-button>
              <el-button size="small" @click="downloadCertificate">下载</el-button>
            </div>
          </div>
        </template>
        
        <el-descriptions :column="2" border>
          <el-descriptions-item label="域名">
            {{ certificate.domain }}
          </el-descriptions-item>
          <el-descriptions-item label="证书类型">
            <el-tag size="small">{{ getCertTypeText(certificate.type) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusTagType(certificate.status)">
              {{ getStatusText(certificate.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="CA类型">
            {{ certificate.ca_type }}
          </el-descriptions-item>
          <el-descriptions-item label="验证方式">
            {{ certificate.validation_method === 'dns' ? 'DNS验证' : 'HTTP验证' }}
          </el-descriptions-item>
          <el-descriptions-item label="自动续期">
            <el-switch
              v-model="certificate.auto_renew"
              @change="toggleAutoRenew"
            />
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">
            {{ formatDate(certificate.created_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="过期时间">
            {{ formatDate(certificate.expires_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="剩余天数">
            <el-tag :type="getDaysLeftTagType(daysLeft)">
              {{ daysLeft }}天
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="所属服务器">
            <el-link 
              v-if="certificate.server_name"
              type="primary" 
              @click="viewServer"
            >
              {{ certificate.server_name }}
            </el-link>
            <span v-else>-</span>
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- 证书内容 -->
      <el-card class="content-card">
        <template #header>
          <div class="card-header">
            <span>证书内容</span>
          </div>
        </template>
        
        <el-tabs v-model="activeTab">
          <el-tab-pane label="证书文件" name="certificate">
            <el-input
              v-model="certificate.certificate"
              type="textarea"
              :rows="10"
              readonly
              placeholder="证书内容将在这里显示"
            />
          </el-tab-pane>
          <el-tab-pane label="私钥文件" name="private_key">
            <el-input
              v-model="certificate.private_key"
              type="textarea"
              :rows="10"
              readonly
              placeholder="私钥内容将在这里显示"
            />
          </el-tab-pane>
        </el-tabs>
      </el-card>

      <!-- 部署记录 -->
      <el-card class="deployments-card">
        <template #header>
          <div class="card-header">
            <span>部署记录</span>
          </div>
        </template>
        
        <el-table :data="deployments" style="width: 100%">
          <el-table-column prop="service_type" label="服务类型" width="120" />
          <el-table-column prop="config_path" label="配置路径" min-width="200" />
          <el-table-column prop="status" label="状态" width="100">
            <template #default="scope">
              <el-tag :type="getDeployStatusTagType(scope.row.status)" size="small">
                {{ getDeployStatusText(scope.row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="部署时间" width="160">
            <template #default="scope">
              {{ formatDate(scope.row.created_at) }}
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>

    <div v-else class="error-container">
      <el-result
        icon="error"
        title="证书不存在"
        sub-title="请检查证书ID是否正确"
      >
        <template #extra>
          <el-button type="primary" @click="$router.push('/certificates')">
            返回证书列表
          </el-button>
        </template>
      </el-result>
    </div>

    <!-- 下载证书对话框 -->
    <el-dialog
      v-model="downloadDialogVisible"
      title="下载证书"
      width="400px"
    >
      <div class="download-options">
        <el-button 
          type="primary" 
          @click="downloadFile('cert')"
          style="width: 100%; margin-bottom: 10px;"
        >
          下载证书文件 (.crt)
        </el-button>
        <el-button 
          type="primary" 
          @click="downloadFile('key')"
          style="width: 100%; margin-bottom: 10px;"
        >
          下载私钥文件 (.key)
        </el-button>
        <el-button 
          type="primary" 
          @click="downloadFile('fullchain')"
          style="width: 100%;"
        >
          下载完整链 (.pem)
        </el-button>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { certificateApi } from '@/api/certificate'
import type { Certificate, CertificateDeployment } from '@/types/certificate'
import dayjs from 'dayjs'

const route = useRoute()
const router = useRouter()

// 响应式数据
const loading = ref(true)
const downloadDialogVisible = ref(false)
const activeTab = ref('certificate')
const certificate = ref<Certificate | null>(null)
const deployments = ref<CertificateDeployment[]>([])

// 证书ID
const certificateId = computed(() => {
  return parseInt(route.params.id as string)
})

// 剩余天数
const daysLeft = computed(() => {
  if (!certificate.value) return 0
  const now = dayjs()
  const expiry = dayjs(certificate.value.expires_at)
  return expiry.diff(now, 'day')
})

// 获取证书详情
const fetchCertificateDetail = async () => {
  try {
    loading.value = true
    
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 500))
    
    // 模拟数据
    certificate.value = {
      id: certificateId.value,
      domain: 'example.com',
      type: 'single',
      status: 'valid',
      server_id: 1,
      server_name: 'web-server-01',
      ca_type: 'letsencrypt',
      validation_method: 'dns',
      auto_renew: true,
      created_at: '2025-03-01T00:00:00Z',
      expires_at: '2025-06-01T00:00:00Z',
      updated_at: '2025-03-01T00:00:00Z',
      certificate: '-----BEGIN CERTIFICATE-----\nMIIFXTCCBEWgAwIBAgISA...\n-----END CERTIFICATE-----',
      private_key: '-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC...\n-----END PRIVATE KEY-----'
    }
    
    // 模拟部署记录
    deployments.value = [
      {
        id: 1,
        certificate_id: certificateId.value,
        service_type: 'nginx',
        config_path: '/etc/nginx/ssl/example.com.crt',
        status: 'success',
        created_at: '2025-03-01T00:30:00Z',
        updated_at: '2025-03-01T00:30:00Z'
      },
      {
        id: 2,
        certificate_id: certificateId.value,
        service_type: 'apache',
        config_path: '/etc/apache2/ssl/example.com.crt',
        status: 'success',
        created_at: '2025-03-01T00:35:00Z',
        updated_at: '2025-03-01T00:35:00Z'
      }
    ]
    
  } catch (error) {
    console.error('Failed to fetch certificate detail:', error)
    certificate.value = null
  } finally {
    loading.value = false
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

// 获取状态标签类型
const getStatusTagType = (status: string) => {
  switch (status) {
    case 'valid': return 'success'
    case 'expired': return 'danger'
    case 'pending': return 'warning'
    case 'revoked': return 'info'
    default: return 'info'
  }
}

// 获取状态文本
const getStatusText = (status: string) => {
  switch (status) {
    case 'valid': return '有效'
    case 'expired': return '已过期'
    case 'pending': return '待处理'
    case 'revoked': return '已吊销'
    default: return status
  }
}

// 获取剩余天数标签类型
const getDaysLeftTagType = (days: number) => {
  if (days <= 3) return 'danger'
  if (days <= 7) return 'warning'
  if (days <= 30) return 'info'
  return 'success'
}

// 获取部署状态标签类型
const getDeployStatusTagType = (status: string) => {
  switch (status) {
    case 'success': return 'success'
    case 'failed': return 'danger'
    case 'pending': return 'warning'
    default: return 'info'
  }
}

// 获取部署状态文本
const getDeployStatusText = (status: string) => {
  switch (status) {
    case 'success': return '成功'
    case 'failed': return '失败'
    case 'pending': return '进行中'
    default: return status
  }
}

// 格式化日期
const formatDate = (dateString: string) => {
  return dayjs(dateString).format('YYYY-MM-DD HH:mm:ss')
}

// 查看服务器
const viewServer = () => {
  if (certificate.value?.server_id) {
    router.push(`/servers/${certificate.value.server_id}`)
  }
}

// 续期证书
const renewCertificate = async () => {
  if (!certificate.value) return
  
  try {
    await certificateApi.renew(certificate.value.id)
    ElMessage.success('证书续期任务已提交')
  } catch (error) {
    console.error('Failed to renew certificate:', error)
  }
}

// 下载证书
const downloadCertificate = () => {
  downloadDialogVisible.value = true
}

// 下载文件
const downloadFile = async (type: 'cert' | 'key' | 'fullchain') => {
  if (!certificate.value) return
  
  try {
    const blob = await certificateApi.download(certificate.value.id, type)
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    
    const extension = type === 'key' ? 'key' : type === 'fullchain' ? 'pem' : 'crt'
    link.download = `${certificate.value.domain}.${extension}`
    
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    
    ElMessage.success('文件下载已开始')
    downloadDialogVisible.value = false
  } catch (error) {
    console.error('Failed to download certificate:', error)
    ElMessage.error('下载失败')
  }
}

// 切换自动续期
const toggleAutoRenew = async () => {
  if (!certificate.value) return
  
  try {
    await certificateApi.update(certificate.value.id, { auto_renew: certificate.value.auto_renew })
    ElMessage.success('设置已更新')
  } catch (error) {
    // 恢复原状态
    certificate.value.auto_renew = !certificate.value.auto_renew
    console.error('Failed to update auto renew:', error)
  }
}

onMounted(() => {
  fetchCertificateDetail()
})
</script>

<style scoped>
.certificate-detail {
  padding: 0;
}

.page-header {
  margin-bottom: 20px;
}

.loading-container,
.error-container {
  padding: 40px;
}

.certificate-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.info-card,
.content-card,
.deployments-card {
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
}

.download-options {
  padding: 10px 0;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .certificate-content {
    gap: 15px;
  }
  
  .info-card,
  .content-card,
  .deployments-card {
    margin-bottom: 15px;
  }
  
  .header-actions {
    flex-direction: column;
    gap: 5px;
  }
}
</style>
