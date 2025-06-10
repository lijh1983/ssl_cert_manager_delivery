<template>
  <div class="monitoring-config">
    <el-card class="config-card">
      <template #header>
        <div class="card-header">
          <span>监控配置</span>
          <el-switch
            v-model="monitoringEnabled"
            @change="updateMonitoringStatus"
            :loading="updating"
            active-text="启用"
            inactive-text="禁用"
          />
        </div>
      </template>

      <div class="config-content" v-loading="loading">
        <!-- 基础监控配置 -->
        <div class="basic-config">
          <h3>基础监控</h3>
          <el-form :model="config" label-width="120px" size="small">
            <el-form-item label="检查频率">
              <el-select v-model="config.check_frequency" @change="updateConfig">
                <el-option label="每小时" value="hourly" />
                <el-option label="每6小时" value="6hourly" />
                <el-option label="每12小时" value="12hourly" />
                <el-option label="每天" value="daily" />
                <el-option label="每周" value="weekly" />
              </el-select>
            </el-form-item>
            
            <el-form-item label="告警阈值">
              <el-input-number
                v-model="config.alert_threshold_days"
                :min="1"
                :max="365"
                @change="updateConfig"
              />
              <span style="margin-left: 8px">天</span>
            </el-form-item>
            
            <el-form-item label="连续失败次数">
              <el-input-number
                v-model="config.max_retry_count"
                :min="1"
                :max="10"
                @change="updateConfig"
              />
              <span style="margin-left: 8px">次</span>
            </el-form-item>
          </el-form>
        </div>

        <!-- 域名监控配置 -->
        <div class="domain-config">
          <h3>域名监控</h3>
          <el-form :model="config" label-width="120px" size="small">
            <el-form-item label="DNS检查">
              <el-switch
                v-model="config.dns_check_enabled"
                @change="updateConfig"
              />
            </el-form-item>
            
            <el-form-item label="可达性检查">
              <el-switch
                v-model="config.reachability_check_enabled"
                @change="updateConfig"
              />
            </el-form-item>
            
            <el-form-item label="检查超时">
              <el-input-number
                v-model="config.check_timeout"
                :min="5"
                :max="60"
                @change="updateConfig"
              />
              <span style="margin-left: 8px">秒</span>
            </el-form-item>
          </el-form>
        </div>

        <!-- 端口监控配置 -->
        <div class="port-config">
          <h3>端口监控</h3>
          <el-form :model="config" label-width="120px" size="small">
            <el-form-item label="SSL检查">
              <el-switch
                v-model="config.ssl_check_enabled"
                @change="updateConfig"
              />
            </el-form-item>
            
            <el-form-item label="TLS版本检查">
              <el-switch
                v-model="config.tls_version_check_enabled"
                @change="updateConfig"
              />
            </el-form-item>
            
            <el-form-item label="监控端口">
              <el-select
                v-model="config.monitored_ports"
                multiple
                filterable
                allow-create
                placeholder="选择或输入端口号"
                @change="updateConfig"
              >
                <el-option label="80 (HTTP)" :value="80" />
                <el-option label="443 (HTTPS)" :value="443" />
                <el-option label="8080 (HTTP备用)" :value="8080" />
                <el-option label="8443 (HTTPS备用)" :value="8443" />
              </el-select>
            </el-form-item>
          </el-form>
        </div>

        <!-- 告警配置 -->
        <div class="alert-config">
          <h3>告警配置</h3>
          <el-form :model="config" label-width="120px" size="small">
            <el-form-item label="邮件告警">
              <el-switch
                v-model="config.email_alerts_enabled"
                @change="updateConfig"
              />
            </el-form-item>
            
            <el-form-item label="告警邮箱">
              <el-input
                v-model="config.alert_email"
                placeholder="输入告警邮箱地址"
                @change="updateConfig"
              />
            </el-form-item>
            
            <el-form-item label="告警级别">
              <el-select v-model="config.alert_level" @change="updateConfig">
                <el-option label="低" value="low" />
                <el-option label="中" value="medium" />
                <el-option label="高" value="high" />
                <el-option label="紧急" value="critical" />
              </el-select>
            </el-form-item>
          </el-form>
        </div>

        <!-- 操作按钮 -->
        <div class="actions">
          <el-button @click="resetConfig">重置配置</el-button>
          <el-button type="primary" @click="saveConfig" :loading="saving">
            保存配置
          </el-button>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { certificateApi } from '@/api/certificate'
