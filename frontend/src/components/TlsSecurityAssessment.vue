<template>
  <div class="tls-security-assessment">
    <el-card class="assessment-card">
      <template #header>
        <div class="card-header">
          <span>TLS安全评估</span>
          <div class="header-actions">
            <el-button
              size="small"
              @click="runAssessment"
              :loading="assessing"
            >
              重新评估
            </el-button>
            <el-button
              size="small"
              type="info"
              @click="showAssessmentDetails"
            >
              详细报告
            </el-button>
          </div>
        </div>
      </template>

      <div class="assessment-content" v-loading="loading">
        <!-- 总体评级 -->
        <div class="overall-grade">
          <div class="grade-display">
            <div class="grade-letter" :class="getGradeClass(assessment.overall_grade)">
              {{ assessment.overall_grade || 'N/A' }}
            </div>
            <div class="grade-description">
              {{ getGradeDescription(assessment.overall_grade) }}
            </div>
          </div>
          
          <div class="grade-details">
            <el-descriptions :column="2" border size="small">
              <el-descriptions-item label="评估时间">
                {{ formatTime(assessment.assessed_at) }}
              </el-descriptions-item>
              <el-descriptions-item label="评估版本">
                {{ assessment.assessment_version || 'v1.0' }}
              </el-descriptions-item>
              <el-descriptions-item label="证书有效性">
                <el-tag :type="assessment.certificate_valid ? 'success' : 'danger'" size="small">
                  {{ assessment.certificate_valid ? '有效' : '无效' }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="证书链完整性">
                <el-tag :type="assessment.chain_complete ? 'success' : 'danger'" size="small">
                  {{ assessment.chain_complete ? '完整' : '不完整' }}
                </el-tag>
              </el-descriptions-item>
            </el-descriptions>
          </div>
        </div>

        <!-- 评估项目 -->
        <div class="assessment-items">
          <h4>评估详情</h4>
          
          <!-- 协议支持 -->
          <div class="assessment-section">
            <h5>协议支持</h5>
            <div class="protocol-grid">
              <div
                v-for="protocol in assessment.protocols"
                :key="protocol.name"
                class="protocol-item"
                :class="getProtocolClass(protocol.grade)"
              >
                <div class="protocol-name">{{ protocol.name }}</div>
                <div class="protocol-grade">{{ protocol.grade }}</div>
                <div class="protocol-status">
                  <el-tag :type="protocol.supported ? 'success' : 'info'" size="small">
                    {{ protocol.supported ? '支持' : '不支持' }}
                  </el-tag>
                </div>
              </div>
            </div>
          </div>

          <!-- 加密套件 -->
          <div class="assessment-section">
            <h5>加密套件</h5>
            <div class="cipher-summary">
              <el-row :gutter="20">
                <el-col :span="6">
                  <div class="cipher-stat">
                    <div class="stat-value">{{ assessment.cipher_suites?.total || 0 }}</div>
                    <div class="stat-label">总数</div>
                  </div>
                </el-col>
                <el-col :span="6">
                  <div class="cipher-stat">
                    <div class="stat-value strong">{{ assessment.cipher_suites?.strong || 0 }}</div>
                    <div class="stat-label">强加密</div>
                  </div>
                </el-col>
                <el-col :span="6">
                  <div class="cipher-stat">
                    <div class="stat-value weak">{{ assessment.cipher_suites?.weak || 0 }}</div>
                    <div class="stat-label">弱加密</div>
                  </div>
                </el-col>
                <el-col :span="6">
                  <div class="cipher-stat">
                    <div class="stat-value insecure">{{ assessment.cipher_suites?.insecure || 0 }}</div>
                    <div class="stat-label">不安全</div>
                  </div>
                </el-col>
              </el-row>
            </div>
          </div>

          <!-- 安全特性 -->
          <div class="assessment-section">
            <h5>安全特性</h5>
            <div class="security-features">
              <div
                v-for="feature in assessment.security_features"
                :key="feature.name"
                class="feature-item"
              >
                <div class="feature-name">{{ feature.name }}</div>
                <div class="feature-status">
                  <el-tag
                    :type="getFeatureStatusType(feature.status)"
                    size="small"
                  >
                    {{ getFeatureStatusText(feature.status) }}
                  </el-tag>
                </div>
                <div class="feature-description">{{ feature.description }}</div>
              </div>
            </div>
          </div>

          <!-- 漏洞检测 -->
          <div class="assessment-section">
            <h5>漏洞检测</h5>
            <div v-if="assessment.vulnerabilities?.length === 0" class="no-vulnerabilities">
              <el-result
                icon="success"
                title="未发现已知漏洞"
                sub-title="当前配置未检测到已知的安全漏洞"
              />
            </div>
            <div v-else class="vulnerabilities-list">
              <div
                v-for="vuln in assessment.vulnerabilities"
                :key="vuln.id"
                class="vulnerability-item"
                :class="getSeverityClass(vuln.severity)"
              >
                <div class="vuln-header">
                  <div class="vuln-name">{{ vuln.name }}</div>
                  <el-tag :type="getSeverityType(vuln.severity)" size="small">
                    {{ getSeverityText(vuln.severity) }}
                  </el-tag>
                </div>
                <div class="vuln-description">{{ vuln.description }}</div>
                <div v-if="vuln.recommendation" class="vuln-recommendation">
                  <strong>建议:</strong> {{ vuln.recommendation }}
                </div>
              </div>
            </div>
          </div>

          <!-- 改进建议 -->
          <div class="assessment-section">
            <h5>改进建议</h5>
            <div v-if="assessment.recommendations?.length === 0" class="no-recommendations">
              <el-result
                icon="success"
                title="配置良好"
                sub-title="当前TLS配置已达到最佳实践标准"
              />
            </div>
            <div v-else class="recommendations-list">
              <div
                v-for="(rec, index) in assessment.recommendations"
                :key="index"
                class="recommendation-item"
              >
                <div class="rec-priority">
                  <el-tag :type="getPriorityType(rec.priority)" size="small">
                    {{ getPriorityText(rec.priority) }}
                  </el-tag>
                </div>
                <div class="rec-content">
                  <div class="rec-title">{{ rec.title }}</div>
                  <div class="rec-description">{{ rec.description }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 详细报告对话框 -->
    <el-dialog
      v-model="detailsVisible"
      title="TLS安全评估详细报告"
      width="80%"
      :close-on-click-modal="false"
    >
      <div class="assessment-details">
        <el-tabs v-model="activeTab">
          <el-tab-pane label="协议分析" name="protocols">
            <div class="protocol-analysis">
              <!-- 协议详细分析内容 -->
              <pre>{{ JSON.stringify(assessment.protocols, null, 2) }}</pre>
            </div>
          </el-tab-pane>
          
          <el-tab-pane label="加密套件" name="ciphers">
            <div class="cipher-analysis">
              <!-- 加密套件详细分析内容 -->
              <pre>{{ JSON.stringify(assessment.cipher_suites, null, 2) }}</pre>
            </div>
          </el-tab-pane>
          
          <el-tab-pane label="证书链" name="certificate">
            <div class="certificate-analysis">
              <!-- 证书链详细分析内容 -->
              <pre>{{ JSON.stringify(assessment.certificate_chain, null, 2) }}</pre>
            </div>
          </el-tab-pane>
          
          <el-tab-pane label="原始数据" name="raw">
            <div class="raw-data">
              <pre>{{ JSON.stringify(assessment, null, 2) }}</pre>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="detailsVisible = false">关闭</el-button>
          <el-button type="primary" @click="exportReport">导出报告</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { certificateApi } from '@/api/certificate'
import type { Certificate } from '@/types/certificate'
import dayjs from 'dayjs'

interface Props {
  certificate: Certificate
}

const props = defineProps<Props>()

// 响应式数据
const loading = ref(false)
const assessing = ref(false)
const detailsVisible = ref(false)
const activeTab = ref('protocols')

// 评估结果
const assessment = reactive({
  overall_grade: 'A',
  assessed_at: '',
  assessment_version: 'v1.0',
  certificate_valid: true,
  chain_complete: true,
  protocols: [
    { name: 'TLS 1.3', grade: 'A+', supported: true },
    { name: 'TLS 1.2', grade: 'A', supported: true },
    { name: 'TLS 1.1', grade: 'C', supported: false },
    { name: 'TLS 1.0', grade: 'F', supported: false }
  ],
  cipher_suites: {
    total: 15,
    strong: 12,
    weak: 3,
    insecure: 0
  },
  security_features: [
    { name: 'Perfect Forward Secrecy', status: 'enabled', description: '支持完美前向保密' },
    { name: 'HSTS', status: 'enabled', description: 'HTTP严格传输安全已启用' },
    { name: 'OCSP Stapling', status: 'disabled', description: 'OCSP装订未启用' }
  ],
  vulnerabilities: [],
  recommendations: [
    { priority: 'medium', title: '启用OCSP Stapling', description: '建议启用OCSP装订以提高证书验证性能' }
  ]
})

// 方法
const getGradeClass = (grade: string): string => {
  switch (grade) {
    case 'A+':
    case 'A': return 'grade-excellent'
    case 'B': return 'grade-good'
    case 'C': return 'grade-fair'
    case 'D':
    case 'F': return 'grade-poor'
    default: return 'grade-unknown'
  }
}

const getGradeDescription = (grade: string): string => {
  switch (grade) {
    case 'A+': return '优秀 - 最佳安全配置'
    case 'A': return '优秀 - 安全配置良好'
    case 'B': return '良好 - 配置基本安全'
    case 'C': return '一般 - 存在安全隐患'
    case 'D': return '较差 - 安全配置不足'
    case 'F': return '失败 - 存在严重安全问题'
    default: return '未知 - 无法评估'
  }
}

const getProtocolClass = (grade: string): string => {
  return `protocol-${grade?.toLowerCase()}`
}

const getFeatureStatusType = (status: string): string => {
  switch (status) {
    case 'enabled': return 'success'
    case 'disabled': return 'warning'
    case 'error': return 'danger'
    default: return 'info'
  }
}

const getFeatureStatusText = (status: string): string => {
  switch (status) {
    case 'enabled': return '已启用'
    case 'disabled': return '未启用'
    case 'error': return '错误'
    default: return status
  }
}

const getSeverityClass = (severity: string): string => {
  return `severity-${severity}`
}

const getSeverityType = (severity: string): string => {
  switch (severity) {
    case 'critical': return 'danger'
    case 'high': return 'danger'
    case 'medium': return 'warning'
    case 'low': return 'info'
    default: return 'info'
  }
}

const getSeverityText = (severity: string): string => {
  switch (severity) {
    case 'critical': return '严重'
    case 'high': return '高危'
    case 'medium': return '中危'
    case 'low': return '低危'
    default: return severity
  }
}

const getPriorityType = (priority: string): string => {
  switch (priority) {
    case 'high': return 'danger'
    case 'medium': return 'warning'
    case 'low': return 'info'
    default: return 'info'
  }
}

const getPriorityText = (priority: string): string => {
  switch (priority) {
    case 'high': return '高优先级'
    case 'medium': return '中优先级'
    case 'low': return '低优先级'
    default: return priority
  }
}

const formatTime = (time?: string): string => {
  if (!time) return '未评估'
  return dayjs(time).format('YYYY-MM-DD HH:mm:ss')
}

const runAssessment = async () => {
  try {
    assessing.value = true
    
    const response = await certificateApi.runTlsAssessment(props.certificate.id)
    
    Object.assign(assessment, response.data)
    ElMessage.success('TLS安全评估完成')
    
  } catch (error) {
    console.error('TLS安全评估失败:', error)
    ElMessage.error('TLS安全评估失败')
  } finally {
    assessing.value = false
  }
}

const showAssessmentDetails = () => {
  detailsVisible.value = true
}

const exportReport = () => {
  const reportData = JSON.stringify(assessment, null, 2)
  const blob = new Blob([reportData], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `tls_assessment_${props.certificate.domain}_${dayjs().format('YYYYMMDD')}.json`
  link.click()
  URL.revokeObjectURL(url)
  
  ElMessage.success('报告已导出')
}

const fetchAssessment = async () => {
  try {
    loading.value = true
    
    const response = await certificateApi.getTlsAssessment(props.certificate.id)
    Object.assign(assessment, response.data)
    
  } catch (error) {
    console.error('获取TLS评估失败:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchAssessment()
})
</script>

<style scoped>
.tls-security-assessment {
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

.overall-grade {
  display: flex;
  gap: 30px;
  margin-bottom: 30px;
  padding: 20px;
  background-color: #f5f7fa;
  border-radius: 8px;
}

.grade-display {
  text-align: center;
}

.grade-letter {
  font-size: 48px;
  font-weight: bold;
  margin-bottom: 10px;
}

.grade-excellent { color: #67c23a; }
.grade-good { color: #409eff; }
.grade-fair { color: #e6a23c; }
.grade-poor { color: #f56c6c; }
.grade-unknown { color: #909399; }

.grade-description {
  font-size: 14px;
  color: #606266;
}

.grade-details {
  flex: 1;
}

.assessment-items h4 {
  margin: 0 0 20px 0;
  color: #303133;
}

.assessment-section {
  margin-bottom: 30px;
}

.assessment-section h5 {
  margin: 0 0 15px 0;
  color: #303133;
  font-size: 14px;
}

.protocol-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
}

.protocol-item {
  padding: 15px;
  border-radius: 4px;
  border: 1px solid #ebeef5;
  text-align: center;
}

.protocol-name {
  font-weight: 500;
  margin-bottom: 5px;
}

.protocol-grade {
  font-size: 18px;
  font-weight: bold;
  margin-bottom: 10px;
}

.cipher-summary {
  margin: 15px 0;
}

.cipher-stat {
  text-align: center;
  padding: 15px;
  background-color: #f5f7fa;
  border-radius: 4px;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  margin-bottom: 5px;
}

.stat-value.strong { color: #67c23a; }
.stat-value.weak { color: #e6a23c; }
.stat-value.insecure { color: #f56c6c; }

.stat-label {
  font-size: 12px;
  color: #909399;
}

.security-features {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 10px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
}

.feature-name {
  font-weight: 500;
  min-width: 150px;
}

.feature-description {
  color: #606266;
  font-size: 12px;
}

.vulnerabilities-list,
.recommendations-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.vulnerability-item,
.recommendation-item {
  padding: 15px;
  border-radius: 4px;
  border: 1px solid #ebeef5;
}

.vuln-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.vuln-name {
  font-weight: 500;
}

.vuln-description,
.vuln-recommendation {
  font-size: 14px;
  color: #606266;
  margin: 5px 0;
}

.recommendation-item {
  display: flex;
  gap: 15px;
}

.rec-priority {
  flex-shrink: 0;
}

.rec-title {
  font-weight: 500;
  margin-bottom: 5px;
}

.rec-description {
  font-size: 14px;
  color: #606266;
}

.assessment-details pre {
  background-color: #f5f7fa;
  padding: 15px;
  border-radius: 4px;
  overflow-x: auto;
  font-size: 12px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>
