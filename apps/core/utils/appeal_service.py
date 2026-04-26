import json
import os
import shutil
import uuid
from ..models import SystemConfiguration, Appeal
from .project_analyzer import ProjectAnalyzer
from openai import OpenAI


class AppealService:
    """
    申诉审计服务：集成代码解压、逻辑聚合与 AI 决策
    负责对学生申诉理由进行“自查”，判定是否存在误判，并为老师提供审计建议。
    """

    @staticmethod
    def process_student_appeal(submission, student_reason):
        """
        核心工具方法：由 View 直接调用

        逻辑步骤：
        1. 获取系统配置并初始化 AI 客户端。
        2. 提取源代码上下文（单文件或 ZIP 项目）。
        3. 构造包含“原始证据”和“申诉理由”的审计 Prompt。
        4. 调用 AI 获取结构化判定结果。
        """
        # 1. 初始化配置与 AI 客户端
        config = SystemConfiguration.get_config()
        client = OpenAI(api_key=config.deepseek_api_key, base_url=config.deepseek_base_url)
        analyzer = ProjectAnalyzer()

        # 2. 准备代码上下文 (利用 ProjectAnalyzer 处理嵌套结构)
        # 注意：这里建议使用 settings.MEDIA_ROOT 下的 temp 目录以保证跨平台兼容性
        temp_dir = os.path.join(os.path.dirname(submission.file.path), f"appeal_eval_{uuid.uuid4().hex}")
        code_context = ""

        try:
            if submission.file.name.lower().endswith('.zip'):
                # 如果是项目压缩包，解压并遍历所有 Python 源文件
                analyzer.unzip_project(submission.file.path, temp_dir)
                snippets = []
                for root, _, files in os.walk(temp_dir):
                    for file in files:
                        # 过滤掉隐藏文件和 __pycache__ 等
                        if file.endswith(('.py', '.java')) and not file.startswith('__'):
                            rel_path = os.path.relpath(os.path.join(root, file), temp_dir)
                            try:
                                with open(os.path.join(root, file), 'r', encoding='utf-8', errors='ignore') as f:
                                    snippets.append(f"--- File: {rel_path} ---\n{f.read()}")
                            except Exception as e:
                                snippets.append(f"--- File: {rel_path} (读取失败: {str(e)}) ---")
                code_context = "\n\n".join(snippets)
            else:
                # 单文件直接读取
                with open(submission.file.path, 'r', encoding='utf-8', errors='ignore') as f:
                    code_context = f.read()
        except Exception as e:
            code_context = f"代码上下文提取失败: {str(e)}"
        finally:
            # 及时清理临时解压目录
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)

        # 3. 构造 AI 审计 Prompt (关键：强制 AI 提供代码证据)
        eval_obj = submission.ai_evaluation
        prompt = f"""
        你是一名公正且严谨的编程课程审计主管。请评估学生对 AI 自动评分结果的申诉是否合理。

        [背景信息]
        作业要求: {submission.assignment.content}
        评分维度: {json.dumps(submission.assignment.rubric_config, ensure_ascii=False)}

        [学生代码上下文]
        {code_context}

        [原始评估证据]
        原始总分: {eval_obj.total_score}
        原始反馈: {eval_obj.feedback}

        [学生申诉理由]
        “{student_reason}”

        [任务要求]
        请站在中立角度，根据“学生代码”和“作业要求”核实申诉理由：
        1. 如果学生指出 AI 漏判了某个功能点，请在代码中寻找具体实现。
        2. 如果确实存在误判，请支持申诉 (is_reasonable = true)。
        3. 如果学生理由不成立或理解偏差，请反驳并说明原因 (is_reasonable = false)。

        [输出要求]
        请严格按以下 JSON 格式输出，不要包含任何 Markdown 代码块标记：
        {{
          "is_reasonable": bool, 
          "ai_judgment": "给老师看的专业分析。如果驳回，请列出代码中缺失或错误的证据；如果支持，请指出误判位置。",
          "reply_for_student": "给学生的解释。语气需平和，明确告知是维持原判还是已转交老师人工复核。"
        }}
        """

        # 4. 调用 AI (启用 JSON Mode 确保返回格式)
        try:
            response = client.chat.completions.create(
                model=config.deepseek_model_name,
                messages=[
                    {"role": "system", "content": "You are a professional educational auditor."},
                    {"role": "user", "content": prompt}
                ],
                response_format={'type': 'json_object'},
                temperature=0.3
            )

            result = json.loads(response.choices[0].message.content)

            # 逻辑兜底：确保返回了必要的字段
            if 'is_reasonable' not in result:
                result['is_reasonable'] = True  # 默认推给老师复核
            return result

        except Exception as e:
            # 异常处理：如果 AI 服务波动，默认返回一个需要人工介入的结果
            return {
                "is_reasonable": True,
                "ai_judgment": f"AI 审计服务调用失败: {str(e)}。建议手动复核。",
                "reply_for_student": "申诉已收到，系统审计服务暂时繁忙，已为您转交老师人工复核。"
            }