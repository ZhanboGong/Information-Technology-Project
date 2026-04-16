import { createRouter, createWebHistory } from 'vue-router';
import { getToken, getUser } from '../utils/auth';

const routes = [
  // 1. Login Page
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/LoginView.vue'),
    meta: { public: true }
  },

  // 2. Admin Side
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

  // 3. Teacher Side
  {
    path: '/teacher',
    component: () => import('../layout/MainLayout.vue'),
    meta: { roles: ['teacher', 'admin'] }, // Allow admin to access the teacher interface
    children: [
      { path: '', redirect: '/teacher/dashboard' },
      { path: 'dashboard', name: 'Dashboard', component: () => import('../views/teacher/DashboardView.vue') },
      { path: 'courses', name: 'Courses', component: () => import('../views/teacher/CoursesView.vue') },
      { path: 'grading', name: 'Grading', component: () => import('../views/teacher/GradingListView.vue') },
      { path: 'profile', name: 'TeacherProfile', component: () => import('../views/teacher/TeacherProfileView.vue') },
    ]
  },

  // 4. Student Side
  {
    path: '/student',
    component: () => import('../layout/StudentLayout.vue'),
    meta: { roles: ['student'] },
    children: [
      { path: '', redirect: '/student/dashboard' },
      { path: 'dashboard', name: 'StudentDashboard', component: () => import('../views/student/StudentDashboardView.vue') },
      { path: 'assignments', name: 'StudentAssignments', component: () => import('../views/student/StudentAssignmentsView.vue') },
      {
        path: 'assignments/course/:courseId',
        name: 'StudentCourseAssignments',
        component: () => import('../views/student/StudentCourseAssignmentsView.vue')
      },
      {
        path: 'assignments/submit/:assignId',
        name: 'StudentSubmission',
        component: () => import('../views/student/StudentSubmissionView.vue')
      },
      {
        path: 'grades',
        name: 'StudentGrades',
        component: () => import('../views/student/StudentGradesView.vue')
      },
      {
        path: 'grades/detail/:id',
        name: 'StudentGradeDetail',
        component: () => import('../views/student/StudentGradeDetailView.vue')
      },
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

  // 5. Root path "/" - Automated routing
  {
    path: '/',
    name: 'Root',
    redirect: to => {
      const user = getUser();
      const token = getToken();
      if (!token || !user) return '/login';
      // Switch to the corresponding background based on the role.
      if (user.role === 'admin') return '/admin/dashboard';
      if (user.role === 'teacher') return '/teacher/dashboard';
      return '/student/dashboard';
    }
  },

  // 6. 404
  {
    path: '/:pathMatch(.*)*',
    redirect: '/login'
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

router.beforeEach((to, from, next) => {
  const token = getToken();
  const user = getUser();
  const isAuthenticated = !!token;
  const userRole = user?.role;

  // A. Access login page: If already logged in, simply proceed.
  if (to.path === '/login') {
    if (isAuthenticated) {
      if (userRole === 'admin') return next('/admin/dashboard');
      if (userRole === 'teacher') return next('/teacher/dashboard');
      return next('/student/dashboard');
    }
    return next();
  }

  // B. Login Required Block: All non-public pages redirect to the login page.
  if (!isAuthenticated && !to.meta.public) {
    return next({ name: 'Login' });
  }

  // C. Permission verification
  if (to.meta.roles && !to.meta.roles.includes(userRole)) {
    console.warn(`[Guard] 越权访问: ${userRole} -> ${to.path}`);
    // Force a redirection back to the appropriate homepage of this character.
    if (userRole === 'admin') return next('/admin/dashboard');
    if (userRole === 'teacher') return next('/teacher/dashboard');
    return next('/student/dashboard');
  }

  next();
});

export default router;