import os
import pandas as pd
from fuzzywuzzy import fuzz  # 模糊匹配核心库
from fuzzywuzzy import process

from utils.text_utils import clean_ocr_text


def match_notice_with_files(target_notice, file_list, threshold=50):
    """
    通知名称与文件夹中的文件名称做相似度匹配
    :param target_notice: 目标通知名称
    :param file_list: 文件夹文件列表（(路径, 文件名)）
    :param threshold: 相似度阈值（0-100，越高越严格）
    :return: 匹配结果列表，每个元素是 (文件名, 相似度, 文件路径)
    """
    # 提取所有文件名，用于匹配
    file_name_to_path = {name: path for path, name in file_list}
    file_names = list(file_name_to_path.keys())
    # 模糊匹配：找出相似度≥threshold的文件
    matches = process.extract(target_notice, file_names, scorer=fuzz.ratio, limit=None)
    # 2. 找到相似度最高的结果
    result = []
    for file_name, score in matches:
        if score >= threshold:
            best_file_path = file_name_to_path[file_name]
            result.append((file_name, score, best_file_path))

    result.sort(key=lambda x: x[1], reverse=True)
    return result


def match_site_with_ocr_docs(site_name, documents, threshold=70):
    """
    匹配 site_name 与 OCR 文档内容，返回相似度最高的文档
    :param site_name: 目标文保单位名称
    :param documents: OCR 拆分后的文档列表（每个元素含 page_content）
    :param threshold: 相似度阈值（0-100）
    :return: 最优匹配结果 (文档内容, 相似度) | None（无满足阈值的匹配）
    """
    if not documents or not site_name:
        return None

    # 1. 预处理 site_name（统一格式）
    clean_site_name = clean_ocr_text(site_name)
    if not clean_site_name:
        return None

    # 2. 预处理所有文档内容，并存入列表
    doc_texts = []
    for doc in documents:
        raw_text = doc.page_content if hasattr(doc, "page_content") else ""
        clean_text = clean_ocr_text(raw_text)
        doc_texts.append(clean_text)

    # 3. 模糊匹配：找出与 site_name 最相似的文档内容
    matches = process.extract(
        clean_site_name, doc_texts, scorer=chinese_partial_match, limit=None
    )
    if not matches:
        return None

    result = []
    for doc_text, source in matches:
        if source >= threshold:
            # 找到原始文档（对应清洗后的文本）
            best_raw_doc = documents[doc_texts.index(doc_text)]
            result.append((best_raw_doc, source))

    result.sort(key=lambda x: x[1], reverse=True)
    return result


def calculate_address_similarity(address1: str, address2: str) -> int:
    """计算两个地址的相似度（返回0-100的整数）"""
    if not address1 or not address2:
        return 0
    return fuzz.ratio(address1.strip(), address2.strip())


def chinese_partial_match(s1: str, s2: str) -> int:
    """
    中文适配的部分匹配算法（解决超长文本问题）：
    1. 若短字符串完整出现在长字符串中 → 返回100%
    2. 否则用partial_ratio计算相似度
    """
    # 确保s1是较短的字符串（partial_ratio的逻辑）
    if len(s1) > len(s2):
        s1, s2 = s2, s1

    # 核心：先判断短字符串是否完整包含在长字符串中
    if s1 in s2:
        return 100
    # 否则用partial_ratio计算（处理部分匹配场景）
    return fuzz.partial_ratio(s1, s2)
