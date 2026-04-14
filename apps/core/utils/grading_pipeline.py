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
    """
    Automatic correction pipeline core control class.

    This class coordinates code execution, semantic scoring, and data persistence.
    It is not only a business logic class, but also a state machine manager that ensures Submission.
    Flow smoothly from 'pending' to 'completed' or 'failed'.

    Attributes:
    submission: This is the currently pending Submission object.
    runner (DockerRunner): Docker sandbox execution engine instance
    scorer (AIScorer): AI scoring engine instance.
    """

    def __init__(self, submission_id):
        try:
            self.submission = Submission.objects.get(id=submission_id)
        except Submission.DoesNotExist:
            raise ValueError(f"Submission {submission_id} 不存在")
        self.runner = DockerRunner()
        self.scorer = AIScorer()

    def run_full_pipeline(self, entry_point=None, work_dir=None):
        """
        Implement a complete automated correction pipeline.

        Adopt a phased strategy:
        1. State locking: Immediately change the state to 'running' to avoid concurrent conflicts.
        2. Fact fetching (Stage 1) : Run the code in the sandbox to get objective runtime output and exit codes.
        3. Semantic evaluation (Stage 2) : AI generates subjective ratings and feedback by combining source code and runtime facts.
        Exception isolation: Catch full-link exceptions to ensure that the pipeline correctly flags task failures when it crashes.
        :param entry_point: The entry file path for the project to run.
        :param work_dir: Temporary working directory after unzipped source code.
        :return:
        """
        print(f"--- Start the automated correction pipeline: Submission {self.submission.id} ---")

        # 状态锁定：防止重复执行
        self.submission.status = 'running'
        self.submission.save(update_fields=['status'])

        try:
            # 第一阶段：Docker 沙箱运行获取事实证据
            docker_report = self.run_stage_one_docker(entry_point, work_dir)

            # 第二阶段：AI 语义评分与数据持久化
            self.run_stage_two_ai(docker_report, work_dir)

        except Exception as e:
            print(f"流水线执行失败: {str(e)}")
            self.submission.status = 'failed'
            self.submission.save(update_fields=['status'])
            raise e

    def run_stage_one_docker(self, entry_point=None, work_dir=None):
        """
        Phase 1: Collection of factual evidence.
        Invoke DockerRunner to run the code in an isolated container. The captured results (such as stdout, exit_code, etc.)
        will be stored as "undeniable facts" in DockerReport, for reference by the second-stage AI review.
        :param entry_point: The entry file of the code
        :param work_dir: Source working directory path.
        :return: Sandbox run report after persistence.
        """
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
        """
        第二阶段：调用 AI 引擎评分，并严格对齐 AIEvaluation 模型字段。
        """
        with transaction.atomic():
            # 1. 调用 AI 获取结构化评审数据
            eval_data = self.scorer.evaluate_code(self.submission, docker_report, project_path=work_dir)

            # 分数精度转换
            try:
                raw_val = eval_data.get('total_score', 0)
                current_score = Decimal(str(raw_val))
            except Exception:
                current_score = Decimal('0.00')

            # 2. 影子存储逻辑：分离统计分与详细分
            # stats_scores (Logic/Design/Style) 存入 scores 字段，对接数据分析图表
            stats_scores = eval_data.get('stats_scores', {"Logic": 0, "Design": 0, "Style": 0})

            # 老师定义的详细维度分 (如 Parts 1-7) 存入 ai_raw_feedback 字段
            detailed_scores_json = json.dumps(eval_data.get('scores', {}), ensure_ascii=False)

            log_content = str(docker_report.stdout) if docker_report.stdout else "无运行日志"

            # 3. 严格对齐模型字段持久化数据
            AIEvaluation.objects.update_or_create(
                submission=self.submission,
                defaults={
                    # 基础得分字段
                    'total_score': current_score,
                    'feedback': eval_data.get('feedback', "AI 评审未生成内容"),

                    # 关键修复：显式填充模型中的原始评分字段
                    'ai_raw_score': current_score,  # 存入 ai_raw_score
                    'ai_raw_feedback': detailed_scores_json,  # 存入 ai_raw_feedback

                    # 结构化评分字段
                    'scores': stats_scores,  # 存入维度得分 (用于统计)
                    'kp_scores': eval_data.get('kp_scores', {}),

                    # 证据备份
                    'raw_response': json.dumps(eval_data, ensure_ascii=False),
                    'raw_sandbox_output': f"EXIT_{docker_report.exit_code} | LOGS: {log_content}",
                    'is_published': True
                }
            )

            # 4. 全量成绩对齐（刷分逻辑）：确保 Submission 表中的 final_score 始终为历史最高分
            print(f"正在同步历史最高分记录...")
            aggregate_res = AIEvaluation.objects.filter(
                submission__student=self.submission.student,
                submission__assignment=self.submission.assignment
            ).aggregate(max_val=Max('total_score'))

            highest_score = aggregate_res.get('max_val') or current_score

            Submission.objects.filter(
                student=self.submission.student,
                assignment=self.submission.assignment
            ).update(final_score=highest_score)

            # 更新当前提交状态为完成
            self.submission.status = 'completed'
            self.submission.save(update_fields=['status'])

            print(f"批改完成! 当前得分: {current_score}, 同步最高分: {highest_score}")