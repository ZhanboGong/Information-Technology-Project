from datetime import timedelta
from django.utils import timezone
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.core.cache import cache
import random
import string

def generate_invite_code():
    """
    Generates a unique, human-readable invitation string for course enrollment.
    :return: A 6-character alphanumeric string (e.g., 'A7K9X2').
    """
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


# User Table
class User(AbstractUser):
    """
    The system adopts a unified user model.
    It has expanded the role field, student ID/work ID, and class information, and supports three types of identities: administrators, teachers, and students.
    """
    ROLE_CHOICES = (
        ('admin', '管理员'),
        ('teacher', '教师'),
        ('student', '学生')
    )

    APPROVAL_CHOICES = [
        ('pending_email', '待验证邮箱'),
        ('pending_approval', '待管理员审核'),
        ('approved', '审核通过'),
        ('rejected', '已驳回')
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student', verbose_name="角色")
    student_id_num = models.CharField(max_length=50, null=True, blank=True, verbose_name="学号/工号")
    class_name = models.CharField(max_length=30, db_column='class', null=True, blank=True, verbose_name="班级")
    enable_deadline_reminder = models.BooleanField(default=False, verbose_name="开启截止提醒邮件")
    approval_status = models.CharField(
        max_length=20,
        choices=APPROVAL_CHOICES,
        default='approved',
        verbose_name="审核状态"
    )
    rejected_reason = models.TextField(
        null=True,
        blank=True,
        verbose_name="驳回原因"
    )

    def __str__(self):
        return f"{self.username} ({self.get_role_display()}) - {self.get_approval_status_display()}"


class EmailVerificationToken(models.Model):
    """
    Model for storing email verification tokens during teacher registration.

    Responsibilities:
    1. Identity Proof: Links a unique, short-lived hash to a specific User instance.
    2. Lifecycle Management: Defines a 24-hour expiration window for the verification process.
    3. Cleanup Support: Uses CASCADE delete so that removing a user automatically purges their token.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='email_token'
    )
    token = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        """
        Validates if the token has expired based on its creation timestamp.
        :return: True if current time is within 24 hours of generation, False otherwise.
        """
        return timezone.now() < self.created_at + timedelta(hours=24)

    class Meta:
        db_table = 'auth_email_verification_token'
        verbose_name = "邮箱验证Token"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"Token for {self.user.username}"


@receiver(post_save, sender=User)
def create_default_notification_config(sender, instance, created, **kwargs):
    """
    Signal receiver that auto-generates notification settings for new teachers.

    Responsibilities:
    1. Lifecycle Trigger: Executes immediately after a User record is persisted.
    2. Role Filtering: Only applies to users with the 'teacher' role.
    3. Idempotency: Uses 'get_or_create' to ensure settings aren't duplicated
       during profile updates.
    4. Template Provisioning: Injects a default email subject template for
       immediate report readiness.
    """
    if created and instance.role == 'teacher':
        NotificationConfig.objects.get_or_create(
            teacher=instance,
            defaults={
                'enable_report': True,
                'remind_before_hours': 0,
                'subject_template': "【系统通知】作业截止统计报告：《{title}》"
            }
        )


# Course Table
class Course(models.Model):
    """
    Teaching curriculum model.
    Core logic: One teacher corresponds to multiple courses (1:N), and one course corresponds to multiple students (M:N).
    """
    name = models.CharField(max_length=100, verbose_name="课程名称")
    description = models.TextField(null=True, blank=True, verbose_name="课程描述")
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='teaching_courses', verbose_name="授课教师")
    students = models.ManyToManyField(User, related_name='enrolled_courses', blank=True, verbose_name="选课学生")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    invite_code = models.CharField(
        max_length=10,
        null=True,
        unique=True,
        blank=True,
        default=generate_invite_code,
        verbose_name="邀请码"
    )

    def __str__(self):
        return self.name


# KnowledgePoint Table
class KnowledgePoint(models.Model):
    """
    Knowledge point/assessment dimension model.
    Supporting hierarchical management (L1 system-level general, L2 course-specific) is a key context for retrieval when AI scoring.
    """
    name = models.CharField(max_length=100, verbose_name="知识点简称")
    description = models.TextField(null=True, blank=True, verbose_name="详细考核逻辑")
    category = models.CharField(max_length=50, null=True, verbose_name="分类(L1/L2)")
    is_system = models.BooleanField(default=False, verbose_name="是否为系统级(L1)")
    language = models.CharField(max_length=50, null=True, blank=True, verbose_name="编程语言")
    BLOOM_CHOICES = (
        ('remember', '记忆'),
        ('understand', '理解'),
        ('apply', '应用'),
        ('analyze', '分析'),
        ('evaluate', '评价'),
        ('create', '创造'),
    )

    bloom_level = models.CharField(
        max_length=20,
        choices=BLOOM_CHOICES,
        default='apply',
        verbose_name="布鲁姆认知层级"
    )
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=True, blank=True, verbose_name="所属课程")

    class Meta:
        unique_together = ('name', 'language', 'course')
        verbose_name = "知识点"
        verbose_name_plural = "知识点库"

    def __str__(self):
        return f"[{self.category}] {self.name}"


class Group(models.Model):
    name = models.CharField(max_length=100, verbose_name="小组名称")
    course = models.ForeignKey('Course', on_delete=models.CASCADE, related_name='groups', verbose_name="所属课程")
    leader = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='led_groups', verbose_name="组长")
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='joined_groups', verbose_name="小组成员")
    invite_code = models.CharField(
        max_length=10,
        unique=True,
        default=generate_invite_code,
        verbose_name="小组邀请码"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "小组"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.name} ({self.course.name})"


# 4. Assessment Table
class Assignment(models.Model):
    """
    The assessment task model.
    Contains the core correction configuration:
        - rubric_config: Defines scoring dimensions (e.g. code style, feature implementation, etc.)
        -reference_logic: The Layer 3 reference logic point provided to the AI (e.g. recursion must be used).
    """
    title = models.CharField(max_length=200, verbose_name="作业标题")
    content = models.TextField(verbose_name="作业要求")
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='assignments',
        verbose_name="所属课程"
    )
    deadline = models.DateTimeField(verbose_name="截止日期")
    rubric_config = models.JSONField(help_text="存储各维度的评分标准", verbose_name="评分维度配置")
    max_attempts = models.IntegerField(default=3, verbose_name="最大允许提交次数")
    reference_logic = models.JSONField(default=list, help_text="Layer 3 动态逻辑点", verbose_name="核心逻辑考点")
    knowledge_points = models.ManyToManyField(KnowledgePoint, blank=True, related_name='assignments', verbose_name="考查知识点(L1/L2)")
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='assignments', default=1)
    category = models.CharField(max_length=50, default='basic', verbose_name="难度分类")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Sprint 2
    report_sent = models.BooleanField(default=False, verbose_name="是否已发送截止报告")
    attachment = models.FileField(
        upload_to='assignments/attachments/%Y/%m/%d/',
        null=True,
        blank=True,
        verbose_name="作业附件"
    )
    is_group = models.BooleanField(default=False, verbose_name="是否为小组作业")
    max_group_size = models.PositiveIntegerField(default=5, verbose_name="小组人数上限")

    def __str__(self):
        return self.title


# 5. Submission Table
class Submission(models.Model):
    """
    The student submits the record model.
    It acts as a state carrier for the Pipeline that keeps track of the final score for each attempt.
    """
    SUBMISSION_TYPE_CHOICES = (('file', '单文件'), ('archive', '项目压缩包'))
    STATUS_CHOICES = (('pending', '待处理'), ('running', '运行中'), ('completed', '已完成'), ('failed', '失败'), ('appealing', '申诉中'))
    sub_type = models.CharField(max_length=10, choices=SUBMISSION_TYPE_CHOICES, default='file')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submissions')
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE)
    file = models.FileField(upload_to='submissions/%Y/%m/%d/')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    attempt_number = models.IntegerField(default=1)
    final_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    group = models.ForeignKey(
        'Group',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='submissions',
        verbose_name="关联小组"
    )


# 6. Docker Report Table
class DockerReport(models.Model):
    """
    Model for storing raw execution results from the Docker sandbox.

    Responsibilities:
    1. Result Capture: Records exit codes and output streams (stdout/stderr).
    2. Performance Profiling: Tracks total execution time in seconds.
    3. Status Tracking: Distinguishes between successful runs, timeouts, or OOM (Out of Memory).
    4. Compile Auditing: Specifically flags failures occurring during the build/compile phase.
    """
    submission = models.OneToOneField('Submission', on_delete=models.CASCADE, related_name='docker_report')
    exit_code = models.IntegerField(null=True)
    stdout = models.TextField(null=True, blank=True)
    stderr = models.TextField(null=True, blank=True)
    compile_status = models.BooleanField(default=True, verbose_name="编译状态")
    execution_time = models.FloatField(null=True)
    status = models.CharField(max_length=20, default='success')
    created_at = models.DateTimeField(auto_now_add=True)


# 7. AI Evaluation Report Table
class AIEvaluation(models.Model):
    """
    AI Intelligence Score report.
    The DockerReport and Submission source code were used for semantic analysis.
    kp_scores stores the performance of the specific knowledge point segmentation (L2 level).
    """
    submission = models.OneToOneField('Submission', on_delete=models.CASCADE, related_name='ai_evaluation')
    ai_raw_score = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    ai_raw_feedback = models.TextField(null=True)
    raw_sandbox_output = models.TextField(null=True, blank=True, verbose_name="沙箱原始反馈")
    scores = models.JSONField(verbose_name="维度得分")
    kp_scores = models.JSONField(verbose_name="知识点细分得分", default=dict)
    total_score = models.DecimalField(max_digits=5, decimal_places=2)
    feedback = models.TextField()
    is_published = models.BooleanField(default=False)
    teacher_reviewed = models.BooleanField(default=False)
    raw_response = models.TextField(null=True, blank=True)
    static_analysis = models.JSONField(null=True, blank=True, verbose_name="静态分析数据")
    created_at = models.DateTimeField(auto_now_add=True)
    learning_resources = models.JSONField(null=True, blank=True, verbose_name="学习资源推荐")
    practice_exercises = models.JSONField(null=True, blank=True, verbose_name="练习题目")

    # Sprint 2
    plagiarism_info = models.JSONField(
        null=True,
        blank=True,
        verbose_name="查重信息",
        help_text="格式: {'max_similarity': 0.85, 'target_student': '张三', 'target_submission_id': 101}"
    )


# 9. Teaching Insight Report Table
class TeachingInsightReport(models.Model):
    """
    Pedagogical Diagnostic Report Model.

    Responsibilities:
    1. Knowledge Aggregation: Caches deep AI analysis of class-wide performance.
    2. Data Flexibility: Stores semi-structured statistical and qualitative data via JSON.
    3. Performance Optimization: Prevents expensive AI re-computation by persisting insights.
    """
    STATUS_CHOICES = (
        ('pending', '分析中'),
        ('ready', '就绪'),
        ('error', '失败')
    )

    assignment = models.OneToOneField(
        'Assignment',
        on_delete=models.CASCADE,
        related_name='teaching_report',
        verbose_name="关联作业"
    )

    # Store statistical indicators (average score, number of people, knowledge point score statistics, etc.)
    stats_data = models.JSONField(default=dict, verbose_name="统计指标数据")

    # Store AI-generated analysis reports (analysis, strengths, weaknesses, suggestions)
    ai_insights = models.JSONField(default=dict, verbose_name="AI 诊断结果")

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='ready',
        verbose_name="生成状态"
    )

    generated_at = models.DateTimeField(auto_now=True, verbose_name="生成时间")

    class Meta:
        db_table = 'teaching_insight_report'
        verbose_name = '教情诊断报告'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"Report for: {self.assignment.title}"


class PlagiarismReport(models.Model):
    """
    Plagiarism Detection Report Model.

    Responsibilities:
    1. Result Archiving: Stores outcomes from both remote (MOSS) and local similarity engines.
    2. Workflow Tracking: Manages the lifecycle of an audit from 'pending' to 'completed'.
    3. Evidence Storage: Holds structured match data (student pairs + percentages) for UI rendering.
    """
    assignment = models.ForeignKey('Assignment', on_delete=models.CASCADE, related_name='plagiarism_reports')

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('error', 'Error'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    mode = models.CharField(max_length=20, null=True, blank=True, help_text="moss or local")
    report_url = models.URLField(null=True, blank=True, help_text="MOSS report URL")
    matches = models.JSONField(default=list, blank=True, help_text="Local similarity results")
    file_count = models.IntegerField(default=0)
    error_message = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Plagiarism Report: {self.assignment.title} ({self.status})"


# 8. System Configuration
class SystemConfiguration(models.Model):
    """
    Global System Settings (Singleton).

    Responsibilities:
    1. AI Orchestration: Manages credentials and endpoints for LLM services (DeepSeek).
    2. Sandbox Security: Defines strict hardware limits (CPU, RAM, PIDs) for Docker containers.
    3. Performance Optimization: Uses a cache-aside pattern to reduce database load.
    """
    deepseek_api_key = models.CharField(max_length=255, default="sk-f532188d5dd5436a920de5b44b1f9596", verbose_name="DeepSeek API Key", blank=True)
    deepseek_base_url = models.URLField(default="https://api.deepseek.com", verbose_name="DeepSeek Base URL")
    deepseek_model_name = models.CharField(max_length=100, default="deepseek-chat", verbose_name="模型名称")


    # Docker
    docker_mem_limit = models.CharField(
        max_length=20,
        default="512m",
        verbose_name="容器内存限制",
        help_text="例如: 256m, 512m, 1g"
    )
    docker_cpu_quota = models.BigIntegerField(
        default=1000000000,
        verbose_name="CPU配额(Nano)",
        help_text="1,000,000,000 代表 1 核 CPU"
    )
    docker_pids_limit = models.IntegerField(
        default=50,
        verbose_name="最大进程数限制",
        help_text="防止 Fork 炸弹攻击"
    )
    docker_timeout = models.IntegerField(
        default=30,
        verbose_name="容器运行超时(秒)",
        help_text="代码执行的最长时间"
    )
    # max_tokens = models.IntegerField(default=2000)
    # temperature = models.FloatField(default=0.7)

    class Meta:
        verbose_name = "系统全局配置"
        verbose_name_plural = "系统全局配置"

    def save(self, *args, **kwargs):
        """
        Enforces the Singleton pattern by hardcoding the primary key.
        Invalidates the 'system_config' cache upon any update.
        """
        self.pk = 1
        super().save(*args, **kwargs)
        cache.delete('system_config')
        print(f"DEBUG: Configuration saved. New model: {self.deepseek_model_name}")

    @classmethod
    def get_config(cls):
        """
        Retrieves the global configuration instance.
        Implements a cache-first strategy with a 10-minute TTL.
        :return: The existing configuration instance (creates one if none exists).
        """
        config = cache.get('system_config')
        if not config:
            config, created = cls.objects.get_or_create(pk=1)
            cache.set('system_config', config, 600)
        return config

    def __str__(self):
        return "系统全局配置"


class Appeal(models.Model):
    """
    Grade Appeal Model.
    Responsibilities:
    1. Dispute Management: Tracks the lifecycle of a student's grade contestation.
    2. Automated Screening: Stores AI-generated preliminary audits (ai_judgment) to filter non-substantive appeals.
    3. Human Arbitration: Provides fields for teacher review and final score adjustments.
    4. Data Integrity: Uses a One-to-One link to ensure each evaluation has only one active dispute.
    """
    STATUS_CHOICES = (
        ('pending_ai', 'AI Auditing'),
        ('rejected_by_ai', 'AI Rejected'),
        ('pending_teacher', 'Pending Review'),
        ('completed', 'Resolved')
    )
    # Associated score record
    evaluation = models.OneToOneField('AIEvaluation', on_delete=models.CASCADE, related_name='appeal')
    # Student appeal
    student_reason = models.TextField(verbose_name="学生申诉理由")
    # AI first review opinion
    ai_judgment = models.TextField(null=True, blank=True, verbose_name="AI 初审意见")
    # Final processing state
    adjusted_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="调整后分数"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending_ai')
    # Teacher's Notes
    teacher_remark = models.TextField(null=True, blank=True, verbose_name="教师复核备注")
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)


class NotificationConfig(models.Model):
    """
    Global Notification Preferences for Teachers.

    Responsibilities:
    1. Preference Persistence: Stores "Set and Forget" settings for automated reports.
    2. Timing Orchestration: Defines the lead time for report generation.
    3. Template Customization: Manages dynamic subject line formatting for emails.
    """
    teacher = models.OneToOneField(
        'User',
        on_delete=models.CASCADE,
        related_name='notification_config',
        limit_choices_to={'role': 'teacher'},
        verbose_name="所属教师"
    )

    # Global switch: Whether the teacher wants to receive the deadline report
    enable_report = models.BooleanField(
        default=True,
        verbose_name="开启截止报告通知"
    )

    # Global offset: Default how long before the deadline to send
    remind_before_hours = models.IntegerField(
        default=0,
        verbose_name="提醒偏移小时数",
        help_text="0为截止时发送，正数代表提前发送"
    )


    # Global template: What does the email subject look like
    subject_template = models.CharField(
        max_length=255,
        default="【系统通知】作业截止统计报告：《{title}》",
        verbose_name="标题模板"
    )

    class Meta:
        verbose_name = "全局通知配置"

    def __str__(self):
        return f"{self.teacher.username} 的系统设置"


class SystemOperationLog(models.Model):
    """
    Centralized Audit Logging Model.

    Responsibilities:
    1. Accountability: Records which administrator or teacher performed a specific action.
    2. Forensic Analysis: Captures IP addresses and target identifiers for security reviews.
    3. State Tracking: Provides a chronological history of system-wide modifications.
    """
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="操作人")
    action = models.CharField(max_length=100, verbose_name="操作行为")
    target_type = models.CharField(max_length=50, verbose_name="目标类型") # 如 Assignment, User, Config
    target_id = models.CharField(max_length=50, null=True, blank=True, verbose_name="目标ID")
    detail = models.TextField(verbose_name="详情描述")
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP地址")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="操作时间")

    class Meta:
        ordering = ['-created_at']

