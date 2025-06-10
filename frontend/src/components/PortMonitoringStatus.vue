<template>
  <div class="port-monitoring-status">
    <el-card class="status-card">
      <template #header>
        <div class="card-header">
          <span>端口监控状态</span>
          <el-button
            size="small"
            type="primary"
            @click="refreshStatus"
            :loading="refreshing"
          >
            刷新
          </el-button>
        </div>
      </template>

      <div class="status-content">
        <!-- SSL握手时间 -->
        <div class="status-item">
          <div class="status-label">SSL握手时间</div>
          <div class="status-value">
            <span v-if="certificate.ssl_handshake_time" class="handshake-time">
              {{ certificate.ssl_handshake_time }}ms
            </span>
            <span v-else class="no-data">未检测</span>
            <el-tag
              v-if="certificate.ssl_handshake_time"
              :type="getHandshakeTimeType(certificate.ssl_handshake_time)"
              size="small"
            >
              {{ getHandshakeTimeText(certificate.ssl_handshake_time) }}
            </el-tag>
          </div>
        </div>

        <!-- TLS版本 -->
        <div class="status-item">
          <div class="status-label">TLS版本</div>
          <div class="status-value">
            <el-tag
              v-if="certificate.tls_version"
              :type="getTlsVersionType(certificate.tls_version)"
              size="small"
            >
              {{ certificate.tls_version }}
            </el-tag>
            <span v-else class="no-data">未检测</span>
          </div>
        </div>

        <!-- 加密套件 -->
        <div class="status-item">
          <div class="status-label">加密套件</div>
          <div class="status-value">
            <span v-if="certificate.cipher_suite" class="cipher-suite">
              {{ certificate.cipher_suite }}
            </span>
            <span v-else class="no-data">未检测</span>
          </div>
        </div>

        <!-- 证书链有效性 -->
        <div class="status-item">
          <div class="status-label">证书链</div>
          <div class="status-value">
            <el-tag
              :type="certificate.certificate_chain_valid === true ? 'success' : certificate.certificate_chain_valid === false ? 'danger' : 'info'"
              size="small"
            >
              {{ certificate.certificate_chain_valid === true ? '完整' : certificate.certificate_chain_valid === false ? '不完整' : '未知' }}
            </el-tag>
          </div>
        </div>

        <!-- HTTP重定向状态 -->
        <div class="status-item">
          <div class="status-label">HTTP重定向</div>
          <div class="status-value">
            <el-tag
              v-if="certificate.http_redirect_status"
              :type="getRedirectStatusType(certificate.http_redirect_status)"
              size="small"
            >
              {{ getRedirectStatusText(certificate.http_redirect_status) }}
            </el-tag>
            <span v-else class="no-data">未检测</span>
          </div>
        </div>

        <!-- 监控端口配置 -->
        <div class="status-item">
          <div class="status-label">监控端口</div>
          <div class="status-value">
            <el-select
              v-model="monitoredPorts"
              @change="updateMonitoredPorts"
              multiple
              filterable
              allow-create
              placeholder="选择监控端口"
              style="width: 200px"
            >
              <el-option label="80 (HTTP)" :value="80" />
              <el-option label="443 (HTTPS)" :value="443" />
              <el-option label="8080 (HTTP备用)" :value="8080" />
              <el-option label="8443 (HTTPS备用)" :value="8443" />
            </el-select>
          </div>
        </div>
      </div>

      <!-- 安全评估 -->
      <div class="security-assessment">
        <h4>安全评估</h4>
        <div class="security-grid">
          <div class="security-item">
            <div class="security-label">安全等级</div>
            <div class="security-value">
              <el-tag
                :type="getSecurityGradeType(securityInfo.grade)"
                size="large"
              >
                {{ securityInfo.grade || 'N/A' }}
              </el-tag>
            </div>
          </div>
          
          <div class="security-item">
            <div class="security-label">协议支持</div>
            <div class="security-value">
              <el-tag
                v-for="protocol in securityInfo.protocols"
                :key="protocol"
                :type="getProtocolType(protocol)"
                size="small"
                style="margin-right: 5px"
              >
                {{ protocol }}
              </el-tag>
            </div>
          </div>
          
          <div class="security-item">
            <div class="security-label">漏洞检测</div>
            <div class="security-value">
              <el-tag
                v-if="securityInfo.vulnerabilities.length === 0"
                type="success"
                size="small"
              >
                无已知漏洞
              </el-tag>
              <el-tag
                v-else
                v-for="vuln in securityInfo.vulnerabilities"
                :key="vuln"
                type="danger"
                size="small"
                style="margin-right: 5px"
              >
                {{ vuln }}
              </el-tag>
            </div>
          </div>
        </div>
      </div>

      <!-- 端口监控历史 -->
      <div class="monitoring-history">
        <h4>最近监控记录</h4>
        <el-table
          :data="monitoringHistory"
          size="small"
          max-height="200"
          v-loading="loadingHistory"
        >
          <el-table-column prop="port" label="端口" width="80" />
          
          <el-table-column prop="check_type" label="检查类型" width="100">
            <template #default="scope">
              <el-tag size="small">
                {{ getCheckTypeText(scope.row.check_type) }}
              </el-tag>
            </template>
          </el-table-column>
          
          <el-table-column prop="status" label="状态" width="80">
            <template #default="scope">
              <el-tag
                :type="scope.row.status === 'success' ? 'success' : 'danger'"
                size="small"
              >
                {{ scope.row.status === 'success' ? '成功' : '失败' }}
              </el-tag>
            </template>
          </el-table-column>
          
          <el-table-column prop="handshake_time" label="握手时间" width="100">
            <template #default="scope">
              <span v-if="scope.row.handshake_time">
                {{ scope.row.handshake_time }}ms
              </span>
              <span v-else>-</span>
            </template>
          </el-table-column>
          
          <el-table-column prop="tls_version" label="TLS版本" width="100" />
          
          <el-table-column prop="security_grade" label="安全等级" width="100">
            <template #default="scope">
              <el-tag
                v-if="scope.row.security_grade"
                :type="getSecurityGradeType(scope.row.security_grade)"
                size="small"
              >
                {{ scope.row.security_grade }}
              </el-tag>
            </template>
          </el-table-column>
          
          <el-table-column prop="created_at" label="检查时间" min-width="150">
            <template #default="scope">
              {{ formatTime(scope.row.created_at) }}
            </template>
          </el-table-column>
        </el-table>

        <div v-if="monitoringHistory.length === 0 && !loadingHistory" class="no-history">
          暂无监控记录
        </div>
      </div>

      <!-- 手动检查 -->
      <div class="manual-check">
        <h4>手动检查</h4>
        <div class="check-buttons">
          <el-button
            size="small"
            @click="manualCheck('ssl')"
            :loading="checking.ssl"
          >
            SSL检查
          </el-button>
          
          <el-button
            size="small"
            @click="manualCheck('http_redirect')"
            :loading="checking.http_redirect"
          >
            HTTP重定向检查
          </el-button>
          
          <el-button
            size="small"
            type="primary"
            @click="manualCheck('all')"
            :loading="checking.all"
          >
            全面检查
          </el-button>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { certificateApi } from '@/api/certificate'
