# 前端设计文档

## 1. 概述

本文档描述了SSL证书自动化管理系统的前端设计，包括技术栈选择、架构设计、UI组件和页面布局等。前端采用现代化的单页应用(SPA)架构，提供直观、高效的用户界面。

## 2. 技术栈

### 2.1 核心框架与库

- **Vue.js 3**: 核心前端框架，采用Composition API
- **Vue Router**: 路由管理
- **Pinia**: 状态管理
- **Axios**: HTTP请求库
- **Element Plus**: UI组件库
- **ECharts**: 数据可视化图表库
- **Day.js**: 日期处理库
- **TypeScript**: 类型系统

### 2.2 构建工具

- **Vite**: 现代前端构建工具
- **ESLint**: 代码质量检查
- **Prettier**: 代码格式化
- **Vitest**: 单元测试框架

## 3. 架构设计

### 3.1 目录结构

```
frontend/
├── public/              # 静态资源
├── src/
│   ├── api/             # API请求模块
│   ├── assets/          # 资源文件
│   ├── components/      # 通用组件
│   ├── composables/     # 组合式函数
│   ├── layouts/         # 布局组件
│   ├── router/          # 路由配置
│   ├── stores/          # 状态管理
│   ├── types/           # TypeScript类型定义
│   ├── utils/           # 工具函数
│   ├── views/           # 页面组件
│   ├── App.vue          # 根组件
│   └── main.ts          # 入口文件
├── .eslintrc.js         # ESLint配置
├── .prettierrc          # Prettier配置
├── index.html           # HTML模板
├── package.json         # 项目依赖
├── tsconfig.json        # TypeScript配置
└── vite.config.ts       # Vite配置
```

### 3.2 核心模块

#### 3.2.1 API模块

API模块负责与后端API通信，采用基于Axios的封装：

```typescript
// src/api/index.ts
import axios from 'axios';
import type { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';
import { useUserStore } from '@/stores/user';

// 创建axios实例
const api: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
});

// 请求拦截器
api.interceptors.request.use(
  (config: AxiosRequestConfig) => {
    const userStore = useUserStore();
    if (userStore.token) {
      config.headers = {
        ...config.headers,
        Authorization: `Bearer ${userStore.token}`
      };
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
api.interceptors.response.use(
  (response: AxiosResponse) => {
    const { code, message, data } = response.data;
    if (code === 200) {
      return data;
    }
    // 处理错误
    return Promise.reject(new Error(message || 'Error'));
  },
  (error) => {
    // 处理HTTP错误
    return Promise.reject(error);
  }
);

export default api;
```

#### 3.2.2 状态管理

使用Pinia进行状态管理，主要包括以下Store：

- **UserStore**: 用户信息和认证状态
- **ServerStore**: 服务器列表和详情
- **CertificateStore**: 证书列表和详情
- **AlertStore**: 告警信息
- **SettingStore**: 系统设置

```typescript
// src/stores/user.ts
import { defineStore } from 'pinia';
import api from '@/api';

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    userInfo: null
  }),
  getters: {
    isLoggedIn: (state) => !!state.token,
    isAdmin: (state) => state.userInfo?.role === 'admin'
  },
  actions: {
    async login(username: string, password: string) {
      try {
        const data = await api.post('/auth/login', { username, password });
        this.token = data.token;
        this.userInfo = data.user;
        localStorage.setItem('token', data.token);
        return data;
      } catch (error) {
        throw error;
      }
    },
    async logout() {
      try {
        await api.post('/auth/logout');
      } finally {
        this.token = '';
        this.userInfo = null;
        localStorage.removeItem('token');
      }
    },
    async fetchUserInfo() {
      if (!this.token) return;
      try {
        const data = await api.get('/users/me');
        this.userInfo = data;
      } catch (error) {
        this.logout();
      }
    }
  }
});
```

#### 3.2.3 路由管理

使用Vue Router管理路由，实现路由守卫和权限控制：

