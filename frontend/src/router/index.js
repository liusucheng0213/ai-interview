import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    component: () => import('../views/MainLayout.vue'),
    children: [
      {
        path: '',
        name: 'Home',
        component: () => import('../views/Home.vue'),
      },
      {
        path: 'company',
        name: 'CompanyDashboard',
        component: () => import('../views/company/Company.vue'),
      },
    ],
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
  },
  {
    path: '/interview',
    component: () => import('../views/MainLayout.vue'),
    redirect: '/interview/start',
    children: [
      {
        path: 'start',
        name: 'StartInterview',
        component: () => import('../views/interview/Start.vue'),
      },
      {
        path: 'history',
        name: 'InterviewHistory',
        component: () => import('../views/interview/History.vue'),
      },
      {
        path: 'growth',
        name: 'GrowthCurve',
        component: () => import('../views/interview/Growth.vue'),
      },
      {
        path: 'question-bank',
        redirect: { name: 'KnowledgeBase', query: { tab: 'questions' } },
      },
      {
        path: 'profile',
        name: 'Profile',
        component: () => import('../views/interview/Profile.vue'),
      },
      {
        path: 'resume',
        name: 'ResumeOptimization',
        component: () => import('../views/interview/Resume.vue'),
      },
      {
        path: 'knowledge',
        name: 'KnowledgeBase',
        component: () => import('../views/interview/Knowledge.vue'),
      },
    ],
  },
  {
    path: '/interview/chat',
    name: 'InterviewChat',
    component: () => import('../views/interview/Chat.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  const whiteList = ['/login']

  if (whiteList.includes(to.path)) {
    next()
  } else {
    if (!token) return next('/login')

    const accountType = localStorage.getItem('account_type') || 'personal'
    const enterpriseBlocked = [
      '/interview/start',
      '/interview/chat',
      '/interview/history',
      '/interview/growth',
      '/interview/resume',
    ]
    if (accountType === 'enterprise' && enterpriseBlocked.some(p => to.path.startsWith(p))) {
      return next('/company')
    }
    if (accountType !== 'enterprise' && to.path.startsWith('/company')) {
      return next('/')
    }
    next()
  }
})

export default router
