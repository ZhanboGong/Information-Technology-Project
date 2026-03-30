from django.contrib import admin
from django.utils.html import format_html
from .models import User, Course, KnowledgePoint, Assignment, Submission, DockerReport, AIEvaluation


# 1. 定义 Docker 报告的内联显示 (保持只读，增加编译状态显示)
class DockerReportInline(admin.StackedInline):
    model = DockerReport
    extra = 0
    readonly_fields = ('compile_status', 'exit_code', 'status', 'execution_time', 'stdout', 'stderr', 'created_at')
    can_delete = False
    classes = ('collapse',) # 默认折叠，保持界面整洁


# 2. 修改 AI 评审内联 (在 Submission 详情页直接看本次评分)
class AIEvaluationInline(admin.StackedInline):
    model = AIEvaluation
    extra = 0
    readonly_fields = ('total_score', 'kp_scores', 'feedback', 'raw_sandbox_output', 'created_at')
    fieldsets = (
        ('评分概览', {'fields': ('total_score', 'kp_scores', 'feedback')}),
        ('原始证据', {'fields': ('raw_sandbox_output',)}),
    )
    can_delete = False


# 3. 增强 Submission（提交记录）管理界面
@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    # 🚀 优化点：增加 color_final_score，直接在列表对比最高分
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
        """用颜色标识最高分，方便一眼定位优生"""
        score = obj.final_score or 0
        color = "#28a745" if score >= 90 else "#007bff" if score >= 60 else "#dc3545"
        return format_html(
            '<b style="color: {};">{} 分</b>',
            color,
            score
        )


# 4. 注册其他基础业务表
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
    # 🚀 优化点：增加 kp_scores 显示
    list_display = ('submission_id', 'get_student', 'total_score', 'is_published', 'teacher_reviewed', 'created_at')
    list_filter = ('is_published', 'teacher_reviewed', 'total_score')

    fieldsets = (
        ('关联信息', {
            'fields': ('submission', 'created_at')
        }),
        ('AI 维度评分 & 知识点得分', {
            'fields': ('scores', 'kp_scores', 'raw_sandbox_output'),
        }),
        ('老师裁定 & 反馈', {
            'fields': ('total_score', 'feedback', 'is_published', 'teacher_reviewed'),
        }),
        ('AI 原始响应 (仅供调试)', {
            'fields': ('raw_response',),
            'classes': ('collapse',),
        }),
    )
    readonly_fields = ('submission', 'created_at', 'raw_response', 'scores', 'kp_scores', 'raw_sandbox_output')

    @admin.display(description='学生')
    def get_student(self, obj):
        return obj.submission.student.username

    @admin.display(description='提交ID')
    def submission_id(self, obj):
        return obj.submission.id