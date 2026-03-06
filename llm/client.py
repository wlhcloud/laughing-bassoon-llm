from langchain_openai import ChatOpenAI


chat_llm = ChatOpenAI(
    timeout=300,
    model="qwen-32b",
    api_key="43234",
    base_url="http://www.wlhcloud.top:9111/v1",
    temperature=0.3,  # 降低随机性，提升结构化输出稳定性
    streaming=False,  # 结构化输出建议关闭流式（部分模型流式不兼容json_schema）
)
