import { createRouter, createWebHistory } from 'vue-router';
import { getToken, getUser } from '../utils/auth';

const routes = [
  // 1. 登录页
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/LoginView.vue'),
    meta: { public: true }
  },

  // 2. Admin 管理端 (独立 Layout)
  {
    path: '/admin',
    component: () => import('../layout/AdminLayout.vue'),
    meta: { roles: ['admin'] },
    children: [
      { path: '', redirect: '/admin/dashboard' },
      { path: 'dashboard', name: 'AdminDashboard', component: () => import('../views/admin/DashboardView.vue') },
      { path: 'users', name: 'UserManagement', component: () => import('../views/admin/UserManagementView.vue') },
      { path: 'config', name: 'SystemConfig', component: () => import('../views/admin/SystemConfigView.vue') },
      { path: 'monitor', name: 'ApiMonitor', component: () => import('../views/admin/MonitorView.vue') },
      {
        path: 'register',
        name: 'AdminRegister',
        component: () => import('../views/admin/RegisterNewView.vue')
      },
      {
        path: 'logs',
        name: 'SystemLogs',
        component: () => import('../views/admin/SystemLogView.vue')
      }
    ]
  },

  // 3. 教师端 (使用 MainLayout)
  {
    path: '/teacher',
    component: () => import('../layout/MainLayout.vue'),
    meta: { roles: ['teacher', 'admin'] }, // 允许 admin 访问教师界面
    children: [
      { path: '', redirect: '/teacher/dashboard' },
      { path: 'dashboard', name: 'Dashboard', component: () => import('../views/teacher/DashboardView.vue') },
      { path: 'courses', name: 'Courses', component: () => import('../views/teacher/CoursesView.vue') },
      { path: 'grading', name: 'Grading', component: () => import('../views/teacher/GradingListView.vue') },
      { path: 'profile', name: 'TeacherProfile', component: () => import('../views/teacher/TeacherProfileView.vue') },
    ]
  },

  // 4. 学生端 (补全了旧版本中缺失的作业、成绩、分析等路由)
  {
    path: '/student',
    component: () => import('../layout/StudentLayout.vue'),
    meta: { roles: ['student'] },
    children: [
      { path: '', redirect: '/student/dashboard' },
      { path: 'dashboard', name: 'StudentDashboard', component: () => import('../views/student/StudentDashboardView.vue') },
      { path: 'assignments', name: 'StudentAssignments', component: () => import('../views/student/StudentAssignmentsView.vue') },
      // 补全：课程作业列表
      {
        path: 'assignments/course/:courseId',
        name: 'StudentCourseAssignments',
        component: () => import('../views/student/StudentCourseAssignmentsView.vue')
      },
      // 补全：提交作业
      {
        path: 'assignments/submit/:assignId',
        name: 'StudentSubmission',
        component: () => import('../views/student/StudentSubmissionView.vue')
      },
      // 补全：成绩列表
      {
        path: 'grades',
        name: 'StudentGrades',
        component: () => import('../views/student/StudentGradesView.vue')
      },
      // 补全：成绩详情
      {
        path: 'grades/detail/:id',
        name: 'StudentGradeDetail',
        component: () => import('../views/student/StudentGradeDetailView.vue')
      },
      // 补全：学情分析
      {
        path: 'analysis',
        name: 'StudentAnalysis',
        component: () => import('../views/student/StudentAnalysisView.vue')
      },
      {
        path: 'profile',
        name: 'student-profile',
        component: () => import('../views/student/StudentProfileView.vue'),
        meta: { title: 'Personal Information' }
      }
    ]
  },

  // 5. 根路径 "/" 自动化分流
  {
    path: '/',
    name: 'Root',
    redirect: to => {
      const user = getUser();
      const token = getToken();
      if (!token || !user) return '/login';
      // 根据角色跳转到对应后台
      if (user.role === 'admin') return '/admin/dashboard';
      if (user.role === 'teacher') return '/teacher/dashboard';
      return '/student/dashboard';
    }
  },

  // 6. 兜底 404
  {
    path: '/:pathMatch(.*)*',
    redirect: '/login'
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

// 核心路由守卫
router.beforeEach((to, from, next) => {
  const token = getToken();
  const user = getUser();
  const isAuthenticated = !!token;
  const userRole = user?.role;

  // A. 访问登录页：已登录则直接送走
  if (to.path === '/login') {
    if (isAuthenticated) {
      if (userRole === 'admin') return next('/admin/dashboard');
      if (userRole === 'teacher') return next('/teacher/dashboard');
      return next('/student/dashboard');
    }
    return next();
  }

  // B. 未登录拦截：非公开页面全部跳登录
  if (!isAuthenticated && !to.meta.public) {
    return next({ name: 'Login' });
  }

  // C. 权限验证
  if (to.meta.roles && !to.meta.roles.includes(userRole)) {
    console.warn(`[Guard] 越权访问: ${userRole} -> ${to.path}`);
    // 强制跳转回该角色应有的首页
    if (userRole === 'admin') return next('/admin/dashboard');
    if (userRole === 'teacher') return next('/teacher/dashboard');
    return next('/student/dashboard');
  }

  next();
});

export default router;