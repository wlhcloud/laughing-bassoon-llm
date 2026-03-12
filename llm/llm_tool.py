from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate

from model import SiteInfo
from llm.client import chat_llm
from logger import log

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

    请从以下文档内容中，提取与目标名称相似/一致的文物保护单位信息，严格遵守以下规则：

    ### 核心提取规则
    1. site_name：
       - 优先提取文档中与{site_name}**完全一致**的名称（原样返回，包括标点）；
       - 若没有完全一致的，提取**语义相似**的名称（如“东岗遗址”匹配“东岗子遗址”、“营城子遗址”匹配“营城子古遗址”）；
       - 相似判定标准：核心词汇一致（如“遗址”类、“堡子”类），仅前缀/后缀有少量差异；
       - 无相似/一致名称时返回null。

    2. detailed_address：
       - 仅提取该文物保护单位在文档中**明确标注**的完整地址（如XX镇XX村、XX街道XX号）；
       - 文档中无任何地址信息（仅列名称），必须返回null；
       - 禁止使用参考地址{site_address}，禁止编造、推测地址。

    ### 输出要求
    - 仅返回JSON格式数据，无任何多余文本、解释、备注；
    - JSON字段仅包含site_name和detailed_address，格式示例：
      示例1（完全匹配）："site_name":"东岗遗址","detailed_address":null
      示例2（相似匹配）："site_name":"东岗子遗址","detailed_address":null
      示例3（无匹配）：null
    - 未找到对应信息时，对应字段返回null，禁止用空字符串替代。

    文档内容：
    {content}
    """
    prompt = PromptTemplate(
        input_variables=["site_name", "content", "detailed_address"], template=prompt_template
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
        log.error(f"结构化抽取失败：{str(e)}")
        return None
