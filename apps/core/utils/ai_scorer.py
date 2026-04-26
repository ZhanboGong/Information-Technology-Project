import json
import os
import time
from openai import OpenAI
from dotenv import load_dotenv
from django.db.models import Q
from apps.core.models import KnowledgePoint, SystemConfiguration
from apps.analytics.models import AIServiceLog

# Loading environment variables
load_dotenv()


class AIScorer:
    """
    Intelligent Code Review Engine Based on DeepSeek Large Model.

    核心理念：评价对齐教学。
    通过动态注入老师在数据库中预设的三层知识维度，结合 Docker 沙箱运行事实，
    实现对学生代码的精准、客观评价。
    """

    def __init__(self):
        # 初始化留空，利用下面的 @property 实现配置热更新
        pass

    @property
    def config(self):
        return SystemConfiguration.get_config()

    @property
    def model(self):
        return self.config.deepseek_model_name

    @property
    def api_key(self):
        return self.config.deepseek_api_key

    @property
    def base_url(self):
        return self.config.deepseek_base_url

    @property
    def client(self):
        return OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

    def ask(self, prompt):
        """
        通用 AI 问答接口，用于辅助任务（如入口识别、结构分析）。
        内置流量监控日志。
        """
        if not self.api_key:
            raise ValueError("API Key is missing in System Configuration.")
        start_time = time.time()
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0,
                top_p=0.1,
                messages=[
                    {"role": "system",
                     "content": "You are a professional backend assistant. Please provide concise and accurate responses in English."},
                    {"role": "user", "content": prompt}
                ]
            )

            duration = time.time() - start_time
            if response.usage:
                AIServiceLog.objects.create(
                    service_name='deepseek',
                    endpoint='chat.completions/ask',
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens,
                    response_time=duration,
                    status_code=200
                )

            return response.choices[0].message.content
        except Exception as e:
            duration = time.time() - start_time
            AIServiceLog.objects.create(
                service_name='deepseek', endpoint='chat.completions/ask',
                response_time=duration, status_code=500
            )
            print(f"Error: AIScorer.ask interface exception: {str(e)}")
            return ""

    def _read_project_source(self, project_path):
        """
        深度扫描项目源码，支持多编码感知读取。
        """
        full_source = ""
        supported_exts = ('.py', '.java', '.c', '.cpp')
        for root, _, files in os.walk(project_path):
            for f in files:
                if f.endswith(supported_exts):
                    path = os.path.join(root, f)
                    rel_path = os.path.relpath(path, project_path)
                    content = ""
                    for enc in ['utf-8', 'gbk', 'latin-1']:
                        try:
                            with open(path, 'r', encoding=enc) as file:
                                content = file.read()
                            break
                        except:
                            continue
                    if content:
                        lang = "java" if f.endswith('.java') else "python"
                        full_source += f"\n\n### FILE: {rel_path} ###\n```{lang}\n{content}\n```"
        return full_source

    def _build_rubric_description(self, rubric_config):
        """
        将 Layer 3 动态评分量表解析为 Markdown 指令。
        """
        if not rubric_config or 'items' not in rubric_config:
            return "Grade based on general programming best practices and clean code standards."

        text = "### Strict Grading Standards and Level Rubrics (Layer 3):\n"
        for item in rubric_config.get('items', []):
            name = item.get('criterion', 'Unnamed Dimension')
            weight = item.get('weight', 0)
            text += f"\n- Dimension: {name} (Weight: {weight}%)\n"
            detailed = item.get('detailed_rubric')
            if detailed and isinstance(detailed, dict) and any(detailed.values()):
                for level, desc in detailed.items():
                    if desc: text += f"  * {level}: {desc}\n"
            else:
                text += f"  Requirement: {item.get('description', '')}\n"
        return text

    def evaluate_code(self, submission, docker_report, project_path=None):
        """
        核心评价流水线：将执行事实转化为语义评估。
        """
        is_java = submission.file.name.endswith(('.java', '.zip'))
        lang_name = "Java" if is_java else "Python"

        # 1. 获取源码
        if submission.sub_type == 'archive' and project_path:
            source_code = self._read_project_source(project_path)
        else:
            try:
                with open(submission.file.path, 'r', encoding='utf-8', errors='ignore') as f:
                    source_code = f.read()
            except:
                source_code = "Unable to read source code content."

        # 2. 准备精准上下文与量表配置
        contexts = self.get_rag_contexts(submission)
        rubric_config = submission.assignment.rubric_config
        custom_dim_names = [i.get('criterion') for i in rubric_config.get('items', [])] if rubric_config.get(
            'items') else ["Logic", "Design", "Style"]

        # 3. 构造沙箱事实证据
        if not docker_report.compile_status:
            sandbox_evidence = f"🚨 Compilation Failed: The code did not compile successfully.\nError Stack Trace:\n{docker_report.stderr}"
        else:
            sandbox_evidence = f"✅ Execution Successful:\nSTDOUT: {docker_report.stdout or 'Empty'}\nSTDERR: {docker_report.stderr or 'None'}"

        # 4. 构造深度评论 Prompt
        # 核心逻辑：强制 AI 在 kp_scores 中使用我们提供的标签
            # 4. 增强版深度评论 Prompt
            prompt = f"""
                You are a senior Software Engineering Mentor and Programming Instructor. 
                Your goal is to provide a "Diagnostic and Growth-Oriented" feedback report for the student.
                
                ### TARGET LENGTH: 
                Your total feedback should be approximately 600-800 words, designed to perfectly fit one A4 page of technical documentation.

                ### 1. Execution Context (Facts):
                {sandbox_evidence}

                ### 2. Strict Grading Standards (Rubric - Layer 3):
                {self._build_rubric_description(rubric_config)}

                ### 3. Knowledge Point Reference (Layer 1 & 2):
                {contexts['l1']}
                {contexts['l2']}

                ### 4. Student Source Code:
                {source_code}

                ### 5. Review Instructions (FOR FEEDBACK):
                Your "feedback" field MUST be written in professional Markdown and include the following sections:
                - ## 🎯 Executive Summary: A 2-sentence overview of the submission quality.
                - ## 🔍 Execution Analysis: Explain the sandbox results. Why did it pass or fail? Link it to specific lines of code.
                - ## 💡 Logic & Design Deep-Dive: 
                    - Analyze the use of {contexts['allowed_labels']}. 
                    - Did the student follow OOP principles or the required logic ({contexts['l3']})?
                - ## 🛠️ Refactoring Suggestions: Provide 2-3 specific "Before vs After" logic improvements (use text descriptions or pseudocode snippets).
                - ## 🌟 Best Practices: Mention one professional industry standard the student should aim for next.

                ### 6. Scoring Constraints:
                1. **Detailed Scoring (scores)**: Keys MUST match: {custom_dim_names}.
                2. **Statistical Mapping (stats_scores)**: Logic, Design, Style (0-100).
                3. **Knowledge Profiling (kp_scores)**: Evaluate ONLY: {contexts['allowed_labels']}. Keys must match exactly.

                Return a strictly formatted JSON object:
                {{
                    "scores": {{ ... }},
                    "stats_scores": {{ ... }},
                    "kp_scores": {{ ... }},
                    "total_score": value,
                    "feedback": "...(Detailed Markdown Content)..."
                }}
                """

        start_time = time.time()
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system",
                     "content": "You are a rigorous programming mentor. Output ONLY structured JSON data. All evaluation and feedback MUST be in English."},
                    {"role": "user", "content": prompt}
                ],
                response_format={'type': 'json_object'},
                temperature=0,
                top_p=0.1
            )

            duration = time.time() - start_time
            if response.usage:
                AIServiceLog.objects.create(
                    service_name='deepseek', endpoint='chat.completions/evaluate',
                    prompt_tokens=response.usage.prompt_tokens, completion_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens, response_time=duration, status_code=200
                )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            duration = time.time() - start_time
            AIServiceLog.objects.create(service_name='deepseek', endpoint='chat.completions/evaluate',
                                        response_time=duration, status_code=500)
            raise Exception(f"AI Evaluation Engine communication failed: {str(e)}")

    def get_rag_contexts(self, submission):
        """
        精准上下文提取逻辑：实现作业级评价闭环。
        """
        assignment = submission.assignment

        # 直接获取老师为这个具体作业勾选的 Knowledge Points 关联记录
        assigned_kps = assignment.knowledge_points.all()

        l1, l2, allowed = "", "", []
        for kp in assigned_kps:
            allowed.append(kp.name)
            detail = f"· {kp.name}: {kp.description}\n"
            # 根据模型中的 is_system 属性自动归类
            if kp.is_system:
                l1 += detail
            else:
                l2 += detail

        # 任务特定逻辑点 (L3)
        task_points = "\n".join(
            [f"- {p}" for p in assignment.reference_logic]
        ) if assignment.reference_logic else "Standard functional implementation."

        return {
            'l1': l1 or "Follow standard coding conventions",
            'l2': l2 or "Demonstrate mastery of course objectives.",
            'l3': task_points,
            'allowed_labels': allowed
        }
