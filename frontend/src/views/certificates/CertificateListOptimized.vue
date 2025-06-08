<template>
  <div class="certificate-list-optimized">
    <!-- 页面标题和操作栏 -->
    <div class="page-header">
      <div class="header-left">
        <h2>证书管理</h2>
        <p class="header-description">管理和监控SSL证书的状态</p>
      </div>
      <div class="header-actions">
        <el-button type="primary" :icon="Plus" @click="goToCreatePage">
          申请证书
        </el-button>
        <el-button :icon="Refresh" @click="refreshData" :loading="loading">
          刷新
        </el-button>
      </div>
    </div>

    <!-- 搜索和筛选 -->
    <el-card class="search-card">
      <el-form :model="searchForm" inline>
        <el-form-item label="关键词">
          <el-input
            v-model="searchForm.keyword"
            placeholder="搜索域名"
            clearable
            @keyup.enter="handleSearch"
            @clear="handleSearch"
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="searchForm.status" placeholder="选择状态" clearable @change="handleSearch">
            <el-option label="有效" value="valid" />
            <el-option label="已过期" value="expired" />
            <el-option label="待处理" value="pending" />
            <el-option label="已吊销" value="revoked" />
          </el-select>
        </el-form-item>
        <el-form-item label="服务器">
          <el-select v-model="searchForm.server_id" placeholder="选择服务器" clearable @change="handleSearch">
            <el-option
              v-for="server in serverOptions"
              :key="server.id"
              :label="server.name"
              :value="server.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="CA类型">
          <el-select v-model="searchForm.ca_type" placeholder="选择CA" clearable @change="handleSearch">
            <el-option label="Let's Encrypt" value="letsencrypt" />
            <el-option label="ZeroSSL" value="zerossl" />
            <el-option label="Buypass" value="buypass" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 统计卡片 -->
    <div class="stats-cards">
      <el-card class="stat-card">
        <div class="stat-content">
          <div class="stat-number">{{ stats.total }}</div>
          <div class="stat-label">总证书数</div>
        </div>
        <el-icon class="stat-icon"><Document /></el-icon>
      </el-card>
      <el-card class="stat-card valid">
        <div class="stat-content">
          <div class="stat-number">{{ stats.valid }}</div>
          <div class="stat-label">有效证书</div>
        </div>
        <el-icon class="stat-icon"><CircleCheck /></el-icon>
      </el-card>
      <el-card class="stat-card warning">
        <div class="stat-content">
          <div class="stat-number">{{ stats.expiring }}</div>
          <div class="stat-label">即将过期</div>
        </div>
        <el-icon class="stat-icon"><Warning /></el-icon>
      </el-card>
      <el-card class="stat-card danger">
        <div class="stat-content">
          <div class="stat-number">{{ stats.expired }}</div>
          <div class="stat-label">已过期</div>
        </div>
        <el-icon class="stat-icon"><CircleClose /></el-icon>
      </el-card>
    </div>

    <!-- 虚拟表格 -->
    <el-card class="table-card">
      <VirtualTable
        :data="certificateList"
        :columns="tableColumns"
        :loading="loading"
        :pagination="true"
        :total="pagination.total"
        :page-size="pagination.limit"
        :container-height="600"
        :item-height="60"
        @row-click="handleRowClick"
        @page-change="handlePageChange"
        @load-more="loadMoreData"
      >
        <!-- 域名列 -->
        <template #domain="{ row }">
          <div class="domain-cell">
            <el-link type="primary" @click="viewDetail(row.id)">
              {{ row.domain }}
            </el-link>
            <div class="domain-info">
              <el-tag v-if="row.domains && row.domains.includes(',')" size="small" type="info">
                +{{ row.domains.split(',').length - 1 }}
              </el-tag>
            </div>
          </div>
        </template>

        <!-- 状态列 -->
        <template #status="{ row }">
          <el-tag :type="getStatusTagType(row.status)" size="small">
            {{ getStatusText(row.status) }}
          </el-tag>
        </template>

        <!-- 过期时间列 -->
        <template #expires_at="{ row }">
          <div class="expires-cell">
            <div>{{ formatDate(row.expires_at) }}</div>
            <el-tag :type="getDaysLeftTagType(row.days_left)" size="small">
              {{ row.days_left }}天
            </el-tag>
          </div>
        </template>

        <!-- 自动续期列 -->
        <template #auto_renew="{ row }">
          <el-switch
            v-model="row.auto_renew"
            @change="toggleAutoRenew(row)"
            :loading="row.updating"
          />
        </template>

        <!-- 操作列 -->
        <template #actions="{ row }">
          <div class="action-buttons">
            <el-button type="primary" size="small" @click="viewDetail(row.id)">
              查看
            </el-button>
            <el-button 
              type="success" 
              size="small" 
              @click="renewCertificate(row.id)"
              :loading="row.renewing"
            >
              续期
            </el-button>
            <el-dropdown @command="handleCommand">
              <el-button size="small">
                更多<el-icon class="el-icon--right"><arrow-down /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item :command="`download:${row.id}`">下载证书</el-dropdown-item>
                  <el-dropdown-item :command="`revoke:${row.id}`">撤销证书</el-dropdown-item>
                  <el-dropdown-item :command="`delete:${row.id}`" divided>删除证书</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </template>
      </VirtualTable>

      <!-- 智能分页 -->
      <SmartPagination
        :total="pagination.total"
        :current-page="pagination.page"
        :page-size="pagination.limit"
        :show-performance="true"
        :performance-data="performanceData"
        @page-change="handlePageChange"
        @size-change="handleSizeChange"
      />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  Plus, Refresh, Document, CircleCheck, Warning, CircleClose, ArrowDown 
} from '@element-plus/icons-vue'
import VirtualTable from '@/components/common/VirtualTable.vue'
import SmartPagination from '@/components/common/SmartPagination.vue'
import { certificateApi } from '@/api/certificate'
import { serverApi } from '@/api/server'
import { formatDate } from '@/utils/date'
import { apiCache } from '@/utils/cache'
import type { Certificate } from '@/types/certificate'
import type { Server } from '@/types/server'

