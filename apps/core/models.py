from datetime import timedelta

from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.core.cache import cache
import random
import string

def generate_invite_code():
    # Produces a combination of six capital letters and numbers
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
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student', verbose_name="角色")
    student_id_num = models.CharField(max_length=50, null=True, blank=True, verbose_name="学号/工号")
    class_name = models.CharField(max_length=30, db_column='class', null=True, blank=True, verbose_name="班级")

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


@receiver(post_save, sender=User)
def create_default_notification_config(sender, instance, created, **kwargs):
    """
    当新用户被创建，且角色是老师时，自动生成全局通知配置
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
    Supporting hierarchical management (L1 system-level general, L2 course-specific) is a key context for RAG retrieval when AI scoring.
    """
    name = models.CharField(max_length=100, verbose_name="知识点简称")
    description = models.TextField(null=True, blank=True, verbose_name="详细考核逻辑")
    category = models.CharField(max_length=50, null=True, verbose_name="分类(L1/L2)")
    is_system = models.BooleanField(default=False, verbose_name="是否为系统级(L1)")
    language = models.CharField(max_length=50, null=True, blank=True, verbose_name="编程语言")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=True, blank=True, verbose_name="所属课程")

    class Meta:
        unique_together = ('name', 'language', 'course')
        verbose_name = "知识点"
        verbose_name_plural = "知识点库"

    def __str__(self):
        return f"[{self.category}] {self.name}"


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


# 6. Docker Report Table
class DockerReport(models.Model):
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
    created_at = models.DateTimeField(auto_now_add=True)

    # Sprint 2
    plagiarism_info = models.JSONField(
        null=True,
        blank=True,
        verbose_name="查重信息",
        help_text="格式: {'max_similarity': 0.85, 'target_student': '张三', 'target_submission_id': 101}"
    )


# 8. System Configuration
class SystemConfiguration(models.Model):
    deepseek_api_key = models.CharField(max_length=255, default="sk-f532188d5dd5436a920de5b44b1f9596", verbose_name="DeepSeek API Key", blank=True)
    deepseek_base_url = models.URLField(default="https://api.deepseek.com", verbose_name="DeepSeek Base URL")
    deepseek_model_name = models.CharField(max_length=100, default="deepseek-chat", verbose_name="模型名称")

    # max_tokens = models.IntegerField(default=2000)
    # temperature = models.FloatField(default=0.7)

    class Meta:
        verbose_name = "系统全局配置"
        verbose_name_plural = "系统全局配置"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
        cache.delete('system_config')
        print(f"DEBUG: Configuration saved. New model: {self.deepseek_model_name}")

    @classmethod
    def get_config(cls):
        config = cache.get('system_config')
        if not config:
            config, created = cls.objects.get_or_create(pk=1)
            cache.set('system_config', config, 600)
        return config

    def __str__(self):
        return "系统全局配置"


# Sprint 2
class Appeal(models.Model):
    STATUS_CHOICES = (
        ('pending_ai', 'AI 审核中'),
        ('rejected_by_ai', 'AI 驳回'),
        ('pending_teacher', '待教师复核'),
        ('completed', '处理完成')
    )
    # 关联评分记录
    evaluation = models.OneToOneField('AIEvaluation', on_delete=models.CASCADE, related_name='appeal')
    # 学生诉求
    student_reason = models.TextField(verbose_name="学生申诉理由")
    # AI 初审意见
    ai_judgment = models.TextField(null=True, blank=True, verbose_name="AI 初审意见")
    # 最终处理状态
    adjusted_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="调整后分数"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending_ai')
    # 教师备注
    teacher_remark = models.TextField(null=True, blank=True, verbose_name="教师复核备注")
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)


class NotificationConfig(models.Model):
    """
    老师的系统全局通知偏好。
    每个老师 ID 仅对应一条记录，实现“一劳永逸”的设置。
    """
    teacher = models.OneToOneField(
        'User',
        on_delete=models.CASCADE,
        related_name='notification_config',
        limit_choices_to={'role': 'teacher'},
        verbose_name="所属教师"
    )

    # 全局开关：老师是否想接收截止报告
    enable_report = models.BooleanField(
        default=True,
        verbose_name="开启截止报告通知"
    )

    # 全局偏移：默认在截止前多久发送
    remind_before_hours = models.IntegerField(
        default=0,
        verbose_name="提醒偏移小时数",
        help_text="0为截止时发送，正数代表提前发送"
    )

    # 全局模板：邮件标题长什么样
    subject_template = models.CharField(
        max_length=255,
        default="【系统通知】作业截止统计报告：《{title}》",
        verbose_name="标题模板"
    )

    class Meta:
        verbose_name = "全局通知配置"

    def __str__(self):
        return f"{self.teacher.username} 的系统设置"
