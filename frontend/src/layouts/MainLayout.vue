<template>
  <div class="layout-container">
    <!-- 顶部导航栏 -->
    <el-header class="header">
      <div class="header-left">
        <el-button 
          class="menu-toggle" 
          :icon="Fold" 
          @click="toggleSidebar"
          v-if="isMobile"
        />
        <div class="logo">
          <el-icon class="logo-icon"><Lock /></el-icon>
          <h1 class="logo-text">SSL证书管理系统</h1>
        </div>
      </div>
      
      <div class="header-right">
        <el-dropdown @command="handleUserCommand">
          <span class="user-dropdown">
            <el-avatar :size="32" :src="userAvatar">
              {{ authStore.user?.username?.charAt(0).toUpperCase() }}
            </el-avatar>
            <span class="username">{{ authStore.user?.username }}</span>
            <el-icon><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="profile">
                <el-icon><User /></el-icon>
                个人信息
              </el-dropdown-item>
              <el-dropdown-item command="logout" divided>
                <el-icon><SwitchButton /></el-icon>
                退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </el-header>

    <el-container class="main-container">
      <!-- 侧边栏 -->
      <el-aside 
        class="sidebar" 
        :class="{ 'is-collapse': isCollapse, 'is-mobile': isMobile }"
        :width="sidebarWidth"
      >
        <el-menu
          :default-active="activeMenu"
          :collapse="isCollapse"
          :unique-opened="true"
          router
          class="sidebar-menu"
        >
          <el-menu-item index="/dashboard">
            <el-icon><Odometer /></el-icon>
            <template #title>仪表盘</template>
          </el-menu-item>
          
          <el-menu-item index="/servers">
            <el-icon><Monitor /></el-icon>
            <template #title>服务器管理</template>
          </el-menu-item>
          
          <el-menu-item index="/certificates">
            <el-icon><Document /></el-icon>
            <template #title>证书管理</template>
          </el-menu-item>
          
          <el-menu-item index="/alerts">
            <el-icon><Bell /></el-icon>
            <template #title>告警管理</template>
          </el-menu-item>
          
          <el-menu-item index="/logs">
            <el-icon><Tickets /></el-icon>
            <template #title>操作日志</template>
          </el-menu-item>
          
          <el-menu-item 
            v-if="authStore.isAdmin" 
            index="/users"
          >
            <el-icon><UserFilled /></el-icon>
            <template #title>用户管理</template>
          </el-menu-item>
          
          <el-menu-item 
            v-if="authStore.isAdmin" 
            index="/settings"
          >
            <el-icon><Setting /></el-icon>
            <template #title>系统设置</template>
          </el-menu-item>
        </el-menu>
      </el-aside>

      <!-- 主内容区域 -->
      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>

    <!-- 移动端遮罩层 -->
    <div 
      v-if="isMobile && !isCollapse" 
      class="mobile-overlay"
      @click="closeSidebar"
    ></div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { 
  Lock, Fold, ArrowDown, User, SwitchButton,
  Odometer, Monitor, Document, Bell, Tickets, 
  UserFilled, Setting 
} from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const isCollapse = ref(false)
const isMobile = ref(false)
const userAvatar = ref('')

const activeMenu = computed(() => {
  const path = route.path
  if (path.startsWith('/servers')) return '/servers'
  if (path.startsWith('/certificates')) return '/certificates'
  if (path.startsWith('/alerts')) return '/alerts'
  if (path.startsWith('/logs')) return '/logs'
  if (path.startsWith('/users')) return '/users'
  if (path.startsWith('/settings')) return '/settings'
  return path
})

const sidebarWidth = computed(() => {
  if (isMobile.value) {
    return isCollapse.value ? '0px' : '220px'
  }
  return isCollapse.value ? '64px' : '220px'
})

// 检查是否为移动端
const checkMobile = () => {
  isMobile.value = window.innerWidth <= 768
  if (isMobile.value) {
    isCollapse.value = true
  }
}

// 切换侧边栏
const toggleSidebar = () => {
  isCollapse.value = !isCollapse.value
}

// 关闭侧边栏（移动端）
const closeSidebar = () => {
  if (isMobile.value) {
    isCollapse.value = true
  }
}

// 处理用户下拉菜单命令
const handleUserCommand = async (command: string) => {
  switch (command) {
    case 'profile':
      router.push('/profile')
      break
    case 'logout':
      try {
        await ElMessageBox.confirm(
          '确定要退出登录吗？',
          '提示',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )
        await authStore.logout()
        router.push('/login')
      } catch (error) {
        // 用户取消
      }
      break
  }
}

onMounted(() => {
  checkMobile()
  window.addEventListener('resize', checkMobile)
})

onUnmounted(() => {
  window.removeEventListener('resize', checkMobile)
})
</script>

<style scoped>
.layout-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background-color: #409eff;
  color: white;
  padding: 0 20px;
  height: 60px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 15px;
}

.menu-toggle {
  background: transparent;
  border: none;
  color: white;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
}

.logo-icon {
  font-size: 24px;
}

.logo-text {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
}

.header-right {
  display: flex;
  align-items: center;
}

.user-dropdown {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 8px;
  border-radius: 4px;
  transition: background-color 0.3s;
}

.user-dropdown:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

.username {
  font-size: 14px;
}

.main-container {
  flex: 1;
  overflow: hidden;
}

.sidebar {
  background-color: #fff;
  border-right: 1px solid #e6e6e6;
  transition: width 0.3s;
  overflow: hidden;
}

.sidebar.is-mobile {
  position: fixed;
  top: 60px;
  left: 0;
  bottom: 0;
  z-index: 1000;
  box-shadow: 2px 0 6px rgba(0, 0, 0, 0.1);
}

.sidebar-menu {
  height: 100%;
  border-right: none;
}

.main-content {
  background-color: #f5f7fa;
  overflow-y: auto;
  padding: 20px;
}

.mobile-overlay {
  position: fixed;
  top: 60px;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.3);
  z-index: 999;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .header {
    padding: 0 15px;
  }
  
  .logo-text {
    display: none;
  }
  
  .main-content {
    padding: 15px;
  }
}
</style>
