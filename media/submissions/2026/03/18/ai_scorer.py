import json
import os
import re
from openai import OpenAI
from django.db.models import Q  # 必须导入 Q 用于复杂查询
from apps.core.models import KnowledgePoint  # 导入你的知识点模型


class AIScorer:
    def __init__(self):
        # 建议将 API Key 放入环境变量或 settings 中
        self.client = OpenAI(
            api_key="sk-f532188d5dd5436a920de5b44b1f9596",
            base_url="https://api.deepseek.com"
        )

    def ask(self, prompt):
        """通用 AI 请求方法，供 ProjectAnalyzer 调用进行入口决策"""
        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"AI 决策失败: {str(e)}"

    def _read_project_source(self, project_path):
        """读取项目中所有的源码文件，支持多语言和多种编码"""
        full_source = ""
        supported_exts = ('.py', '.java', '.c', '.cpp')

        for root, _, files in os.walk(project_path):
            for f in files:
                if f.endswith(supported_exts):
                    path = os.path.join(root, f)
                    rel_path = os.path.relpath(path, project_path)
                    content = ""
                    # 针对学生作业常用的编码进行轮询尝试
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

    def get_rag_contexts(self, submission):
        """
        核心 RAG 逻辑：从数据库模型中提取三层知识背景
        """
        assignment = submission.assignment

        # 1. Layer 3 (题目要点)：从 Assignment 模型的 reference_logic 字段提取
        # 对应你在 Admin 后台填写的 JSON 列表
        task_points = ""
        if assignment.reference_logic and isinstance(assignment.reference_logic, list):
            task_points = "\n".join([f"- {point}" for point in assignment.reference_logic])
        else:
            task_points = str(assignment.reference_logic or "按照常规编程逻辑实现评分")

        # 2. Layer 1 & 2 (行业规范与课程目标)：从 KnowledgePoint 表提取
        # 自动匹配当前课程的知识点或系统全局知识点
        is_java = submission.file.name.endswith(('.java', '.zip'))
        lang_filter = 'java' if is_java else 'python'

        kp_list = KnowledgePoint.objects.filter(
            Q(course=assignment.course) | Q(is_system=True),
            language__icontains=lang_filter
        )
        kp_context = "\n".join([f"· {kp.category}: {kp.name}" for kp in kp_list])

        return {
            'global': "遵循工业级封装原则、命名规范及资源管理要求" if is_java else "遵循 PEP 8 及 Python 惯用法",
            'course': kp_context if kp_context else "掌握核心语法与面向对象设计",
            'task': task_points
        }

    def evaluate_code(self, submission, docker_report, project_path=None):
        """执行最终的 AI 评分与反馈生成"""
        is_java = submission.file.name.endswith(('.java', '.zip'))
        lang_name = "Java" if is_java else "Python"

        # 获取全量源码
        if submission.sub_type == 'archive' and project_path:
            source_code = self._read_project_source(project_path)
        else:
            # 单文件读取逻辑
            try:
                with open(submission.file.path, 'r', encoding='utf-8', errors='ignore') as f:
                    source_code = f.read()
            except:
                source_code = "无法读取源代码"

        # 检索 RAG 背景
        contexts = self.get_rag_contexts(submission)

        # 组装执行日志
        execution_log = f"STDOUT:\n{docker_report.stdout}\nSTDERR:\n{docker_report.stderr}"

        # 语言特定的辅助指令
        lang_hint = ""
        if is_java:
            lang_hint = "重点评审：Interface 实现、LinkedList/Queue 应用、Comparator 排序逻辑、属性私有化。"
        else:
            lang_hint = "重点评审：异常处理规范、PEP8 风格、函数/类设计合理性。"

        # 构造专家级 Prompt
        prompt = f"""
        你是一名资深的 {lang_name} 教学专家。请根据以下维度对学生代码进行深度评审：

        ### 1. 评分依据（RAG 知识库）：
        - 【题目考点 (L3)】：{contexts['task']}
        - 【课程目标 (L2)】：{contexts['course']}
        - 【行业规范 (L1)】：{contexts['global']}

        ### 2. 执行实况：
        - 【运行日志】：{execution_log}

        ### 3. 学生提交的源码：
        {source_code}

        ### 4. 评审任务：
        {lang_hint}
        请指出代码中的亮点、对标 L3 考点指出漏项、提供针对性的启发式改进建议。

        ### 必须返回的 JSON 格式：
        {{
            "scores": {{ "逻辑实现": 分数, "面向对象/设计": 分数, "编码规范": 分数 }},
            "total_score": 总分,
            "feedback": "Markdown 格式的反馈内容"
        }}
        """

        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "你是一个严谨的编程导师，只输出结构化的 JSON 数据。"},
                    {"role": "user", "content": prompt}
                ],                response_format={'type': 'json_object'}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            return {
                "scores": {},
                "total_score": 0,
                "feedback": f"AI 评审过程中发生错误: {str(e)}"
            }