```typescript
// src/router/index.ts
import { createRouter, createWebHistory } from 'vue-router';
import { useUserStore } from '@/stores/user';

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    component: () => import('@/layouts/DefaultLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard.vue')
      },
      {
        path: 'servers',
        name: 'Servers',
        component: () => import('@/views/servers/ServerList.vue')
      },
      {
        path: 'servers/:id',
        name: 'ServerDetail',
        component: () => import('@/views/servers/ServerDetail.vue')
      },
      {
        path: 'certificates',
        name: 'Certificates',
        component: () => import('@/views/certificates/CertificateList.vue')
      },
      {
        path: 'certificates/:id',
        name: 'CertificateDetail',
        component: () => import('@/views/certificates/CertificateDetail.vue')
      },
      {
        path: 'alerts',
        name: 'Alerts',
        component: () => import('@/views/alerts/AlertList.vue')
      },
      {
        path: 'logs',
        name: 'Logs',
        component: () => import('@/views/logs/LogList.vue')
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('@/views/settings/Settings.vue'),
        meta: { requiresAdmin: true }
      },
      {
        path: 'users',
        name: 'Users',
        component: () => import('@/views/users/UserList.vue'),
        meta: { requiresAdmin: true }
      }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFound.vue')
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

// 路由守卫
router.beforeEach(async (to, from, next) => {
  const userStore = useUserStore();
  
  // 检查是否需要认证
  if (to.meta.requiresAuth && !userStore.isLoggedIn) {
    next({ name: 'Login', query: { redirect: to.fullPath } });
    return;
  }
  
  // 检查是否需要管理员权限
  if (to.meta.requiresAdmin && !userStore.isAdmin) {
    next({ name: 'Dashboard' });
    return;
  }
  
  // 如果已登录但访问登录页，重定向到首页
  if (to.name === 'Login' && userStore.isLoggedIn) {
    next({ name: 'Dashboard' });
    return;
  }
  
  next();
});

export default router;
```

## 4. UI设计

### 4.1 布局设计

系统采用经典的管理后台布局，包括：

- 顶部导航栏：显示logo、用户信息和全局操作
- 侧边菜单：主要导航菜单
- 主内容区：显示页面内容
- 页脚：版权信息和辅助链接

```vue
<!-- src/layouts/DefaultLayout.vue -->
<template>
  <el-container class="layout-container">
    <el-header class="header">
      <div class="logo">
        <img src="@/assets/logo.svg" alt="Logo" />
        <h1>SSL证书管理系统</h1>
      </div>
      <div class="user-info">
        <el-dropdown>
          <span class="user-dropdown">
            {{ userStore.userInfo?.username }}
            <el-icon><arrow-down /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="navigateToProfile">个人信息</el-dropdown-item>
              <el-dropdown-item @click="logout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </el-header>
    
    <el-container>
      <el-aside width="220px" class="sidebar">
        <el-menu
          :default-active="activeMenu"
          router
          class="sidebar-menu"
        >
          <el-menu-item index="/">
            <el-icon><dashboard /></el-icon>
            <span>仪表盘</span>
          </el-menu-item>
          <el-menu-item index="/servers">
            <el-icon><server /></el-icon>
            <span>服务器管理</span>
          </el-menu-item>
          <el-menu-item index="/certificates">
            <el-icon><certificate /></el-icon>
            <span>证书管理</span>
          </el-menu-item>
          <el-menu-item index="/alerts">
            <el-icon><bell /></el-icon>
            <span>告警管理</span>
          </el-menu-item>
          <el-menu-item index="/logs">
            <el-icon><document /></el-icon>
            <span>操作日志</span>
          </el-menu-item>
          <el-menu-item v-if="userStore.isAdmin" index="/users">
            <el-icon><user /></el-icon>
            <span>用户管理</span>
          </el-menu-item>
          <el-menu-item v-if="userStore.isAdmin" index="/settings">
            <el-icon><setting /></el-icon>
            <span>系统设置</span>
          </el-menu-item>
        </el-menu>
      </el-aside>
      
      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>
    
    <el-footer class="footer">
      <p>© 2025 SSL证书自动化管理系统 - 版本 1.0.0</p>
    </el-footer>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useUserStore } from '@/stores/user';

const router = useRouter();
const route = useRoute();
const userStore = useUserStore();

const activeMenu = computed(() => route.path);

const navigateToProfile = () => {
  router.push('/profile');
};

const logout = async () => {
  await userStore.logout();
  router.push('/login');
};
</script>

<style scoped>
.layout-container {
  height: 100vh;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background-color: #409eff;
  color: white;
  padding: 0 20px;
}

.logo {
  display: flex;
  align-items: center;
}

.logo img {
  height: 32px;
  margin-right: 10px;
}

.logo h1 {
  font-size: 18px;
  margin: 0;
}

.user-dropdown {
  cursor: pointer;
  display: flex;
  align-items: center;
  color: white;
}

.sidebar {
  background-color: #f5f7fa;
  border-right: 1px solid #e6e6e6;
}

.sidebar-menu {
  height: 100%;
  border-right: none;
}

.main-content {
  padding: 20px;
  background-color: #f5f7fa;
}

.footer {
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: white;
  border-top: 1px solid #e6e6e6;
  font-size: 14px;
  color: #606266;
}
</style>
```