import type { Certificate } from '@/types/certificate'
import dayjs from 'dayjs'

interface Props {
  certificate: Certificate
}

const props = defineProps<Props>()
const emit = defineEmits<{
  updated: [certificate: Certificate]
}>()

// 响应式数据
const refreshing = ref(false)
const loadingHistory = ref(false)
const monitoringHistory = ref([])

const checking = reactive({
  ssl: false,
  http_redirect: false,
  all: false
})

// 安全信息
const securityInfo = reactive({
  grade: 'A',
  protocols: ['TLS 1.2', 'TLS 1.3'],
  vulnerabilities: []
})

// 计算属性
const monitoredPorts = computed({
  get: () => {
    try {
      return props.certificate.monitored_ports ? 
        JSON.parse(props.certificate.monitored_ports) : [443]
    } catch {
      return [443]
    }
  },
  set: (value: number[]) => {
    // 这里会触发 updateMonitoredPorts 方法
  }
})

// 方法
const getHandshakeTimeType = (time: number): string => {
  if (time < 100) return 'success'
  if (time < 500) return 'warning'
  return 'danger'
}

const getHandshakeTimeText = (time: number): string => {
  if (time < 100) return '优秀'
  if (time < 500) return '良好'
  return '较慢'
}

const getTlsVersionType = (version: string): string => {
  if (version.includes('1.3')) return 'success'
  if (version.includes('1.2')) return 'success'
  if (version.includes('1.1') || version.includes('1.0')) return 'warning'
  return 'danger'
}

const getRedirectStatusType = (status: string): string => {
  switch (status) {
    case 'enabled': return 'success'
    case 'disabled': return 'warning'
    case 'error': return 'danger'
    default: return 'info'
  }
}

