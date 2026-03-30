# 运行方式：python scripts/init_teaching_rag.py
import sys
import os

# 将项目根目录加入路径，防止找不到 apps
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apps.core.utils.rag_engine import RAGEngine

TEACHING_GUIDELINES = """
[代码风格规范] 变量命名应使用小写字母和下划线（snake_case），具有明确含义，严禁使用 a, b, c 等单字符命名。
[代码风格规范] 函数必须包含文档字符串（Docstrings），说明参数含义和返回值类型。
[逻辑健壮性] 必须处理用户输入的异常情况，例如输入非数字时应使用 try-except 捕获 ValueError。
[逻辑健壮性] 在进行除法运算前，必须判断除数是否为零，并给出友好提示。
[人性化反馈] 评价语气应温和且具启发性。先夸奖代码的逻辑优点，再指出改进空间，最后给出学习方向。
[人性化反馈] 严禁直接给出修正后的代码，应通过提示词引导学生自主修改。例如：'观察一下循环边界，是否会多跑一次？'。
[教学目标] 重点考察学生对类（Class）的封装意识，观察私有属性（_name）的使用是否规范。
"""

def main():
    print("🚀 正在初始化 RAG 教学知识库...")
    engine = RAGEngine()
    count = engine.add_documents_from_text(TEACHING_GUIDELINES)
    print(f"✅ 成功导入 {count} 条核心规范到向量数据库！")

if __name__ == "__main__":
    main()