### 4.2 主要页面设计

#### 4.2.1 仪表盘

仪表盘页面显示系统概览信息，包括：

- 证书统计（总数、有效、即将过期、已过期）
- 服务器统计（总数、在线、离线）
- 告警统计（未处理、已处理）
- 最近过期证书列表
- 最近告警列表
- 证书有效期分布图表

```vue
<!-- src/views/Dashboard.vue -->
<template>
  <div class="dashboard">
    <el-row :gutter="20">
      <!-- 统计卡片 -->
      <el-col :span="6" v-for="card in statisticsCards" :key="card.title">
        <el-card class="statistics-card" :class="card.class">
          <div class="card-content">
            <div class="card-value">{{ card.value }}</div>
            <div class="card-title">{{ card.title }}</div>
          </div>
          <div class="card-icon">
            <el-icon><component :is="card.icon" /></el-icon>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <el-row :gutter="20" class="chart-row">
      <!-- 证书有效期分布图表 -->
      <el-col :span="12">
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span>证书有效期分布</span>
            </div>
          </template>
          <div class="chart-container" ref="expiryChartRef"></div>
        </el-card>
      </el-col>
      
      <!-- 证书类型分布图表 -->
      <el-col :span="12">
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span>证书类型分布</span>
            </div>
          </template>
          <div class="chart-container" ref="typeChartRef"></div>
        </el-card>
      </el-col>
    </el-row>
    
    <el-row :gutter="20">
      <!-- 即将过期证书列表 -->
      <el-col :span="12">
        <el-card class="list-card">
          <template #header>
            <div class="card-header">
              <span>即将过期证书</span>
              <el-button type="text" @click="navigateToCertificates">查看全部</el-button>
            </div>
          </template>
          <el-table :data="expiringCertificates" style="width: 100%">
            <el-table-column prop="domain" label="域名" />
            <el-table-column prop="expires_at" label="过期时间">
              <template #default="scope">
                {{ formatDate(scope.row.expires_at) }}
              </template>
            </el-table-column>
            <el-table-column prop="days_left" label="剩余天数">
              <template #default="scope">
                <el-tag :type="getDaysLeftTagType(scope.row.days_left)">
                  {{ scope.row.days_left }} 天
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120">
              <template #default="scope">
                <el-button type="text" @click="navigateToCertificateDetail(scope.row.id)">
                  查看
                </el-button>
                <el-button type="text" @click="renewCertificate(scope.row.id)">
                  续期
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      
      <!-- 最近告警列表 -->
      <el-col :span="12">
        <el-card class="list-card">
          <template #header>
            <div class="card-header">
              <span>最近告警</span>
              <el-button type="text" @click="navigateToAlerts">查看全部</el-button>
            </div>
          </template>
          <el-table :data="recentAlerts" style="width: 100%">
            <el-table-column prop="type" label="类型">
              <template #default="scope">
                <el-tag :type="getAlertTypeTagType(scope.row.type)">
                  {{ getAlertTypeText(scope.row.type) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="message" label="消息" />
            <el-table-column prop="created_at" label="时间">
              <template #default="scope">
                {{ formatDate(scope.row.created_at) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120">
              <template #default="scope">
                <el-button type="text" @click="resolveAlert(scope.row.id)">
                  处理
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import * as echarts from 'echarts/core';
import { PieChart, BarChart } from 'echarts/charts';
import { TooltipComponent, LegendComponent, GridComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import { useCertificateStore } from '@/stores/certificate';
import { useAlertStore } from '@/stores/alert';
import { useServerStore } from '@/stores/server';
import { formatDate } from '@/utils/date';

// 注册ECharts组件
echarts.use([PieChart, BarChart, TooltipComponent, LegendComponent, GridComponent, CanvasRenderer]);

const router = useRouter();
const certificateStore = useCertificateStore();
const alertStore = useAlertStore();
const serverStore = useServerStore();

const expiryChartRef = ref<HTMLElement | null>(null);
const typeChartRef = ref<HTMLElement | null>(null);

// 统计卡片数据
const statisticsCards = computed(() => [
  {
    title: '证书总数',
    value: certificateStore.totalCount,
    icon: 'Certificate',
    class: 'blue-card'
  },
  {
    title: '即将过期',
    value: certificateStore.expiringCount,
    icon: 'Warning',
    class: 'orange-card'
  },
  {
    title: '服务器总数',
    value: serverStore.totalCount,
    icon: 'Server',
    class: 'green-card'
  },
  {
    title: '未处理告警',
    value: alertStore.pendingCount,
    icon: 'Bell',
    class: 'red-card'
  }
]);

// 即将过期证书
const expiringCertificates = computed(() => certificateStore.expiringCertificates);

// 最近告警
const recentAlerts = computed(() => alertStore.recentAlerts);

// 初始化图表
const initCharts = () => {
  // 证书有效期分布图表
  if (expiryChartRef.value) {
    const expiryChart = echarts.init(expiryChartRef.value);
    expiryChart.setOption({
      tooltip: {
        trigger: 'item',
        formatter: '{b}: {c} ({d}%)'
      },
      legend: {
        orient: 'vertical',
        left: 'left'
      },
      series: [
        {
          name: '证书有效期',
          type: 'pie',
          radius: '70%',
          data: [
            { value: certificateStore.validCount, name: '有效' },
            { value: certificateStore.expiringCount, name: '即将过期' },
            { value: certificateStore.expiredCount, name: '已过期' }
          ],
          emphasis: {
            itemStyle: {
              shadowBlur: 10,
              shadowOffsetX: 0,
              shadowColor: 'rgba(0, 0, 0, 0.5)'
            }
          }
        }
      ]
    });
    
    window.addEventListener('resize', () => {
      expiryChart.resize();
    });
  }
  
  // 证书类型分布图表
  if (typeChartRef.value) {
    const typeChart = echarts.init(typeChartRef.value);
    typeChart.setOption({
      tooltip: {
        trigger: 'item',
        formatter: '{b}: {c} ({d}%)'
      },
      legend: {
        orient: 'vertical',
        left: 'left'
      },
      series: [
        {
          name: '证书类型',
          type: 'pie',
          radius: '70%',
          data: certificateStore.certificateTypeDistribution,
          emphasis: {
            itemStyle: {
              shadowBlur: 10,
              shadowOffsetX: 0,
              shadowColor: 'rgba(0, 0, 0, 0.5)'
            }
          }
        }
      ]
    });
    
    window.addEventListener('resize', () => {
      typeChart.resize();
    });
  }
};

// 获取剩余天数标签类型
const getDaysLeftTagType = (days: number) => {
  if (days <= 7) return 'danger';
  if (days <= 15) return 'warning';
  return 'success';
};

// 获取告警类型标签类型
const getAlertTypeTagType = (type: string) => {
  switch (type) {
    case 'expiry': return 'warning';
    case 'error': return 'danger';
    case 'revoke': return 'info';
    default: return 'info';
  }
};

// 获取告警类型文本
const getAlertTypeText = (type: string) => {
  switch (type) {
    case 'expiry': return '即将过期';
    case 'error': return '错误';
    case 'revoke': return '已吊销';
    default: return type;
  }
};

// 导航到证书列表
const navigateToCertificates = () => {
  router.push('/certificates');
};

// 导航到证书详情
const navigateToCertificateDetail = (id: number) => {
  router.push(`/certificates/${id}`);
};

// 导航到告警列表
const navigateToAlerts = () => {
  router.push('/alerts');
};

// 续期证书
const renewCertificate = async (id: number) => {
  try {
    await certificateStore.renewCertificate(id);
    ElMessage.success('证书续期任务已提交');
  } catch (error) {
    ElMessage.error('证书续期失败');
  }
};

// 处理告警
const resolveAlert = async (id: number) => {
  try {
    await alertStore.resolveAlert(id);
    ElMessage.success('告警已处理');
  } catch (error) {
    ElMessage.error('处理告警失败');
  }
};

onMounted(async () => {
  // 加载数据
  await Promise.all([
    certificateStore.fetchExpiringCertificates(),
    alertStore.fetchRecentAlerts(),
    certificateStore.fetchCertificateStatistics(),
    serverStore.fetchServerStatistics()
  ]);
  
  // 初始化图表
  initCharts();
});
</script>

<style scoped>
.dashboard {
  padding: 20px 0;
}

.statistics-card {
  height: 120px;
  margin-bottom: 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px;
}

.blue-card {
  background: linear-gradient(to right, #1890ff, #36cbcb);
  color: white;
}

.orange-card {
  background: linear-gradient(to right, #ff9800, #ff5722);
  color: white;
}

.green-card {
  background: linear-gradient(to right, #4caf50, #8bc34a);
  color: white;
}

.red-card {
  background: linear-gradient(to right, #f44336, #e91e63);
  color: white;
}

.card-content {
  display: flex;
  flex-direction: column;
}

.card-value {
  font-size: 28px;
  font-weight: bold;
  margin-bottom: 5px;
}

.card-title {
  font-size: 16px;
}

.card-icon {
  font-size: 48px;
  opacity: 0.8;
}

.chart-row {
  margin-bottom: 20px;
}

.chart-card, .list-card {
  margin-bottom: 20px;
}

.chart-container {
  height: 300px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
```