const router = useRouter()

// 响应式数据
const loading = ref(false)
const certificateList = ref<Certificate[]>([])
const serverOptions = ref<Server[]>([])
const performanceData = ref<{ queryTime: number; totalTime: number } | null>(null)

// 搜索表单
const searchForm = reactive({
  keyword: '',
  status: '',
  server_id: undefined as number | undefined,
  ca_type: ''
})

// 分页
const pagination = reactive({
  page: 1,
  limit: 20,
  total: 0
})

// 统计数据
const stats = computed(() => {
  const total = certificateList.value.length
  const valid = certificateList.value.filter(cert => cert.status === 'valid').length
  const expired = certificateList.value.filter(cert => cert.status === 'expired').length
  const expiring = certificateList.value.filter(cert => 
    cert.status === 'valid' && cert.days_left <= 30
  ).length

  return { total, valid, expired, expiring }
})

// 表格列配置
const tableColumns = [
  { key: 'domain', title: '域名', width: 200, slot: 'domain' },
  { key: 'type', title: '类型', width: 100 },
  { key: 'status', title: '状态', width: 100, slot: 'status' },
  { key: 'server_name', title: '服务器', width: 150 },
  { key: 'ca_type', title: 'CA类型', width: 120 },
  { key: 'expires_at', title: '过期时间', width: 180, slot: 'expires_at' },
  { key: 'auto_renew', title: '自动续期', width: 100, slot: 'auto_renew' },
  { key: 'actions', title: '操作', width: 200, slot: 'actions' }
]

