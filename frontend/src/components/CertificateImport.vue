<template>
  <div class="certificate-import">
    <el-steps :active="currentStep" finish-status="success">
      <el-step title="选择导入方式" />
      <el-step title="配置导入参数" />
      <el-step title="预览和确认" />
      <el-step title="导入结果" />
    </el-steps>

    <!-- 步骤1: 选择导入方式 -->
    <div v-if="currentStep === 0" class="step-content">
      <h3>选择导入方式</h3>
      <el-radio-group v-model="importMethod" size="large">
        <el-radio-button label="csv">CSV文件导入</el-radio-button>
        <el-radio-button label="manual">手动添加</el-radio-button>
      </el-radio-group>

      <div class="method-description">
        <div v-if="importMethod === 'csv'" class="csv-description">
          <h4>CSV文件导入</h4>
          <p>支持批量导入证书信息，CSV文件应包含以下字段：</p>
          <ul>
            <li><strong>domain</strong> - 域名（必填）</li>
            <li><strong>server_ip</strong> - 服务器IP地址</li>
            <li><strong>server_port</strong> - 端口号（默认443）</li>
            <li><strong>type</strong> - 证书类型（single/wildcard/multi）</li>
            <li><strong>ca_type</strong> - CA类型（letsencrypt/digicert等）</li>
            <li><strong>notes</strong> - 备注信息</li>
          </ul>
          
          <el-button @click="downloadTemplate">下载CSV模板</el-button>
        </div>

        <div v-if="importMethod === 'manual'" class="manual-description">
          <h4>手动添加</h4>
          <p>逐个添加证书信息，适合少量证书的导入。</p>
        </div>
      </div>

      <div class="step-actions">
        <el-button type="primary" @click="nextStep">下一步</el-button>
      </div>
    </div>

    <!-- 步骤2: 配置导入参数 -->
    <div v-if="currentStep === 1" class="step-content">
      <h3>配置导入参数</h3>

      <!-- CSV导入配置 -->
      <div v-if="importMethod === 'csv'" class="csv-config">
        <el-upload
          ref="uploadRef"
          class="upload-demo"
          drag
          :auto-upload="false"
          :on-change="handleFileChange"
          :file-list="fileList"
          accept=".csv"
          :limit="1"
        >
          <el-icon class="el-icon--upload"><upload-filled /></el-icon>
          <div class="el-upload__text">
            将CSV文件拖到此处，或<em>点击上传</em>
          </div>
          <template #tip>
            <div class="el-upload__tip">
              只能上传CSV文件，且不超过10MB
            </div>
          </template>
        </el-upload>

        <div v-if="csvData.length > 0" class="csv-preview">
          <h4>文件预览（前5行）</h4>
          <el-table :data="csvData.slice(0, 5)" border>
            <el-table-column
              v-for="(column, index) in csvColumns"
              :key="index"
              :prop="column"
              :label="column"
              min-width="120"
            />
          </el-table>
          <p>总计 {{ csvData.length }} 行数据</p>
        </div>

        <div class="import-options">
          <h4>导入选项</h4>
          <el-form :model="importOptions" label-width="120px">
            <el-form-item label="跳过重复">
              <el-switch v-model="importOptions.skipDuplicates" />
              <span class="option-desc">跳过已存在的域名</span>
            </el-form-item>
            
            <el-form-item label="更新现有">
              <el-switch v-model="importOptions.updateExisting" />
              <span class="option-desc">更新已存在域名的信息</span>
            </el-form-item>
            
            <el-form-item label="验证域名">
              <el-switch v-model="importOptions.validateDomains" />
              <span class="option-desc">导入前验证域名格式</span>
            </el-form-item>
          </el-form>
        </div>
      </div>

      <!-- 手动添加配置 -->
      <div v-if="importMethod === 'manual'" class="manual-config">
        <el-form :model="manualForm" :rules="manualRules" ref="manualFormRef" label-width="120px">
          <el-form-item label="域名" prop="domain">
            <el-input v-model="manualForm.domain" placeholder="例如: example.com" />
          </el-form-item>
          
          <el-form-item label="服务器IP" prop="server_ip">
            <el-input v-model="manualForm.server_ip" placeholder="例如: 192.168.1.100" />
          </el-form-item>
          
          <el-form-item label="端口" prop="server_port">
            <el-input-number v-model="manualForm.server_port" :min="1" :max="65535" />
          </el-form-item>
          
          <el-form-item label="证书类型" prop="type">
            <el-select v-model="manualForm.type">
              <el-option label="单域名" value="single" />
              <el-option label="通配符" value="wildcard" />
              <el-option label="多域名" value="multi" />
            </el-select>
          </el-form-item>
          
          <el-form-item label="CA类型" prop="ca_type">
            <el-select v-model="manualForm.ca_type">
              <el-option label="Let's Encrypt" value="letsencrypt" />
              <el-option label="DigiCert" value="digicert" />
              <el-option label="Comodo" value="comodo" />
            </el-select>
          </el-form-item>
          
          <el-form-item label="备注">
            <el-input v-model="manualForm.notes" type="textarea" rows="3" />
          </el-form-item>
        </el-form>
      </div>

      <div class="step-actions">
        <el-button @click="prevStep">上一步</el-button>
        <el-button type="primary" @click="nextStep" :disabled="!canProceed">下一步</el-button>
      </div>
    </div>

    <!-- 步骤3: 预览和确认 -->
    <div v-if="currentStep === 2" class="step-content">
      <h3>预览和确认</h3>
      
      <div class="import-summary">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="导入方式">
            {{ importMethod === 'csv' ? 'CSV文件导入' : '手动添加' }}
          </el-descriptions-item>
          <el-descriptions-item label="证书数量">
            {{ importMethod === 'csv' ? csvData.length : 1 }}
          </el-descriptions-item>
          <el-descriptions-item label="跳过重复">
            {{ importOptions.skipDuplicates ? '是' : '否' }}
          </el-descriptions-item>
          <el-descriptions-item label="更新现有">
            {{ importOptions.updateExisting ? '是' : '否' }}
          </el-descriptions-item>
        </el-descriptions>
      </div>

      <div class="preview-data">
        <h4>导入数据预览</h4>
        <el-table :data="previewData" border max-height="400">
          <el-table-column prop="domain" label="域名" min-width="150" />
          <el-table-column prop="server_ip" label="服务器IP" min-width="120" />
          <el-table-column prop="server_port" label="端口" width="80" />
          <el-table-column prop="type" label="类型" width="100" />
          <el-table-column prop="ca_type" label="CA类型" width="120" />
          <el-table-column prop="notes" label="备注" min-width="150" show-overflow-tooltip />
        </el-table>
      </div>

      <div class="step-actions">
        <el-button @click="prevStep">上一步</el-button>
        <el-button type="primary" @click="executeImport" :loading="importing">
          确认导入
        </el-button>
      </div>
    </div>

    <!-- 步骤4: 导入结果 -->
    <div v-if="currentStep === 3" class="step-content">
      <h3>导入结果</h3>
      
      <div class="import-result">
        <el-result
          :icon="importResult.success ? 'success' : 'error'"
          :title="importResult.success ? '导入成功' : '导入失败'"
          :sub-title="importResult.message"
        >
          <template #extra>
            <div class="result-details">
              <el-descriptions :column="3" border>
                <el-descriptions-item label="总数">
                  {{ importResult.total || 0 }}
                </el-descriptions-item>
                <el-descriptions-item label="成功">
                  <el-tag type="success">{{ importResult.success_count || 0 }}</el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="失败">
                  <el-tag type="danger">{{ importResult.failed_count || 0 }}</el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="跳过">
                  <el-tag type="info">{{ importResult.skipped_count || 0 }}</el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="重复">
                  <el-tag type="warning">{{ importResult.duplicate_count || 0 }}</el-tag>
                </el-descriptions-item>
              </el-descriptions>

              <div v-if="importResult.errors && importResult.errors.length > 0" class="error-list">
                <h4>错误详情</h4>
                <el-table :data="importResult.errors" border max-height="200">
                  <el-table-column prop="row" label="行号" width="80" />
                  <el-table-column prop="domain" label="域名" min-width="150" />
                  <el-table-column prop="error" label="错误信息" min-width="200" />
                </el-table>
              </div>
            </div>
          </template>
        </el-result>
      </div>

      <div class="step-actions">
        <el-button @click="resetImport">重新导入</el-button>
        <el-button type="primary" @click="finishImport">完成</el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { certificateApi } from '@/api/certificate'
