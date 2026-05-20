from rest_framework import permissions


class IsApprovedTeacher(permissions.BasePermission):
    """
    针对教师的准入权限：
    1. 管理员：永远放行。
    2. 教师：必须 (approval_status == 'approved') 且 (is_active == True)。
    3. 学生：不属于此权限范围（学生应该用 IsStudent 或 IsAuthenticated）。
    """
    message = "您的教师账号尚未通过审核，或邮箱验证未完成。请检查邮箱或联系管理员。"

    def has_permission(self, request, view):
        user = request.user

        # 1. 必须是已登录用户
        if not user or not user.is_authenticated:
            return False

        # 2. 如果是管理员，直接放行
        if user.role == 'admin' or user.is_superuser:
            return True

        # 3. 如果是教师，检查审核状态
        if user.role == 'teacher':
            # 只有审核通过且账号激活的老师才能访问
            return user.is_active and user.approval_status == 'approved'

        # 4. 如果是学生，访问教师接口会被拒绝
        return False


class IsStudent(permissions.BasePermission):
    """
    仅允许角色为学生的用户访问。
    由于学生是导入的，默认状态就是 approved。
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'student'