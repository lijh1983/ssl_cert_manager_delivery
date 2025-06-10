<template>
  <div class="certificate-discovery">
    <el-steps :active="currentStep" finish-status="success">
      <el-step title="配置扫描参数" />
      <el-step title="执行扫描" />
      <el-step title="选择证书" />
      <el-step title="导入结果" />
    </el-steps>

    <!-- 步骤1: 配置扫描参数 -->
    <div v-if="currentStep === 0" class="step-content">
      <h3>配置网络扫描参数</h3>
      
      <el-form :model="scanConfig" :rules="scanRules" ref="scanFormRef" label-width="120px">
        <el-form-item label="IP范围" prop="ip_ranges">
          <el-input
            v-model="scanConfig.ip_ranges"
            type="textarea"
            :rows="3"
            placeholder="支持多种格式：&#10;192.168.1.1 (单个IP)&#10;192.168.1.1-192.168.1.10 (IP范围)&#10;192.168.1.0/24 (CIDR)&#10;每行一个"
          />
          <div class="input-tip">
            支持单个IP、IP范围和CIDR格式，每行一个
          </div>
        </el-form-item>
        
        <el-form-item label="扫描端口" prop="ports">
          <el-select
            v-model="scanConfig.ports"
            multiple
            filterable
            allow-create
            placeholder="选择或输入端口号"
            style="width: 100%"
          >
            <el-option label="80 (HTTP)" :value="80" />
            <el-option label="443 (HTTPS)" :value="443" />
            <el-option label="8080 (HTTP备用)" :value="8080" />
            <el-option label="8443 (HTTPS备用)" :value="8443" />
            <el-option label="9443 (管理端口)" :value="9443" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="连接超时">
          <el-input-number
            v-model="scanConfig.timeout"
            :min="1"
            :max="60"
            :step="1"
          />
          <span style="margin-left: 8px">秒</span>
        </el-form-item>
        
        <el-form-item label="并发数">
          <el-input-number
            v-model="scanConfig.max_concurrent"
            :min="1"
            :max="50"
            :step="1"
          />
          <span style="margin-left: 8px">个</span>
        </el-form-item>
        
        <el-form-item label="扫描选项">
          <el-checkbox-group v-model="scanConfig.options">
            <el-checkbox label="ssl_only">仅扫描SSL端口</el-checkbox>
            <el-checkbox label="verify_cert">验证证书有效性</el-checkbox>
            <el-checkbox label="get_cert_info">获取证书详细信息</el-checkbox>
            <el-checkbox label="check_expiry">检查证书到期时间</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
      </el-form>

      <div class="scan-preview">
        <h4>扫描预览</h4>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="目标数量">
            {{ estimatedTargets }}
          </el-descriptions-item>
          <el-descriptions-item label="预计时间">
            {{ estimatedTime }}
          </el-descriptions-item>
        </el-descriptions>
      </div>

      <div class="step-actions">
        <el-button type="primary" @click="startScan" :disabled="!canStartScan">
          开始扫描
        </el-button>
      </div>
    </div>

    <!-- 步骤2: 执行扫描 -->
    <div v-if="currentStep === 1" class="step-content">
      <h3>正在执行网络扫描</h3>
      
      <div class="scan-progress">
        <el-progress
          :percentage="scanProgress.percentage"
          :status="scanProgress.status"
          :stroke-width="20"
        />
        
        <div class="progress-info">
          <p>{{ scanProgress.message }}</p>
          <p>已扫描: {{ scanProgress.scanned }} / {{ scanProgress.total }}</p>
          <p>发现证书: {{ scanProgress.found }}</p>
        </div>
      </div>

      <div class="scan-log">
        <h4>扫描日志</h4>
        <el-scrollbar height="200px">
          <div class="log-content">
            <div
              v-for="(log, index) in scanLogs"
              :key="index"
              :class="['log-item', `log-${log.level}`]"
            >
              <span class="log-time">{{ formatTime(log.timestamp) }}</span>
              <span class="log-message">{{ log.message }}</span>
            </div>
          </div>
        </el-scrollbar>
      </div>

      <div class="step-actions">
        <el-button @click="cancelScan" :disabled="scanProgress.status === 'success'">
          取消扫描
        </el-button>
      </div>
    </div>

    <!-- 步骤3: 选择证书 -->
    <div v-if="currentStep === 2" class="step-content">
      <h3>选择要导入的证书</h3>
      
      <div class="discovery-summary">
        <el-alert
          :title="`发现 ${discoveredCertificates.length} 个证书`"
          type="success"
          :closable="false"
          show-icon
        />
      </div>

      <div class="certificate-selection">
        <div class="selection-toolbar">
          <el-button @click="selectAll">全选</el-button>
          <el-button @click="selectNone">全不选</el-button>
          <el-button @click="selectValid">仅选择有效证书</el-button>
        </div>

        <el-table
          ref="certificateTableRef"
          :data="discoveredCertificates"
          @selection-change="handleSelectionChange"
          border
          max-height="400"
        >
          <el-table-column type="selection" width="55" />
          
          <el-table-column prop="ip_address" label="IP地址" width="120" />
          <el-table-column prop="port" label="端口" width="80" />
          <el-table-column prop="domain" label="域名" min-width="150" />
          
          <el-table-column label="证书状态" width="100">
            <template #default="scope">
              <el-tag
                :type="getCertStatusType(scope.row.status)"
                size="small"
              >
                {{ getCertStatusText(scope.row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          
          <el-table-column prop="issuer" label="颁发者" min-width="120" />
          
          <el-table-column label="到期时间" width="120">
            <template #default="scope">
              <span :class="getExpiryClass(scope.row.expires_at)">
                {{ formatDate(scope.row.expires_at) }}
              </span>
            </template>
          </el-table-column>
          
          <el-table-column label="操作" width="100">
            <template #default="scope">
              <el-button
                size="small"
                @click="viewCertDetails(scope.row)"
              >
                详情
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="step-actions">
        <el-button @click="prevStep">上一步</el-button>
        <el-button
          type="primary"
          @click="importSelected"
          :disabled="selectedCertificates.length === 0"
        >
          导入选中的证书 ({{ selectedCertificates.length }})
        </el-button>
      </div>
    </div>

    <!-- 步骤4: 导入结果 -->
    <div v-if="currentStep === 3" class="step-content">
      <h3>导入结果</h3>
      
      <el-result
        :icon="importResult.success ? 'success' : 'error'"
        :title="importResult.success ? '导入完成' : '导入失败'"
        :sub-title="importResult.message"
      >
        <template #extra>
          <div class="import-summary">
            <el-descriptions :column="3" border>
              <el-descriptions-item label="选中数量">
                {{ importResult.selected_count || 0 }}
              </el-descriptions-item>
              <el-descriptions-item label="成功导入">
                <el-tag type="success">{{ importResult.success_count || 0 }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="导入失败">
                <el-tag type="danger">{{ importResult.failed_count || 0 }}</el-tag>
              </el-descriptions-item>
            </el-descriptions>
          </div>
        </template>
      </el-result>

      <div class="step-actions">
        <el-button @click="resetDiscovery">重新扫描</el-button>
        <el-button type="primary" @click="finishDiscovery">完成</el-button>
      </div>
    </div>

    <!-- 证书详情对话框 -->
    <el-dialog
      v-model="certDetailsVisible"
      title="证书详情"
      width="600px"
    >
      <div v-if="selectedCertDetails" class="cert-details">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="域名">
            {{ selectedCertDetails.domain }}
          </el-descriptions-item>
          <el-descriptions-item label="IP地址">
            {{ selectedCertDetails.ip_address }}:{{ selectedCertDetails.port }}
          </el-descriptions-item>
          <el-descriptions-item label="颁发者">
            {{ selectedCertDetails.issuer }}
          </el-descriptions-item>
          <el-descriptions-item label="有效期">
            {{ formatDate(selectedCertDetails.not_before) }} - {{ formatDate(selectedCertDetails.expires_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="SAN域名">
            <el-tag
              v-for="san in selectedCertDetails.san_domains"
              :key="san"
              size="small"
              style="margin-right: 5px"
            >
              {{ san }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { certificateApi } from '@/api/certificate'
import dayjs from 'dayjs'

const emit = defineEmits<{
  discoveryCompleted: [certificates: any[]]
}>()

// 响应式数据
const currentStep = ref(0)
const scanFormRef = ref()
const certificateTableRef = ref()
const certDetailsVisible = ref(false)
const selectedCertDetails = ref(null)

// 扫描配置
const scanConfig = reactive({
  ip_ranges: '192.168.1.1-192.168.1.10',
  ports: [443, 8443],
  timeout: 10,
  max_concurrent: 10,
  options: ['ssl_only', 'verify_cert', 'get_cert_info']
})

// 表单验证规则
const scanRules = {
  ip_ranges: [
    { required: true, message: '请输入IP范围', trigger: 'blur' }
  ],
  ports: [
    { required: true, message: '请选择扫描端口', trigger: 'change' }
  ]
}

// 扫描进度
const scanProgress = reactive({
  percentage: 0,
  status: 'normal',
  message: '准备开始扫描...',
  scanned: 0,
  total: 0,
  found: 0
})

// 扫描日志
const scanLogs = ref([])

// 发现的证书
const discoveredCertificates = ref([])
const selectedCertificates = ref([])

// 导入结果
const importResult = ref({
  success: false,
  message: '',
  selected_count: 0,
  success_count: 0,
  failed_count: 0
})

// 计算属性
const estimatedTargets = computed(() => {
  // 简单估算目标数量
  const ipCount = scanConfig.ip_ranges.split('\n').length * 10 // 粗略估算
  return ipCount * scanConfig.ports.length
})

const estimatedTime = computed(() => {
  const targets = estimatedTargets.value
  const timePerTarget = scanConfig.timeout + 1
  const totalTime = Math.ceil(targets * timePerTarget / scanConfig.max_concurrent)
  return `约 ${Math.ceil(totalTime / 60)} 分钟`
})

const canStartScan = computed(() => {
  return scanConfig.ip_ranges && scanConfig.ports.length > 0
})

// 方法
const nextStep = () => {
  if (currentStep.value < 3) {
    currentStep.value++
  }
}

const prevStep = () => {
  if (currentStep.value > 0) {
    currentStep.value--
  }
}

const startScan = async () => {
  try {
    currentStep.value = 1
    
    // 重置进度
    Object.assign(scanProgress, {
      percentage: 0,
      status: 'normal',
      message: '正在启动扫描...',
      scanned: 0,
      total: estimatedTargets.value,
      found: 0
    })
    
    scanLogs.value = []
    
    // 启动扫描
    const response = await certificateApi.startDiscoveryScan({
      ip_ranges: scanConfig.ip_ranges.split('\n').filter(ip => ip.trim()),
      ports: scanConfig.ports,
      timeout: scanConfig.timeout,
      max_concurrent: scanConfig.max_concurrent,
      options: scanConfig.options
    })
    
    // 模拟扫描进度（实际应该通过WebSocket或轮询获取）
    simulateScanProgress(response.data.task_id)
    
  } catch (error) {
    console.error('启动扫描失败:', error)
    ElMessage.error('启动扫描失败')
  }
}

const simulateScanProgress = (taskId: string) => {
  const interval = setInterval(async () => {
    try {
      // 这里应该调用真实的任务状态API
      scanProgress.percentage += 10
      scanProgress.scanned += Math.floor(scanProgress.total * 0.1)
      
      if (scanProgress.percentage >= 100) {
        scanProgress.status = 'success'
        scanProgress.message = '扫描完成'
        clearInterval(interval)
        
        // 模拟发现的证书数据
        discoveredCertificates.value = [
          {
            ip_address: '192.168.1.100',
            port: 443,
            domain: 'example.com',
            status: 'valid',
            issuer: 'Let\'s Encrypt',
            expires_at: '2024-12-31T23:59:59Z',
            san_domains: ['www.example.com', 'api.example.com']
          }
        ]
        
        scanProgress.found = discoveredCertificates.value.length
        currentStep.value = 2
      }
    } catch (error) {
      clearInterval(interval)
      scanProgress.status = 'exception'
      scanProgress.message = '扫描失败'
    }
  }, 1000)
}

const cancelScan = () => {
  scanProgress.status = 'exception'
  scanProgress.message = '扫描已取消'
  currentStep.value = 0
}

const selectAll = () => {
  certificateTableRef.value?.toggleAllSelection()
}

const selectNone = () => {
  certificateTableRef.value?.clearSelection()
}

const selectValid = () => {
  certificateTableRef.value?.clearSelection()
  discoveredCertificates.value.forEach(cert => {
    if (cert.status === 'valid') {
      certificateTableRef.value?.toggleRowSelection(cert, true)
    }
  })
}

const handleSelectionChange = (selection: any[]) => {
  selectedCertificates.value = selection
}

const viewCertDetails = (cert: any) => {
  selectedCertDetails.value = cert
  certDetailsVisible.value = true
}

const importSelected = async () => {
  try {
    const response = await certificateApi.importFromDiscovery({
      certificates: selectedCertificates.value
    })
    
    importResult.value = {
      success: true,
      message: '证书导入成功',
      selected_count: selectedCertificates.value.length,
      success_count: response.data.success_count,
      failed_count: response.data.failed_count
    }
    
    currentStep.value = 3
    
  } catch (error) {
    console.error('导入失败:', error)
    ElMessage.error('导入失败')
  }
}

const resetDiscovery = () => {
  currentStep.value = 0
  discoveredCertificates.value = []
  selectedCertificates.value = []
  scanLogs.value = []
}

const finishDiscovery = () => {
  emit('discoveryCompleted', discoveredCertificates.value)
}

// 辅助方法
const getCertStatusType = (status: string) => {
  switch (status) {
    case 'valid': return 'success'
    case 'expired': return 'danger'
    case 'expiring': return 'warning'
    default: return 'info'
  }
}

const getCertStatusText = (status: string) => {
  switch (status) {
    case 'valid': return '有效'
    case 'expired': return '已过期'
    case 'expiring': return '即将过期'
    default: return '未知'
  }
}

const getExpiryClass = (expiresAt: string) => {
  const days = dayjs(expiresAt).diff(dayjs(), 'day')
  if (days < 0) return 'expired'
  if (days < 30) return 'expiring'
  return 'valid'
}

const formatDate = (dateString: string) => {
  return dayjs(dateString).format('YYYY-MM-DD')
}

const formatTime = (timestamp: number) => {
  return dayjs(timestamp).format('HH:mm:ss')
}
</script>

<style scoped>
.certificate-discovery {
  padding: 20px;
}

.step-content {
  margin-top: 30px;
  min-height: 400px;
}

.input-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 5px;
}

.scan-preview {
  margin: 20px 0;
  padding: 15px;
  background-color: #f5f7fa;
  border-radius: 4px;
}

.step-actions {
  margin-top: 30px;
  text-align: center;
}

.scan-progress {
  text-align: center;
  margin: 30px 0;
}

.progress-info {
  margin-top: 20px;
}

.scan-log {
  margin: 20px 0;
}

.log-content {
  padding: 10px;
  background-color: #f5f7fa;
  border-radius: 4px;
}

.log-item {
  margin: 5px 0;
  font-family: monospace;
  font-size: 12px;
}

.log-time {
  color: #909399;
  margin-right: 10px;
}

.discovery-summary {
  margin-bottom: 20px;
}

.selection-toolbar {
  margin-bottom: 10px;
}

.expired {
  color: #f56c6c;
}

.expiring {
  color: #e6a23c;
}

.valid {
  color: #67c23a;
}

.cert-details {
  padding: 10px;
}
</style>
