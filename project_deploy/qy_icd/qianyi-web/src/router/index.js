import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import { apiMe } from '@/api/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
      redirect: '/bigModel',
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/Login.vue'),
      meta: { public: true },
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('../views/Register.vue'),
      meta: { public: true },
    },
    {
      path: '/homeIndex',
      name: 'homeIndex',
      // route level code-splitting
      // this generates a separate chunk (About.[hash].js) for this route
      // which is lazy-loaded when the route is visited.
      component: () => import('../views/homeIndex.vue'),
    },
    // 新增大模型路由
    {
      path: '/bigModel',
      name: 'bigModel',
      component: () => import('../views/bigModel_biaoge.vue'),
      meta: { menuType: 'coding' },
    },
    // 新增PDF编码路由
    {
      path: '/coding-pdf',
      name: 'codingPdf',
      component: () => import('../views/bigModel_biaoge.vue'),
      meta: { menuType: 'coding' },
    },
    // 新增结构化编码路由
    {
      path: '/coding-structured',
      name: 'codingStructured',
      component: () => import('../views/bigModel_biaoge.vue'),
      meta: { menuType: 'coding' },
    },
    // 新增编码历史路由
    {
      path: '/coding-history',
      name: 'codingHistory',
      component: () => import('../views/CodingHistory.vue'),
    },
    // 系统设置相关路由
    {
      path: '/user-management',
      name: 'userManagement',
      component: () => import('../views/system/UserManagement.vue'),
      meta: { menuType: 'system' },
    },
    {
      path: '/change-password',
      name: 'changePassword',
      component: () => import('../views/system/ChangePassword.vue'),
      meta: { menuType: 'system' },
    },
    {
      path: '/drgGrouping',
      name: 'drgGrouping',
      // route level code-splitting
      // this generates a separate chunk (About.[hash].js) for this route
      // which is lazy-loaded when the route is visited.
      component: () => import('../views/drgGrouping.vue'),
    },
    {
      path: '/query',
      name: 'query',
      // route level code-splitting
      // this generates a separate chunk (About.[hash].js) for this route
      // which is lazy-loaded when the route is visited.
      component: () => import('../views/query.vue'),
    },
    {
      path: '/ICDCoding',
      name: 'ICDCoding',
      // route level code-splitting
      // this generates a separate chunk (About.[hash].js) for this route
      // which is lazy-loaded when the route is visited.
      component: () => import('../views/ICDCoding.vue'),
    },
  ],
})

// Global auth guard: require login for all routes except meta.public
router.beforeEach(async (to, from, next) => {
  if (to.meta.public) return next()
  try {
    const { data } = await apiMe()
    if (data && data.code === 200) {
      return next()
    }
  } catch (e) {}
  return next({ name: 'login', query: { redirect: to.fullPath } })
})

export default router
