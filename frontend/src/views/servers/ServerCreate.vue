<template>
  <div class="server-create">
    <!-- 页面标题 -->
    <div class="page-header">
      <el-breadcrumb separator="/">
        <el-breadcrumb-item :to="{ path: '/servers' }">服务器管理</el-breadcrumb-item>
        <el-breadcrumb-item>添加服务器</el-breadcrumb-item>
      </el-breadcrumb>
    </div>

    <el-card class="create-card">
      <template #header>
        <div class="card-header">
          <span>添加新服务器</span>
        </div>
      </template>
      
      <el-form
        ref="formRef"
        :model="form"
        :rules="formRules"
        label-width="120px"
        class="create-form"
      >
        <el-form-item label="服务器名称" prop="name">
          <el-input 
            v-model="form.name" 
            placeholder="请输入服务器名称，如: web-server-01"
          />
          <div class="form-tip">
            用于标识服务器的友好名称
          </div>
        </el-form-item>

        <el-form-item label="自动续期">
          <el-switch v-model="form.auto_renew" />
          <div class="form-tip">
            开启后系统将自动为该服务器上的证书进行续期
          </div>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="submitting" @click="handleSubmit">
            创建服务器
          </el-button>
          <el-button @click="handleCancel">
            取消
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 安装说明 -->
    <el-card v-if="serverToken" class="install-card">
      <template #header>
        <div class="card-header">
          <span>客户端安装说明</span>
        </div>
      </template>
      
      <div class="install-content">
        <el-alert
          title="服务器创建成功！"
          type="success"
          :closable="false"
          style="margin-bottom: 20px;"
        >
          <template #default>
            请在目标服务器上执行以下命令来安装和配置客户端：
          </template>
        </el-alert>

        <div class="install-step">
          <h4>1. 下载客户端脚本</h4>
          <el-input
            v-model="downloadCommand"
            readonly
            class="command-input"
          >
            <template #append>
              <el-button @click="copyToClipboard(downloadCommand)">
                复制
              </el-button>
            </template>
          </el-input>
        </div>

        <div class="install-step">
          <h4>2. 安装并启动客户端</h4>
          <el-input
            v-model="installCommand"
            readonly
            class="command-input"
          >
            <template #append>
              <el-button @click="copyToClipboard(installCommand)">
                复制
              </el-button>
            </template>
          </el-input>
        </div>

        <div class="install-notes">
          <h4>注意事项：</h4>
          <ul>
            <li>请确保目标服务器可以访问管理系统的API地址</li>
            <li>客户端需要root权限来管理证书文件</li>
            <li>安装完成后，客户端将自动向系统发送心跳信号</li>
            <li>服务器令牌仅显示一次，请妥善保存</li>
          </ul>
        </div>

        <div class="install-actions">
          <el-button type="primary" @click="goToServerList">
            返回服务器列表
          </el-button>
          <el-button @click="goToServerDetail">
            查看服务器详情
          </el-button>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { serverApi } from '@/api/server'
import type { CreateServerRequest } from '@/types/server'

const router = useRouter()

// 响应式数据
const submitting = ref(false)
const serverToken = ref('')
const serverId = ref(0)

// 表单引用
const formRef = ref<FormInstance>()

// 表单数据
const form = reactive<CreateServerRequest>({
  name: '',
  auto_renew: true
})

// 表单验证规则
const formRules: FormRules = {
  name: [
    { required: true, message: '请输入服务器名称', trigger: 'blur' },
    { min: 2, max: 50, message: '长度在 2 到 50 个字符', trigger: 'blur' },
    { 
      pattern: /^[a-zA-Z0-9\-_]+$/,
      message: '只能包含字母、数字、连字符和下划线',
      trigger: 'blur'
    }
  ]
}

// 下载命令
const downloadCommand = computed(() => {
  return `curl -o ssl-cert-client.sh https://your-domain.com/client/install.sh`
})

// 安装命令
const installCommand = computed(() => {
  if (!serverToken.value) return ''
  return `chmod +x ssl-cert-client.sh && sudo ./ssl-cert-client.sh --token="${serverToken.value}" --server="https://your-domain.com"`
})

// 提交表单
const handleSubmit = async () => {
  if (!formRef.value) return
  
  try {
    const valid = await formRef.value.validate()
    if (!valid) return
    
    submitting.value = true
    const response = await serverApi.create(form)
    
    // 保存服务器信息和令牌
    serverId.value = response.data.id
    serverToken.value = response.data.token || ''
    
    ElMessage.success('服务器创建成功')
  } catch (error) {
    console.error('Failed to create server:', error)
    ElMessage.error('服务器创建失败')
  } finally {
    submitting.value = false
  }
}

// 取消操作
const handleCancel = () => {
  router.push('/servers')
}

// 复制到剪贴板
const copyToClipboard = async (text: string) => {
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制到剪贴板')
  } catch (error) {
    console.error('Failed to copy to clipboard:', error)
    ElMessage.error('复制失败')
  }
}

// 返回服务器列表
const goToServerList = () => {
  router.push('/servers')
}

// 查看服务器详情
const goToServerDetail = () => {
  if (serverId.value) {
    router.push(`/servers/${serverId.value}`)
  }
}
</script>

<style scoped>
.server-create {
  padding: 0;
}

.page-header {
  margin-bottom: 20px;
}

.create-card,
.install-card {
  max-width: 800px;
  margin-bottom: 20px;
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

.install-content {
  padding: 10px 0;
}

.install-step {
  margin-bottom: 20px;
}

.install-step h4 {
  margin-bottom: 10px;
  color: #303133;
}

.command-input {
  font-family: 'Courier New', monospace;
}

.install-notes {
  margin: 20px 0;
  padding: 15px;
  background-color: #f5f7fa;
  border-radius: 4px;
}

.install-notes h4 {
  margin-bottom: 10px;
  color: #303133;
}

.install-notes ul {
  margin: 0;
  padding-left: 20px;
}

.install-notes li {
  margin-bottom: 5px;
  color: #606266;
}

.install-actions {
  margin-top: 20px;
  text-align: center;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .create-form {
    padding: 10px 0;
  }
  
  .install-actions {
    text-align: left;
  }
  
  .install-actions .el-button {
    width: 100%;
    margin-bottom: 10px;
  }
}
</style>