#### 4.2.2 服务器管理

服务器管理页面包括服务器列表和详情页：

- 服务器列表：显示所有服务器，支持搜索、筛选和添加
- 服务器详情：显示服务器信息、证书列表和操作日志

#### 4.2.3 证书管理

证书管理页面包括证书列表和详情页：

- 证书列表：显示所有证书，支持搜索、筛选和手动申请
- 证书详情：显示证书信息、部署记录和操作日志

#### 4.2.4 告警管理

告警管理页面显示系统告警，支持筛选和处理。

#### 4.2.5 操作日志

操作日志页面显示系统操作记录，支持筛选和导出。

#### 4.2.6 用户管理

用户管理页面显示系统用户，支持添加、编辑和删除（仅管理员可见）。

#### 4.2.7 系统设置

系统设置页面配置全局参数，如默认CA、续期天数等（仅管理员可见）。

### 4.3 组件设计

系统包含以下通用组件：

#### 4.3.1 确认对话框

```vue
<!-- src/components/ConfirmDialog.vue -->
<template>
  <el-dialog
    v-model="visible"
    :title="title"
    :width="width"
    :before-close="handleClose"
  >
    <div class="confirm-content">
      <el-icon v-if="icon" class="confirm-icon" :class="iconClass">
        <component :is="icon" />
      </el-icon>
      <div class="confirm-message">{{ message }}</div>
    </div>
    <template #footer>
      <span class="dialog-footer">
        <el-button @click="handleCancel">{{ cancelText }}</el-button>
        <el-button type="primary" @click="handleConfirm" :loading="loading">
          {{ confirmText }}
        </el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  title: {
    type: String,
    default: '确认'
  },
  message: {
    type: String,
    default: '确认执行此操作？'
  },
  icon: {
    type: String,
    default: 'Warning'
  },
  type: {
    type: String,
    default: 'warning',
    validator: (value: string) => ['success', 'warning', 'info', 'error'].includes(value)
  },
  width: {
    type: String,
    default: '420px'
  },
  confirmText: {
    type: String,
    default: '确认'
  },
  cancelText: {
    type: String,
    default: '取消'
  },
  loading: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['update:modelValue', 'confirm', 'cancel']);

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
});

const iconClass = computed(() => `confirm-icon-${props.type}`);

const handleConfirm = () => {
  emit('confirm');
};

const handleCancel = () => {
  emit('cancel');
  visible.value = false;
};

const handleClose = () => {
  handleCancel();
};

watch(() => props.modelValue, (val) => {
  visible.value = val;
});
</script>

<style scoped>
.confirm-content {
  display: flex;
  align-items: flex-start;
  padding: 10px 0;
}

.confirm-icon {
  font-size: 24px;
  margin-right: 12px;
}

.confirm-icon-success {
  color: #67c23a;
}

.confirm-icon-warning {
  color: #e6a23c;
}

.confirm-icon-info {
  color: #909399;
}

.confirm-icon-error {
  color: #f56c6c;
}

.confirm-message {
  font-size: 14px;
  line-height: 1.5;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
}
</style>
```

