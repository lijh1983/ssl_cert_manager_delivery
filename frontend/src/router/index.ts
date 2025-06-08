import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { createRouteComponent, componentPreloader } from '@/utils/asyncComponent'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: createRouteComponent(() => import('@/views/Login.vue')),
      meta: { requiresAuth: false }
    },
    {
      path: '/',
      redirect: '/dashboard'
    },
    {
      path: '/dashboard',
      name: 'Dashboard',
      component: createRouteComponent(() => import('@/layouts/MainLayout.vue')),
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          name: 'DashboardHome',
          component: createRouteComponent(() => import('@/views/Dashboard.vue'))
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
          component: createRouteComponent(() => import('@/views/servers/ServerList.vue'))
        },
        {
          path: 'create',
          name: 'ServerCreate',
          component: createRouteComponent(() => import('@/views/servers/ServerCreate.vue'))
        },
        {
          path: ':id',
          name: 'ServerDetail',
          component: createRouteComponent(() => import('@/views/servers/ServerDetail.vue'))
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
          component: createRouteComponent(() => import('@/views/certificates/CertificateList.vue'))
        },
        {
          path: 'create',
          name: 'CertificateCreate',
          component: createRouteComponent(() => import('@/views/certificates/CertificateCreate.vue'))
        },
        {
          path: ':id',
          name: 'CertificateDetail',
          component: createRouteComponent(() => import('@/views/certificates/CertificateDetail.vue'))
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
          component: createRouteComponent(() => import('@/views/alerts/ActiveAlerts.vue')),
          meta: { title: '活跃告警' }
        },
        {
          path: 'rules',
          name: 'AlertRules',
          component: createRouteComponent(() => import('@/views/alerts/AlertRules.vue')),
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
          component: createRouteComponent(() => import('@/views/logs/LogList.vue'))
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

// 预加载关键组件
router.beforeEach((to, from, next) => {
  // 根据目标路由预加载相关组件
  if (to.path.startsWith('/certificates')) {
    componentPreloader.add('CertificateList', () => import('@/views/certificates/CertificateList.vue'))
    componentPreloader.add('CertificateDetail', () => import('@/views/certificates/CertificateDetail.vue'))
  } else if (to.path.startsWith('/servers')) {
    componentPreloader.add('ServerList', () => import('@/views/servers/ServerList.vue'))
    componentPreloader.add('ServerDetail', () => import('@/views/servers/ServerDetail.vue'))
  } else if (to.path.startsWith('/alerts')) {
    componentPreloader.add('ActiveAlerts', () => import('@/views/alerts/ActiveAlerts.vue'))
    componentPreloader.add('AlertRules', () => import('@/views/alerts/AlertRules.vue'))
  }

  next()
})

export default router