// 获取证书列表
const fetchCertificateList = async (useCache = true) => {
  try {
    loading.value = true
    const startTime = performance.now()
    
    const params = {
      page: pagination.page,
      limit: pagination.limit,
      keyword: searchForm.keyword || undefined,
      status: searchForm.status || undefined,
      server_id: searchForm.server_id,
      ca_type: searchForm.ca_type || undefined
    }
    
    const response = await certificateApi.getList(params, { cache: useCache ? 5 * 60 * 1000 : false })
    
    certificateList.value = response.data.items.map(cert => ({
      ...cert,
      days_left: calculateDaysLeft(cert.expires_at),
      updating: false,
      renewing: false
    }))
    
    pagination.total = response.data.total
    
    const endTime = performance.now()
    performanceData.value = {
      queryTime: Math.round(endTime - startTime),
      totalTime: Math.round(endTime - startTime)
    }
    
  } catch (error) {
    console.error('Failed to fetch certificate list:', error)
    ElMessage.error('获取证书列表失败')
  } finally {
    loading.value = false
  }
}

// 获取服务器选项
const fetchServerOptions = async () => {
  try {
    const response = await serverApi.getList({ limit: 1000 }, { cache: 10 * 60 * 1000 })
    serverOptions.value = response.data.items
  } catch (error) {
    console.error('Failed to fetch server options:', error)
  }
}

// 计算剩余天数
const calculateDaysLeft = (expiresAt: string) => {
  const now = new Date()
  const expiry = new Date(expiresAt)
  const diffTime = expiry.getTime() - now.getTime()
  return Math.ceil(diffTime / (1000 * 60 * 60 * 24))
}

// 获取状态标签类型
const getStatusTagType = (status: string) => {
  const types = {
    valid: 'success',
    expired: 'danger',
    pending: 'warning',
    revoked: 'info'
  }
  return types[status] || 'info'
}

// 获取状态文本
const getStatusText = (status: string) => {
  const texts = {
    valid: '有效',
    expired: '已过期',
    pending: '待处理',
    revoked: '已吊销'
  }
  return texts[status] || status
}

// 获取剩余天数标签类型
const getDaysLeftTagType = (days: number) => {
  if (days <= 3) return 'danger'
  if (days <= 7) return 'warning'
  if (days <= 30) return 'info'
  return 'success'
}

// 搜索
const handleSearch = () => {
  pagination.page = 1
  fetchCertificateList(false) // 搜索时不使用缓存
}

// 重置搜索
const handleReset = () => {
  Object.assign(searchForm, {
    keyword: '',
    status: '',
    server_id: undefined,
    ca_type: ''
  })
  pagination.page = 1
  fetchCertificateList(false)
}

// 刷新数据
const refreshData = () => {
  apiCache.clear() // 清除缓存
  fetchCertificateList(false)
}

// 分页处理
const handlePageChange = (page: number, size?: number) => {
  pagination.page = page
  if (size) pagination.limit = size
  fetchCertificateList()
}

const handleSizeChange = (size: number) => {
  pagination.limit = size
  pagination.page = 1
  fetchCertificateList()
}

// 行点击处理
const handleRowClick = (row: Certificate) => {
  viewDetail(row.id)
}

// 加载更多数据（虚拟滚动）
const loadMoreData = () => {
  if (pagination.page * pagination.limit < pagination.total) {
    pagination.page++
    fetchCertificateList()
  }
}

// 查看详情
const viewDetail = (id: number) => {
  router.push(`/certificates/${id}`)
}

// 跳转到申请证书页面
const goToCreatePage = () => {
  router.push('/certificates/create')
}

// 续期证书
const renewCertificate = async (id: number) => {
  const cert = certificateList.value.find(c => c.id === id)
  if (!cert) return

  try {
    cert.renewing = true
    await certificateApi.renew(id)
    ElMessage.success('证书续期任务已提交')
    
    // 更新证书状态
    setTimeout(() => {
      fetchCertificateList(false)
    }, 1000)
    
  } catch (error) {
    console.error('Failed to renew certificate:', error)
    ElMessage.error('证书续期失败')
  } finally {
    cert.renewing = false
  }
}

