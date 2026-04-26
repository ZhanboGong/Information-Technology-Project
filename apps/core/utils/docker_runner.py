import docker
import os
import re


class DockerRunner:
    """
    General purpose multilingual code sandbox runner.

    Supports restricted execution of Python and Java programs. The runner provides hardware-level resource isolation through Docker containers,
    In addition, deep adaptation is made for Java Package structure and Python script execution.

    Core security features:
        - Resource isolation: CPU (1 core), memory (512MB), number of processes (50) are strictly quota.
        - Deep cleanup: Force the container and associated resources to be destroyed regardless of success, failure, or timeout.
        - Robustness: Handles Java fully qualified class name recognition and multi-encoding source code reading automatically.
    """

    def __init__(self):
        try:
            self.client = docker.from_env()
        except Exception:
            self.client = None

    def _get_java_full_class_name(self, absolute_path):
        """
        Resolving Fully Qualified Class names in Java source code
        1. Read source code first: Use regular expressions to search for the 'package' keyword.
        2. Directory traceback: If the source code is not declared, logical package names are inferred from the physical path of the project (based on the com/structure).
        :param absolute_path: The absolute path to the Java source file
        :return: A class name, such as com.test.Main, used for java command execution.
        """
        pkg_name = ""
        class_simple_name = os.path.basename(absolute_path).replace('.java', '')
        try:
            if os.path.exists(absolute_path):
                with open(absolute_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(4096)
                    match = re.search(r'^\s*package\s+([\w\.]+)\s*;', content, re.MULTILINE)
                    if match:
                        pkg_name = match.group(1).strip()
            # Path inference backend
            if not pkg_name:
                normalized_path = absolute_path.replace("\\", "/")
                parts = normalized_path.split("/")
                if "com" in parts:
                    idx = parts.index("com")
                    pkg_name = ".".join(parts[idx:-1])
            return f"{pkg_name}.{class_simple_name}".strip('.') if pkg_name else class_simple_name
        except Exception:
            return class_simple_name

    def run_code(self, file_path, is_project=True, project_root=None):
        """
        Execute the specified code file in the sandbox and capture the execution result.

        The method automatically switches the execution strategy based on the file extension:
        - Python: Automatically compute relative paths and execute them directly.
        - Java: Enable a compile-run dual-stage pipeline with support for multi-file dependencies and UTF-8 encoding.

        Security Control:
        - Set a mandatory timeout of 25 seconds.
        - Disable network access to prevent malicious code attacks or data leakage.
        - Limit the number of processes (pids_limit) to prevent Fork bombs.
        :param file_path: Path to the main file to be executed.
        :param is_project: Whether it is a multi-file project mode (affects the determination of mount root directory).
        :param project_root: Project root directory, inferred automatically if not specified.
        :return: This includes exit_code, output, status, and compile_status.
        """
        if not self.client:
            return {"exit_code": -1, "output": "Docker service unavailable", "status": "error"}

        abs_file_path = os.path.abspath(file_path)
        ext = os.path.splitext(abs_file_path)[1].lower()

        # 如果提供了 project_root（通常是项目模式），则以项目根目录为挂载点；
        # 如果未提供（通常是单文件模式），则以文件所在目录为挂载点。
        effective_root = os.path.abspath(project_root if project_root else os.path.dirname(abs_file_path))

        # Security and restricted configuration
        container_config = {
            "volumes": {effective_root: {'bind': '/workspace', 'mode': 'rw'}},
            "working_dir": '/workspace',
            "detach": True,
            "mem_limit": "512m",
            "nano_cpus": 1000000000,
            "network_disabled": True,
            "pids_limit": 50,
            "remove": False
        }

        if ext == '.py':
            image = "python:3.9-slim"
            # 计算相对于挂载根目录的路径
            rel_path = os.path.relpath(abs_file_path, effective_root).replace("\\", "/")

            # 如果 rel_path 包含 ".."，说明文件计算出的相对路径超出了挂载根目录的范围，
            # 这会导致容器找不到文件。此时强制取文件名（Basename），因为文件必然在 /workspace 顶层。
            if ".." in rel_path:
                rel_path = os.path.basename(abs_file_path)

            command = f"python {rel_path}"
        elif ext == '.java':
            image = "eclipse-temurin:17-jdk-alpine"
            full_class_name = self._get_java_full_class_name(abs_file_path)
            command = (
                f"sh -c 'mkdir -p bin && find . -name \"*.java\" > sources.txt && "
                f"javac -encoding utf-8 -d bin @sources.txt 2>compile_errors.log; "
                f"if [ $? -ne 0 ]; then cat compile_errors.log && exit 100; "
                f"else java -Xmx384m -cp \"bin:.\" {full_class_name}; fi'"
            )
        else:
            return {"exit_code": -1, "output": f"Unsupported extension: {ext}", "status": "error"}

        container = None
        try:
            container = self.client.containers.run(image, command, **container_config)
            try:
                result = container.wait(timeout=25)
                exit_code = result.get("StatusCode", 0)
                # 获取最后 2000 行日志，防止内存溢出
                output = container.logs(tail=2000).decode('utf-8', errors='replace')
            except Exception:
                if container: container.kill()
                return {"exit_code": -1, "output": "Execution Timeout", "status": "timeout"}

            return {
                "exit_code": exit_code,
                "output": output,
                "status": "success" if exit_code == 0 else "failed",
                "compile_status": True if ext == '.py' else (exit_code != 100)
            }
        except Exception as e:
            return {"exit_code": -1, "output": str(e), "status": "error"}
        finally:
            if container:
                try:
                    container.remove(force=True)
                except:
                    pass