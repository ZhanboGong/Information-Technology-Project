import os
import zipfile
import re


class ProjectAnalyzer:
    def __init__(self, ai_client=None):
        self.ai_client = ai_client

    def unzip_project(self, zip_path, extract_path):
        """核心修复：解压项目到指定目录"""
        if not os.path.exists(extract_path):
            os.makedirs(extract_path, exist_ok=True)
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_path)
            print(f"✅ 解压完成: {extract_path}")
        except Exception as e:
            print(f"❌ 解压失败: {str(e)}")
            raise e

    def heuristic_detect(self, project_path):
        """算法阶段：基于规则识别所有潜在入口"""
        candidates = []
        py_entry_patterns = [r'if\s+__name__\s*==\s*["\']__main__["\']\s*:']
        java_main_pattern = r'public\s+static\s+void\s+main\s*\('

        for root, _, files in os.walk(project_path):
            for file in files:
                path = os.path.join(root, file)
                rel_path = os.path.relpath(path, project_path).replace("\\", "/")

                # Python 识别
                if file.endswith('.py'):
                    try:
                        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            if any(re.search(p, content) for p in py_entry_patterns):
                                candidates.append(rel_path)
                    except:
                        pass

                # Java 识别
                elif file.endswith('.java'):
                    try:
                        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            if re.search(java_main_pattern, content):
                                candidates.append(rel_path)
                    except:
                        pass
        return list(set(candidates))

    def ai_assist_detect(self, project_path, candidates, task_context=None):
        """AI 阶段：识别干扰项，锁定真业务入口"""
        if not self.ai_client:
            return candidates[0] if candidates else None

        # 🚀 增强：读取每个候选入口的前 30 行代码，让 AI 判断“含金量”
        candidate_snippets = ""
        for path in candidates[:5]:  # 最多分析 5 个候选者
            try:
                full_path = os.path.join(project_path, path)
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()[:30]
                    snippet = "".join(lines)
                    candidate_snippets += f"\n--- FILE: {path} ---\n{snippet}\n"
            except:
                continue

        prompt = f"""
        你是一个项目分析专家。当前项目中发现了多个入口点（main 方法），请通过语义分析找出“真正的业务逻辑入口”。

        【题目要求背景】：
        {task_context}

        【候选文件内容预览】：
        {candidate_snippets}

        判定准则：
        1. 排除简单的测试、Demo 或仅包含 'Hello World' 的演示文件（如 Main.java 中仅有打印欢迎语）。
        2. 寻找与题目背景（如：Person, Ride, Employee 管理系统）强关联的文件。
        3. 必须返回候选列表中的一个路径，不要输出其他废话。

        直接返回路径：
        """
        response = self.ai_client.ask(prompt).strip()
        # 再次清理路径，防止 AI 话多
        clean_path = response.replace('`', '').split('\n')[0].strip()
        return clean_path

    def get_entry_point(self, project_path, task_context=None):
        """对外接口：先扫描，若有干扰则让 AI 决策"""
        candidates = self.heuristic_detect(project_path)

        if not candidates:
            return None

        # 🚀 即使只有一个入口，如果名字叫 Main.java，也建议让 AI 走一下决策，
        # 因为它可能只是个脚手架文件，真正的入口可能没被正则扫到。
        # 但为了效率，如果候选者 > 1，强制执行 AI 语义分析。
        if len(candidates) == 1 and "Main.java" not in candidates[0]:
            return candidates[0]

        return self.ai_assist_detect(project_path, candidates, task_context)