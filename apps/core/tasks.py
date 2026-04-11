import os
import shutil
from celery import shared_task
from django.utils import timezone
from datetime import timedelta

from Backend import settings
from .models import Assignment, Submission
from .utils.grading_pipeline import GradingPipeline
from django.core.mail import send_mail


@shared_task
def run_grading_task(submission_id, temp_workspace, entry_point=None):
    """
    异步评分任务：仅负责调度 Pipeline 和 资源清理
    """
    print(f"--- 🚀 Celery 收到任务: Submission {submission_id} ---")

    try:
        # 1. 实例化流水线
        pipeline = GradingPipeline(submission_id)

        # 2. 执行流水线 (内部已包含：Docker -> AI -> 最高分覆盖)
        if entry_point:
            # 多文件/项目模式
            pipeline.run_full_pipeline(entry_point=entry_point, work_dir=temp_workspace)
        else:
            # 单文件模式
            pipeline.run_full_pipeline()

    except Exception as e:
        print(f"🚨 Celery Task Error: {str(e)}")
    finally:
        # 3. 任务完成后，统一清理临时目录，防止磁盘爆满
        if temp_workspace and os.path.exists(temp_workspace):
            shutil.rmtree(temp_workspace, ignore_errors=True)
            print(f"🧹 已清理临时目录: {temp_workspace}")

# Sprint 2
@shared_task
def check_deadlines_and_send_reports():
    """
    检查截止日期，并向老师发送成绩报告
    """
    # 1. 查找已过截止日期、但在过去 1 小时内截止且尚未处理的作业 (防止重复发送)
    now = timezone.now()
    one_hour_ago = now - timezone.timedelta(hours=1)

    # 筛选作业：截止时间在当前时间之前，且属于最近截止的作业
    pending_assignments = Assignment.objects.filter(
        deadline__lte=now,
        deadline__gte=one_hour_ago
    )

    for assignment in pending_assignments:
        teacher = assignment.teacher
        if not teacher.email:
            continue

        # 2. 统计全班成绩
        # 获取所有选了这门课的学生
        students = assignment.course.students.all()
        report_lines = [f"作业：{assignment.title}", f"截止时间：{assignment.deadline}", "---成绩列表---"]

        for student in students:
            # 获取该学生对此作业的最高分提交记录
            submission = Submission.objects.filter(
                student=student,
                assignment=assignment,
                status='completed'
            ).order_by('-final_score').first()

            score = submission.final_score if submission else "未提交"
            report_lines.append(f"学生：{student.username} (学号：{student.student_id_num}) - 成绩：{score}")

        # 3. 发送邮件
        subject = f"【自动报告】作业《{assignment.title}》成绩统计"
        message = "\n".join(report_lines)

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [teacher.email],
            fail_silently=False,
        )
        print(f"📧 已向 {teacher.username} 发送作业 {assignment.title} 的成绩报告")
