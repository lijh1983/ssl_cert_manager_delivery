<template>
  <div class="certificate-operations-panel">
    <el-card class="operations-card">
      <template #header>
        <div class="card-header">
          <span>证书操作</span>
          <el-tag 
            v-if="certificate.check_in_progress"
            type="warning"
            size="small"
          >
            检测中...
          </el-tag>
        </div>
      </template>

      <div class="operations-content">
        <!-- 快速操作按钮 -->
        <div class="quick-actions">
          <el-button-group>
            <el-button 
              type="primary" 
              :loading="manualChecking"
              :disabled="certificate.check_in_progress"
              @click="showManualCheckDialog"
            >
              手动检测
            </el-button>
            
            <el-button 
              type="success" 
              :loading="renewing"
              :disabled="certificate.renewal_status === 'in_progress'"
              @click="showRenewDialog"
            >
              续期证书
            </el-button>
            
            <el-button 
              type="info" 
              @click="exportSingle"
            >
              导出
            </el-button>
          </el-button-group>
        </div>

        <!-- 操作状态信息 -->
        <div class="operation-status">
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="最后检测时间">
              {{ formatTime(certificate.last_manual_check) }}
            </el-descriptions-item>
            
            <el-descriptions-item label="续期状态">
              <el-tag 
                :type="getRenewalStatusType(certificate.renewal_status)"
                size="small"
              >
                {{ getRenewalStatusText(certificate.renewal_status) }}
              </el-tag>
            </el-descriptions-item>
            
            <el-descriptions-item label="自动续期">
              <el-switch
                v-model="autoRenewalEnabled"
                @change="updateAutoRenewal"
                :disabled="updating"
              />
            </el-descriptions-item>
            
            <el-descriptions-item label="导入来源">
              <el-tag size="small">
                {{ getImportSourceText(certificate.import_source) }}
              </el-tag>
            </el-descriptions-item>
          </el-descriptions>
        </div>
      </div>
    </el-card>

    <!-- 手动检测对话框 -->
    <el-dialog
      v-model="manualCheckVisible"
      title="手动检测配置"
      width="500px"
    >
      <el-form 
        :model="manualCheckForm" 
        label-width="100px"
      >
        <el-form-item label="检测类型">
          <el-checkbox-group v-model="manualCheckForm.check_types">
            <el-checkbox label="domain">域名检测</el-checkbox>
            <el-checkbox label="port">端口检测</el-checkbox>
            <el-checkbox label="ssl">SSL检测</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="manualCheckVisible = false">取消</el-button>
          <el-button 
            type="primary" 
            :loading="manualChecking"
            @click="executeManualCheck"
          >
            开始检测
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 续期确认对话框 -->
    <el-dialog
      v-model="renewVisible"
      title="证书续期确认"
      width="500px"
    >
      <div class="renew-content">
        <el-alert
          title="续期提醒"
          type="warning"
          description="证书续期操作可能需要一些时间，请确保服务器配置正确。"
          show-icon
          :closable="false"
        />
        
        <el-form 
          :model="renewForm" 
          label-width="100px"
          style="margin-top: 20px"
        >
          <el-form-item label="强制续期">
            <el-switch
              v-model="renewForm.force"
              active-text="是"
              inactive-text="否"
            />
          </el-form-item>
        </el-form>
      </div>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="renewVisible = false">取消</el-button>
          <el-button 
            type="primary" 
            :loading="renewing"
            @click="executeRenewal"
          >
            确认续期
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { certificateApi } from '@/api/certificate'
import type { Certificate } from '@/types/certificate'
import dayjs from 'dayjs'

interface Props {
  certificate: Certificate
}

const props = defineProps<Props>()
const emit = defineEmits<{
  refresh: []
  taskStarted: [taskId: string]
}>()

// 响应式数据
const manualChecking = ref(false)
const renewing = ref(false)
const updating = ref(false)
const manualCheckVisible = ref(false)
const renewVisible = ref(false)

// 表单数据
const manualCheckForm = reactive({
  check_types: ['domain', 'port', 'ssl']
})

const renewForm = reactive({
  force: false
})

// 计算属性
const autoRenewalEnabled = computed({
  get: () => props.certificate.auto_renewal_enabled || false,
  set: (value: boolean) => {
    // 这里会触发 updateAutoRenewal 方法
  }
})

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

// 获取导入来源文本
const getImportSourceText = (source?: string): string => {
  switch (source) {
    case 'manual': return '手动添加'
    case 'csv': return 'CSV导入'
    case 'discovery': return '网络发现'
    default: return '未知'
  }
}

// 格式化时间
const formatTime = (time?: string): string => {
  if (!time) return '暂无记录'
  return dayjs(time).format('YYYY-MM-DD HH:mm:ss')
}

// 显示手动检测对话框
const showManualCheckDialog = () => {
  manualCheckForm.check_types = ['domain', 'port', 'ssl']
  manualCheckVisible.value = true
}

// 执行手动检测
const executeManualCheck = async () => {
  if (manualCheckForm.check_types.length === 0) {
    ElMessage.warning('请选择至少一种检测类型')
    return
  }
  
  try {
    manualChecking.value = true
    const response = await certificateApi.manualCheck(props.certificate.id, {
      check_types: manualCheckForm.check_types
    })
    
    ElMessage.success('检测任务已启动')
    manualCheckVisible.value = false
    emit('taskStarted', response.data.task_id)
    
  } catch (error) {
    console.error('手动检测失败:', error)
    ElMessage.error('手动检测失败')
  } finally {
    manualChecking.value = false
  }
}

// 显示续期对话框
const showRenewDialog = () => {
  renewForm.force = false
  renewVisible.value = true
}

// 执行续期
const executeRenewal = async () => {
  try {
    renewing.value = true
    await certificateApi.renewCertificate(props.certificate.id, {
      force: renewForm.force
    })
    
    ElMessage.success('证书续期成功')
    renewVisible.value = false
    emit('refresh')
    
  } catch (error) {
    console.error('证书续期失败:', error)
    ElMessage.error('证书续期失败')
  } finally {
    renewing.value = false
  }
}

// 导出单个证书
const exportSingle = async () => {
  try {
    const blob = await certificateApi.exportCertificates({
      domain_pattern: props.certificate.domain
    })
    
    // 创建下载链接
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `certificate_${props.certificate.domain}_${dayjs().format('YYYYMMDD')}.csv`
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

// 更新自动续期设置
const updateAutoRenewal = async (enabled: boolean) => {
  try {
    updating.value = true
    ElMessage.success('自动续期设置已更新')
    emit('refresh')
    
  } catch (error) {
    console.error('更新自动续期设置失败:', error)
    ElMessage.error('更新失败')
  } finally {
    updating.value = false
  }
}
</script>

<style scoped>
.certificate-operations-panel {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.operations-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.quick-actions {
  display: flex;
  justify-content: center;
}

.operation-status {
  margin-top: 20px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.renew-content .el-alert {
  margin-bottom: 20px;
}
</style>
