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
                    {"role": "system", "content": "You are a professional backend assistant. Please provide concise and accurate responses in English."},
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
            print(f"Error: AIScorer.ask interface exception: {str(e)}")
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

        # 1. Getting the source code
        if submission.sub_type == 'archive' and project_path:
            source_code = self._read_project_source(project_path)
        else:
            try:
                with open(submission.file.path, 'r', encoding='utf-8', errors='ignore') as f:
                    source_code = f.read()
            except:
                source_code = "Unable to read source code content."

        # 2. Prepare the context and Rubric configuration
        contexts = self.get_rag_contexts(submission)
        rubric_config = submission.assignment.rubric_config
        custom_dim_names = [i.get('criterion') for i in rubric_config.get('items', [])] if rubric_config.get(
            'items') else ["Logic", "Design", "Style"]

        # 3. Construct sandbox fact evidence
        if not docker_report.compile_status:
            sandbox_evidence = f"🚨 Compilation Failed: The code did not compile successfully.\nError Stack Trace:\n{docker_report.stderr}"
        else:
            sandbox_evidence = f"✅ Execution Successful:\nSTDOUT: {docker_report.stdout or 'Empty'}\nSTDERR: {docker_report.stderr or 'None'}"

        # 4. Construct the deep review Prompt
        prompt = f"""
        You are a rigorous {lang_name} programming mentor. Please evaluate the student's submission based on the provided evidence and criteria.

        ### 1. Execution Context (Facts):
        {sandbox_evidence}

        ### 2. Strict Grading Standards (Rubric - Layer 3):
        {self._build_rubric_description(rubric_config)}

        ### 3. Knowledge Point Reference (Layer 1 & 2):
        - System Specifications: {contexts['l1']}
        - Course Competencies: {contexts['l2']}

        ### 4. Student Source Code:
        {source_code}

        ### 5. Review Instructions:
        1. **Detailed Scoring (scores)**: The keys in the "scores" dictionary MUST exactly match these dimension names: {custom_dim_names}. Evaluate strictly based on the Level Rubrics provided in Layer 3.
        2. **Statistical Mapping (stats_scores)**: Map your findings into these 3 fixed system metrics (0-100):
            - Logic: Correctness, functional completeness, and execution facts.
            - Design: Architecture, OOP principles, and class relationships.
            - Style: Naming conventions, comments, and code cleanliness.
        3. **Knowledge Profiling (kp_scores)**: You MUST evaluate mastery levels strictly using these provided labels: {contexts['allowed_labels']}. Do not create new labels.

        Return a strictly formatted JSON object:
        {{
            "scores": {{ "Dimension Name": score }},
            "stats_scores": {{ "Logic": score, "Design": score, "Style": score }},
            "kp_scores": {{ "Knowledge Point Name": score }},
            "total_score": total_score_value,
            "feedback": "## Diagnostic \\n... ## Suggestions \\n... (Please respond in professional English)"
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
                # seed = 42
            )

            # Monitoring logs
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
            [f"- {p}" for p in assignment.reference_logic]) if assignment.reference_logic else "Standard functional implementation."
        return {'l1': l1 or "Follow standard coding conventions", 'l2': l2 or "Demonstrate mastery of course objectives.", 'l3': task_points, 'allowed_labels': allowed}