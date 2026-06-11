import ast
import difflib

# 当前代码暂时不使用，但考虑到后续项目结束后是否需要继续开发的问题，这里不将代码进行删除
# The current code will not be used for now, but it will not be removed to consider whether it is necessary to continue development after the end of the project
class PlagiarismTransformer(ast.NodeTransformer):
    """
    现改为使用Moss
    """

    def visit_Name(self, node):
        # 保持上下文 (ctx) 不变，但将变量名统一
        return ast.copy_location(ast.Name(id='var', ctx=node.ctx), node)

    def visit_FunctionDef(self, node):
        # 统一函数名
        node.name = 'func'
        return self.generic_visit(node)

    def visit_Constant(self, node):
        # 抹除具体数值、字符串、布尔值
        return ast.copy_location(ast.Constant(value=None), node)

    def visit_Attribute(self, node):
        # 统一属性调用，如 obj.attr
        node.attr = 'attr'
        return self.generic_visit(node)

    def visit_arg(self, node):
        # 统一函数参数名
        node.arg = 'p'
        return self.generic_visit(node)


class PlagiarismDetector:
    @classmethod
    def get_code_fingerprint(cls, code_content):
        """
        生成代码的结构指纹字符串。
        即使学生交换了代码块顺序，局部结构的指纹依然高度相似。
        """
        try:
            # 过滤掉注释和空行
            tree = ast.parse(code_content)
            # 安全地转换树节点
            transformer = PlagiarismTransformer()
            normalized_tree = transformer.visit(tree)
            # 序列化为指纹字符串
            return ast.dump(normalized_tree)
        except Exception:
            return ""

    @classmethod
    def calculate_similarity(cls, code1, code2):
        """
        利用 Python 内置的 difflib (基于 Gestalt Pattern Matching 算法)
        比对两份结构指纹的重合度。
        """
        f1 = cls.get_code_fingerprint(code1)
        f2 = cls.get_code_fingerprint(code2)

        if not f1 or not f2:
            return 0.0

        return difflib.SequenceMatcher(None, f1, f2).ratio()