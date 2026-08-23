import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/login', name: 'Login', component: () => import('@/views/Login.vue'), meta: { public: true } },
  {
    path: '/',
    component: () => import('@/layout/MainLayout.vue'),
    redirect: '/dashboard',
    children: [
      { path: 'dashboard', name: 'Dashboard', component: () => import('@/views/Dashboard.vue'), meta: { title: '首页' } },
      { path: 'material', name: 'MaterialList', component: () => import('@/views/MaterialList.vue'), meta: { title: '物料列表' } },
      { path: 'material/detail/:id', name: 'MaterialDetail', component: () => import('@/views/MaterialDetail.vue'), meta: { title: '物料详情' } },
      { path: 'category', name: 'CategoryManage', component: () => import('@/views/CategoryManage.vue'), meta: { title: '分类管理' } },
      { path: 'project', name: 'ProjectList', component: () => import('@/views/ProjectList.vue'), meta: { title: '项目列表' } },
      { path: 'project/detail/:id', name: 'ProjectDetail', component: () => import('@/views/ProjectDetail.vue'), meta: { title: '项目详情' } },
      { path: 'stock-log', name: 'StockLog', component: () => import('@/views/StockLog.vue'), meta: { title: '库存流水' } },
      { path: 'settings', name: 'Settings', component: () => import('@/views/Settings.vue'), meta: { title: '系统设置' } }
    ]
  },
  { path: '/:pathMatch(.*)*', redirect: '/dashboard' }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 全局路由拦截：未登录强制跳转登录页
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  if (to.meta.public) {
    next()
  } else if (!token) {
    next('/login')
  } else {
    next()
  }
})

export default router
