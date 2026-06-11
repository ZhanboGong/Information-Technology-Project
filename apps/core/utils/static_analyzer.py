import os
import re


class StaticAnalyzer:
    """
    Static Code Analysis Engine.

    This utility quantifies code quality by measuring structural metrics:
    - Python: Uses the 'radon' library for professional-grade analysis.
    - Java: Uses regex-based heuristics for structural approximation.
    """

    @staticmethod
    def analyze(file_path):
        """
        Dispatches the analysis strategy based on the file extension.
        :param file_path: Path to the source file to be analyzed.
        :return: Dictionary containing language-specific metrics.
        """
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.py':
            return StaticAnalyzer.analyze_python(file_path)
        elif ext == '.java':
            return StaticAnalyzer.analyze_java(file_path)
        return {}

    @staticmethod
    def analyze_python(file_path):
        """
        Performs deep structural analysis of Python code using the Radon library.

        Metrics tracked:
        1. Cyclomatic Complexity (CC): Measures independent paths through code.
        2. Maintainability Index (MI): A weighted score representing ease of maintenance.
        3. Raw Metrics: Physical (LOC) vs Logical (SLOC) line counts.
        :param file_path: Path to the .py file.
        :return: Detailed structural metrics for Python code.
        """
        try:
            from radon.complexity import cc_visit, cc_rank
            import radon.mi
            from radon.raw import analyze as raw_analyze

            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                code = f.read()

            # 1. cyclomatic complexity
            cc_results = cc_visit(code)
            cc_scores = []
            for block in cc_results:
                cc_scores.append({
                    'name': block.name,
                    'complexity': block.complexity,
                    'rank': cc_rank(block.complexity)
                })
            avg_cc = sum(c['complexity'] for c in cc_scores) / len(cc_scores) if cc_scores else 0
            max_cc = max((c['complexity'] for c in cc_scores), default=0)

            # 2. maintainability index
            mi_score = radon.mi.mi_visit(code, True)

            # 3. Original indicators (LOC, SLOC, comments, etc.)
            raw = raw_analyze(code)

            return {
                'language': 'python',
                'total_loc': raw.loc,
                'sloc': raw.sloc,
                'comments': raw.comments,
                'comment_ratio': round(raw.comments / raw.loc * 100, 1) if raw.loc > 0 else 0,
                'blank_lines': raw.blank,
                'cyclomatic_complexity': {
                    'average': round(avg_cc, 2),
                    'max': max_cc,
                    'functions': cc_scores[:20]
                },
                'maintainability_index': round(mi_score, 1),
                'function_count': len(cc_scores)
            }
        except Exception as e:
            return {'language': 'python', 'error': str(e)}

    @staticmethod
    def analyze_java(file_path):
        """
        Performs heuristic-based Java code analysis using Regular Expressions.

        This approach approximates structural metrics without requiring a
        full Abstract Syntax Tree (AST) parser or JVM environment.
        :param file_path: Path to the .java file.
        :return: Estimated structural metrics for Java code.
        """
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                code = f.read()

            lines = code.split('\n')
            total_loc = len(lines)

            # Effective code lines (excluding blank lines and pure comment lines)
            code_lines = [l for l in lines if l.strip() and not l.strip().startswith('//') and not l.strip().startswith('*')]
            sloc = len(code_lines)

            # comment line
            comment_lines = [l for l in lines if l.strip().startswith('//') or l.strip().startswith('*')]

            # Number of methods
            methods = re.findall(r'(?:public|private|protected|static|\s)+[\w<>\[\]]+\s+(\w+)\s*\(', code)
            method_count = len(methods)

            # nesting depth
            max_depth = 0
            for line in code_lines:
                stripped = line.lstrip()
                if stripped:
                    indent = len(line) - len(stripped)
                    depth = indent // 4  # 假设 4 空格缩进
                    max_depth = max(max_depth, depth)

            # 近似圈复杂度（统计分支关键字）
            branch_keywords = re.findall(
                r'\b(if|else\s+if|elif|for|while|case|catch|&&|\|\|)\b', code
            )
            estimated_cc = 1 + len(branch_keywords)  # 基础 CC = 1 + 分支数

            return {
                'language': 'java',
                'total_loc': total_loc,
                'sloc': sloc,
                'comments': len(comment_lines),
                'comment_ratio': round(len(comment_lines) / total_loc * 100, 1) if total_loc > 0 else 0,
                'blank_lines': total_loc - sloc - len(comment_lines),
                'cyclomatic_complexity': {
                    'average': round(estimated_cc / max(method_count, 1), 2),
                    'max': estimated_cc,
                    'functions': []
                },
                'max_nesting_depth': max_depth,
                'method_count': method_count
            }
        except Exception as e:
            return {'language': 'java', 'error': str(e)}

    @staticmethod
    def analyze_project(project_path):
        """
        Walks through a project directory to aggregate global quality statistics.

        It filters out non-source directories (e.g., venv, git) to ensure the
        metrics reflect the student's actual logic and not library code.
        :param project_path: Root path of the submitted project/archive.
        :return: Aggregated summary of metrics across all identified files.
        """
        results = []
        skip_dirs = {'__pycache__', 'venv', '.git', 'node_modules', '.idea', 'migrations'}
        for root, dirs, files in os.walk(project_path):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for f in files:
                if f.endswith(('.py', '.java')):
                    path = os.path.join(root, f)
                    result = StaticAnalyzer.analyze(path)
                    if result and 'error' not in result:
                        results.append(result)

        if not results:
            return {'files_analyzed': 0, 'summary': {}}

        # 汇总
        total_loc = sum(r.get('total_loc', 0) for r in results)
        total_sloc = sum(r.get('sloc', 0) for r in results)
        all_cc = []
        total_methods = 0
        for r in results:
            cc = r.get('cyclomatic_complexity', {})
            all_cc.extend(cc.get('functions', []))
            if not cc.get('functions') and cc.get('max', 0) > 0:
                all_cc.append({'complexity': cc['max']})
            total_methods += r.get('function_count', r.get('method_count', 0))

        avg_cc = sum(c['complexity'] for c in all_cc) / len(all_cc) if all_cc else 0
        max_cc = max((c['complexity'] for c in all_cc), default=0)

        # 可维护性指数取平均
        mi_scores = [r.get('maintainability_index', 50) for r in results if 'maintainability_index' in r]
        avg_mi = sum(mi_scores) / len(mi_scores) if mi_scores else 50

        return {
            'files_analyzed': len(results),
            'summary': {
                'total_loc': total_loc,
                'total_sloc': total_sloc,
                'cyclomatic_complexity': {
                    'average': round(avg_cc, 2),
                    'max': max_cc
                },
                'maintainability_index': round(avg_mi, 1),
                'function_count': total_methods
            }
        }

    @staticmethod
    def check_interface_compliance(project_path):
        """检查 Java 项目的接口实现完整性"""
        import re, os

        java_files = {}
        for root, _, files in os.walk(project_path):
            for f in files:
                if f.endswith('.java'):
                    with open(os.path.join(root, f), 'r', encoding='utf-8', errors='ignore') as fh:
                        java_files[f] = fh.read()

        interfaces = {}
        for fname, content in java_files.items():
            match = re.search(r'public\s+interface\s+(\w+)', content)
            if match:
                # 只提取接口中声明的方法（排除构造器和注释）
                method_lines = [l.strip() for l in content.split('\n')
                                if l.strip() and not l.strip().startswith('//')
                                and not l.strip().startswith('*')
                                and '(' in l and ';' in l]
                methods = []
                for line in method_lines:
                    m = re.search(r'\w+\s+(\w+)\s*\(', line)
                    if m:
                        methods.append(m.group(1))
                interfaces[match.group(1)] = methods

        issues = []
        for iface_name, required_methods in interfaces.items():
            implementors = []
            for fname, content in java_files.items():
                # 跳过接口定义文件本身
                if f'interface {iface_name}' in content:
                    continue

                if re.search(r'implements\s+' + iface_name, content):
                    implementors.append(fname)
                    # implements 了，检查方法是否完整
                    for method in required_methods:
                        if method + '(' not in content:
                            issues.append(
                                f"Class {fname.replace('.java', '')} implements {iface_name} "
                                f"but is missing method: {iface_name}.{method}()"
                            )
                else:
                    # 没有 implements，检查是否被其他类引用（说明它应该实现）
                    for other_fname, other_content in java_files.items():
                        if fname != other_fname and fname.replace('.java', '') in other_content:
                            # 这个类被其他文件使用，说明它存在但没 implements
                            pass

            if not implementors:
                issues.append(
                    f"No class implements interface {iface_name} "
                    f"(required methods: {', '.join(required_methods)})"
                )

        return {
            'has_interfaces': len(interfaces) > 0,
            'issues': issues,
            'summary': f"Found {len(interfaces)} interface(s), {len(issues)} compliance issue(s)"
        }