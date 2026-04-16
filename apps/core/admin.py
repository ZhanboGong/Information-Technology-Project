from django.contrib import admin
from django.utils.html import format_html
from .models import User, Course, KnowledgePoint, Assignment, Submission, DockerReport, AIEvaluation, SystemConfiguration


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
    fieldsets = (
        ('评分概览', {'fields': ('total_score', 'kp_scores', 'feedback')}),
        ('原始证据', {'fields': ('raw_sandbox_output',)}),
    )
    can_delete = False


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('id', 'student', 'assignment', 'attempt_number', 'status', 'get_current_score', 'color_final_score', 'created_at')
    list_filter = ('status', 'assignment', 'created_at')
    search_fields = ('student__username', 'student__student_id_num', 'assignment__title')
    raw_id_fields = ('student', 'assignment')
    inlines = [DockerReportInline, AIEvaluationInline]

    @admin.display(description='本次得分')
    def get_current_score(self, obj):
        try:
            return obj.ai_evaluation.total_score
        except:
            return "-"

    @admin.display(description='历史最高记录', ordering='final_score')
    def color_final_score(self, obj):
        score = obj.final_score or 0
        color = "#28a745" if score >= 90 else "#007bff" if score >= 60 else "#dc3545"
        return format_html(
            '<b style="color: {};">{} 分</b>',
            color,
            score
        )


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'student_id_num', 'role', 'class_name', 'is_staff')
    list_filter = ('role', 'class_name')
    search_fields = ('username', 'student_id_num')


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('name', 'teacher', 'get_student_count', 'created_at')
    filter_horizontal = ('students',)
    search_fields = ('name',)

    @admin.display(description='选课人数')
    def get_student_count(self, obj):
        return obj.students.count()


@admin.register(KnowledgePoint)
class KnowledgePointAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'language', 'is_system')
    list_filter = ('language', 'is_system', 'category')
    search_fields = ('name', 'description')


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'max_attempts', 'deadline')
    filter_horizontal = ('knowledge_points',)

    fieldsets = (
        ('基本信息', {
            'fields': ('title', 'content', 'course', 'teacher', 'deadline', 'category', 'max_attempts')
        }),
        ('核心考察范围', {
            'fields': ('knowledge_points',),
        }),
        ('AI 批改配置 (RAG/L3)', {
            'fields': ('rubric_config', 'reference_logic'),
        }),
    )


@admin.register(AIEvaluation)
class AIEvaluationAdmin(admin.ModelAdmin):
    list_display = ('submission_id', 'total_score', 'ai_raw_score', 'is_published', 'created_at')

    fieldsets = (
        ('关联信息', {'fields': ('submission', 'created_at')}),
        ('AI 维度评分 & 知识点得分', {
            'fields': ('scores', 'ai_raw_score', 'ai_raw_feedback', 'kp_scores', 'raw_sandbox_output'),
        }),
        ('老师裁定 & 反馈', {'fields': ('total_score', 'feedback', 'is_published', 'teacher_reviewed')}),
        ('AI 原始响应', {'fields': ('raw_response',), 'classes': ('collapse',)}),
    )

    readonly_fields = (
    'submission', 'created_at', 'raw_response', 'scores', 'ai_raw_score', 'ai_raw_feedback', 'kp_scores',
    'raw_sandbox_output')

    @admin.display(description='学生')
    def get_student(self, obj):
        return obj.submission.student.username

    @admin.display(description='提交ID')
    def submission_id(self, obj):
        return obj.submission.id


@admin.register(SystemConfiguration)
class SystemConfigurationAdmin(admin.ModelAdmin):
    # 限制：不允许添加新记录（只能修改 pk=1 那条）和删除
    def has_add_permission(self, request):
        return not SystemConfiguration.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    fieldsets = (
        ('DeepSeek API 设置', {
            'fields': ('deepseek_api_key', 'deepseek_base_url', 'deepseek_model_name'),
        }),
    )