import Papa from 'papaparse'

const emit = defineEmits<{
  importCompleted: [result: any]
}>()

// 响应式数据
const currentStep = ref(0)
const importMethod = ref('csv')
const importing = ref(false)
const fileList = ref([])
const csvData = ref([])
const csvColumns = ref([])

// 导入选项
const importOptions = reactive({
  skipDuplicates: true,
  updateExisting: false,
  validateDomains: true
})

// 手动添加表单
const manualForm = reactive({
  domain: '',
  server_ip: '',
  server_port: 443,
  type: 'single',
  ca_type: 'letsencrypt',
  notes: ''
})

// 表单验证规则
const manualRules = {
  domain: [
    { required: true, message: '请输入域名', trigger: 'blur' },
    { pattern: /^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$/, message: '请输入有效的域名', trigger: 'blur' }
  ],
  server_ip: [
    { required: true, message: '请输入服务器IP', trigger: 'blur' },
    { pattern: /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/, message: '请输入有效的IP地址', trigger: 'blur' }
  ]
}

// 导入结果
const importResult = ref({
  success: false,
  message: '',
  total: 0,
  success_count: 0,
  failed_count: 0,
  skipped_count: 0,
  duplicate_count: 0,
  errors: []
})

// 计算属性
const canProceed = computed(() => {
  if (importMethod.value === 'csv') {
    return csvData.value.length > 0
  } else {
    return manualForm.domain && manualForm.server_ip
  }
})