const getRedirectStatusText = (status: string): string => {
  switch (status) {
    case 'enabled': return '已启用'
    case 'disabled': return '未启用'
    case 'error': return '错误'
    default: return status
  }
}

const getSecurityGradeType = (grade: string): string => {
  switch (grade) {
    case 'A+':
    case 'A': return 'success'
    case 'B': return 'warning'
    case 'C':
    case 'D':
    case 'F': return 'danger'
    default: return 'info'
  }
}

const getProtocolType = (protocol: string): string => {
  if (protocol.includes('1.3')) return 'success'
  if (protocol.includes('1.2')) return 'success'
  return 'warning'
}

const getCheckTypeText = (type: string): string => {
  switch (type) {
    case 'ssl': return 'SSL'
    case 'http_redirect': return 'HTTP重定向'
    default: return type
  }
}

const formatTime = (time?: string): string => {
  if (!time) return '未知'
  return dayjs(time).format('YYYY-MM-DD HH:mm:ss')
}

const refreshStatus = async () => {
  try {
    refreshing.value = true
    // 重新获取证书信息
    const response = await certificateApi.getDetail(props.certificate.id)
    emit('updated', response.data)
    
    // 刷新监控历史
    await fetchMonitoringHistory()
    
  } catch (error) {
    console.error('刷新状态失败:', error)
    ElMessage.error('刷新状态失败')
  } finally {
    refreshing.value = false
  }
}

const updateMonitoredPorts = async (ports: number[]) => {
  try {
    await certificateApi.updateMonitoringConfig(props.certificate.id, {
      monitored_ports: JSON.stringify(ports)
    })
    
    ElMessage.success('监控端口已更新')
    emit('updated', { ...props.certificate, monitored_ports: JSON.stringify(ports) })
    
  } catch (error) {
    console.error('更新监控端口失败:', error)
    ElMessage.error('更新监控端口失败')
  }
}

const fetchMonitoringHistory = async () => {
  try {
    loadingHistory.value = true
    const response = await certificateApi.getPortMonitoringHistory(props.certificate.id)
    monitoringHistory.value = response.data.history || []
    
  } catch (error) {
    console.error('获取监控历史失败:', error)
  } finally {
    loadingHistory.value = false
  }
}

const manualCheck = async (type: 'ssl' | 'http_redirect' | 'all') => {
  try {
    checking[type] = true
    
    let checkTypes = []
    if (type === 'ssl') {
      checkTypes = ['ssl']
    } else if (type === 'http_redirect') {
      checkTypes = ['http_redirect']
    } else {
      checkTypes = ['ssl', 'http_redirect']
    }
    
    await certificateApi.manualPortCheck(props.certificate.id, {
      check_types: checkTypes,
      ports: monitoredPorts.value
    })
    
    ElMessage.success('检查任务已启动')
    
    // 延迟刷新状态
    setTimeout(() => {
      refreshStatus()
    }, 2000)
    
  } catch (error) {
    console.error('手动检查失败:', error)
    ElMessage.error('手动检查失败')
  } finally {
    checking[type] = false
  }
}

onMounted(() => {
  fetchMonitoringHistory()
})
</script>

<style scoped>
.port-monitoring-status {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.status-content {
  margin-bottom: 20px;
}

.status-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid #f0f0f0;
}

.status-item:last-child {
  border-bottom: none;
}

.status-label {
  font-weight: 500;
  color: #303133;
  min-width: 120px;
}

.status-value {
  display: flex;
  align-items: center;
  gap: 10px;
}

.handshake-time {
  font-weight: 500;
  color: #409eff;
}

.cipher-suite {
  font-family: monospace;
  font-size: 12px;
  color: #606266;
}

.no-data {
  color: #909399;
  font-style: italic;
}

.security-assessment {
  margin: 20px 0;
}

.security-assessment h4 {
  margin: 0 0 15px 0;
  color: #303133;
}

.security-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
}

.security-item {
  padding: 15px;
  background-color: #f5f7fa;
  border-radius: 4px;
}

.security-label {
  font-size: 12px;
  color: #909399;
  margin-bottom: 8px;
}

.security-value {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.monitoring-history {
  margin: 20px 0;
}

.monitoring-history h4 {
  margin: 0 0 10px 0;
  color: #303133;
}

.no-history {
  text-align: center;
  color: #909399;
  padding: 20px;
}

.manual-check {
  margin-top: 20px;
}

.manual-check h4 {
  margin: 0 0 10px 0;
  color: #303133;
}

.check-buttons {
  display: flex;
  gap: 10px;
}
</style>
