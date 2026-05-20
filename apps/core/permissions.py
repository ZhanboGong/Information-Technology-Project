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

        # 1. Must be a logged-in user
        if not user or not user.is_authenticated:
            return False

        # 2. Admin
        if user.role == 'admin' or user.is_superuser:
            return True

        # 3. If it is a teacher, check the audit status
        if user.role == 'teacher':
            # Only teachers who have approved and activated their accounts can access it
            return user.is_active and user.approval_status == 'approved'

        # 4. If it is a student, access to the teacher interface is denied
        return False


class IsStudent(permissions.BasePermission):
    """
    Allow access only to users whose role is student.
    Since students are imported, the default state is approved.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'student'