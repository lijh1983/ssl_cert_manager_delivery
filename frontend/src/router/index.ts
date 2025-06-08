import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/Login.vue'),
      meta: { requiresAuth: false }
    },
    {
      path: '/',
      redirect: '/dashboard'
    },
    {
      path: '/dashboard',
      name: 'Dashboard',
      component: () => import('@/layouts/MainLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          name: 'DashboardHome',
          component: () => import('@/views/Dashboard.vue')
        }
      ]
    },
    {
      path: '/servers',
      name: 'Servers',
      component: () => import('@/layouts/MainLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          name: 'ServerList',
          component: () => import('@/views/servers/ServerList.vue')
        },
        {
          path: 'create',
          name: 'ServerCreate',
          component: () => import('@/views/servers/ServerCreate.vue')
        },
        {
          path: ':id',
          name: 'ServerDetail',
          component: () => import('@/views/servers/ServerDetail.vue')
        }
      ]
    },
    {
      path: '/certificates',
      name: 'Certificates',
      component: () => import('@/layouts/MainLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          name: 'CertificateList',
          component: () => import('@/views/certificates/CertificateList.vue')
        },
        {
          path: 'create',
          name: 'CertificateCreate',
          component: () => import('@/views/certificates/CertificateCreate.vue')
        },
        {
          path: ':id',
          name: 'CertificateDetail',
          component: () => import('@/views/certificates/CertificateDetail.vue')
        }
      ]
    },
    {
      path: '/alerts',
      name: 'Alerts',
      component: () => import('@/layouts/MainLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          name: 'ActiveAlerts',
          component: () => import('@/views/alerts/ActiveAlerts.vue'),
          meta: { title: '活跃告警' }
        },
        {
          path: 'rules',
          name: 'AlertRules',
          component: () => import('@/views/alerts/AlertRules.vue'),
          meta: { title: '告警规则', requiresAdmin: true }
        }
      ]
    },
    {
      path: '/logs',
      name: 'Logs',
      component: () => import('@/layouts/MainLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          name: 'LogList',
          component: () => import('@/views/logs/LogList.vue')
        }
      ]
    },
    {
      path: '/users',
      name: 'Users',
      component: () => import('@/layouts/MainLayout.vue'),
      meta: { requiresAuth: true, requiresAdmin: true },
      children: [
        {
          path: '',
          name: 'UserList',
          component: () => import('@/views/users/UserList.vue')
        }
      ]
    },
    {
      path: '/settings',
      name: 'Settings',
      component: () => import('@/layouts/MainLayout.vue'),
      meta: { requiresAuth: true, requiresAdmin: true },
      children: [
        {
          path: '',
          name: 'SystemSettings',
          component: () => import('@/views/settings/SystemSettings.vue')
        }
      ]
    },
    {
      path: '/profile',
      name: 'Profile',
      component: () => import('@/layouts/MainLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          name: 'UserProfile',
          component: () => import('@/views/profile/UserProfile.vue')
        }
      ]
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'NotFound',
      component: () => import('@/views/NotFound.vue')
    }
  ]
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next('/login')
  } else if (to.meta.requiresAdmin && !authStore.isAdmin) {
    next('/dashboard')
  } else if (to.name === 'Login' && authStore.isAuthenticated) {
    next('/dashboard')
  } else {
    next()
  }
})

export default router
