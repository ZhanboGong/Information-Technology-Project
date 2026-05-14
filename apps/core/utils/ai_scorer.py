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
        # Leave the initialization blank and use @property below to implement hot configuration updates
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

    def evaluate_code(self, submission, docker_report, project_path=None, static_report=None, review_context=None):
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

        # 3.5 静态分析报告
        if static_report and 'error' not in static_report:
            summary = static_report.get('summary', static_report)
            cc = summary.get('cyclomatic_complexity', {})
            static_evidence = (
                f"### Static Code Analysis (Objective Metrics):\n"
                f"- Total Lines of Code: {summary.get('total_loc', summary.get('sloc', 'N/A'))}\n"
                f"- Cyclomatic Complexity: avg={cc.get('average', 'N/A')}, max={cc.get('max', 'N/A')}\n"
                f"- Maintainability Index: {summary.get('maintainability_index', 'N/A')}/100\n"
                f"- Function/Method Count: {summary.get('function_count', summary.get('method_count', 'N/A'))}\n"
                f"- Comment Ratio: {summary.get('comment_ratio', 'N/A')}%\n"
            )
        else:
            static_evidence = "### Static Code Analysis: Not available"

        # 3.6 接口合规检测（仅 Java 项目）
        if is_java and project_path:
            from apps.core.utils.static_analyzer import StaticAnalyzer
            compliance = StaticAnalyzer.check_interface_compliance(project_path)
            if compliance['issues']:
                compliance_evidence = (
                    f"### ⚠️ Structural Compliance Issues (CRITICAL):\n"
                    f"The following required features are MISSING from the student's code:\n"
                    + "\n".join(f"- ❌ {issue}" for issue in compliance['issues'])
                    + "\nThese are REQUIREMENT GAPS, not style issues. Score affected dimensions accordingly.\n"
                )
            else:
                compliance_evidence = "### Structural Compliance: All interfaces and methods implemented correctly."
        else:
            compliance_evidence = ""

        # 4. 构造深度评论 Prompt
        # 核心逻辑：强制 AI 在 kp_scores 中使用我们提供的标签
            # 4. 增强版深度评论 Prompt
        prompt = f"""
                You are a university programming instructor performing a fair and comprehensive assessment.
                Your goal is to provide a balanced evaluation that accurately reflects the student's demonstrated competence.
                
                ### TARGET LENGTH: 
                Your total feedback should be approximately 600-800 words, designed to perfectly fit one A4 page of technical documentation.
                
                ### 0. Assignment Requirements (CRITICAL - You MUST check every item):
                {submission.assignment.content or "No specific requirements provided."}

                ### 1. Execution Context (Facts):
                {sandbox_evidence}
                
                {static_evidence}
                
                {compliance_evidence}
                ### 2. Strict Grading Standards (Rubric - Layer 3):
                {self._build_rubric_description(rubric_config)}

                ### 3. Knowledge Point Reference (Layer 1 & 2):
                {contexts['l1']}
                {contexts['l2']}

                ### 4. Student Source Code:
                {source_code}
                
                ### 5. ANALYSIS PROCESS (think step by step before scoring):
                Before outputting the final JSON, evaluate in order:
                Step 0 - Requirement Completion Check (MANDATORY):
                You have TWO independent sources of requirements. Check BOTH carefully.

                **Source A — Explicit Requirements (Section 0):**
                From the Assignment Requirements text, extract EVERY specific task, feature, or deliverable.
                For each, compare against the Student Source Code (Section 4) and mark:
                  ✅ FULLY IMPLEMENTED — feature is CORRECT, COMPLETE, and handles normal and edge cases
                  ❌ NOT IMPLEMENTED — feature is completely missing
                  ⚠️ PARTIALLY IMPLEMENTED — feature exists but is buggy, incomplete, or misses key logic

                CRITICAL DISTINCTION — "PARTIALLY" vs "FULLY":
                - If the code has a relevant function/class/method but the logic is flawed, mark ⚠️ PARTIALLY
                - If the code mentions the concept but doesn't actually solve the problem, mark ⚠️ PARTIALLY  
                - Only mark ✅ FULLY if you would give this feature at least a C-grade (65+) if graded in isolation

                Source A implemented count = (count of ✅) + (count of ⚠️ × 0.5)

                **Source B — Rubric Minimum Requirements (Section 2):**
                Each dimension in the rubric has a P-level (Pass) description defining its MINIMUM standard.
                For EACH rubric dimension, read its P-level description and determine:
                  ✅ MEETS EXPECTATION — student's work satisfies at least the C-level (Credit) description in the rubric
                  ❌ BELOW EXPECTATION — work only reaches P-level or below
                
                IMPORTANT: P-level means "barely passable." Only count a dimension as ✅ if the student 
                demonstrates competence beyond the bare minimum — at least C-level. 
                If the work only scrapes by at P-level, mark ❌.
                Source B implemented count = count of ✅

                **Combined Completion Rate:**
                = (Source A implemented count + Source B implemented count)
                  / (Source A total tasks + Source B total dimensions)
                  × 100%

                This combined rate captures both "did they do what was asked" (text requirements) 
                AND "does each quality dimension demonstrate competence beyond bare minimum" (rubric C-level+).

                IMPORTANT: Do NOT apply any score caps yourself. Simply report the completion_rate 
                as a 0-100 integer. The scoring system applies caps automatically.
                Step 1 - Compilation: Did the code compile? If not, identify the error and the line that caused it.
                Step 2 - Execution: If compiled, did it run correctly? Analyze stdout/stderr for correctness.
                Step 3 - Structure: Count functions/classes. Assess naming conventions, indentation, organization.
                Step 4 - Knowledge Points: For each of {contexts['allowed_labels']}, did the student demonstrate it? Score 0-100.
                Step 5 - Rubric Alignment: For each dimension in {custom_dim_names}, evaluate against the detailed rubric above.
                Step 6 - Final Score: Calculate weighted total based on rubric weights.

                ### 6. Review Instructions (FOR FEEDBACK):
                Your "feedback" field MUST be written in professional Markdown and include the following sections:
                - ## Executive Summary: A 2-sentence overview of the submission quality.
                - ## Execution Analysis: Explain the sandbox results. Why did it pass or fail? Link it to specific lines of code.
                - ## Logic & Design Deep-Dive: 
                    - Analyze the use of {contexts['allowed_labels']}. 
                    - Did the student follow OOP principles or the required logic ({contexts['l3']})?
                - ## Refactoring Suggestions: Provide 2-3 specific "Before vs After" logic improvements (use text descriptions or pseudocode snippets).
                - ## Best Practices: Mention one professional industry standard the student should aim for next.

                ### 7. Scoring Constraints:
                1. **Detailed Scoring (scores)**: Keys MUST match: {custom_dim_names}.
                2. **Statistical Mapping (stats_scores)**: Logic, Design, Style (0-100).
                3. **Knowledge Profiling (kp_scores)**: Evaluate ONLY: {contexts['allowed_labels']}. Keys must match exactly.

                Return a strictly formatted JSON object:
                {{
                    "completion_rate": integer (0-100, from Step 0 analysis),
                    "scores": {{ ... }},
                    "stats_scores": {{ ... }},
                    "kp_scores": {{ ... }},
                    "total_score": value (one decimal, e.g. 85.9),
                    "feedback": "...(Detailed Markdown Content)..."
                }}
                
                ### 8. OUTPUT FORMAT EXAMPLE:
                Here is a correctly formatted response:
                
                {{
                    "scores": {{
                        "Object-Oriented Programming (Parts 1-2)": 87.5,
                        "Collections Management (Parts 3-5)": 82.0,
                        "I/O Mechanism (Parts 6-7)": 78.5,
                        "Accuracy & Efficiency": 85.0,
                        "Concept Understanding": 90.0
                    }},
                    "stats_scores": {{
                        "Logic": 87.0,
                        "Design": 82.5,
                        "Style": 85.0
                    }},
                    "kp_scores": {{
                        "Interface Implementation": 90.0,
                        "Class Inheritance and Polymorphism": 88.0,
                        "Collections Framework (LinkedList, Comparator)": 82.0,
                        "File I/O and Exception Handling": 76.0,
                        "Data Encapsulation and Validation": 85.5
                    }},
                    "total_score": 85.5,
                    "feedback": "## Executive Summary\\nThis submission demonstrates solid OOP understanding...\\n\\n## Execution Analysis\\nThe program executed successfully...\\n\\n## Logic & Design Deep-Dive\\n**Interface Implementation**: The Ride class fully implements RideInterface... (Score: 90)\\n**Class Inheritance and Polymorphism**: Excellent use of abstract class Person... (Score: 90)\\n\\n## Refactoring Suggestions\\n### 1. Fix checkVisitorFromHistory...\\n**Before:** ...\\n**After:** ...\\n\\n## Best Practices\\nConsider using dependency injection for file paths..."
                }}

                IMPORTANT RULES:
                - scores keys MUST be exactly: {custom_dim_names}  (teacher's rubric dimensions)
                - kp_scores keys MUST be exactly: {contexts['allowed_labels']}  (knowledge points)
                - stats_scores keys are always: Logic, Design, Style
                - total_score MUST be a number with one decimal place (e.g. 85.9, not 86)
                - total_score MUST be calculated from the weighted average of scores dimensions, NOT copied from any example
                - completion_rate MUST be an integer (0-100) reflecting actual requirement completion from Step 0
                - All feedback MUST be in English
                """
        if review_context:
            issues_text = "\n".join(f"- {i}" for i in review_context.get('issues', []))
            suggestion_text = review_context.get('suggestion', '')
            review_block = f"""

                        ### ⚠️ QUALITY REVIEW: The previous scoring attempt was flagged for the following issues:
                        {issues_text}

                        Review Instruction: {suggestion_text}
                        Please re-evaluate carefully and correct the inconsistencies.
                        """
            prompt += review_block

        start_time = time.time()
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system",
                     "content": """You are a senior university programming instructor. Output ONLY structured JSON data. All evaluation and feedback MUST be in English.

                    SCORING METHOD — THIS IS THE MOST IMPORTANT RULE:
                    Score each rubric dimension by matching the student's work against the teacher's rubric levels 
                    provided in Section 2 (HD / D / C / P / F descriptions).
                    
                    For EACH dimension:
                    1. Read the rubric level descriptions (HD, D, C, P, F) provided by the teacher.
                    2. Determine which level best describes the student's work.
                    3. Assign a score within that level's range:
                       - Clearly meets HD criteria → 85-100
                       - Clearly meets D criteria → 75-84
                       - Clearly meets C criteria → 65-74
                       - Clearly meets P criteria → 50-64
                       - Does not meet P criteria → below 50
                    4. If the student's work is between two levels, score at the higher level's lower bound.
                    
                    CORE PRINCIPLES:
                    1. YOUR SCORE MUST TRACE TO THE RUBRIC: Every number you give must match a specific rubric level. If you cannot justify it from the rubric, you scored wrong.
                    2. DO NOT INVENT YOUR OWN CRITERIA: Do not deduct points for things not in the rubric (e.g., missing comments if rubric doesn't mention comments).
                    
                    Output ONLY a valid JSON object. No text outside the JSON."""},

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

            raw = response.choices[0].message.content
            result = json.loads(raw)

            result.setdefault('scores', {})
            result.setdefault('stats_scores', {"Logic": 0, "Design": 0, "Style": 0})
            result.setdefault('kp_scores', {})
            result.setdefault('feedback', "AI evaluation did not generate feedback.")


            # --- Step 0: 完成度强制封顶（确定性规则）---
            completion_rate = result.get('completion_rate', 100)
            try:
                completion_rate = int(completion_rate)
            except (ValueError, TypeError):
                completion_rate = 100
                # --- 交叉修正：KP 均分低于 80 时，按比例校正完成度虚高 ---
            kp_values = [float(v) for v in result.get('kp_scores', {}).values() if v is not None]
            if kp_values:
                kp_avg = sum(kp_values) / len(kp_values)
                if kp_avg < 80:
                    penalty = kp_avg / 80
                    adjusted = round(completion_rate * penalty)
                    completion_rate = min(completion_rate, adjusted)

            if completion_rate >= 85:
                score_ceiling = 100
            elif completion_rate >= 70:
                score_ceiling = 85
            elif completion_rate >= 55:
                score_ceiling = 75
            elif completion_rate >= 35:
                score_ceiling = 60
            else:
                score_ceiling = 45

            # 封顶：每个维度和总分都不能超过天花板
            result['completion_rate'] = completion_rate



            # ============================================
            # 分数计算流水线（三层联动）
            # 1. 合规检测 → 修正 KP 分数
            # 2. KP 分数 → 影响 Rubric 维度分数
            # 3. Rubric 加权 → 最终 total_score
            # ============================================
            scores_dict = result.get('scores', {})
            kp_scores = result.get('kp_scores', {})
            rubric_items = submission.assignment.rubric_config.get('items', [])

            # --- Step 1: 合规检测修正 KP 分数 ---
            if is_java and project_path:
                from apps.core.utils.static_analyzer import StaticAnalyzer
                compliance = StaticAnalyzer.check_interface_compliance(project_path)
                if compliance['issues']:
                    for issue in compliance['issues']:
                        # 未实现接口 → 相关 KP 直接压低
                        if 'No class implements' in issue or 'does NOT implement' in issue:
                            for kp_name in kp_scores:
                                if any(kw in kp_name.lower() for kw in
                                       ['interface', 'implementation', 'polymorphism']):
                                    kp_scores[kp_name] = 15.0
                        # 缺失方法 → 对应 KP 扣分
                        elif 'missing method' in issue:
                            for kp_name in kp_scores:
                                if any(kw in kp_name.lower() for kw in
                                       ['collection', 'exception', 'i/o', 'file']):
                                    kp_scores[kp_name] = min(float(kp_scores.get(kp_name, 50)), 30)
                    result['feedback'] += "\n\n---\n## ⚠️ Structural Compliance Report\n"
                    for issue in compliance['issues']:
                        result['feedback'] += f"- {issue}\n"

            # --- 灾难性缺陷检测：任一 KP < 30 直压上限 ---
            kp_values_for_check = [float(v) for v in kp_scores.values() if v is not None]
            if kp_values_for_check and min(kp_values_for_check) < 30:
                completion_rate = min(completion_rate, 54)
                score_ceiling = min(score_ceiling, 60)



            # --- Step 2: KP 分数影响 Rubric 维度分数 ---
            if kp_scores and rubric_items:
                kp_values = [float(v) for v in kp_scores.values() if v is not None]
                kp_avg = sum(kp_values) / len(kp_values) if kp_values else 70

                for item in rubric_items:
                    dim_name = item.get('criterion', '')
                    ai_score = float(scores_dict.get(dim_name, 70))
                    # 混合：70% AI 判断 + 30% KP 客观证据
                    KP_WEIGHT = 0.20
                    blended = ai_score * (1 - KP_WEIGHT) + kp_avg * KP_WEIGHT
                    scores_dict[dim_name] = round(blended, 1)

            # --- Step 3: Rubric 加权计算最终总分 ---
            if scores_dict and rubric_items:
                # 先封顶每个维度
                for item in rubric_items:
                    dim_name = item.get('criterion', '')
                    dim_score = float(scores_dict.get(dim_name, 0))
                    scores_dict[dim_name] = round(min(dim_score, score_ceiling), 1)

                # 再加权计算总分
                weighted_sum = 0
                for item in rubric_items:
                    dim_name = item.get('criterion', '')
                    weight = item.get('weight', 0) / 100.0
                    dim_score = float(scores_dict.get(dim_name, 0))
                    weighted_sum += dim_score * weight
                result['total_score'] = round(weighted_sum, 1)
                result['total_score'] = min(result['total_score'], score_ceiling)

            else:
                result['total_score'] = result.get('total_score', 0)

            return result


        except json.JSONDecodeError as e:
            duration = time.time() - start_time
            AIServiceLog.objects.create(service_name='deepseek', endpoint='chat.completions/evaluate',
                                        response_time=duration, status_code=500)
            raise Exception(f"AI returned invalid JSON: {str(e)}")

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

    def generate_learning_resources(self, assignment_title, category, feedback, kp_scores):
        """

        :param assignment_title:
        :param category:
        :param feedback:
        :param kp_scores:
        :return:
        """
        # 1. 按分数分级推荐（个性化数量）
        recommendations = []
        if isinstance(kp_scores, dict):
            for k, v in kp_scores.items():
                try:
                    score = float(v)
                except (ValueError, TypeError):
                    continue
                if score < 60:
                    recommendations.append((k, score, 3))  # 弱项：推荐 3 个
                elif score < 80:
                    recommendations.append((k, score, 1))  # 中等：推荐 1 个

        # 没有需要推荐的
        if not recommendations:
            return []

        # 按分数排序，最弱的在前，最多取 3 个
        recommendations.sort(key=lambda x: x[1])
        recommendations = recommendations[:3]

        # 2. 获取 Bloom 层级
        BLOOM_ORDER = ['remember', 'understand', 'apply', 'analyze', 'evaluate', 'create']
        kp_bloom_map = {}
        try:
            from apps.core.models import KnowledgePoint
            assigned_kps = KnowledgePoint.objects.filter(
                name__in=[r[0] for r in recommendations]
            )
            for kp in assigned_kps:
                kp_bloom_map[kp.name] = kp.bloom_level
        except Exception:
            pass

        # 3. 构造带 Bloom 层级的推荐 Prompt
        weak_details = []
        for name, score, count in recommendations:
            current_bloom = kp_bloom_map.get(name, 'apply')
            current_idx = BLOOM_ORDER.index(current_bloom) if current_bloom in BLOOM_ORDER else 2
            next_bloom = BLOOM_ORDER[min(current_idx + 1, len(BLOOM_ORDER) - 1)]
            weak_details.append(
                f"- {name} (Score: {score:.1f}, Current Level: {current_bloom}, "
                f"Target Level: {next_bloom}, Recommend: {count} resources)"
            )

        prompt = f"""
        The student has weak areas in: {category}

        {chr(10).join(weak_details)}

        For each weak area listed above, note the "Count" value — generate that many YouTube search queries targeting the "Target Level" Bloom's taxonomy tier.

        For each resource:
        1. Generate a YouTube search query for the target Bloom's level.
        2. Briefly describe what a target-level exercise looks like for this topic.

        Return a JSON array of objects, each with:
        - "topic": the weak area name
        - "query": the YouTube search query
        - "bloom_target": the target Bloom's level from the details above

        Return ONLY a JSON array.
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Output ONLY a JSON array."},
                    {"role": "user", "content": prompt}
                ],
                response_format={'type': 'json_object'},
                temperature=0
            )

            import re, json
            raw_res = response.choices[0].message.content
            clean_json = re.sub(r'```json\s?|\s?```', '', raw_res).strip()
            queries = json.loads(clean_json)

            if isinstance(queries, dict):
                for val in queries.values():
                    if isinstance(val, list):
                        queries = val
                        break

            if not isinstance(queries, list):
                return []

        except Exception as e:
            print(f"AI query generation failed: {str(e)}")
            return []

        # 3. 调用 YouTube Data API 搜索视频
        import requests as req
        YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY', '')

        # 没有 API key 时降级为 YouTube 搜索页链接
        if not YOUTUBE_API_KEY:
            return [
                {
                    "title": f"Tutorial: {q.get('topic', 'Programming')}",
                    "url": f"https://www.youtube.com/results?search_query={q.get('query', 'programming tutorial').replace(' ', '+')}",
                    "reason": f"Video tutorial for {q.get('topic', 'this topic')}",
                    "bloom_target": q.get('bloom_target', '')
                }
                for q in queries[:3]
            ]

        final_resources = []
        for q in queries[:3]:
            search_query = q.get('query', '')
            topic = q.get('topic', '')
            if not search_query:
                continue

            try:
                yt_response = req.get(
                    "https://www.googleapis.com/youtube/v3/search",
                    params={
                        "part": "snippet",
                        "q": f"{search_query} tutorial",
                        "type": "video",
                        "maxResults": 1,
                        "key": YOUTUBE_API_KEY,
                        "videoCategoryId": "28"
                    },
                    timeout=5
                )
                yt_data = yt_response.json()
                items = yt_data.get('items', [])
                if items:
                    video_id = items[0]['id']['videoId']
                    title = items[0]['snippet']['title']
                    final_resources.append({
                        "title": title,
                        "url": f"https://www.youtube.com/watch?v={video_id}",
                        "reason": f"Video tutorial for {topic}",
                        "bloom_target": q.get('bloom_target', '')
                    })
            except Exception as e:
                print(f"YouTube API error for '{search_query}': {str(e)}")
                continue

        return final_resources
