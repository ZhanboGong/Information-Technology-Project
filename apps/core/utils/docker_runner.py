import docker
import os


class DockerRunner:
    def __init__(self):
        try:
            self.client = docker.from_env()
        except Exception as e:
            print(f"Docker 连接失败: {e}")
            self.client = None

    def run_code(self, file_path, is_project=False, project_root=None):
        """
        全量精进版：支持 AI 识别路径、包名自动转换及路径符号兼容
        """
        if not self.client:
            return {
                "exit_code": -1,
                "output": "Docker 引擎未启动",
                "status": "timeout_or_error",
                "compile_status": False
            }

        ext = os.path.splitext(file_path)[1].lower()

        # 1. 确定物理挂载路径
        host_path = os.path.abspath(project_root if is_project else os.path.dirname(file_path))
        container_path = "/workspace"

        # 🚀 路径兼容逻辑：处理 Windows 的反斜杠，确保在容器内（Linux）运行正常
        rel_file_path = os.path.relpath(file_path, project_root) if is_project else os.path.basename(file_path)
        rel_file_path = rel_file_path.replace("\\", "/")

        # 2. 生成运行配置
        if ext == '.py':
            image = "python:3.9-slim"
            command = f"python {rel_file_path}"
            mem_limit = "128m"
            is_compiled_lang = False

        elif ext == '.java':
            image = "eclipse-temurin:17-jdk-alpine"

            # 🚀 智能包名识别逻辑 (解决 Could not find or load main class)
            # 逻辑：如果路径是 src/com/abc/Main.java，自动拆分为：
            # working_sub_dir = "src"
            # class_name = "com.abc.Main"
            parts = rel_file_path.split('/')
            if 'src' in parts:
                src_index = parts.index('src')
                # 提取 src 之后的路径作为包路径
                package_parts = parts[src_index + 1:]
                class_name = '.'.join(package_parts).replace('.java', '')
                # 切换到 src 所在的父目录或直接进入 src
                working_sub_dir = '/'.join(parts[:src_index + 1])
            else:
                # 如果没有 src 目录，则尝试根据当前路径生成类名
                class_name = rel_file_path.replace('.java', '').replace('/', '.')
                working_sub_dir = "."

            # 核心脚本：先 cd 到正确的包根目录，再用 -cp . 运行
            command = (
                f"sh -c 'cd {working_sub_dir} && find . -name \"*.java\" > sources.txt && "
                f"javac @sources.txt 2>compile_errors.log; "
                f"if [ $? -ne 0 ]; then cat compile_errors.log && exit 100; "
                f"else java -cp . {class_name}; fi'"
            )
            mem_limit = "512m"
            is_compiled_lang = True

        else:
            return {"exit_code": -1, "output": f"不支持 {ext}", "status": "error", "compile_status": False}

        try:
            # 3. 执行容器
            container = self.client.containers.run(
                image=image,
                command=command,
                volumes={host_path: {'bind': container_path, 'mode': 'rw'}},
                working_dir=container_path,
                detach=True,
                mem_limit=mem_limit,
                network_disabled=True,
            )

            # 4. 结果捕获 (25s 超时，多文件项目需要更多编译时间)
            result = container.wait(timeout=25)
            exit_code = result.get("StatusCode", 0)
            output = container.logs().decode('utf-8', errors='ignore')
            container.remove()

            # 逻辑判断
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
                "output": f"沙箱运行异常: {str(e)}",
                "status": "timeout_or_error",
                "compile_status": False
            }