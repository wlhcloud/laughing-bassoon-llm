from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate

from model import SiteInfo
from llm.client import chat_llm


def extract_site_info_structured(site_name, site_address, doc_content):
    """
    调用LLM抽取结构化的文物保护单位信息
    :param site_name: 目标文保单位参考名称
    :param site_address: 目标文本单位参考地址
    :param doc_content: 匹配到的文档内容
    :return: SiteInfo 对象（结构化数据）| None
    """
    # 2. 配置结构化输出（核心：with_structured_output）
    structured_llm = chat_llm.with_structured_output(
        schema=SiteInfo,  # 指定输出Schema
        method="json_schema",  # 用JSON Schema约束输出
        strict=True,  # 严格模式：必须符合Schema，否则报错
    )

    # 3. 构建Prompt（加入site_name引导，适配结构化输出）
    prompt_template = """
    已知目标文物保护单位参考名称：{site_name}
    已知目标文物保护单位参考地址：{site_address}
    
    请从以下文档内容中，严格按照指定Schema提取该目标单位的信息：
    1. site_name：文档中该文物保护单位的完整名称（和原文一致，无则返回null）
    2. detailed_address：该单位的详细地点（无则返回null）
    
    文档内容：
    {content}
    
    【强制要求】
    - 仅返回符合Schema的JSON数据，不要添加任何多余文本、解释、备注；
    - 未找到对应信息时，对应字段返回null。
    """
    prompt = PromptTemplate(
        input_variables=["site_name", "content"], template=prompt_template
    )

    # 4. 链式调用：Prompt → 结构化LLM → 输出SiteInfo对象
    chain = prompt | structured_llm

    try:
        # 执行调用并返回结构化对象
        structured_result = chain.invoke(
            {
                "site_name": site_name,
                "site_address": site_address,
                "content": doc_content,
            }
        )
        return structured_result
    except Exception as e:
        print(f"结构化抽取失败：{str(e)}")
        return None
