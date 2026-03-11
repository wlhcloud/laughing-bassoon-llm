from langchain_openai import ChatOpenAI
from langchain_core.embeddings import Embeddings
from sentence_transformers import SentenceTransformer
from numpy import ndarray

from config.config import LOCAL_TEXT_EMB_PATH


class CustomQwen3Embeddings(Embeddings):
    """自定义一个qwen3的Embedding和langchain整合的类"""

    def __init__(self, model_name):
        self.qwen3_embedding = SentenceTransformer(model_name)

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]

    def embed_documents(self, texts: list[str]) -> ndarray:
        return self.qwen3_embedding.encode(texts)


chat_llm = ChatOpenAI(
    timeout=300,
    model="qwen-32b",
    api_key="43234",
    base_url="http://www.wlhcloud.top:9111/v1",
    temperature=0.3,  # 降低随机性，提升结构化输出稳定性
    streaming=False,  # 结构化输出建议关闭流式（部分模型流式不兼容json_schema）
)

# 意图识别的小模型embedding
text_emb = CustomQwen3Embeddings(LOCAL_TEXT_EMB_PATH)