#### 4.3.2 状态标签

```vue
<!-- src/components/StatusTag.vue -->
<template>
  <el-tag :type="tagType" :effect="effect" :size="size">
    {{ displayText }}
  </el-tag>
</template>

<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps({
  status: {
    type: String,
    required: true
  },
  type: {
    type: String,
    default: 'certificate',
    validator: (value: string) => ['certificate', 'server', 'alert', 'deployment'].includes(value)
  },
  size: {
    type: String,
    default: 'default'
  },
  effect: {
    type: String,
    default: 'light'
  }
});

const statusMap = {
  certificate: {
    valid: { type: 'success', text: '有效' },
    expired: { type: 'danger', text: '已过期' },
    revoked: { type: 'info', text: '已吊销' },
    pending: { type: 'warning', text: '处理中' },
    renewing: { type: 'warning', text: '续期中' }
  },
  server: {
    online: { type: 'success', text: '在线' },
    offline: { type: 'danger', text: '离线' },
    pending: { type: 'warning', text: '待激活' }
  },
  alert: {
    pending: { type: 'warning', text: '未处理' },
    sent: { type: 'info', text: '已发送' },
    resolved: { type: 'success', text: '已处理' }
  },
  deployment: {
    success: { type: 'success', text: '成功' },
    failed: { type: 'danger', text: '失败' },
    pending: { type: 'warning', text: '处理中' }
  }
};

const tagType = computed(() => {
  const typeMap = statusMap[props.type as keyof typeof statusMap] || {};
  const statusInfo = typeMap[props.status as keyof typeof typeMap] || { type: 'info', text: props.status };
  return statusInfo.type;
});

const displayText = computed(() => {
  const typeMap = statusMap[props.type as keyof typeof statusMap] || {};
  const statusInfo = typeMap[props.status as keyof typeof typeMap] || { type: 'info', text: props.status };
  return statusInfo.text;
});
</script>
```

