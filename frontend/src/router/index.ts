import { createRouter, createWebHistory } from 'vue-router'

import AppLayout from '@/layouts/AppLayout.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      component: AppLayout,
      children: [
        {
          path: '',
          name: 'dashboard',
          component: () => import('@/views/DashboardView.vue'),
          meta: { title: '创作工作台' },
        },
        {
          path: 'library',
          name: 'library',
          component: () => import('@/views/LibraryView.vue'),
          meta: { title: '作品与素材库' },
        },
        {
          path: 'creation',
          name: 'creation',
          component: () => import('@/views/CreationView.vue'),
          meta: { title: '多 Agent 创作' },
        },
        {
          path: 'memory',
          name: 'memory',
          component: () => import('@/views/MemoryView.vue'),
          meta: { title: '个性化记忆' },
        },
        {
          path: 'settings',
          name: 'settings',
          component: () => import('@/views/SettingsView.vue'),
          meta: { title: '系统设置' },
        },
      ],
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/',
    },
  ],
})

router.afterEach((to) => {
  const title = typeof to.meta.title === 'string' ? to.meta.title : 'CreatorMind'
  document.title = `${title} · CreatorMind`
})

export default router