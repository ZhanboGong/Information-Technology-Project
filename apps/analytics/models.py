from django.db import models
from apps.core.models import User, KnowledgePoint

# 1. Knowledge point mastery (record the average score and trend of students for each KP)
class StudentKnowledgeMastery(models.Model):
    """
    Student knowledge mastery portrait.
    It is used to record and track students' learning performance on specific knowledge points.
    This model is a key data source for generating radar charts and progress analysis of students.
    """
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    kp = models.ForeignKey(KnowledgePoint, on_delete=models.CASCADE)
    total_evaluations = models.IntegerField(default=0)
    avg_score = models.DecimalField(max_digits=5, decimal_places=2)
    latest_score = models.DecimalField(max_digits=5, decimal_places=2)
    trend = models.DecimalField(max_digits=5, decimal_places=2)

# 2. Comprehensive portrait (summarizing the performance of the whole site)
class StudentOverallProfile(models.Model):
    """
    The comprehensive quality portrait of students under the whole station dimension.
    The performance of students in all courses is aggregated to provide a macro learning ability assessment and competitive ranking.
    """
    student = models.OneToOneField(User, on_delete=models.CASCADE)
    overall_avg_score = models.DecimalField(max_digits=5, decimal_places=2)
    learning_ability_score = models.DecimalField(max_digits=5, decimal_places=2)
    rank_in_all_students = models.IntegerField(null=True)


class AIServiceLog(models.Model):
    """
    Large Model Interface (LLM API) service call logs.
    Used to monitor the cost (Token consumption), performance (response time), and stability (status code) of the AI service.
    This is the core table for high availability and budget control.
    """
    SERVICE_CHOICES = [
        ('deepseek', 'DeepSeek'),
        ('openai', 'OpenAI'),
    ]

    service_name = models.CharField(max_length=50, choices=SERVICE_CHOICES, default='deepseek', verbose_name="AI服务")
    endpoint = models.CharField(max_length=255, verbose_name="请求接口")

    # Token consumption
    prompt_tokens = models.IntegerField(default=0, verbose_name="输入 Token")
    completion_tokens = models.IntegerField(default=0, verbose_name="输出 Token")
    total_tokens = models.IntegerField(default=0, verbose_name="总消耗 Token")

    # Performance and Status
    response_time = models.FloatField(help_text="单位：秒", verbose_name="响应耗时")
    status_code = models.IntegerField(verbose_name="状态码")

    # timestamp
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="记录时间")
 
    class Meta:
        verbose_name = "AI 接口日志"
        verbose_name_plural = "AI 接口监控"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.service_name} - {self.total_tokens} tokens ({self.created_at})"