#### 4.3.3 倒计时组件

```vue
<!-- src/components/Countdown.vue -->
<template>
  <span :class="['countdown', { 'warning': isWarning, 'danger': isDanger }]">
    {{ formattedTime }}
  </span>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import dayjs from 'dayjs';

const props = defineProps({
  targetDate: {
    type: [String, Date],
    required: true
  },
  warningDays: {
    type: Number,
    default: 15
  },
  dangerDays: {
    type: Number,
    default: 7
  }
});

const remainingTime = ref(0);
const timer = ref<number | null>(null);

const calculateRemainingTime = () => {
  const now = dayjs();
  const target = dayjs(props.targetDate);
  const diff = target.diff(now, 'second');
  remainingTime.value = diff > 0 ? diff : 0;
};

const formattedTime = computed(() => {
  if (remainingTime.value <= 0) {
    return '已过期';
  }
  
  const days = Math.floor(remainingTime.value / 86400);
  const hours = Math.floor((remainingTime.value % 86400) / 3600);
  const minutes = Math.floor((remainingTime.value % 3600) / 60);
  const seconds = remainingTime.value % 60;
  
  if (days > 0) {
    return `${days}天 ${hours}小时`;
  }
  
  return `${hours}小时 ${minutes}分 ${seconds}秒`;
});

const isWarning = computed(() => {
  const days = Math.floor(remainingTime.value / 86400);
  return days <= props.warningDays && days > props.dangerDays;
});

const isDanger = computed(() => {
  const days = Math.floor(remainingTime.value / 86400);
  return days <= props.dangerDays;
});

onMounted(() => {
  calculateRemainingTime();
  timer.value = window.setInterval(calculateRemainingTime, 1000);
});

onBeforeUnmount(() => {
  if (timer.value) {
    clearInterval(timer.value);
  }
});
</script>

<style scoped>
.countdown {
  font-weight: bold;
}

.warning {
  color: #e6a23c;
}

.danger {
  color: #f56c6c;
}
</style>
```

## 5. 响应式设计

系统采用响应式设计，适配不同屏幕尺寸：

- 桌面端（>= 1200px）：完整布局
- 平板端（768px - 1199px）：适当调整布局
- 移动端（< 768px）：单列布局，侧边栏可折叠

