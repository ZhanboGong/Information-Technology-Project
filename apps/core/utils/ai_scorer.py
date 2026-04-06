import json
import os
import time
from openai import OpenAI
from dotenv import load_dotenv
from django.db.models import Q
from apps.core.models import KnowledgePoint
from apps.analytics.models import AIServiceLog
from .error_messages import AI_ERRORS

# Load the contents of the .env file into environment variables
load_dotenv()

class AIScorer:
    def __init__(self):
        """
        Initialize the DeepSeek client.
        Read the API Key and Base URL from an environment variable. If BASE_URL is not set,
        This will default to the official DeepSeek API.
        """
        api_key = os.getenv("DEEPSEEK_API_KEY")
        base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )

    def ask(self, prompt):
        """
        Send a conversation request to DeepSeek and get an AI reply.
        A preset System Prompt is configured to ensure that the output conforms to the role of the "back-end assistant",
        and exceptions are caught during API calls.
        :param prompt: Pre-set the question content or instruction that needs i input
        :return: Ai-generated response text.
        If an exception occurs (e.g., a network problem, authentication failure, etc.), an empty string is returned.
        """
        start_time = time.time()
        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "你是一个专业的后端助手，请根据要求给出简短、准确的回答。"},
                    {"role": "user", "content": prompt}
                ]
            )

            # 流量监控
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
            # 失败记录
            duration = time.time() - start_time
            AIServiceLog.objects.create(
                service_name='deepseek',
                endpoint='chat.completions/ask',
                response_time=duration,
                status_code=500
            )
            print(f"Error: AI 询问接口异常: {str(e)}")
            return ""

    def _read_project_source(self, project_path):
        """
        深度读取项目源码：支持多级目录遍历
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

    def evaluate_code(self, submission, docker_report, project_path=None):
        """
        🚀 核心精进逻辑：事实对齐 (Docker) + 路径走查 (AI)
        """
        is_java = submission.file.name.endswith(('.java', '.zip'))
        lang_name = "Java" if is_java else "Python"

        # 1. 获取源码内容
        if submission.sub_type == 'archive' and project_path:
            source_code = self._read_project_source(project_path)
        else:
            try:
                # 兼容处理：优先读取文件系统，失败则返回提示
                with open(submission.file.path, 'r', encoding='utf-8', errors='ignore') as f:
                    source_code = f.read()
            except:
                source_code = "无法读取源代码，请检查文件存取权限"

        # 2. 准备 RAG 知识库上下文
        contexts = self.get_rag_contexts(submission)

        # 3. 构造沙箱事实事实证据（方案一核心）
        # 区分编译失败 (compile_status=False) 和 运行时异常
        if not docker_report.compile_status:
            sandbox_evidence = f"🚨 编译失败：代码未能通过编译。\n错误堆栈：\n{docker_report.stderr}"
        else:
            sandbox_evidence = f"✅ 编译成功，运行输出如下：\nSTDOUT: {docker_report.stdout or '空'}\nSTDERR: {docker_report.stderr or '无'}"

        # 4. 构造深度评审 Prompt（方案三核心）
        prompt = f"""
        你是一名严谨的 {lang_name} 编程导师。请对学生的作业进行【沙箱事实对齐】与【源码逻辑深度走查】。

        ### 1. 运行事实背景：
        {sandbox_evidence}

        ### 2. 评审维度与考点 (RAG 知识库)：
        【L1-系统通用规范】：
        {contexts['l1']}
        【L2-课程专项能力】：
        {contexts['l2']}
        【L3-本题核心业务逻辑】：
        {contexts['l3']}

        ### 3. 学生源码内容：
        {source_code}

        ### 4. 评审核心指令：
        1. **事实对齐**：参考沙箱事实。若编译失败，请在源码中精准定位语法错误；若运行成功，核对输出是否符合预期。
        2. **逻辑走查**：这是半开放作业。即使代码运行报错或无输出，你也必须模拟执行所有逻辑路径。
        3. **宽严相济 (人道主义)**：若代码逻辑实现度高，仅因微小语法错误（如漏写分号、大小写）导致编译失败，不得判 0 分，应在 Logic 维度保留大部分得分。
        4. **知识点穿透**：严格对照 L2 知识点列表，评估掌握程度。

        注意：kp_scores 的 Key 必须严格匹配以下列表，不得自行生成：
        {contexts['allowed_labels']}

        请直接返回 JSON：
        {{
            "scores": {{ "Logic": 分数, "Design": 分数, "Style": 分数 }},
            "kp_scores": {{ "知识点名称": 分数 }},
            "total_score": 总分,
            "feedback": "## 运行诊断 \n... ## 逻辑建议 \n..."
        }}
        """
        start_time = time.time()
        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "你是一个严谨的编程导师，只输出结构化的 JSON 数据。"},
                    {"role": "user", "content": prompt}
                ],
                response_format={'type': 'json_object'}
            )

            # 流量监控
            duration = time.time() - start_time
            if response.usage:
                AIServiceLog.objects.create(
                    service_name='deepseek',
                    endpoint='chat.completions/evaluate',
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens,
                    response_time=duration,
                    status_code=200
                )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            # 失败记录
            duration = time.time() - start_time
            AIServiceLog.objects.create(
                service_name='deepseek',
                endpoint='chat.completions/evaluate',
                response_time=duration,
                status_code=500
            )
            # 异常向上抛出，由 GradingPipeline 捕获并处理状态
            raise Exception(f"AI 评审引擎通信失败: {str(e)}")

    def get_rag_contexts(self, submission):
        """
        静默 RAG 检索逻辑
        """
        assignment = submission.assignment
        is_java = submission.file.name.endswith(('.java', '.zip'))
        lang_filter = 'java' if is_java else 'python'

        # 检索系统级及本课程相关的知识点
        kp_query = KnowledgePoint.objects.filter(
            Q(is_system=True) | Q(course=assignment.course),
            language__icontains=lang_filter
        )

        l1, l2, allowed = "", "", []
        for kp in kp_query:
            allowed.append(kp.name)
            detail = f"· {kp.name}: {kp.description}\n"
            if kp.is_system:
                l1 += detail
            else:
                l2 += detail

        # 注入 Layer 3 业务逻辑
        task_points = "\n".join(
            [f"- {p}" for p in assignment.reference_logic]) if assignment.reference_logic else "常规业务实现"

        return {
            'l1': l1 or "遵循标准编码规范",
            'l2': l2 or "掌握课程核心目标",
            'l3': task_points,
            'allowed_labels': allowed
        }
