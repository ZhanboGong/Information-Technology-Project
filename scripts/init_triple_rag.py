# scripts/init_triple_rag.py
from apps.core.utils.rag_engine import TripleLayerRAG


def init_real_data():
    rag = TripleLayerRAG()

    # Layer 1: 只要写 Python 就要遵守的硬规范
    l1_docs = [
        "变量和函数名应使用 snake_case，具有明确语义，严禁 a, b, c。",
        "所有函数必须有 Docstrings 说明功能和参数类型。",
        "严禁使用 eval() 执行用户输入，防止代码注入。"
    ]
    rag.add_knowledge(1, l1_docs, [f"l1_{i}" for i in range(len(l1_docs))])

    # Layer 2: 庞大的教学资源库（AI 自动挑选相关的）
    l2_docs = [
        "【基础要求】重点考察输入提示的友好度及对非法输入的异常处理。",
        "【OOP要求】考察封装性，私有属性应以 _ 或 __ 开头，类结构清晰。",
        "【函数要求】鼓励使用递归解决分治问题，但必须设定终止条件。",
        "【评价语气】采用启发式教学，指出不足时请给出引导性问题。"
    ]
    rag.add_knowledge(2, l2_docs, [f"l2_{i}" for i in range(len(l2_docs))])



    print("✅ 三层智能检索知识库已就绪！")


if __name__ == "__main__":
    init_real_data()