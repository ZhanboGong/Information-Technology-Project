import time
import json
import os
from decimal import Decimal
from django.db import transaction
from django.db.models import Max
from apps.core.models import Submission, DockerReport, AIEvaluation
from .docker_runner import DockerRunner
from .ai_scorer import AIScorer


class GradingPipeline:
    def __init__(self, submission_id):
        try:
            self.submission = Submission.objects.get(id=submission_id)
        except Submission.DoesNotExist:
            raise ValueError(f"Submission {submission_id} 不存在")
        self.runner = DockerRunner()
        self.scorer = AIScorer()

    def run_full_pipeline(self, entry_point=None, work_dir=None):
        """执行完整评分流水线"""
        print(f"--- 🚀 开始后台批改: Submission {self.submission.id} ---")

        # 1. 状态锁定
        self.submission.status = 'running'
        self.submission.save(update_fields=['status'])

        try:
            # 2. 第一阶段：Docker 运行
            docker_report = self.run_stage_one_docker(entry_point, work_dir)

            # 3. 第二阶段：AI 评分与分值同步
            self.run_stage_two_ai(docker_report, work_dir)

        except Exception as e:
            print(f"❌ 流水线崩溃: {str(e)}")
            self.submission.status = 'failed'
            self.submission.save(update_fields=['status'])
            raise e

    def run_stage_one_docker(self, entry_point=None, work_dir=None):
        """第一阶段：Docker 运行事实捕获"""
        target_file = entry_point if entry_point else self.submission.file.path
        docker_res = self.runner.run_code(
            file_path=target_file,
            is_project=bool(entry_point),
            project_root=work_dir
        )
        report, _ = DockerReport.objects.update_or_create(
            submission=self.submission,
            defaults={
                'exit_code': docker_res.get('exit_code'),
                'stdout': docker_res.get('output'),
                'compile_status': docker_res.get('compile_status', True),
                'status': docker_res.get('status', 'success')
            }
        )
        return report

    def run_stage_two_ai(self, docker_report, work_dir=None):
        """第二阶段：AI 评分与全量最高分同步"""
        with transaction.atomic():
            # 获取 AI 评分
            eval_data = self.scorer.evaluate_code(self.submission, docker_report, project_path=work_dir)

            try:
                raw_val = eval_data.get('total_score', 0)
                current_score = Decimal(str(raw_val))
            except Exception:
                current_score = Decimal('0.00')

            # 1. 保存本次评价记录
            log_content = str(docker_report.stdout) if docker_report.stdout else "无运行日志"
            AIEvaluation.objects.update_or_create(
                submission=self.submission,
                defaults={
                    'raw_response': json.dumps(eval_data, ensure_ascii=False),
                    'raw_sandbox_output': f"EXIT_{docker_report.exit_code} | LOGS: {log_content}",
                    'scores': eval_data.get('scores', {}),
                    'kp_scores': eval_data.get('kp_scores', {}),
                    'total_score': current_score,
                    'feedback': eval_data.get('feedback', "AI 评审未生成内容"),
                    'is_published': True
                }
            )

            # 🚀 2. 核心修正：找出该学生针对该作业的历史最高分
            print(f"🔍 正在检索全量历史成绩...")
            aggregate_res = AIEvaluation.objects.filter(
                submission__student=self.submission.student,
                submission__assignment=self.submission.assignment
            ).aggregate(max_val=Max('total_score'))

            # 取得最终确定的最高分
            highest_score = aggregate_res.get('max_val')
            if highest_score is None:
                highest_score = current_score

            # 🚀 3. 刷库逻辑：不仅更新当前提交，还同步所有历史提交的 final_score 字段
            # 这解决了你“修改代码前的历史数据没变”的问题
            Submission.objects.filter(
                student=self.submission.student,
                assignment=self.submission.assignment
            ).update(final_score=highest_score)

            # 4. 更新当前提交状态
            self.submission.status = 'completed'
            self.submission.save(update_fields=['status'])

            print(f"✅ 处理完成！本次得分: {current_score}, 全局最高已对齐: {highest_score}")