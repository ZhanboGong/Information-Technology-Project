from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    MyTokenObtainPairView,
    TeacherAssignmentViewSet,
    TeacherCourseViewSet,            # 🚀 导入新增视图
    TeacherStudentManagementViewSet, # 🚀 导入新增视图
    StudentAssignmentViewSet,
    StudentSubmissionViewSet,
    StudentCourseViewSet
)
from rest_framework_simplejwt.views import TokenRefreshView

# 创建路由器
router = DefaultRouter()

# --- 教师端接口 ---
# /api/auth/teacher/assignments/
router.register(r'teacher/assignments', TeacherAssignmentViewSet, basename='teacher-assignment')
# /api/auth/teacher/courses/ (这就是你刚才报错 404 的地址)
router.register(r'teacher/courses', TeacherCourseViewSet, basename='teacher-course')
# /api/auth/teacher/students/
router.register(r'teacher/students', TeacherStudentManagementViewSet, basename='teacher-student')

# --- 学生端接口 ---
# /api/auth/student/assignments/
router.register(r'student/assignments', StudentAssignmentViewSet, basename='student-assignment')
# /api/auth/student/submissions/
router.register(r'student/submissions', StudentSubmissionViewSet, basename='student-submission')
# /api/auth/student/courses/  <-- 新增这个
router.register(r'student/courses', StudentCourseViewSet, basename='student-course')

urlpatterns = [
    # 1. 路由器生成的 API 路径 (包括上面所有的 register 路径)
    path('', include(router.urls)),

    # 2. 身份认证相关路径
    path('login/', MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
