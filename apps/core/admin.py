from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import (
    User, Course, KnowledgePoint, Assignment, Submission,
    DockerReport, AIEvaluation, SystemConfiguration, Appeal, NotificationConfig
)


# --- 1. 内联组件 (Inlines) ---

class DockerReportInline(admin.StackedInline):
    model = DockerReport
    extra = 0
    readonly_fields = ('compile_status', 'exit_code', 'status', 'execution_time', 'stdout', 'stderr', 'created_at')
    can_delete = False
    classes = ('collapse',)


class AIEvaluationInline(admin.StackedInline):
    model = AIEvaluation
    extra = 0
    readonly_fields = ('total_score', 'kp_scores', 'feedback', 'raw_sandbox_output', 'created_at')
    can_delete = False


class AppealInline(admin.StackedInline):
    model = Appeal
    extra = 0
    readonly_fields = ('student_reason', 'ai_judgment', 'created_at')
    can_delete = False
    verbose_name = "关联申诉详情"
    classes = ('collapse',)


# --- 2. 管理配置 (ModelAdmins) ---

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'student_id_num', 'role', 'class_name', 'is_staff')
    list_filter = ('role', 'class_name')
    search_fields = ('username', 'student_id_num')


@admin.register(NotificationConfig)
class NotificationConfigAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'enable_report', 'remind_before_hours', 'subject_template')
    list_filter = ('enable_report',)
    raw_id_fields = ('teacher',)
    search_fields = ('teacher__username',)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('name', 'teacher', 'invite_code', 'get_student_count', 'created_at')
    filter_horizontal = ('students',)
    search_fields = ('name', 'invite_code')

    @admin.display(description='选课人数')
    def get_student_count(self, obj):
        return obj.students.count()


@admin.register(KnowledgePoint)
class KnowledgePointAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'language', 'is_system', 'course')
    list_filter = ('language', 'is_system', 'category', 'course')
    search_fields = ('name', 'description')


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'course', 'teacher', 'deadline', 'report_sent_status')
    list_filter = ('course', 'teacher', 'report_sent')
    filter_horizontal = ('knowledge_points',)
    search_fields = ('title',)

    # 🚀 修复点 1：使用 mark_safe 渲染固定 HTML 字符串，避免 format_html 的参数缺失错误
    @admin.display(description='报告状态')
    def report_sent_status(self, obj):
        if obj.report_sent:
            return mark_safe('<span style="color: #28a745;">✅ 已发送</span>')
        return mark_safe('<span style="color: #6c757d;">⏳ 待触发</span>')


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('id', 'student', 'assignment', 'status', 'appeal_status', 'color_final_score', 'created_at')
    list_filter = ('status', 'assignment', 'created_at')
    raw_id_fields = ('student', 'assignment')
    inlines = [DockerReportInline, AIEvaluationInline]

    # 🚀 修复点 2：统一使用 mark_safe 渲染状态标签
    @admin.display(description='申诉')
    def appeal_status(self, obj):
        if hasattr(obj, 'ai_evaluation') and hasattr(obj.ai_evaluation, 'appeal'):
            return mark_safe('<span style="color: #e67e22; font-weight: bold;">⚠️ 已申诉</span>')
        return "-"

    # 🚀 修复点 3：这里因为带了变量 color 和 score，使用 format_html 是正确的
    @admin.display(description='得分')
    def color_final_score(self, obj):
        score = obj.final_score or 0
        color = "#28a745" if score >= 85 else "#007bff" if score >= 60 else "#dc3545"
        return format_html('<b style="color: {};">{}</b>', color, score)


@admin.register(AIEvaluation)
class AIEvaluationAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_student', 'total_score', 'is_published', 'has_appeal', 'created_at')
    inlines = [AppealInline]
    readonly_fields = ('submission',)

    @admin.display(description='学生')
    def get_student(self, obj):
        return obj.submission.student.username

    @admin.display(description='是否有申诉', boolean=True)
    def has_appeal(self, obj):
        return hasattr(obj, 'appeal')


@admin.register(Appeal)
class AppealAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_student', 'get_assignment', 'status', 'adjusted_score', 'created_at')
    list_filter = ('status', 'created_at')
    readonly_fields = ('evaluation', 'student_reason', 'ai_judgment', 'created_at')

    fieldsets = (
        ('原始信息', {'fields': ('evaluation', 'student_reason', 'ai_judgment', 'created_at')}),
        ('教师审核', {'fields': ('status', 'teacher_remark', 'adjusted_score')}),
    )

    @admin.display(description='学生')
    def get_student(self, obj):
        return obj.evaluation.submission.student.username

    @admin.display(description='作业')
    def get_assignment(self, obj):
        return obj.evaluation.submission.assignment.title


@admin.register(SystemConfiguration)
class SystemConfigurationAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'deepseek_model_name', 'deepseek_base_url')

    def has_add_permission(self, request):
        # 保持单例，不允许添加多个配置
        return not SystemConfiguration.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False