from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import (
    User, Course, KnowledgePoint, Group, Assignment, Submission,
    DockerReport, AIEvaluation, SystemConfiguration, Appeal,
    NotificationConfig, TeachingInsightReport, SystemOperationLog, PlagiarismReport
)


# --- 1. Inlines ---

class DockerReportInline(admin.StackedInline):
    model = DockerReport
    extra = 0
    readonly_fields = ('compile_status', 'exit_code', 'status', 'execution_time', 'stdout', 'stderr', 'created_at')
    can_delete = False
    classes = ('collapse',)


class AIEvaluationInline(admin.StackedInline):
    model = AIEvaluation
    extra = 0
    readonly_fields = ('total_score', 'kp_scores', 'feedback', 'raw_sandbox_output', 'static_analysis', 'created_at')
    can_delete = False


class AppealInline(admin.StackedInline):
    model = Appeal
    extra = 0
    readonly_fields = ('student_reason', 'ai_judgment', 'created_at')
    can_delete = False
    verbose_name = "关联申诉详情"
    classes = ('collapse',)


# --- 2. Admin Configuration (ModelAdmins)---

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


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'course', 'leader', 'invite_code', 'get_member_count', 'created_at')
    list_filter = ('course',)
    search_fields = ('name', 'invite_code', 'leader__username')
    filter_horizontal = ('members',)
    raw_id_fields = ('leader',)

    @admin.display(description='成员数')
    def get_member_count(self, obj):
        return obj.members.count()


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'course', 'is_group', 'teacher', 'deadline', 'report_sent_status', 'has_ai_insight')
    list_filter = ('course', 'teacher', 'is_group', 'report_sent')
    filter_horizontal = ('knowledge_points',)
    search_fields = ('title',)

    @admin.display(description='报告状态')
    def report_sent_status(self, obj):
        if obj.report_sent:
            return mark_safe('<span style="color: #28a745;">✅ 已发送</span>')
        return mark_safe('<span style="color: #6c757d;">⏳ 待触发</span>')

    @admin.display(description='教情报告', boolean=True)
    def has_ai_insight(self, obj):
        return hasattr(obj, 'teaching_report') and obj.teaching_report.status == 'ready'


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('id', 'student', 'assignment', 'group_info', 'status', 'appeal_status', 'color_final_score', 'created_at')
    list_filter = ('status', 'assignment', 'created_at')
    raw_id_fields = ('student', 'assignment', 'group')
    inlines = [DockerReportInline, AIEvaluationInline]

    @admin.display(description='所属小组')
    def group_info(self, obj):
        if obj.group:
            return obj.group.name
        return mark_safe('<i style="color: #999;">个人提交</i>')

    @admin.display(description='申诉')
    def appeal_status(self, obj):
        if hasattr(obj, 'ai_evaluation') and hasattr(obj.ai_evaluation, 'appeal'):
            return mark_safe('<span style="color: #e67e22; font-weight: bold;">⚠️ 已申诉</span>')
        return "-"

    @admin.display(description='得分')
    def color_final_score(self, obj):
        score = obj.final_score or 0
        color = "#28a745" if score >= 85 else "#007bff" if score >= 60 else "#dc3545"
        return format_html('<b style="color: {};">{}</b>', color, score)


@admin.register(AIEvaluation)
class AIEvaluationAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_student', 'total_score', 'is_published', 'has_appeal', 'created_at')
    inlines = [AppealInline]
    readonly_fields = ('submission', 'static_analysis')

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


# Education diagnosis report management
@admin.register(TeachingInsightReport)
class TeachingInsightReportAdmin(admin.ModelAdmin):
    list_display = ('assignment', 'colored_status', 'get_avg_score', 'generated_at')
    list_filter = ('status', 'generated_at')
    search_fields = ('assignment__title',)
    readonly_fields = ('assignment', 'generated_at')

    @admin.display(description='分析状态')
    def colored_status(self, obj):
        colors = {'ready': '#28a745', 'pending': '#f39c12', 'error': '#dc3545'}
        return format_html(
            '<b style="color: {};">{}</b>',
            colors.get(obj.status, '#000'),
            obj.get_status_display()
        )

    @admin.display(description='班级平均分')
    def get_avg_score(self, obj):
        return obj.stats_data.get('average', 'N/A')

    fieldsets = (
        ('基础信息', {'fields': ('assignment', 'status', 'generated_at')}),
        ('诊断结论 (AI Insights)', {
            'fields': ('ai_insights',),
            'description': '包含：性能总结、优劣势分析、教学建议。'
        }),
        ('统计指标数据 (Stats)', {
            'fields': ('stats_data',),
            'classes': ('collapse',),
            'description': '包含：学生人数、班级均分、各知识点得分明细。'
        }),
    )


# Global Configuration management
@admin.register(SystemConfiguration)
class SystemConfigurationAdmin(admin.ModelAdmin):
    # A list page showing key Docker limitations
    list_display = ('__str__', 'deepseek_model_name', 'docker_mem_limit', 'docker_cpu_quota', 'docker_timeout')

    fieldsets = (
        ('AI 模型配置 (DeepSeek)', {
            'fields': ('deepseek_api_key', 'deepseek_base_url', 'deepseek_model_name'),
            'description': '用于智能批改与代码审计的 AI 接口参数。'
        }),
        ('Docker 沙箱资源限制', {
            'fields': ('docker_mem_limit', 'docker_cpu_quota', 'docker_pids_limit', 'docker_timeout'),
            'description': '控制学生代码运行时的硬件配额，修改后即时刷新缓存并生效。'
        }),
    )

    def has_add_permission(self, request):
        return not SystemConfiguration.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        self.message_user(request, "系统配置已成功保存，新的 Docker 运行策略已生效。")


# Audit log management
@admin.register(SystemOperationLog)
class SystemOperationLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'user', 'action', 'target_type', 'target_id', 'short_detail')
    list_filter = ('action', 'target_type', 'created_at')
    search_fields = ('user__username', 'detail')
    readonly_fields = ('user', 'action', 'target_type', 'target_id', 'detail', 'ip_address', 'created_at')

    @admin.display(description='详情预览')
    def short_detail(self, obj):
        return obj.detail[:50] + "..." if len(obj.detail) > 50 else obj.detail

    def has_add_permission(self, request): return False
    def has_delete_permission(self, request, obj=None): return False


@admin.register(PlagiarismReport)
class PlagiarismReportAdmin(admin.ModelAdmin):
    list_display = ['id', 'assignment', 'status', 'mode', 'file_count', 'created_at']
    list_filter = ['status', 'mode']
    search_fields = ['assignment__title']
    readonly_fields = ['report_url', 'matches', 'error_message', 'created_at']