```scss
// src/assets/styles/responsive.scss

// 响应式断点
$breakpoints: (
  'xs': 576px,
  'sm': 768px,
  'md': 992px,
  'lg': 1200px
);

// 响应式混合器
@mixin respond-to($breakpoint) {
  @if map-has-key($breakpoints, $breakpoint) {
    @media (max-width: map-get($breakpoints, $breakpoint)) {
      @content;
    }
  } @else {
    @media (max-width: $breakpoint) {
      @content;
    }
  }
}

// 移动端样式
@include respond-to('sm') {
  .el-aside {
    position: absolute;
    z-index: 10;
    height: 100%;
    transform: translateX(-100%);
    transition: transform 0.3s;
    
    &.is-open {
      transform: translateX(0);
    }
  }
  
  .el-main {
    padding-left: 0;
  }
  
  .statistics-card {
    margin-bottom: 10px;
  }
  
  .chart-row {
    .el-col {
      width: 100%;
    }
  }
}

// 平板端样式
@include respond-to('md') {
  .el-aside {
    width: 64px !important;
    
    .el-menu {
      width: 64px;
    }
    
    .el-menu-item {
      span {
        display: none;
      }
    }
  }
  
  .el-main {
    padding-left: 64px;
  }
}
```

## 6. 主题与样式

系统支持亮色和暗色两种主题，并提供自定义主题色功能。

```typescript
// src/composables/useTheme.ts
import { ref, watch } from 'vue';
import { useSettingStore } from '@/stores/setting';

export function useTheme() {
  const settingStore = useSettingStore();
  const currentTheme = ref(settingStore.theme || 'light');
  
  const applyTheme = (theme: string) => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
    currentTheme.value = theme;
    settingStore.setTheme(theme);
  };
  
  const toggleTheme = () => {
    const newTheme = currentTheme.value === 'light' ? 'dark' : 'light';
    applyTheme(newTheme);
  };
  
  const applyThemeColor = (color: string) => {
    const style = document.createElement('style');
    style.innerHTML = `
      :root {
        --el-color-primary: ${color};
        --el-color-primary-light-3: ${lightenColor(color, 0.3)};
        --el-color-primary-light-5: ${lightenColor(color, 0.5)};
        --el-color-primary-light-7: ${lightenColor(color, 0.7)};
        --el-color-primary-light-8: ${lightenColor(color, 0.8)};
        --el-color-primary-light-9: ${lightenColor(color, 0.9)};
        --el-color-primary-dark-2: ${darkenColor(color, 0.2)};
      }
    `;
    document.head.appendChild(style);
    localStorage.setItem('theme-color', color);
    settingStore.setThemeColor(color);
  };
  
  // 简单的颜色处理函数
  const lightenColor = (color: string, amount: number) => {
    const hex = color.replace('#', '');
    const r = parseInt(hex.substring(0, 2), 16);
    const g = parseInt(hex.substring(2, 4), 16);
    const b = parseInt(hex.substring(4, 6), 16);
    
    const lightenValue = (value: number) => {
      return Math.min(255, Math.floor(value + (255 - value) * amount));
    };
    
    return `#${lightenValue(r).toString(16).padStart(2, '0')}${lightenValue(g).toString(16).padStart(2, '0')}${lightenValue(b).toString(16).padStart(2, '0')}`;
  };
  
  const darkenColor = (color: string, amount: number) => {
    const hex = color.replace('#', '');
    const r = parseInt(hex.substring(0, 2), 16);
    const g = parseInt(hex.substring(2, 4), 16);
    const b = parseInt(hex.substring(4, 6), 16);
    
    const darkenValue = (value: number) => {
      return Math.max(0, Math.floor(value * (1 - amount)));
    };
    
    return `#${darkenValue(r).toString(16).padStart(2, '0')}${darkenValue(g).toString(16).padStart(2, '0')}${darkenValue(b).toString(16).padStart(2, '0')}`;
  };
  
  // 初始化主题
  const initTheme = () => {
    const savedTheme = localStorage.getItem('theme') || 'light';
    applyTheme(savedTheme);
    
    const savedThemeColor = localStorage.getItem('theme-color');
    if (savedThemeColor) {
      applyThemeColor(savedThemeColor);
    }
  };
  
  // 监听系统主题变化
  const watchSystemTheme = () => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handleChange = (e: MediaQueryListEvent) => {
      if (settingStore.followSystemTheme) {
        applyTheme(e.matches ? 'dark' : 'light');
      }
    };
    
    mediaQuery.addEventListener('change', handleChange);
    
    return () => {
      mediaQuery.removeEventListener('change', handleChange);
    };
  };
  
  // 监听主题设置变化
  watch(() => settingStore.theme, (newTheme) => {
    if (newTheme) {
      applyTheme(newTheme);
    }
  });
  
  watch(() => settingStore.themeColor, (newColor) => {
    if (newColor) {
      applyThemeColor(newColor);
    }
  });
  
  return {
    currentTheme,
    toggleTheme,
    applyTheme,
    applyThemeColor,
    initTheme,
    watchSystemTheme
  };
}
```

## 7. 国际化支持

系统支持中英文两种语言，使用i18n实现国际化：

```typescript
// src/i18n/index.ts
import { createI18n } from 'vue-i18n';
import zhCN from './locales/zh-CN';
import enUS from './locales/en-US';

