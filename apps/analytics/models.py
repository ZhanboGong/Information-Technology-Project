from django.db import models
from apps.core.models import User, KnowledgePoint

# 1. 知识点掌握度 (记录学生对每个KP的平均分和趋势) [cite: 738]
class StudentKnowledgeMastery(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    kp = models.ForeignKey(KnowledgePoint, on_delete=models.CASCADE)
    total_evaluations = models.IntegerField(default=0)
    avg_score = models.DecimalField(max_digits=5, decimal_places=2)
    latest_score = models.DecimalField(max_digits=5, decimal_places=2)
    trend = models.DecimalField(max_digits=5, decimal_places=2) # 进步/退步 [cite: 738]

# 2. 综合画像 (汇总全站表现) [cite: 524, 744]
class StudentOverallProfile(models.Model):
    student = models.OneToOneField(User, on_delete=models.CASCADE)
    overall_avg_score = models.DecimalField(max_digits=5, decimal_places=2)
    learning_ability_score = models.DecimalField(max_digits=5, decimal_places=2) # 学习能力 [cite: 528, 587]
    rank_in_all_students = models.IntegerField(null=True) # 全站排名 [cite: 530, 591]