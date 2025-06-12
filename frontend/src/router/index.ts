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
      redirect: '/certificates'
    },
    {
      path: '/deployment',
      name: 'Deployment',
      component: () => import('@/layouts/MainLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          name: 'DeploymentList',
          component: createRouteComponent(() => import('@/views/deployment/DeploymentList.vue'))
        },
        {
          path: 'create',
          name: 'DeploymentCreate',
          component: createRouteComponent(() => import('@/views/deployment/DeploymentCreate.vue'))
        },
        {
          path: ':id',
          name: 'DeploymentDetail',
          component: createRouteComponent(() => import('@/views/deployment/DeploymentDetail.vue'))
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
      path: '/monitoring',
      name: 'Monitoring',
      component: () => import('@/layouts/MainLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          name: 'MonitoringList',
          component: createRouteComponent(() => import('@/views/monitoring/MonitoringList.vue'))
        },
        {
          path: 'create',
          name: 'MonitoringCreate',
          component: createRouteComponent(() => import('@/views/monitoring/MonitoringCreate.vue'))
        },
        {
          path: ':id',
          name: 'MonitoringDetail',
          component: createRouteComponent(() => import('@/views/monitoring/MonitoringDetail.vue'))
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
  } else if (to.path.startsWith('/deployment')) {
    componentPreloader.add('DeploymentList', () => import('@/views/deployment/DeploymentList.vue'))
    componentPreloader.add('DeploymentDetail', () => import('@/views/deployment/DeploymentDetail.vue'))
  } else if (to.path.startsWith('/monitoring')) {
    componentPreloader.add('MonitoringList', () => import('@/views/monitoring/MonitoringList.vue'))
    componentPreloader.add('MonitoringDetail', () => import('@/views/monitoring/MonitoringDetail.vue'))
  }

  next()
})

export default router