const messages = {
  'zh-CN': zhCN,
  'en-US': enUS
};

const i18n = createI18n({
  legacy: false,
  locale: localStorage.getItem('locale') || 'zh-CN',
  fallbackLocale: 'zh-CN',
  messages
});

export default i18n;
```

## 8. 性能优化

### 8.1 代码分割

使用动态导入实现路由级别的代码分割：

```typescript
const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue')
  },
  // ...
];
```

### 8.2 虚拟滚动

对于大数据列表，使用虚拟滚动优化性能：

```vue
<el-table
  v-virtual-scroll="{ itemSize: 50, buffer: 10 }"
  :data="largeDataList"
  height="400"
>
  <!-- 表格列 -->
</el-table>
```

### 8.3 缓存优化

使用Pinia的持久化插件缓存状态：

```typescript
// src/stores/index.ts
import { createPinia } from 'pinia';
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate';

const pinia = createPinia();
pinia.use(piniaPluginPersistedstate);

export default pinia;
```

## 9. 测试策略

### 9.1 单元测试

使用Vitest进行组件和函数的单元测试：

```typescript
// src/components/__tests__/StatusTag.test.ts
import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import StatusTag from '../StatusTag.vue';

describe('StatusTag', () => {
  it('renders certificate status correctly', () => {
    const wrapper = mount(StatusTag, {
      props: {
        status: 'valid',
        type: 'certificate'
      }
    });
    
    expect(wrapper.text()).toBe('有效');
    expect(wrapper.classes()).toContain('el-tag--success');
  });
  
  it('renders server status correctly', () => {
    const wrapper = mount(StatusTag, {
      props: {
        status: 'offline',
        type: 'server'
      }
    });
    
    expect(wrapper.text()).toBe('离线');
    expect(wrapper.classes()).toContain('el-tag--danger');
  });
});
```

### 9.2 端到端测试

使用Cypress进行端到端测试：

```typescript
// cypress/e2e/login.cy.ts
describe('Login Page', () => {
  it('should login successfully with correct credentials', () => {
    cy.visit('/login');
    cy.get('input[name="username"]').type('admin');
    cy.get('input[name="password"]').type('password');
    cy.get('button[type="submit"]').click();
    cy.url().should('include', '/dashboard');
  });
  
  it('should show error with incorrect credentials', () => {
    cy.visit('/login');
    cy.get('input[name="username"]').type('admin');
    cy.get('input[name="password"]').type('wrong-password');
    cy.get('button[type="submit"]').click();
    cy.contains('用户名或密码错误').should('be.visible');
  });
});
```

## 10. 部署策略

### 10.1 构建配置

```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { resolve } from 'path';

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  build: {
    target: 'es2015',
    outDir: 'dist',
    assetsDir: 'assets',
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true,
        drop_debugger: true
      }
    },
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor': ['vue', 'vue-router', 'pinia'],
          'element-plus': ['element-plus'],
          'echarts': ['echarts']
        }
      }
    }
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:3000',
        changeOrigin: true
      }
    }
  }
});
```

### 10.2 CI/CD配置

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [ main ]

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v2
      
      - name: Setup Node.js
        uses: actions/setup-node@v2
        with:
          node-version: '16'
          
      - name: Install dependencies
        run: npm ci
        
      - name: Build
        run: npm run build
        
      - name: Run tests
        run: npm test
        
      - name: Deploy
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./dist
```
