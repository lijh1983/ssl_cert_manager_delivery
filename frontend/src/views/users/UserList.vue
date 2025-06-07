<template>
  <div class="user-list">
    <!-- 页面标题和操作栏 -->
    <div class="page-header">
      <h2>用户管理</h2>
      <div class="header-actions">
        <el-button type="primary" :icon="Plus" @click="showCreateDialog">
          添加用户
        </el-button>
      </div>
    </div>

    <!-- 用户列表 -->
    <el-card class="table-card">
      <el-table
        v-loading="loading"
        :data="userList"
        style="width: 100%"
      >
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="username" label="用户名" width="150" />
        <el-table-column prop="email" label="邮箱" min-width="200" />
        <el-table-column prop="role" label="角色" width="100">
          <template #default="scope">
            <el-tag :type="scope.row.role === 'admin' ? 'danger' : 'primary'" size="small">
              {{ scope.row.role === 'admin' ? '管理员' : '普通用户' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="160">
          <template #default="scope">
            {{ formatDate(scope.row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间" width="160">
          <template #default="scope">
            {{ formatDate(scope.row.updated_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="scope">
            <el-button type="text" size="small" @click="editUser(scope.row)">
              编辑
            </el-button>
            <el-button type="text" size="small" @click="resetPassword(scope.row)">
              重置密码
            </el-button>
            <el-button 
              v-if="scope.row.username !== 'admin'"
              type="text" 
              size="small" 
              style="color: #f56c6c"
              @click="deleteUser(scope.row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 创建/编辑用户对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="500px"
      @close="resetForm"
    >
      <el-form
        ref="formRef"
        :model="userForm"
        :rules="formRules"
        label-width="100px"
      >
        <el-form-item label="用户名" prop="username">
          <el-input 
            v-model="userForm.username" 
            placeholder="请输入用户名"
            :disabled="!!currentUser"
          />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="userForm.email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item v-if="!currentUser" label="密码" prop="password">
          <el-input 
            v-model="userForm.password" 
            type="password" 
            placeholder="请输入密码"
            show-password
          />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="userForm.role" placeholder="选择角色">
            <el-option label="管理员" value="admin" />
            <el-option label="普通用户" value="user" />
          </el-select>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="submitting" @click="handleSubmit">
            确定
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import type { User } from '@/types/auth'
import dayjs from 'dayjs'

// 响应式数据
const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const userList = ref<User[]>([])
const currentUser = ref<User | null>(null)

// 表单引用
const formRef = ref<FormInstance>()

// 用户表单
const userForm = reactive({
  username: '',
  email: '',
  password: '',
  role: 'user' as 'admin' | 'user'
})

// 表单验证规则
const formRules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 2, max: 50, message: '长度在 2 到 50 个字符', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于 6 个字符', trigger: 'blur' }
  ],
  role: [
    { required: true, message: '请选择角色', trigger: 'change' }
  ]
}

// 模拟数据
const mockUsers: User[] = [
  {
    id: 1,
    username: 'admin',
    email: 'admin@example.com',
    role: 'admin',
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-06-05T10:00:00Z'
  },
  {
    id: 2,
    username: 'user1',
    email: 'user1@example.com',
    role: 'user',
    created_at: '2025-06-01T00:00:00Z',
    updated_at: '2025-06-05T09:00:00Z'
  }
]

// 计算属性
const dialogTitle = computed(() => {
  return currentUser.value ? '编辑用户' : '添加用户'
})

// 获取用户列表
const fetchUserList = async () => {
  try {
    loading.value = true
    
    // 模拟API调用
    await new Promise(resolve => setTimeout(resolve, 500))
    userList.value = [...mockUsers]
    
  } catch (error) {
    console.error('Failed to fetch user list:', error)
    ElMessage.error('获取用户列表失败')
  } finally {
    loading.value = false
  }
}

// 格式化日期
const formatDate = (dateString: string) => {
  return dayjs(dateString).format('YYYY-MM-DD HH:mm')
}

// 显示创建对话框
const showCreateDialog = () => {
  currentUser.value = null
  dialogVisible.value = true
}

// 编辑用户
const editUser = (user: User) => {
  currentUser.value = user
  userForm.username = user.username
  userForm.email = user.email
  userForm.password = ''
  userForm.role = user.role
  dialogVisible.value = true
}

// 重置密码
const resetPassword = async (user: User) => {
  try {
    const { value: newPassword } = await ElMessageBox.prompt(
      '请输入新密码',
      '重置密码',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        inputType: 'password',
        inputValidator: (value) => {
          if (!value || value.length < 6) {
            return '密码长度不能少于 6 个字符'
          }
          return true
        }
      }
    )
    
    // 模拟API调用
    ElMessage.success('密码重置成功')
    
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to reset password:', error)
    }
  }
}

// 删除用户
const deleteUser = async (user: User) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除用户 "${user.username}" 吗？此操作不可恢复。`,
      '警告',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    // 模拟API调用
    const index = userList.value.findIndex(item => item.id === user.id)
    if (index > -1) {
      userList.value.splice(index, 1)
    }
    
    ElMessage.success('用户已删除')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to delete user:', error)
    }
  }
}

// 提交表单
const handleSubmit = async () => {
  if (!formRef.value) return
  
  try {
    const valid = await formRef.value.validate()
    if (!valid) return
    
    submitting.value = true
    
    if (currentUser.value) {
      // 编辑用户
      const index = userList.value.findIndex(item => item.id === currentUser.value!.id)
      if (index > -1) {
        userList.value[index] = {
          ...userList.value[index],
          email: userForm.email,
          role: userForm.role,
          updated_at: new Date().toISOString()
        }
      }
      ElMessage.success('用户已更新')
    } else {
      // 创建用户
      const newUser: User = {
        id: Date.now(),
        username: userForm.username,
        email: userForm.email,
        role: userForm.role,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      }
      userList.value.push(newUser)
      ElMessage.success('用户已创建')
    }
    
    dialogVisible.value = false
  } catch (error) {
    console.error('Failed to submit form:', error)
  } finally {
    submitting.value = false
  }
}

// 重置表单
const resetForm = () => {
  if (formRef.value) {
    formRef.value.resetFields()
  }
  userForm.username = ''
  userForm.email = ''
  userForm.password = ''
  userForm.role = 'user'
  currentUser.value = null
}

onMounted(() => {
  fetchUserList()
})
</script>

<style scoped>
.user-list {
  padding: 0;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  color: #303133;
}

.table-card {
  margin-bottom: 20px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: stretch;
    gap: 15px;
  }
  
  .header-actions {
    display: flex;
    justify-content: center;
  }
}
</style>
