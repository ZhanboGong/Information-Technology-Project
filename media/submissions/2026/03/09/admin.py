# courses/admin.py
"""
课程管理模块 - Django Admin配置
路径: courses/admin.py

提供友好的后台管理界面，支持两种选课方式的管理
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Q
from .models import Course, Enrollment


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    """课程管理后台"""

    list_display = [
        'course_id', 'course_code', 'course_name', 'semester',
        'teacher_link', 'enrolled_students', 'assignment_count_display',
        'enrollment_code_display', 'is_active', 'created_at'
    ]

    list_filter = ['is_active', 'semester', 'created_at']

    search_fields = ['course_code', 'course_name', 'teacher__username', 'enrollment_code']

    readonly_fields = [
        'course_id', 'enrollment_code', 'created_at', 'updated_at',
        'enrolled_count_display', 'active_students_display',
        'code_enrolled_display', 'import_enrolled_display'
    ]

    fieldsets = (
        ('基本信息', {
            'fields': ('course_id', 'course_code', 'course_name', 'semester')
        }),
        ('课程设置', {
            'fields': ('teacher', 'description', 'is_active', 'max_students')
        }),
        ('选课信息', {
            'fields': (
                'enrollment_code',
                'enrolled_count_display',
                'active_students_display',
                'code_enrolled_display',
                'import_enrolled_display'
            ),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    actions = ['activate_courses', 'deactivate_courses', 'regenerate_enrollment_codes']

    def get_queryset(self, request):
        """添加统计数据"""
        qs = super().get_queryset(request)
        return qs.annotate(
            # enrolled_count=Count('enrollments'),
            active_count=Count('enrollments', filter=Q(enrollments__is_active=True)),
            code_count=Count('enrollments', filter=Q(enrollments__is_active=True, enrollments__enroll_method='code')),
            import_count=Count('enrollments',
                               filter=Q(enrollments__is_active=True, enrollments__enroll_method='import')),
            # assignment_count=Count('assignments')
        )

    def teacher_link(self, obj):
        """教师链接"""
        url = reverse('admin:authentication_user_change', args=[obj.teacher.user_id])
        return format_html('<a href="{}">{}</a>', url, obj.teacher.username)

    teacher_link.short_description = '授课教师'

    def enrolled_students(self, obj):
        """选课学生数（带链接）"""
        count = obj.active_count
        color = 'green' if count > 0 else 'gray'
        url = reverse('admin:courses_enrollment_changelist') + f'?course__id__exact={obj.course_id}'
        return format_html(
            '<a href="{}" style="color: {}; font-weight: bold;">{} 人</a>',
            url, color, count
        )

    enrolled_students.short_description = '选课人数'
    enrolled_students.admin_order_field = 'active_count'

    def assignment_count_display(self, obj):
        """作业数量"""
        # count = obj.assignment_count
        count = 0
        if count > 0:
            return format_html('<span style="color: blue;">{} 个</span>', count)
        return format_html('<span style="color: gray;">0 个</span>')

    assignment_count_display.short_description = '作业数'
    # assignment_count_display.admin_order_field = 'assignment_count'

    def enrollment_code_display(self, obj):
        """课程码（可复制）"""
        return format_html(
            '<code style="background: #f0f0f0; padding: 3px 6px; border-radius: 3px; '
            'font-weight: bold; font-size: 14px;">{}</code>',
            obj.enrollment_code
        )

    enrollment_code_display.short_description = '课程码'

    def enrolled_count_display(self, obj):
        """总选课人数"""
        return f"{obj.enrollments.count()} 人"

    enrolled_count_display.short_description = '总选课人数'

    def active_students_display(self, obj):
        """当前在读学生"""
        count = obj.enrollments.filter(is_active=True).count()
        return f"{count} 人"

    active_students_display.short_description = '当前在读学生'

    def code_enrolled_display(self, obj):
        """通过课程码选课人数"""
        count = obj.code_count
        return format_html(
            '<span style="color: #0066cc;">{} 人 (课程码)</span>',
            count
        )

    code_enrolled_display.short_description = '课程码选课'
    code_enrolled_display.admin_order_field = 'code_count'

    def import_enrolled_display(self, obj):
        """教师导入人数"""
        count = obj.import_count
        return format_html(
            '<span style="color: #cc6600;">{} 人 (教师导入)</span>',
            count
        )

    import_enrolled_display.short_description = '教师导入'
    import_enrolled_display.admin_order_field = 'import_count'

    # 批量操作
    def activate_courses(self, request, queryset):
        """批量启用课程"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'成功启用 {updated} 门课程')

    activate_courses.short_description = '启用选中的课程'

    def deactivate_courses(self, request, queryset):
        """批量停用课程"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'成功停用 {updated} 门课程')

    deactivate_courses.short_description = '停用选中的课程'

    def regenerate_enrollment_codes(self, request, queryset):
        """批量重新生成课程码"""
        for course in queryset:
            course.enrollment_code = Course.generate_enrollment_code()
            course.save()
        self.message_user(request, f'成功重新生成 {queryset.count()} 个课程码')

    regenerate_enrollment_codes.short_description = '重新生成课程码'


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    """选课记录管理后台"""

    list_display = [
        'enrollment_id', 'student_link', 'course_link',
        'enroll_method_display', 'imported_by_display',
        'status_display', 'enrolled_at'
    ]

    list_filter = [
        'is_active', 'enroll_method', 'enrolled_at', 'course__semester'
    ]

    search_fields = [
        'user__username', 'user__student_id_num',
        'course__course_code', 'course__course_name'
    ]

    readonly_fields = ['enrollment_id', 'enrolled_at', 'dropped_at']

    date_hierarchy = 'enrolled_at'

    fieldsets = (
        ('选课信息', {
            'fields': ('enrollment_id', 'user', 'course', 'is_active')
        }),
        ('选课方式', {
            'fields': ('enroll_method', 'imported_by')
        }),
        ('时间记录', {
            'fields': ('enrolled_at', 'dropped_at')
        })
    )

    actions = ['activate_enrollments', 'deactivate_enrollments']

    def student_link(self, obj):
        """学生链接"""
        url = reverse('admin:authentication_user_change', args=[obj.user.user_id])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)

    student_link.short_description = '学生'

    def course_link(self, obj):
        """课程链接"""
        url = reverse('admin:courses_course_change', args=[obj.course.course_id])
        return format_html('<a href="{}">{}</a>', url, obj.course.course_name)

    course_link.short_description = '课程'

    def enroll_method_display(self, obj):
        """选课方式显示"""
        if obj.enroll_method == 'code':
            return format_html(
                '<span style="color: white; background: #0066cc; padding: 3px 8px; '
                'border-radius: 3px;">课程码</span>'
            )
        else:
            return format_html(
                '<span style="color: white; background: #cc6600; padding: 3px 8px; '
                'border-radius: 3px;">教师导入</span>'
            )

    enroll_method_display.short_description = '选课方式'

    def imported_by_display(self, obj):
        """导入者显示"""
        if obj.enroll_method == 'import' and obj.imported_by:
            url = reverse('admin:authentication_user_change', args=[obj.imported_by.user_id])
            return format_html('<a href="{}">{}</a>', url, obj.imported_by.username)
        return '-'

    imported_by_display.short_description = '导入者'

    def status_display(self, obj):
        """状态显示"""
        if obj.is_active:
            return format_html(
                '<span style="color: white; background: green; padding: 3px 8px; '
                'border-radius: 3px;">在读</span>'
            )
        else:
            return format_html(
                '<span style="color: white; background: gray; padding: 3px 8px; '
                'border-radius: 3px;">已退课</span>'
            )

    status_display.short_description = '状态'

    def activate_enrollments(self, request, queryset):
        """批量激活选课"""
        updated = queryset.update(is_active=True, dropped_at=None)
        self.message_user(request, f'成功激活 {updated} 条选课记录')

    activate_enrollments.short_description = '激活选中的选课记录'

    def deactivate_enrollments(self, request, queryset):
        """批量停用选课"""
        for enrollment in queryset:
            enrollment.drop()
        self.message_user(request, f'成功停用 {queryset.count()} 条选课记录')

    deactivate_enrollments.short_description = '停用选中的选课记录'


# 自定义Admin站点标题
admin.site.site_header = 'AI作业评审系统 - 管理后台'
admin.site.site_title = 'AI作业评审系统'
admin.site.index_title = '课程管理'
