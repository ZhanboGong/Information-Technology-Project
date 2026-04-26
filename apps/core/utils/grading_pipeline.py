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
        target_file = None
        valid_extensions = ('.py', '.java')

        # 🚀 调试日志：核对传入参数
        print(f"DEBUG | Received Params - entry_point: {entry_point}, work_dir: {work_dir}")

        if work_dir and os.path.exists(work_dir):
            # 🚀 诊断日志：强制列出解压目录下的所有文件结构，排查解压是否成功
            print(f"🔍 Listing files in work_dir ({work_dir}):")
            for root, dirs, files in os.walk(work_dir):
                print(f"   Directory: {root}")
                for f in files:
                    print(f"     - {f}")

            # 步骤 A：如果有传入入口点，优先合成绝对路径
            if entry_point:
                potential_path = os.path.join(work_dir, entry_point) if not os.path.isabs(entry_point) else entry_point
                if os.path.exists(potential_path) and potential_path.lower().endswith(valid_extensions):
                    target_file = potential_path
                    print(f"✅ Resolved entry_point to: {target_file}")

            # 步骤 B：如果入口点无效或未提供，执行递归搜索
            if not target_file:
                print(f"🔍 Entry point missing or invalid. Searching for code files in: {work_dir}")
                for root, dirs, files in os.walk(work_dir):
                    # 忽略隐藏文件夹
                    dirs[:] = [d for d in dirs if not d.startswith('.')]
                    for f in files:
                        if f.lower().endswith(valid_extensions):
                            target_file = os.path.join(root, f)
                            print(f"✅ Auto-detected source file: {target_file}")
                            break
                    if target_file: break

        # 🚀 修复逻辑：最后的兜底回退
        if not target_file:
            target_file = self.submission.file.path
            print(f"ℹ️ No source file found in work_dir. Falling back to submission path: {target_file}")

        print(f"🚀 Docker Pipeline final target path: {target_file}")

        # 调用 Runner
        docker_res = self.runner.run_code(
            file_path=target_file,
            is_project=bool(work_dir),
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
        Phase 2: Perform AI semantic scoring, multi-dimensional data persistence, and global score alignment.

        This method is the "brain" of the scoring pipeline, performing the following delicate operations under database transaction protection:

        1. AI Semantic Analysis: AIScorer is called to convert the results (facts) of the sandbox run of the first stage into review data.
        Shadow Storage:
        - scores: Stores standard dimensions like Logic/Design/Style for back-end reports and charts.
        - Detailed score (ai_raw_feedback) : Stores the fine-grained rating items defined by the teacher to ensure that the feedback is personalized and in-depth.
        3. Data Alignment and patching: Explicitly fill in 'ai_raw_score' and 'ai_raw_feedback' to fix model field mismatch.
        4. Score synchronization logic: use the database aggregation function (Max) to calculate the historical highest score of the student under the job in real time.
        And update the associated Submission.final_score field.
        5. Evidence chain retention: complete record of the original response of AI and the original output of sandbox, as the original evidence for subsequent manual review.
        :param docker_report: The Docker operation report generated in the first stage.
        :param work_dir: Source code decompression path for AI to read the code for static analysis.
        """
        with transaction.atomic():
            # 1. Call AI to get structured review data
            eval_data = self.scorer.evaluate_code(self.submission, docker_report, project_path=work_dir)

            # Fractional precision conversion
            try:
                raw_val = eval_data.get('total_score', 0)
                current_score = Decimal(str(raw_val))
            except Exception:
                current_score = Decimal('0.00')

            # 2. Shadow Storage Logic: Separating Statistical and detailed partitions
            stats_scores = eval_data.get('stats_scores', {"Logic": 0, "Design": 0, "Style": 0})

            # The detailed dimensions defined by the teacher (such as Parts 1-7) are stored in the ai_raw_feedback field
            detailed_scores_json = json.dumps(eval_data.get('scores', {}), ensure_ascii=False)

            log_content = str(docker_report.stdout) if docker_report.stdout else "No running logs"

            # 3. Strictly align model fields to persist data
            AIEvaluation.objects.update_or_create(
                submission=self.submission,
                defaults={
                    # Base score field
                    'total_score': current_score,
                    'feedback': eval_data.get('feedback', "The AI review did not generate content"),

                    'ai_raw_score': current_score,
                    'ai_raw_feedback': detailed_scores_json,

                    # Structured scoring fields
                    'scores': stats_scores,
                    'kp_scores': eval_data.get('kp_scores', {}),

                    # Backup of evidence
                    'raw_response': json.dumps(eval_data, ensure_ascii=False),
                    'raw_sandbox_output': f"EXIT_{docker_report.exit_code} | LOGS: {log_content}",
                    'is_published': True
                }
            )

            # 4. Full score alignment (brushing logic) : Ensure that final_score in the Submission table is always the highest score in history
            print(f"Syncing the all-time high score record...")
            aggregate_res = AIEvaluation.objects.filter(
                submission__student=self.submission.student,
                submission__assignment=self.submission.assignment
            ).aggregate(max_val=Max('total_score'))

            highest_score = aggregate_res.get('max_val') or current_score

            Submission.objects.filter(
                student=self.submission.student,
                assignment=self.submission.assignment
            ).update(final_score=highest_score)

            # Update the current commit status to complete
            self.submission.status = 'completed'
            self.submission.save(update_fields=['status'])

            print(f"Correction done! Current score: {current_score}, Synchronous maximum score: {highest_score}")