// 切换自动续期
const toggleAutoRenew = async (certificate: Certificate) => {
  try {
    certificate.updating = true
    await certificateApi.update(certificate.id, { auto_renew: certificate.auto_renew })
    ElMessage.success('设置已更新')
  } catch (error) {
    certificate.auto_renew = !certificate.auto_renew
    console.error('Failed to update auto renew:', error)
    ElMessage.error('设置更新失败')
  } finally {
    certificate.updating = false
  }
}

// 处理下拉菜单命令
const handleCommand = async (command: string) => {
  const [action, id] = command.split(':')
  const certId = parseInt(id)
  
  switch (action) {
    case 'download':
      await downloadCertificate(certId)
      break
    case 'revoke':
      await revokeCertificate(certId)
      break
    case 'delete':
      await deleteCertificate(certId)
      break
  }
}

// 下载证书
const downloadCertificate = async (id: number) => {
  try {
    const blob = await certificateApi.download(id, 'fullchain')
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `certificate-${id}.pem`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    ElMessage.success('证书下载已开始')
  } catch (error) {
    console.error('Failed to download certificate:', error)
    ElMessage.error('证书下载失败')
  }
}

// 撤销证书
const revokeCertificate = async (id: number) => {
  try {
    await ElMessageBox.confirm('确定要撤销此证书吗？撤销后无法恢复。', '确认撤销', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await certificateApi.revoke(id)
    ElMessage.success('证书已撤销')
    fetchCertificateList(false)
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to revoke certificate:', error)
      ElMessage.error('证书撤销失败')
    }
  }
}

// 删除证书
const deleteCertificate = async (id: number) => {
  try {
    await ElMessageBox.confirm('确定要删除此证书吗？删除后无法恢复。', '确认删除', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await certificateApi.delete(id)
    ElMessage.success('证书已删除')
    fetchCertificateList(false)
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to delete certificate:', error)
      ElMessage.error('证书删除失败')
    }
  }
}

// 监听搜索表单变化，实现防抖搜索
watch(
  () => searchForm.keyword,
  () => {
    if (searchForm.keyword.length === 0 || searchForm.keyword.length >= 2) {
      handleSearch()
    }
  },
  { debounce: 500 }
)

// 生命周期
onMounted(() => {
  fetchServerOptions()
  fetchCertificateList()
})
</script>

<style scoped>
.certificate-list-optimized {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
}

.header-left h2 {
  margin: 0 0 8px 0;
  font-size: 24px;
  font-weight: 600;
}

.header-description {
  margin: 0;
  color: #666;
  font-size: 14px;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.search-card {
  margin-bottom: 20px;
}

.stats-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

.stat-card {
  position: relative;
  overflow: hidden;
}

.stat-card.valid {
  border-left: 4px solid #67c23a;
}

.stat-card.warning {
  border-left: 4px solid #e6a23c;
}

.stat-card.danger {
  border-left: 4px solid #f56c6c;
}

.stat-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-number {
  font-size: 28px;
  font-weight: 600;
  color: #303133;
}

.stat-label {
  font-size: 14px;
  color: #606266;
}

.stat-icon {
  position: absolute;
  right: 16px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 32px;
  opacity: 0.3;
}

.table-card {
  margin-bottom: 20px;
}

.domain-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.domain-info {
  display: flex;
  gap: 4px;
}

.expires-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.action-buttons {
  display: flex;
  gap: 8px;
  align-items: center;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    gap: 16px;
  }

  .header-actions {
    width: 100%;
    justify-content: flex-start;
  }

  .stats-cards {
    grid-template-columns: repeat(2, 1fr);
  }

  .action-buttons {
    flex-direction: column;
    gap: 4px;
  }
}
</style>