const previewData = computed(() => {
  if (importMethod.value === 'csv') {
    return csvData.value
  } else {
    return [manualForm]
  }
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

const downloadTemplate = () => {
  const template = [
    ['domain', 'server_ip', 'server_port', 'type', 'ca_type', 'notes'],
    ['example.com', '192.168.1.100', '443', 'single', 'letsencrypt', '示例证书'],
    ['*.example.com', '192.168.1.101', '443', 'wildcard', 'letsencrypt', '通配符证书']
  ]
  
  const csv = Papa.unparse(template)
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = 'certificate_import_template.csv'
  link.click()
}

const handleFileChange = (file: any) => {
  const reader = new FileReader()
  reader.onload = (e) => {
    const csv = e.target?.result as string
    const result = Papa.parse(csv, {
      header: true,
      skipEmptyLines: true
    })
    
    if (result.errors.length > 0) {
      ElMessage.error('CSV文件解析失败')
      return
    }
    
    csvData.value = result.data
    csvColumns.value = result.meta.fields || []
    ElMessage.success(`成功解析 ${csvData.value.length} 行数据`)
  }
  reader.readAsText(file.raw)
}

const executeImport = async () => {
  try {
    importing.value = true
    
    let importData
    if (importMethod.value === 'csv') {
      importData = {
        method: 'csv',
        data: csvData.value,
        options: importOptions
      }
    } else {
      importData = {
        method: 'manual',
        data: [manualForm],
        options: importOptions
      }
    }
    
    const response = await certificateApi.importCertificates(importData)
    
    importResult.value = response.data
    currentStep.value = 3
    
  } catch (error) {
    console.error('导入失败:', error)
    ElMessage.error('导入失败')
  } finally {
    importing.value = false
  }
}

const resetImport = () => {
  currentStep.value = 0
  csvData.value = []
  csvColumns.value = []
  fileList.value = []
  Object.assign(manualForm, {
    domain: '',
    server_ip: '',
    server_port: 443,
    type: 'single',
    ca_type: 'letsencrypt',
    notes: ''
  })
}

const finishImport = () => {
  emit('importCompleted', importResult.value)
}
</script>

<style scoped>
.certificate-import {
  padding: 20px;
}

.step-content {
  margin-top: 30px;
  min-height: 400px;
}

.method-description {
  margin: 20px 0;
  padding: 20px;
  background-color: #f5f7fa;
  border-radius: 4px;
}

.csv-description ul {
  margin: 10px 0;
  padding-left: 20px;
}

.step-actions {
  margin-top: 30px;
  text-align: center;
}

.csv-preview {
  margin: 20px 0;
}

.import-options {
  margin: 20px 0;
}

.option-desc {
  margin-left: 10px;
  color: #909399;
  font-size: 12px;
}

.import-summary {
  margin-bottom: 20px;
}

.preview-data {
  margin: 20px 0;
}

.import-result {
  text-align: center;
}

.result-details {
  margin-top: 20px;
}

.error-list {
  margin-top: 20px;
  text-align: left;
}
</style>
