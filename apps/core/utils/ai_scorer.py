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

    This class integrates the RAG architecture and is responsible for extracting multiple layers of knowledge (Layer 1/2) and job logic (Layer 3) from the database.
    Combined with the running facts of Docker sandbox, the big model is driven to analyze and score the code submitted by students in multi-dimensional semantics.

    Key features:
        1. Automated rating and feedback generation (JSON structured output).
        2. Deep reading of project source code and identification of multiple codes.
        3. AI service invocation monitoring and Token consumption auditing.
    """
    def __init__(self):
        """
        Initialize the DeepSeek client.
        Read the API Key and Base URL from the environment variable.
        """
        config = SystemConfiguration.get_config()
        self.api_key = config.deepseek_api_key
        self.base_url = config.deepseek_base_url
        self.model = config.deepseek_model_name

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

    def ask(self, prompt):
        """
        A General AI Question Answering Interface.

        It is used to perform auxiliary tasks of non-evaluation classification, such as item structure analysis, main entry location, etc.
        Built-in AIServiceLog monitoring to record request time and Token consumption.
        :param prompt: Text of instructions sent to the AI
        :return: The text returned by AI, or an empty string in the case of an exception.
        """
        if not self.api_key:
            raise ValueError("")
        start_time = time.time()
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0,
                top_p=0.1,
                messages=[
                    {"role": "system", "content": "你是一个专业的后端助手，请根据要求给出简短、准确的回答。"},
                    {"role": "user", "content": prompt}
                ]
            )

            # 流量监控日志
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
            print(f"Error: AIScorer.ask 接口异常: {str(e)}")
            return ""

    def _read_project_source(self, project_path):
        """
        Dive into the project source code.

        Recursively iterate through the project directory to identify supported programming language suffixes (Python/Java/C/C++)
        And try to read the file content through utf-8, gbk and other encoding formats to be compatible with the source code of different operating systems.
        :param project_path: Path to the temporary workspace after the project is unzipped
        :return: Concatenated Markdown formatted source text
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
        Parse the Layer 3 dynamic scoring configuration to generate detailed instructions for the AI to read.

        This method converts the JSON scoring criteria stored in the database into Markdown format instruction text.
        It supports nested parsing of "dimension weights" and "level descriptions (F-HD level specification)".

        Logical flow:
            1. Config validation: If there is no config, return a general convention recommendation.
            2. Iterate over dimensions: Extract each rating dimension (e.g. "feature implementation", "code style") and its proportion.
            3. The level of resolution: if any details of the grade rules (Fail/Pass/Credit/Distinction/High Distinction),
                Then it is expanded as an accurate scale for AI scoring.
        :param rubric_config: A rating configuration dictionary containing a list of 'items'.
        :return: The formatted Markdown string is injected as the core of Prompt.
        """
        if not rubric_config or 'items' not in rubric_config:
            return "根据通用编程规范评分。"

        text = "### 严格评分标准与等级细则 (Layer 3)：\n"
        for item in rubric_config.get('items', []):
            name = item.get('criterion', '未命名维度')
            weight = item.get('weight', 0)
            text += f"\n- 维度: {name} (权重: {weight}%)\n"
            detailed = item.get('detailed_rubric')
            if detailed and isinstance(detailed, dict) and any(detailed.values()):
                for level, desc in detailed.items():
                    if desc: text += f"  * {level}: {desc}\n"
            else:
                text += f"  要求: {item.get('description', '')}\n"
        return text

    def evaluate_code(self, submission, docker_report, project_path=None):
        """
        Core scoring pipeline: Realizing the transformation from "factual evidence" to "semantic evaluation".

        Process:
        1. Evidence collection: Integrate the source code with the build/run output of the Docker sandbox.
        Metrics alignment: Dynamically parse rating dimensions from job configuration (Layer 3).
        3. Prompt word project: construct a deep PROMPT with three levels of evaluation criteria (system specification, course ability and assignment logic).
        4. Result Normalization: The AI is required to output JSON containing detailed dimension scores, system statistics scores (Logic/Design/Style), and knowledge mastery.
        :param submission: Submission model instance.
        :param docker_report: Corresponding DockerReport instance.
        :param project_path: Multi-file project path.
        :return: Structured JSON data returned by the AI
        """
        is_java = submission.file.name.endswith(('.java', '.zip'))
        lang_name = "Java" if is_java else "Python"

        # 1. 获取源代码
        if submission.sub_type == 'archive' and project_path:
            source_code = self._read_project_source(project_path)
        else:
            try:
                with open(submission.file.path, 'r', encoding='utf-8', errors='ignore') as f:
                    source_code = f.read()
            except:
                source_code = "无法读取源代码内容"

        # 2. 准备上下文与 Rubric 配置
        contexts = self.get_rag_contexts(submission)
        rubric_config = submission.assignment.rubric_config
        custom_dim_names = [i.get('criterion') for i in rubric_config.get('items', [])] if rubric_config.get(
            'items') else ["Logic", "Design", "Style"]

        # 3. 构造沙箱事实证据
        if not docker_report.compile_status:
            sandbox_evidence = f"🚨 编译失败：代码未能通过编译。\n错误堆栈：\n{docker_report.stderr}"
        else:
            sandbox_evidence = f"✅ 编译成功，运行输出如下：\nSTDOUT: {docker_report.stdout or '空'}\nSTDERR: {docker_report.stderr or '无'}"

        # 4. 构造深度评审 Prompt
        prompt = f"""
        你是一名严谨的 {lang_name} 编程导师。请对学生的作业进行评审。

        ### 1. 运行事实背景：
        {sandbox_evidence}

        ### 2. 严格评分标准 (Layer 3 - 核心依据)：
        {self._build_rubric_description(rubric_config)}

        ### 3. 辅助参考考点 (Layer 1 & 2)：
        - 系统规范: {contexts['l1']}
        - 课程能力: {contexts['l2']}

        ### 4. 学生源码内容：
        {source_code}

        ### 5. 评审核心指令：
        1. **详细评分 (scores)**：返回 JSON 的 "scores" 字典中，Key 必须完全匹配老师定义的维度列表: {custom_dim_names}。必须严格参考 Layer 3 中的 F-HD 等级细则进行判定。
        2. **统计映射 (stats_scores)**：为了系统统计，请务必将上述评审结果映射归类到以下 3 个固定指标 (0-100分)：
           - Logic: 业务逻辑正确性、功能完成度、编译事实。
           - Design: 架构设计、OOP 原则应用、类关系。
           - Style: 命名规范、注释、代码整洁度。
        3. **知识点画像 (kp_scores)**：必须严格匹配以下列表评估掌握度: {contexts['allowed_labels']}。

        请严格返回以下格式的 JSON：
        {{
            "scores": {{ "维度名": 分数 }},
            "stats_scores": {{ "Logic": 分数, "Design": 分数, "Style": 分数 }},
            "kp_scores": {{ "知识点名": 分数 }},
            "total_score": 总分,
            "feedback": "## 运行诊断 \\n... ## 逻辑建议 \\n... (使用中文回复)"
        }}
        """

        start_time = time.time()
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system",
                     "content": "你是一个严谨的编程评审导师，只输出结构化的 JSON 数据。所有评价使用中文。"},
                    {"role": "user", "content": prompt}
                ],
                response_format={'type': 'json_object'},
                temperature=0,
                top_p=0.1
                # seed = 42
            )

            # 监控日志
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
            raise Exception(f"AI 评审引擎通信失败: {str(e)}")

    def get_rag_contexts(self, submission):
        """
        Silent RAG retrieval logic.

        Based on the course and programming language of the current assignment, relevant entries are dynamically retrieved from the knowledge point base:
            - L1 (System Level): General programming best practices
            - L2 (Course Level): the technical points of the current key assessment of the course.
            -L3 (Task Level): The specific business logic requirements defined by the teacher in the assignment.
        :param submission:
        :return: Contains three layers of context description and a list of allowed knowledge point labels.
        """
        assignment = submission.assignment
        is_java = submission.file.name.endswith(('.java', '.zip'))
        lang_filter = 'java' if is_java else 'python'
        kp_query = KnowledgePoint.objects.filter(Q(is_system=True) | Q(course=assignment.course),
                                                 language__icontains=lang_filter)
        l1, l2, allowed = "", "", []
        for kp in kp_query:
            allowed.append(kp.name)
            detail = f"· {kp.name}: {kp.description}\n"
            if kp.is_system:
                l1 += detail
            else:
                l2 += detail
        task_points = "\n".join(
            [f"- {p}" for p in assignment.reference_logic]) if assignment.reference_logic else "常规业务实现"
        return {'l1': l1 or "遵循标准规范", 'l2': l2 or "掌握课程目标", 'l3': task_points, 'allowed_labels': allowed}