import type { MonitoringConfig as ConfigType } from '@/types/certificate'

interface Props {
  certificateId: number
}

const props = defineProps<Props>()
const emit = defineEmits<{
  configUpdated: [config: ConfigType]
}>()

// 响应式数据
const loading = ref(false)
const updating = ref(false)
const saving = ref(false)
const monitoringEnabled = ref(true)

// 配置数据
const config = reactive<ConfigType>({
  certificate_id: props.certificateId,
  monitoring_enabled: true,
  check_frequency: 'daily',
  alert_threshold_days: 30,
  max_retry_count: 3,
  dns_check_enabled: true,
  reachability_check_enabled: true,
  ssl_check_enabled: true,
  tls_version_check_enabled: true,
  check_timeout: 30,
  monitored_ports: [80, 443],
  email_alerts_enabled: false,
  alert_email: '',
  alert_level: 'medium'
})

// 获取监控配置
const fetchConfig = async () => {
  try {
    loading.value = true
    const response = await certificateApi.getMonitoringConfig(props.certificateId)
    Object.assign(config, response.data)
    monitoringEnabled.value = config.monitoring_enabled
  } catch (error) {
    console.error('获取监控配置失败:', error)
    ElMessage.error('获取监控配置失败')
  } finally {
    loading.value = false
  }
}

// 更新监控状态
const updateMonitoringStatus = async (enabled: boolean) => {
  try {
    updating.value = true
    config.monitoring_enabled = enabled
    await certificateApi.updateMonitoringConfig(props.certificateId, {
      monitoring_enabled: enabled
    })
    ElMessage.success(enabled ? '监控已启用' : '监控已禁用')
    emit('configUpdated', config)
  } catch (error) {
    console.error('更新监控状态失败:', error)
    ElMessage.error('更新监控状态失败')
    monitoringEnabled.value = !enabled // 回滚
  } finally {
    updating.value = false
  }
}

// 更新配置
const updateConfig = () => {
  emit('configUpdated', config)
}

// 保存配置
const saveConfig = async () => {
  try {
    saving.value = true
    await certificateApi.updateMonitoringConfig(props.certificateId, config)
    ElMessage.success('配置保存成功')
    emit('configUpdated', config)
  } catch (error) {
    console.error('保存配置失败:', error)
    ElMessage.error('保存配置失败')
  } finally {
    saving.value = false
  }
}

// 重置配置
const resetConfig = () => {
  Object.assign(config, {
    certificate_id: props.certificateId,
    monitoring_enabled: true,
    check_frequency: 'daily',
    alert_threshold_days: 30,
    max_retry_count: 3,
    dns_check_enabled: true,
    reachability_check_enabled: true,
    ssl_check_enabled: true,
    tls_version_check_enabled: true,
    check_timeout: 30,
    monitored_ports: [80, 443],
    email_alerts_enabled: false,
    alert_email: '',
    alert_level: 'medium'
  })
  monitoringEnabled.value = true
}

onMounted(() => {
  fetchConfig()
})
</script>

<style scoped>
.monitoring-config {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.config-content {
  display: flex;
  flex-direction: column;
  gap: 30px;
}

.basic-config h3,
.domain-config h3,
.port-config h3,
.alert-config h3 {
  margin: 0 0 20px 0;
  color: #303133;
  font-size: 16px;
}

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding-top: 20px;
  border-top: 1px solid #ebeef5;
}
</style>
