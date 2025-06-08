<template>
  <div class="certificate-create">
    <!-- 页面标题 -->
    <div class="page-header">
      <el-breadcrumb separator="/">
        <el-breadcrumb-item :to="{ path: '/certificates' }">证书管理</el-breadcrumb-item>
        <el-breadcrumb-item>申请证书</el-breadcrumb-item>
      </el-breadcrumb>
    </div>

    <el-card class="create-card">
      <template #header>
        <div class="card-header">
          <span>申请新证书</span>
        </div>
      </template>
      
      <el-form
        ref="formRef"
        :model="form"
        :rules="formRules"
        label-width="120px"
        class="create-form"
      >
        <el-form-item label="域名" prop="domain">
          <el-input 
            v-model="form.domain" 
            placeholder="请输入域名，如: example.com"
          />
          <div class="form-tip">
            支持单域名、通配符域名（*.example.com）和多域名（用逗号分隔）
          </div>
        </el-form-item>

        <el-form-item label="证书类型" prop="type">
          <el-radio-group v-model="form.type">
            <el-radio label="single">单域名证书</el-radio>
            <el-radio label="wildcard">通配符证书</el-radio>
            <el-radio label="multi">多域名证书</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="目标服务器" prop="server_id">
          <el-select 
            v-model="form.server_id" 
            placeholder="请选择服务器"
            style="width: 100%"
          >
            <el-option
              v-for="server in servers"
              :key="server.id"
              :label="server.name"
              :value="server.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="CA类型" prop="ca_type">
          <el-select v-model="form.ca_type" placeholder="请选择CA类型">
            <el-option label="Let's Encrypt" value="letsencrypt" />
            <el-option label="ZeroSSL" value="zerossl" />
            <el-option label="Buypass" value="buypass" />
          </el-select>
        </el-form-item>

        <el-form-item label="验证方式" prop="validation_method">
          <el-radio-group v-model="form.validation_method">
            <el-radio label="dns">DNS验证</el-radio>
            <el-radio label="http">HTTP验证</el-radio>
          </el-radio-group>
          <div class="form-tip">
            DNS验证适用于通配符证书，HTTP验证适用于单域名证书
          </div>
        </el-form-item>

        <el-form-item label="自动续期">
          <el-switch v-model="form.auto_renew" />
          <div class="form-tip">
            开启后系统将在证书过期前自动续期
          </div>
        </el-form-item>

        <el-form-item label="邮箱地址" prop="email">
          <el-input 
            v-model="form.email" 
            placeholder="用于接收证书相关通知"
          />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="submitting" @click="handleSubmit">
            申请证书
          </el-button>
          <el-button @click="handleCancel">
            取消
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { certificateApi } from '@/api/certificate'
import { serverApi } from '@/api/server'
import type { CreateCertificateRequest } from '@/types/certificate'
import type { Server } from '@/types/server'

const router = useRouter()
const route = useRoute()

// 响应式数据
const submitting = ref(false)
const servers = ref<Server[]>([])

// 表单引用
const formRef = ref<FormInstance>()

// 表单数据
const form = reactive<CreateCertificateRequest>({
  domain: '',
  type: 'single',
  server_id: 0,
  ca_type: 'letsencrypt',
  validation_method: 'http',
  auto_renew: true,
  email: ''
})

// 表单验证规则
const formRules: FormRules = {
  domain: [
    { required: true, message: '请输入域名', trigger: 'blur' },
    { 
      pattern: /^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$/,
      message: '请输入有效的域名格式',
      trigger: 'blur'
    }
  ],
  type: [
    { required: true, message: '请选择证书类型', trigger: 'change' }
  ],
  server_id: [
    { required: true, message: '请选择目标服务器', trigger: 'change' }
  ],
  ca_type: [
    { required: true, message: '请选择CA类型', trigger: 'change' }
  ],
  validation_method: [
    { required: true, message: '请选择验证方式', trigger: 'change' }
  ],
  email: [
    { required: true, message: '请输入邮箱地址', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' }
  ]
}

// 获取服务器列表
const fetchServers = async () => {
  try {
    const response = await serverApi.getList()
    servers.value = response.data.items
  } catch (error) {
    console.error('Failed to fetch servers:', error)
  }
}

// 提交表单
const handleSubmit = async () => {
  if (!formRef.value) return
  
  try {
    const valid = await formRef.value.validate()
    if (!valid) return
    
    submitting.value = true
    await certificateApi.create(form)
    
    ElMessage.success('证书申请已提交，请等待处理')
    router.push('/certificates')
  } catch (error) {
    console.error('Failed to create certificate:', error)
    ElMessage.error('证书申请失败')
  } finally {
    submitting.value = false
  }
}

// 取消操作
const handleCancel = () => {
  router.push('/certificates')
}

onMounted(() => {
  fetchServers()
  
  // 如果URL中有server_id参数，自动选择服务器
  const serverId = route.query.server_id
  if (serverId) {
    form.server_id = parseInt(serverId as string)
  }
})
</script>

<style scoped>
.certificate-create {
  padding: 0;
}

.page-header {
  margin-bottom: 20px;
}

.create-card {
  max-width: 800px;
}

.card-header {
  font-size: 16px;
  font-weight: 600;
}

.create-form {
  padding: 20px 0;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 5px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .create-form {
    padding: 10px 0;
  }
}
</style>
