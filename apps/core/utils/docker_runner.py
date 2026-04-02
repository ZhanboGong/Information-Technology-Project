import docker
import os


class DockerRunner:
    """
    A restricted code execution runner based on Docker.
    This type is responsible for creating isolated container environments to run the code submitted by students. It integrates multiple levels of security restrictions:
    1. Resource isolation: Limiting CPU, memory and the number of processes.
    2. Network isolation: Disabling container networking to prevent data leakage.
    3. Time limit: Enforcing timeout control to prevent dead-loop tasks.
    4. Automatic cleanup: Ensuring that the containers are physically deleted after their operation, releasing system resources.
    """
    def __init__(self):
        try:
            self.client = docker.from_env()
        except Exception as e:
            print(f"Docker connection failed: {e}")
            self.client = None

    def run_code(self, file_path, is_project=False, project_root=None):
        """
        Execute the code within the Docker sandbox and capture the running results.
        This method supports Python and Java. For compiled languages such as Java, there are built-in scripts for automatic compilation and execution.
        :param file_path: The absolute path of the main file to be executed.
        :param is_project: Is it a multi-file project mode? The default is False.
        :param project_root: The root directory path of the project (valid only in project mode).
        :return:
            dict: Dictionary containing the running results:
            - exit_code (int): Exit status code of the process.
            - output (str): Output from the run (stdout/stderr).
            - status (str): Execution status (success/failed/timeout/error).
            - compile_status (bool): Whether the compilation was successful.
        """
        if not self.client:
            return {
                "exit_code": -1,
                "output": "Docker engine is not running.",
                "status": "timeout_or_error",
                "compile_status": False
            }

        ext = os.path.splitext(file_path)[1].lower()

        # 1. Path mapping and mounting logic: Map the host machine project path to /workspace within the container.
        host_path = os.path.abspath(project_root if is_project else os.path.dirname(file_path))
        container_path = "/workspace"

        # Handling relative paths: Ensure that when commands are executed within the container, the files can be accurately located.
        rel_file_path = os.path.relpath(file_path, project_root) if is_project else os.path.basename(file_path)
        rel_file_path = rel_file_path.replace("\\", "/")

        # 2. Based on language generation running strategies (Image, Command, Resource Limits)
        if ext == '.py':
            image = "python:3.9-slim"
            command = f"python {rel_file_path}"
            mem_limit = "128m"
            is_compiled_lang = False

        elif ext == '.java':
            image = "eclipse-temurin:17-jdk-alpine"

            # Smart package name recognition: For Java projects with a package structure, locate the main class name
            parts = rel_file_path.split('/')
            if 'src' in parts:
                src_index = parts.index('src')
                package_parts = parts[src_index + 1:]
                class_name = '.'.join(package_parts).replace('.java', '')
                working_sub_dir = '/'.join(parts[:src_index + 1])
            else:
                class_name = rel_file_path.replace('.java', '').replace('/', '.')
                working_sub_dir = "."

            # Combining Shell commands: Execute the compilation and determine the compilation result based on the exit code. If it passes, then execute.
            command = (
                f"sh -c 'cd {working_sub_dir} && find . -name \"*.java\" > sources.txt && "
                f"javac @sources.txt 2>compile_errors.log; "
                f"if [ $? -ne 0 ]; then cat compile_errors.log && exit 100; "
                f"else java -cp . {class_name}; fi'"
            )
            mem_limit = "512m"
            is_compiled_lang = True

        else:
            return {"exit_code": -1, "output": f"不支持的扩展名: {ext}", "status": "error", "compile_status": False}

        container = None
        try:
            # 3. Start and configure the container: Add core security and resource limitations
            container = self.client.containers.run(
                image=image,
                command=command,
                volumes={host_path: {'bind': container_path, 'mode': 'rw'}},
                working_dir=container_path,
                detach=True,

                # --- Core security and resource limitations ---
                mem_limit=mem_limit,  # Memory Limitation
                memswap_limit=mem_limit,  # Prohibit the use of swap partitions to prevent IO performance fluctuations.
                nano_cpus=500000000,  # CPU limit: 0.5 core (to prevent dead loops from exhausting resources)
                network_disabled=True,  # Disable network connection (to prevent data leakage)
                pids_limit=50,  # Limit the number of processes (to prevent the Fork bomb attack)
                # -------------------------

                stdout=True,
                stderr=True
            )

            # 4. Implement monitoring and timeout capture
            try:
                result = container.wait(timeout=25)
                exit_code = result.get("StatusCode", 0)
                output = container.logs().decode('utf-8', errors='replace')
            except Exception:
                # Timeout response: Immediately terminate the container and return the timeout status.
                if container:
                    container.kill()
                return {
                    "exit_code": -1,
                    "output": "Timeout occurred: The code execution exceeded the preset limit of 25 seconds.",
                    "status": "timeout",
                    "compile_status": True
                }

            # Compilation status identification: 100 is the error code we have agreed upon in shell commands to indicate a compilation failure.
            compile_success = True
            if is_compiled_lang and exit_code == 100:
                compile_success = False

            return {
                "exit_code": exit_code,
                "output": output,
                "status": "success" if exit_code == 0 else "failed",
                "compile_status": compile_success
            }

        except Exception as e:
            return {
                "exit_code": -1,
                "output": f"Sandbox operation failed: {str(e)}",
                "status": "error",
                "compile_status": False
            }
        finally:
            # 5. Garbage collection: Regardless of success or failure, forcibly clear the container to keep the system clean.
            if container:
                try:
                    container.remove(force=True)
                except:
                    pass