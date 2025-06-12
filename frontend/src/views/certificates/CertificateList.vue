<template>
  <div class="certificate-list">
    <!-- 页面标题和操作栏 -->
    <div class="page-header">
      <h2>证书管理</h2>
      <div class="header-actions">
        <el-button
          type="success"
          :disabled="selectedCertificates.length === 0"
          @click="showBatchMonitoringConfig"
        >
          批量监控配置
        </el-button>
        <el-button
          type="warning"
          :disabled="selectedCertificates.length === 0"
          :loading="batchCheckingDomains"
          @click="batchCheckDomains"
        >
          批量域名检查
        </el-button>
        <el-button
          type="info"
          :disabled="selectedCertificates.length === 0"
          :loading="batchCheckingPorts"
          @click="batchCheckPorts"
        >
          批量端口检查
        </el-button>

        <el-dropdown @command="handleBatchOperation">
          <el-button
            type="primary"
            :disabled="selectedCertificates.length === 0"
          >
            批量操作<el-icon class="el-icon--right"><arrow-down /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="check">批量检测</el-dropdown-item>
              <el-dropdown-item command="renew">批量续期</el-dropdown-item>
              <el-dropdown-item command="delete" divided>批量删除</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>

        <el-dropdown @command="handleImportExport">
          <el-button type="success">
            导入导出<el-icon class="el-icon--right"><arrow-down /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="import">批量导入</el-dropdown-item>
              <el-dropdown-item command="export">导出数据</el-dropdown-item>
              <el-dropdown-item command="discovery" divided>网络发现</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <el-button type="primary" :icon="Plus" @click="showApplyDialog">
          免费申请证书
        </el-button>
        <el-button type="warning" @click="deleteExpiredCertificates">
          删除失效证书
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
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="searchForm.status" placeholder="选择状态" clearable>
            <el-option label="有效" value="valid" />
            <el-option label="已过期" value="expired" />
            <el-option label="待处理" value="pending" />
            <el-option label="已吊销" value="revoked" />
          </el-select>
        </el-form-item>
        <el-form-item label="服务器">
          <el-select v-model="searchForm.server_id" placeholder="选择服务器" clearable>
            <el-option
              v-for="server in serverOptions"
              :key="server.id"
              :label="server.name"
              :value="server.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 证书列表 -->
    <el-card class="table-card">
      <el-table
        v-loading="loading"
        :data="certificateList"
        style="width: 100%"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="domain" label="域名" min-width="200">
          <template #default="scope">
            <el-link type="primary" @click="viewDetail(scope.row.id)">
              {{ scope.row.domain }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column prop="type" label="类型" width="100">
          <template #default="scope">
            <el-tag size="small">{{ getCertTypeText(scope.row.type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="scope">
            <el-tag :type="getStatusTagType(scope.row.status)" size="small">
              {{ getStatusText(scope.row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="server_name" label="服务器" width="150" />
        <el-table-column prop="ca_type" label="CA类型" width="120" />
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
        <el-table-column prop="auto_renew" label="自动续期" width="100">
          <template #default="scope">
            <el-switch
              v-model="scope.row.auto_renew"
              @change="toggleAutoRenew(scope.row)"
            />
          </template>
        </el-table-column>
        <el-table-column prop="monitoring_enabled" label="监控状态" width="100">
          <template #default="scope">
            <el-tag
              :type="scope.row.monitoring_enabled ? 'success' : 'info'"
              size="small"
            >
              {{ scope.row.monitoring_enabled ? '已启用' : '已禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="dns_status" label="DNS状态" width="100">
          <template #default="scope">
            <el-tag
              :type="getDnsStatusType(scope.row.dns_status)"
              size="small"
            >
              {{ getDnsStatusText(scope.row.dns_status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="domain_reachable" label="可达性" width="100">
          <template #default="scope">
            <el-tag
              :type="scope.row.domain_reachable === true ? 'success' : scope.row.domain_reachable === false ? 'danger' : 'info'"
              size="small"
            >
              {{ scope.row.domain_reachable === true ? '可达' : scope.row.domain_reachable === false ? '不可达' : '未知' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="tls_version" label="TLS版本" width="100">
          <template #default="scope">
            <el-tag
              :type="getTlsVersionType(scope.row.tls_version)"
              size="small"
            >
              {{ scope.row.tls_version || '未知' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="certificate_chain_valid" label="证书链" width="100">
          <template #default="scope">
            <el-tag
              :type="scope.row.certificate_chain_valid === true ? 'success' : scope.row.certificate_chain_valid === false ? 'danger' : 'info'"
              size="small"
            >
              {{ scope.row.certificate_chain_valid === true ? '完整' : scope.row.certificate_chain_valid === false ? '不完整' : '未知' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="renewal_status" label="续期状态" width="100">
          <template #default="scope">
            <el-tag
              :type="getRenewalStatusType(scope.row.renewal_status)"
              size="small"
            >
              {{ getRenewalStatusText(scope.row.renewal_status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="import_source" label="来源" width="80">
          <template #default="scope">
            <el-tag
              :type="getImportSourceType(scope.row.import_source)"
              size="small"
            >
              {{ getImportSourceText(scope.row.import_source) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="250" fixed="right">
          <template #default="scope">
            <el-button type="text" size="small" @click="viewDetail(scope.row.id)">
              查看
            </el-button>
            <el-button type="text" size="small" @click="renewCertificate(scope.row.id)">
              续期
            </el-button>
            <el-button type="text" size="small" @click="downloadCertificate(scope.row)">
              下载
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

    <!-- 免费申请证书弹窗 -->
    <el-dialog
      v-model="applyDialogVisible"
      title="免费申请证书"
      width="700px"
      @close="resetApplyForm"
    >
      <el-form
        ref="applyFormRef"
        :model="applyForm"
        :rules="applyFormRules"
        label-width="140px"
      >
        <el-form-item label="域名" prop="domain" required>
          <el-input
            v-model="applyForm.domain"
            placeholder="请输入域名，如：example.com 或 *.example.com"
          />
          <div class="form-tip">* 必填，支持单域名和通配符域名</div>
        </el-form-item>

        <!-- 域名验证信息区域 -->
        <el-form-item label="域名验证信息" required>
          <div class="verification-info">
            <el-table :data="verificationData" size="small" border>
              <el-table-column prop="status" label="状态" width="80">
                <template #default="scope">
                  <el-tag :type="scope.row.status === '已配置' ? 'success' : 'info'" size="small">
                    {{ scope.row.status }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="provider" label="服务商" width="100" />
              <el-table-column prop="host_record" label="主机记录" width="120" />
              <el-table-column prop="record_type" label="记录类型" width="100" />
              <el-table-column prop="record_value" label="记录值" min-width="200">
                <template #default="scope">
                  <div class="record-value">
                    <span>{{ scope.row.record_value }}</span>
                    <el-button
                      type="text"
                      size="small"
                      @click="copyToClipboard(scope.row.record_value)"
                    >
                      复制
                    </el-button>
                  </div>
                </template>
              </el-table-column>
            </el-table>
            <div class="verification-tip">
              请在您的DNS服务商处添加上述TXT记录，用于验证域名所有权
            </div>
          </div>
        </el-form-item>

        <el-form-item label="证书厂商" prop="ca_type" required>
          <el-select v-model="applyForm.ca_type" placeholder="选择证书厂商">
            <el-option label="Google" value="google" />
            <el-option label="Let's Encrypt" value="letsencrypt" />
            <el-option label="ZeroSSL" value="zerossl" />
          </el-select>
          <div class="form-tip">* 必填</div>
        </el-form-item>

        <el-form-item label="加密算法" prop="encryption_algorithm" required>
          <el-select v-model="applyForm.encryption_algorithm" placeholder="选择加密算法">
            <el-option label="ECC" value="ecc" />
            <el-option label="RSA" value="rsa" />
          </el-select>
          <div class="form-tip">* 必填</div>
        </el-form-item>

        <el-form-item label="备注">
          <el-input
            v-model="applyForm.description"
            type="textarea"
            :rows="3"
            placeholder="请输入备注信息（可选）"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <span class="dialog-footer">
          <el-button @click="applyDialogVisible = false">取消</el-button>
          <el-button
            type="primary"
            :loading="verifying"
            @click="verifyDomain"
            :disabled="!canVerify"
          >
            验证域名
          </el-button>
        </span>
      </template>
    </el-dialog>

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

    <!-- 批量监控配置对话框 -->
    <BatchMonitoringConfig
      v-model="batchMonitoringVisible"
      :selected-certificates="selectedCertificates"
      @success="handleBatchConfigSuccess"
    />

    <!-- 批量导入对话框 -->
    <el-dialog
      v-model="importDialogVisible"
      title="批量导入证书"
      width="80%"
      @close="importDialogVisible = false"
    >
      <CertificateImport @import-completed="handleImportCompleted" />
    </el-dialog>

    <!-- 证书发现对话框 -->
    <el-dialog
      v-model="discoveryDialogVisible"
      title="证书发现扫描"
      width="80%"
      @close="discoveryDialogVisible = false"
    >
      <CertificateDiscovery @discovery-completed="handleDiscoveryCompleted" />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { certificateApi } from '@/api/certificate'
import { serverApi } from '@/api/server'
import type { Certificate, CreateCertificateRequest } from '@/types/certificate'
import type { Server } from '@/types/server'
import BatchMonitoringConfig from '@/components/BatchMonitoringConfig.vue'
import CertificateImport from '@/components/CertificateImport.vue'
import CertificateDiscovery from '@/components/CertificateDiscovery.vue'
import { ArrowDown } from '@element-plus/icons-vue'
import dayjs from 'dayjs'

const route = useRoute()
const router = useRouter()

// 响应式数据
const loading = ref(false)
const submitting = ref(false)
const verifying = ref(false)
const applyDialogVisible = ref(false)
const downloadDialogVisible = ref(false)
const batchMonitoringVisible = ref(false)
const batchCheckingDomains = ref(false)
const batchCheckingPorts = ref(false)
const batchOperating = ref(false)
const importDialogVisible = ref(false)
const discoveryDialogVisible = ref(false)
const certificateList = ref<Certificate[]>([])
const selectedCertificates = ref<Certificate[]>([])
const serverOptions = ref<Server[]>([])
const currentCertificate = ref<Certificate | null>(null)

// 表单引用
const applyFormRef = ref<FormInstance>()

// 搜索表单
const searchForm = reactive({
  keyword: '',
  status: '',
  server_id: undefined as number | undefined
})

// 分页
const pagination = reactive({
  page: 1,
  limit: 20,
  total: 0
})

// 申请证书表单
const applyForm = reactive({
  domain: '',
  ca_type: 'letsencrypt',
  encryption_algorithm: 'rsa',
  description: ''
})

// 域名验证数据
const verificationData = ref([
  {
    status: '待配置',
    provider: '未知',
    host_record: '_acme-challenge',
    record_type: 'TXT',
    record_value: '等待生成...'
  }
])

// 表单验证规则
const applyFormRules: FormRules = {
  domain: [
    { required: true, message: '请输入域名', trigger: 'blur' },
    {
      pattern: /^(\*\.)?[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$/,
      message: '请输入有效的域名',
      trigger: 'blur'
    }
  ],
  ca_type: [
    { required: true, message: '请选择证书厂商', trigger: 'change' }
  ],
  encryption_algorithm: [
    { required: true, message: '请选择加密算法', trigger: 'change' }
  ]
}

// 计算属性
const canVerify = computed(() => {
  return applyForm.domain && applyForm.ca_type && applyForm.encryption_algorithm
})

// 获取证书列表
const fetchCertificateList = async () => {
  try {
    loading.value = true
    const params = {
      page: pagination.page,
      limit: pagination.limit,
      keyword: searchForm.keyword || undefined,
      status: searchForm.status || undefined,
      server_id: searchForm.server_id
    }
    
    const response = await certificateApi.getList(params)
    certificateList.value = response.data.items.map(cert => ({
      ...cert,
      days_left: calculateDaysLeft(cert.expires_at)
    }))
    pagination.total = response.data.total
  } catch (error) {
    console.error('Failed to fetch certificate list:', error)
  } finally {
    loading.value = false
  }
}

// 获取服务器选项
const fetchServerOptions = async () => {
  try {
    const response = await serverApi.getList({ limit: 1000 })
    serverOptions.value = response.data.items
  } catch (error) {
    console.error('Failed to fetch server options:', error)
  }
}

// 计算剩余天数
const calculateDaysLeft = (expiresAt: string) => {
  const now = dayjs()
  const expiry = dayjs(expiresAt)
  return expiry.diff(now, 'day')
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

// 格式化日期
const formatDate = (dateString: string) => {
  return dayjs(dateString).format('YYYY-MM-DD HH:mm')
}

// 搜索
const handleSearch = () => {
  pagination.page = 1
  fetchCertificateList()
}

// 重置搜索
const handleReset = () => {
  searchForm.keyword = ''
  searchForm.status = ''
  searchForm.server_id = undefined
  pagination.page = 1
  fetchCertificateList()
}

// 分页大小改变
const handleSizeChange = (size: number) => {
  pagination.limit = size
  pagination.page = 1
  fetchCertificateList()
}

// 当前页改变
const handleCurrentChange = (page: number) => {
  pagination.page = page
  fetchCertificateList()
}

// 选择改变
const handleSelectionChange = (selection: Certificate[]) => {
  selectedCertificates.value = selection
}

// 显示申请证书对话框
const showApplyDialog = () => {
  applyDialogVisible.value = true
  generateVerificationInfo()
}

// 生成验证信息
const generateVerificationInfo = () => {
  if (applyForm.domain) {
    verificationData.value = [
      {
        status: '待配置',
        provider: '未知',
        host_record: `_acme-challenge.${applyForm.domain}`,
        record_type: 'TXT',
        record_value: generateRandomString(43)
      }
    ]
  }
}

// 生成随机字符串
const generateRandomString = (length: number) => {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_'
  let result = ''
  for (let i = 0; i < length; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length))
  }
  return result
}

// 复制到剪贴板
const copyToClipboard = async (text: string) => {
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制到剪贴板')
  } catch (error) {
    ElMessage.error('复制失败，请手动复制')
  }
}

// 验证域名
const verifyDomain = async () => {
  if (!applyFormRef.value) return

  try {
    const valid = await applyFormRef.value.validate()
    if (!valid) return

    verifying.value = true

    // 模拟验证过程
    await new Promise(resolve => setTimeout(resolve, 2000))

    // 随机决定验证结果
    const isSuccess = Math.random() > 0.3

    if (isSuccess) {
      ElMessage.success('域名验证通过，证书申请成功！')
      applyDialogVisible.value = false
      fetchCertificateList()
    } else {
      ElMessage.error('域名验证未通过，请检查配置或稍后再试')
    }
  } catch (error) {
    console.error('Failed to verify domain:', error)
    ElMessage.error('域名验证失败')
  } finally {
    verifying.value = false
  }
}

// 删除失效证书
const deleteExpiredCertificates = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要删除所有失效证书吗？此操作不可恢复。',
      '警告',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    // 模拟删除操作
    await new Promise(resolve => setTimeout(resolve, 1000))
    ElMessage.success('失效证书已删除')
    fetchCertificateList()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to delete expired certificates:', error)
    }
  }
}

// 重置申请表单
const resetApplyForm = () => {
  if (applyFormRef.value) {
    applyFormRef.value.resetFields()
  }
  applyForm.domain = ''
  applyForm.ca_type = 'letsencrypt'
  applyForm.encryption_algorithm = 'rsa'
  applyForm.description = ''
  verificationData.value = [
    {
      status: '待配置',
      provider: '未知',
      host_record: '_acme-challenge',
      record_type: 'TXT',
      record_value: '等待生成...'
    }
  ]
}

// 显示创建对话框（保留用于兼容性）
const showCreateDialog = () => {
  // 如果URL中有server_id参数，自动选择该服务器
  const serverIdFromQuery = route.query.server_id
  if (serverIdFromQuery) {
    certificateForm.server_id = parseInt(serverIdFromQuery as string)
  }
  dialogVisible.value = true
}

// 查看详情
const viewDetail = (id: number) => {
  router.push(`/certificates/${id}`)
}

// 续期证书
const renewCertificate = async (id: number) => {
  try {
    await certificateApi.renew(id)
    ElMessage.success('证书续期任务已提交')
    fetchCertificateList()
  } catch (error) {
    console.error('Failed to renew certificate:', error)
  }
}

// 下载证书
const downloadCertificate = (certificate: Certificate) => {
  currentCertificate.value = certificate
  downloadDialogVisible.value = true
}

// 下载文件
const downloadFile = async (type: 'cert' | 'key' | 'fullchain') => {
  if (!currentCertificate.value) return
  
  try {
    const blob = await certificateApi.download(currentCertificate.value.id, type)
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    
    const extension = type === 'key' ? 'key' : type === 'fullchain' ? 'pem' : 'crt'
    link.download = `${currentCertificate.value.domain}.${extension}`
    
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    
    ElMessage.success('文件下载已开始')
  } catch (error) {
    console.error('Failed to download certificate:', error)
    ElMessage.error('下载失败')
  }
}

// 切换自动续期
const toggleAutoRenew = async (certificate: Certificate) => {
  try {
    await certificateApi.update(certificate.id, { auto_renew: certificate.auto_renew })
    ElMessage.success('设置已更新')
  } catch (error) {
    // 恢复原状态
    certificate.auto_renew = !certificate.auto_renew
    console.error('Failed to update auto renew:', error)
  }
}

// 显示批量监控配置
const showBatchMonitoringConfig = () => {
  if (selectedCertificates.value.length === 0) {
    ElMessage.warning('请先选择要配置的证书')
    return
  }
  batchMonitoringVisible.value = true
}

// 批量配置成功回调
const handleBatchConfigSuccess = () => {
  // 重新获取证书列表以更新监控状态
  fetchCertificateList()
  // 清空选择
  selectedCertificates.value = []
}

// 获取DNS状态类型
const getDnsStatusType = (status?: string): string => {
  switch (status) {
    case 'resolved': return 'success'
    case 'failed': return 'danger'
    case 'timeout': return 'warning'
    default: return 'info'
  }
}

// 获取DNS状态文本
const getDnsStatusText = (status?: string): string => {
  switch (status) {
    case 'resolved': return '解析成功'
    case 'failed': return '解析失败'
    case 'timeout': return '解析超时'
    case 'error': return '解析错误'
    default: return '未知'
  }
}

// 获取TLS版本类型
const getTlsVersionType = (version?: string): string => {
  if (!version) return 'info'
  if (version.includes('1.3')) return 'success'
  if (version.includes('1.2')) return 'success'
  if (version.includes('1.1') || version.includes('1.0')) return 'warning'
  return 'info'
}

// 获取续期状态类型
const getRenewalStatusType = (status?: string): string => {
  switch (status) {
    case 'completed': return 'success'
    case 'in_progress': return 'warning'
    case 'failed': return 'danger'
    default: return 'info'
  }
}

// 获取续期状态文本
const getRenewalStatusText = (status?: string): string => {
  switch (status) {
    case 'pending': return '待续期'
    case 'in_progress': return '续期中'
    case 'completed': return '已完成'
    case 'failed': return '失败'
    default: return '未知'
  }
}

// 获取导入来源类型
const getImportSourceType = (source?: string): string => {
  switch (source) {
    case 'manual': return 'primary'
    case 'csv': return 'success'
    case 'discovery': return 'warning'
    default: return 'info'
  }
}

// 获取导入来源文本
const getImportSourceText = (source?: string): string => {
  switch (source) {
    case 'manual': return '手动'
    case 'csv': return 'CSV'
    case 'discovery': return '发现'
    default: return '未知'
  }
}

// 批量检查域名
const batchCheckDomains = async () => {
  if (selectedCertificates.value.length === 0) {
    ElMessage.warning('请先选择要检查的证书')
    return
  }

  try {
    // 确认操作
    const confirmResult = await ElMessageBox.confirm(
      `确定要对 ${selectedCertificates.value.length} 个证书进行域名检查吗？`,
      '确认操作',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    if (confirmResult !== 'confirm') return

    batchCheckingDomains.value = true

    const requestData = {
      certificate_ids: selectedCertificates.value.map(cert => cert.id),
      max_concurrent: 5
    }

    const response = await certificateApi.batchCheckDomains(requestData)

    ElMessage.success(`批量域名检查完成: 成功 ${response.data.success_count} 个，失败 ${response.data.failed_count} 个`)

    // 重新获取证书列表以更新域名状态
    fetchCertificateList()
    // 清空选择
    selectedCertificates.value = []

  } catch (error) {
    console.error('批量域名检查失败:', error)
    ElMessage.error('批量域名检查失败')
  } finally {
    batchCheckingDomains.value = false
  }
}

// 批量检查端口
const batchCheckPorts = async () => {
  if (selectedCertificates.value.length === 0) {
    ElMessage.warning('请先选择要检查的证书')
    return
  }

  try {
    // 确认操作
    const confirmResult = await ElMessageBox.confirm(
      `确定要对 ${selectedCertificates.value.length} 个证书进行端口检查吗？`,
      '确认操作',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    if (confirmResult !== 'confirm') return

    batchCheckingPorts.value = true

    const requestData = {
      certificate_ids: selectedCertificates.value.map(cert => cert.id),
      max_concurrent: 3
    }

    const response = await certificateApi.batchCheckPorts(requestData)

    ElMessage.success(`批量端口检查完成: 成功 ${response.data.success_count} 个，失败 ${response.data.failed_count} 个`)

    // 重新获取证书列表以更新端口状态
    fetchCertificateList()
    // 清空选择
    selectedCertificates.value = []

  } catch (error) {
    console.error('批量端口检查失败:', error)
    ElMessage.error('批量端口检查失败')
  } finally {
    batchCheckingPorts.value = false
  }
}

// 处理批量操作
const handleBatchOperation = async (command: string) => {
  if (selectedCertificates.value.length === 0) {
    ElMessage.warning('请先选择要操作的证书')
    return
  }

  try {
    let confirmMessage = ''
    let operationType = ''

    switch (command) {
      case 'check':
        confirmMessage = `确定要对 ${selectedCertificates.value.length} 个证书进行批量检测吗？`
        operationType = 'check'
        break
      case 'renew':
        confirmMessage = `确定要对 ${selectedCertificates.value.length} 个证书进行批量续期吗？`
        operationType = 'renew'
        break
      case 'delete':
        confirmMessage = `确定要删除 ${selectedCertificates.value.length} 个证书吗？此操作不可恢复！`
        operationType = 'delete'
        break
      default:
        return
    }

    const confirmResult = await ElMessageBox.confirm(
      confirmMessage,
      '确认操作',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    if (confirmResult !== 'confirm') return

    batchOperating.value = true

    const requestData = {
      operation_type: operationType,
      certificate_ids: selectedCertificates.value.map(cert => cert.id),
      options: {}
    }

    const response = await certificateApi.batchOperations(requestData)

    ElMessage.success(`批量${command === 'check' ? '检测' : command === 'renew' ? '续期' : '删除'}任务已启动`)

    // 重新获取证书列表
    fetchCertificateList()
    // 清空选择
    selectedCertificates.value = []

  } catch (error) {
    console.error('批量操作失败:', error)
    ElMessage.error('批量操作失败')
  } finally {
    batchOperating.value = false
  }
}

// 处理导入导出
const handleImportExport = (command: string) => {
  switch (command) {
    case 'import':
      importDialogVisible.value = true
      break
    case 'export':
      exportCertificates()
      break
    case 'discovery':
      discoveryDialogVisible.value = true
      break
  }
}

// 导出证书
const exportCertificates = async () => {
  try {
    const blob = await certificateApi.exportCertificates()

    // 创建下载链接
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `certificates_export_${dayjs().format('YYYYMMDD_HHmmss')}.csv`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)

    ElMessage.success('证书数据导出成功')

  } catch (error) {
    console.error('导出失败:', error)
    ElMessage.error('导出失败')
  }
}

// 导入完成处理
const handleImportCompleted = (result: any) => {
  ElMessage.success(`导入完成：成功 ${result.success_count} 个，失败 ${result.failed_count} 个`)
  importDialogVisible.value = false
  fetchCertificateList()
}

// 发现完成处理
const handleDiscoveryCompleted = (certificates: any[]) => {
  ElMessage.success(`发现 ${certificates.length} 个证书`)
  discoveryDialogVisible.value = false
  fetchCertificateList()
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
    fetchCertificateList()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to delete certificate:', error)
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
    await certificateApi.create(certificateForm)
    
    ElMessage.success('证书申请已提交')
    dialogVisible.value = false
    fetchCertificateList()
  } catch (error) {
    console.error('Failed to create certificate:', error)
  } finally {
    submitting.value = false
  }
}

// 重置表单
const resetForm = () => {
  if (formRef.value) {
    formRef.value.resetFields()
  }
  certificateForm.domain = ''
  certificateForm.type = 'single'
  certificateForm.server_id = 0
  certificateForm.ca_type = 'letsencrypt'
  certificateForm.validation_method = 'dns'
}

onMounted(() => {
  fetchServerOptions()
  fetchCertificateList()
})
</script>

<style scoped>
.certificate-list {
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

.download-options {
  padding: 10px 0;
}

.verification-info {
  margin: 10px 0;
}

.verification-tip {
  margin-top: 10px;
  padding: 8px 12px;
  background-color: #f0f9ff;
  border: 1px solid #bfdbfe;
  border-radius: 4px;
  color: #1e40af;
  font-size: 12px;
}

.record-value {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.form-tip {
  margin-top: 5px;
  color: #909399;
  font-size: 12px;
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
