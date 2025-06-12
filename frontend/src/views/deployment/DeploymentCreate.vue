<template>
  <div class="deployment-create">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>添加服务器</h2>
    </div>

    <!-- 添加服务器弹窗 -->
    <el-card class="form-card">
      <el-form
        ref="formRef"
        :model="serverForm"
        :rules="formRules"
        label-width="120px"
      >
        <el-form-item label="服务器类型" prop="type">
          <el-select v-model="serverForm.type" placeholder="选择服务器类型">
            <el-option label="Nginx" value="nginx" />
            <el-option label="Apache" value="apache" />
            <el-option label="IIS" value="iis" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="名称" prop="name">
          <el-input v-model="serverForm.name" placeholder="请输入服务器名称" />
        </el-form-item>
        
        <el-form-item label="系统信息" prop="os_type">
          <el-input v-model="serverForm.os_type" placeholder="如：CentOS Linux 7 (Core)" />
        </el-form-item>
        
        <el-form-item label="IP地址" prop="ip">
          <el-input v-model="serverForm.ip" placeholder="请输入IP地址" />
        </el-form-item>
        
        <el-form-item label="版本" prop="version">
          <el-input v-model="serverForm.version" placeholder="如：1.17.0" />
        </el-form-item>
        
        <el-form-item label="自动部署">
          <el-switch v-model="serverForm.auto_renew" />
          <span style="margin-left: 10px; color: #606266; font-size: 12px;">
            开启后将自动部署证书到此服务器
          </span>
        </el-form-item>
        
        <el-form-item label="备注">
          <el-input 
            v-model="serverForm.description" 
            type="textarea" 
            :rows="3"
            placeholder="请输入备注信息"
          />
        </el-form-item>
      </el-form>
      
      <div class="form-actions">
        <el-button @click="handleCancel">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          保存
        </el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { serverApi } from '@/api/server'
import type { CreateServerRequest } from '@/types/server'

const router = useRouter()

// 响应式数据
const submitting = ref(false)

// 表单引用
const formRef = ref<FormInstance>()

// 服务器表单
const serverForm = reactive<CreateServerRequest & { 
  type?: string
  os_type?: string
  ip?: string
  version?: string
  description?: string
}>({
  name: '',
  auto_renew: true,
  type: 'nginx',
  os_type: '',
  ip: '',
  version: '',
  description: ''
})

// 表单验证规则
const formRules: FormRules = {
  type: [
    { required: true, message: '请选择服务器类型', trigger: 'change' }
  ],
  name: [
    { required: true, message: '请输入服务器名称', trigger: 'blur' },
    { min: 2, max: 50, message: '长度在 2 到 50 个字符', trigger: 'blur' }
  ],
  os_type: [
    { required: true, message: '请输入系统信息', trigger: 'blur' }
  ],
  ip: [
    { required: true, message: '请输入IP地址', trigger: 'blur' },
    { 
      pattern: /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/,
      message: '请输入有效的IP地址',
      trigger: 'blur'
    }
  ],
  version: [
    { required: true, message: '请输入版本信息', trigger: 'blur' }
  ]
}

// 提交表单
const handleSubmit = async () => {
  if (!formRef.value) return
  
  try {
    const valid = await formRef.value.validate()
    if (!valid) return
    
    submitting.value = true
    await serverApi.create(serverForm)
    
    ElMessage.success('服务器已创建')
    router.push('/deployment')
  } catch (error) {
    console.error('Failed to create server:', error)
    ElMessage.error('服务器创建失败')
  } finally {
    submitting.value = false
  }
}

// 取消操作
const handleCancel = () => {
  router.push('/deployment')
}
</script>

<style scoped>
.deployment-create {
  padding: 0;
}

.page-header {
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  color: #303133;
}

.form-card {
  max-width: 600px;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #ebeef5;
}
</style>
