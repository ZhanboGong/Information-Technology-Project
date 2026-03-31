import os
import zipfile
import re


class ProjectAnalyzer:
    def __init__(self, ai_client=None):
        self.ai_client = ai_client

    def unzip_project(self, zip_path, extract_path):
        """
        Extract the specified ZIP archive into the destination directory.
        This method automatically checks to see if the desired directory exists and recursively creates it if not.
        If encounter a corrupted file or path during the decompression process, an exception will be caught and thrown upward.
        :param zip_path: The full path to the ZIP file to be extracted
        :param extract_path: Path to the unzipped file
        :return: No return value
        """
        if not os.path.exists(extract_path):
            os.makedirs(extract_path, exist_ok=True)
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_path)
            print(f"Unzip completed: {extract_path}")
        except Exception as e:
            print(f"Unzip failed: {str(e)}")
            raise e

    def heuristic_detect(self, project_path):
        """
        Possible program entry files are automatically identified by scanning the project directory with heuristic rules.
        This method recursively traverses the project folder and uses regular expressions to match the Python and Java startup features:
        - Python: matches the 'if __name__ == "__main__":' struct.
        - Java: matches' public static void main(String[] args) 'method signature.
        :param project_path: Path to the root of the project to scan.
        :return: list -Contains a list of relative paths to all suspected entry files
        """
        candidates = []
        # Define entry feature regularities: match standard entry judgment statements
        py_entry_patterns = [r'if\s+__name__\s*==\s*["\']__main__["\']\s*:']
        java_main_pattern = r'public\s+static\s+void\s+main\s*\('

        for root, _, files in os.walk(project_path):
            for file in files:
                path = os.path.join(root, file)
                # Get the path relative to the project root and replace the Windows backslashes uniformly with forward slashes
                rel_path = os.path.relpath(path, project_path).replace("\\", "/")

                # Entry identification logic
                if file.endswith('.py'):
                    try:
                        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            if any(re.search(p, content) for p in py_entry_patterns):
                                candidates.append(rel_path)
                    except:
                        pass

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
        """
        AI semantic analysis is used to accurately locate the core business entrance from multiple candidate entrances.
        When a heuristic scan finds multiple files containing the main method (e.g., both test class, Demo class, and business main class),
        This method reads the first 30 lines of code snippets of each candidate file and sends them to AI for intelligent judgment combined with the background context of the topic.
        :param project_path: Project root directory path
        :param candidates: List of candidate entry paths obtained by heuristic detection
        :param task_context: A background description of the current job or task that helps the AI understand the business logic
        :return:
        """
        if not self.ai_client:
            return candidates[0] if candidates else None

        # Enhancement: Read the first 30 lines of each candidate to assess "Logic Density"
        candidate_snippets = ""
        for path in candidates[:5]:  # Analyze up to 5 candidates
            try:
                full_path = os.path.join(project_path, path)
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()[:30]
                    snippet = "".join(lines)
                    candidate_snippets += f"\n--- FILE: {path} ---\n{snippet}\n"
            except:
                continue

        prompt = f"""
        You are a Software Architect. Multiple entry points (main methods) have been detected in the project. 
        Your task is to identify the "Real Business Logic Entry Point" via semantic analysis.

        [Task Context & Requirements]:
        {task_context}

        [Candidate File Snippets]:
        {candidate_snippets}

        [Decision Criteria]:
        1. EXCLUDE simple test cases, demos, or "Hello World" style boilerplate (e.g., a Main.java that only prints a welcome message).
        2. IDENTIFY the file most closely related to the task context (e.g., systems for Person, Ride, or Employee management).
        3. You MUST select and return EXACTLY ONE path from the candidate list provided above.

        [Output Constraint]:
        - DO NOT provide any explanation or conversational text.
        - Return ONLY the raw file path string.

        Resulting Path:
        """
        response = self.ai_client.ask(prompt).strip()
        # Clear the path again to prevent the AI from talking too much or returning to markdown format
        clean_path = response.replace('`', '').split('\n')[0].strip()
        return clean_path

    def get_entry_point(self, project_path, task_context=None):
        """
        Get the project launch entry file path (external unified interface).
        The entry is located through a two-layer mechanism of "heuristic scanning + AI semantic arbitration" :
        1. First do a quick scan with regular rules.
        2. If the scan results are ambiguous (multiple candidates) or potentially false positives (e.g., generic Main.java),
        Ai-assisted analysis is initiated to ensure accuracy.
        :param project_path: The absolute path to the project root
        :param task_context: A description of the task context to help AI understand the business logic
        :return:
            str: Identified entry file relative path
            None: If no eligible entry file is found
        """

        candidates = self.heuristic_detect(project_path)

        if not candidates:
            return None
        if len(candidates) == 1 and "Main.java" not in candidates[0]:
            return candidates[0]

        return self.ai_assist_detect(project_path, candidates, task_context)