import os
import chromadb
from chromadb.utils import embedding_functions

# 本代码为项目开始前废弃的方案，原因是可能没有足够的知识储备将这种方式运用到我们的项目当中，当然，这种方式比我们当前的方式要更加好和先进，项目结束后如果还要继续开发，会考虑使用这种方法，所以并没有将代码进行删除。
# The reason is that we may not have enough knowledge reserve to apply this method to our project. Of course, this method is better and more advanced than our current method. If we want to continue to develop after the end of the project, we will consider using this method, so we did not delete the code.
class TripleLayerRAG:
    def __init__(self, db_path="./vector_db"):
        # 1. 初始化持久化客户端
        if not os.path.exists(db_path):
            os.makedirs(db_path)
        self.client = chromadb.PersistentClient(path=db_path)

        # 2. 使用支持中文的多语言预训练模型
        self.emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="paraphrase-multilingual-MiniLM-L12-v2"
        )

        # 3. 定义三层隔离的集合 (Collections)
        # L1: 全局规范 (编程规范、安全禁忌)
        self.l1_global = self.client.get_or_create_collection("l1_global", embedding_function=self.emb_fn)
        # L2: 课程大纲 (教学目标、评价语气)
        self.l2_course = self.client.get_or_create_collection("l2_course", embedding_function=self.emb_fn)
        # L3: 题目特定 (参考逻辑、解题要点)
        self.l3_task = self.client.get_or_create_collection("l3_task", embedding_function=self.emb_fn)

    def add_knowledge(self, layer, docs, ids, metadatas=None):
        """通用知识导入接口"""
        target = {1: self.l1_global, 2: self.l2_course, 3: self.l3_task}[layer]

        # 保险逻辑：如果传了 metadata 但长度不够，自动按 docs 长度补齐
        if metadatas and len(metadatas) == 1 and len(docs) > 1:
            metadatas = metadatas * len(docs)

        target.add(documents=docs, ids=ids, metadatas=metadatas)

    def query_smart_context(self, query_text, assignment_id):
        """
        核心：基于语义距离的智能三层检索
        """
        # --- Layer 1: 全局规范（基础分，总是检索） ---
        l1_res = self.l1_global.query(query_texts=[query_text], n_results=2)['documents'][0]

        # --- Layer 2: 课程大纲（智能语义路由） ---
        # 检索 5 条候选，但通过距离（Distance）过滤掉不相关的规范
        l2_raw = self.l2_course.query(
            query_texts=[query_text],
            n_results=5,
            include=['documents', 'distances']
        )

        l2_filtered = []
        for doc, dist in zip(l2_raw['documents'][0], l2_raw['distances'][0]):
            # 阈值 0.7 是经验值（ChromaDB 默认使用余弦距离，数值越小越相似）
            if dist < 0.7:
                l2_filtered.append(doc)
            # 如果是通用语气规范（包含'反馈'或'评价'字样），我们也保留
            elif "反馈" in doc or "语气" in doc:
                l2_filtered.append(doc)

        # --- Layer 3: 题目特定（通过 ID 强匹配） ---
        l3_res = self.l3_task.query(
            query_texts=[query_text],
            where={"assignment_id": int(assignment_id)},
            n_results=3
        )['documents'][0]

        return {
            "global": "\n".join([f"• {d}" for d in l1_res]),
            "course": "\n".join([f"• {d}" for d in l2_filtered]),
            "task": "\n".join([f"• {d}" for d in l3_res])
        }