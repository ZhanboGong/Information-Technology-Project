import os
import shutil
from celery import shared_task
from .utils.grading_pipeline import GradingPipeline


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