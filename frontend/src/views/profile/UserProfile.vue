<template>
  <div class="user-profile">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>个人信息</h2>
    </div>

    <el-row :gutter="20">
      <!-- 基本信息 -->
      <el-col :xs="24" :lg="12">
        <el-card class="profile-card">
          <template #header>
            <div class="card-header">
              <span>基本信息</span>
              <el-button type="primary" size="small" @click="saveProfile">
                保存
              </el-button>
            </div>
          </template>
          
          <el-form 
            ref="profileFormRef"
            :model="profileForm" 
            :rules="profileRules"
            label-width="100px"
          >
            <el-form-item label="用户名">
              <el-input v-model="profileForm.username" disabled />
            </el-form-item>
            <el-form-item label="邮箱" prop="email">
              <el-input v-model="profileForm.email" />
            </el-form-item>
            <el-form-item label="角色">
              <el-tag :type="profileForm.role === 'admin' ? 'danger' : 'primary'">
                {{ profileForm.role === 'admin' ? '管理员' : '普通用户' }}
              </el-tag>
            </el-form-item>
            <el-form-item label="注册时间">
              <span>{{ formatDate(profileForm.created_at) }}</span>
            </el-form-item>
            <el-form-item label="最后更新">
              <span>{{ formatDate(profileForm.updated_at) }}</span>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <!-- 修改密码 -->
      <el-col :xs="24" :lg="12">
        <el-card class="profile-card">
          <template #header>
            <div class="card-header">
              <span>修改密码</span>
              <el-button type="primary" size="small" @click="changePassword">
                修改
              </el-button>
            </div>
          </template>
          
          <el-form 
            ref="passwordFormRef"
            :model="passwordForm" 
            :rules="passwordRules"
            label-width="100px"
          >
            <el-form-item label="当前密码" prop="current_password">
              <el-input 
                v-model="passwordForm.current_password" 
                type="password" 
                show-password
              />
            </el-form-item>
            <el-form-item label="新密码" prop="new_password">
              <el-input 
                v-model="passwordForm.new_password" 
                type="password" 
                show-password
              />
            </el-form-item>
            <el-form-item label="确认密码" prop="confirm_password">
              <el-input 
                v-model="passwordForm.confirm_password" 
                type="password" 
                show-password
              />
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
    </el-row>

    <!-- 登录记录 -->
    <el-card class="profile-card">
      <template #header>
        <div class="card-header">
          <span>最近登录记录</span>
          <el-button size="small" :icon="Refresh" @click="refreshLoginHistory">
            刷新
          </el-button>
        </div>
      </template>
      
      <el-table :data="loginHistory" style="width: 100%">
        <el-table-column prop="ip_address" label="IP地址" width="140" />
        <el-table-column prop="user_agent" label="用户代理" min-width="300" show-overflow-tooltip />
        <el-table-column prop="location" label="登录地点" width="150" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="scope">
            <el-tag :type="scope.row.status === 'success' ? 'success' : 'danger'" size="small">
              {{ scope.row.status === 'success' ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="登录时间" width="160">
          <template #default="scope">
            {{ formatDate(scope.row.created_at) }}
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import dayjs from 'dayjs'

const authStore = useAuthStore()

// 表单引用
const profileFormRef = ref<FormInstance>()
const passwordFormRef = ref<FormInstance>()

// 个人信息表单
const profileForm = reactive({
  username: '',
  email: '',
  role: 'user' as 'admin' | 'user',
  created_at: '',
  updated_at: ''
})

// 密码表单
const passwordForm = reactive({
  current_password: '',
  new_password: '',
  confirm_password: ''
})

// 登录记录
const loginHistory = ref([
  {
    id: 1,
    ip_address: '192.168.1.100',
    user_agent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    location: '北京市',
    status: 'success',
    created_at: '2025-06-05T09:00:00Z'
  },
  {
    id: 2,
    ip_address: '192.168.1.100',
    user_agent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    location: '北京市',
    status: 'success',
    created_at: '2025-06-04T14:30:00Z'
  },
  {
    id: 3,
    ip_address: '10.0.0.50',
    user_agent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X)',
    location: '上海市',
    status: 'failed',
    created_at: '2025-06-03T20:15:00Z'
  }
])

// 表单验证规则
const profileRules: FormRules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' }
  ]
}

const passwordRules: FormRules = {
  current_password: [
    { required: true, message: '请输入当前密码', trigger: 'blur' }
  ],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于 6 个字符', trigger: 'blur' }
  ],
  confirm_password: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== passwordForm.new_password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

// 格式化日期
const formatDate = (dateString: string) => {
  return dayjs(dateString).format('YYYY-MM-DD HH:mm:ss')
}

// 加载用户信息
const loadUserProfile = () => {
  if (authStore.user) {
    profileForm.username = authStore.user.username
    profileForm.email = authStore.user.email
    profileForm.role = authStore.user.role
    profileForm.created_at = authStore.user.created_at
    profileForm.updated_at = authStore.user.updated_at
  }
}

// 保存个人信息
const saveProfile = async () => {
  if (!profileFormRef.value) return
  
  try {
    const valid = await profileFormRef.value.validate()
    if (!valid) return
    
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 500))
    
    // 更新用户信息
    if (authStore.user) {
      authStore.updateUser({
        ...authStore.user,
        email: profileForm.email,
        updated_at: new Date().toISOString()
      })
    }
    
    ElMessage.success('个人信息已更新')
  } catch (error) {
    console.error('Failed to save profile:', error)
    ElMessage.error('保存失败')
  }
}

// 修改密码
const changePassword = async () => {
  if (!passwordFormRef.value) return
  
  try {
    const valid = await passwordFormRef.value.validate()
    if (!valid) return
    
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 500))
    
    ElMessage.success('密码修改成功')
    
    // 重置密码表单
    passwordForm.current_password = ''
    passwordForm.new_password = ''
    passwordForm.confirm_password = ''
    
    if (passwordFormRef.value) {
      passwordFormRef.value.resetFields()
    }
  } catch (error) {
    console.error('Failed to change password:', error)
    ElMessage.error('密码修改失败')
  }
}

// 刷新登录记录
const refreshLoginHistory = async () => {
  try {
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 500))
    ElMessage.success('登录记录已刷新')
  } catch (error) {
    console.error('Failed to refresh login history:', error)
    ElMessage.error('刷新失败')
  }
}

onMounted(() => {
  loadUserProfile()
})
</script>

<style scoped>
.user-profile {
  padding: 0;
}

.page-header {
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  color: #303133;
}

.profile-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .profile-card {
    margin-bottom: 15px;
  }
}
</style>
