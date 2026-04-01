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
    Automatic correction pipeline center control class.
    This class is responsible for coordinating the full lifecycle processing of student submissions, including:
    1. State locking: Prevents concurrent conflicts.
    2. Sandbox run: Use DockerRunner to capture the actual code run data (stdout/exit_code).
    3. AI Evaluation: Combined with the running results, AIScorer is used for semantic analysis and scoring.
    4. Grade alignment: automatic grade brushing logic is implemented to ensure that all historical submissions of students for this assignment are synchronized to the highest grade.
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
        This method links the process from running the code to scoring the AI, and is responsible for maintaining the state machine of the Submission.
        The execution flow is as follows:
        1. Update the state to 'running' to lock the task.
        2. Call the Docker runtime to capture the output.
        3. Invoke the AI scoring system to generate feedback and synchronize the highest score.
        If anything goes wrong, mark the status as 'failed' and throw an exception.
        :param entry_point: The path to the specified program entry file.
        :param work_dir: Path to the temporary working directory in which the project will be unpacked.
        :return: None: The result is persisted directly to the database
        """
        print(f"--- Start the background marking: Submission {self.submission.id} ---")

        # State locking: Update the database state to prevent duplicate scheduling in the frontend or background
        self.submission.status = 'running'
        self.submission.save(update_fields=['status'])

        try:
            # Phase 1: Docker running
            docker_report = self.run_stage_one_docker(entry_point, work_dir)

            # Phase 2: The AI score is synchronized with the score value
            self.run_stage_two_ai(docker_report, work_dir)

        except Exception as e:
            print(f"Error: Pipeline crash: {str(e)}")
            self.submission.status = 'failed'
            self.submission.save(update_fields=['status'])
            raise e

    def run_stage_one_docker(self, entry_point=None, work_dir=None):
        """
        Phase 1: Docker runs fact capture.
        Executing student submitted code or project in a restricted sandbox environment, capturing raw data (standard output, exit code, etc.) at runtime
        And save these "facts" to the DockerReport model for reference in the subsequent AI scoring stage.
        :param entry_point: The path to the project's entry point file
        :param work_dir: Path to the root directory of the extracted project.
        :return: The saved run report instance
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
        Phase 2: Perform AI semantic scoring and perform full grade alignment.
        This method contains the following core logic:
        1. Call AI interface: Intelligent scoring combined with code execution facts (DockerReport).
        2. Data persistence: Save AI rating details, itemized scores, and teacher feedback.
        3. Grade Alignment (core) : Calculate the highest grade of all the historical submissions of the student for the assignment and perform a "brush" synchronization.
        Ensure that the final_score field is consistent for all associated submissions to address historical score lag issues.
        :param docker_report: The container run report instance generated in the first phase
        :param work_dir: A temporary working directory where the project source code resides.
        :return: The results are persisted to the database.
        """

        # Start atomic database transactions to ensure that score saving and synchronization with the highest score are either all successful or all rolled back
        with transaction.atomic():
            # Call the AI rater: semantic analysis, knowledge matching, and feedback generation
            eval_data = self.scorer.evaluate_code(self.submission, docker_report, project_path=work_dir)

            # Safe conversion: Convert the scores returned by the AI to Decimal, ensuring precision and preventing non-numeric exceptions
            try:
                raw_val = eval_data.get('total_score', 0)
                current_score = Decimal(str(raw_val))
            except Exception:
                current_score = Decimal('0.00')

            # 1. Save/update a detailed review of this submission
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

            # 2. Core logic: Retrieve all of the student's historical submissions for the current assignment and find the highest score
            print(f"🔍 正在检索全量历史成绩...")
            aggregate_res = AIEvaluation.objects.filter(
                submission__student=self.submission.student,
                submission__assignment=self.submission.assignment
            ).aggregate(max_val=Max('total_score'))

            # Get the highest score in history (or the current score if this is the first commit)
            highest_score = aggregate_res.get('max_val')
            if highest_score is None:
                highest_score = current_score

            # 3. Synchronous flush logic:
            # Update ' all '  of the student's submissions for that assignment to align final_score to the highest score.
            # This design ensures that the score displayed on the student side is always the "highest score so far".
            Submission.objects.filter(
                student=self.submission.student,
                assignment=self.submission.assignment
            ).update(final_score=highest_score)

            # 4. Update the current commit pipeline status to "completed"
            self.submission.status = 'completed'
            self.submission.save(update_fields=['status'])

            print(f"Processing done! Score: {current_score}, global highest aligned: {highest_score}")
