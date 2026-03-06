import re


def clean_ocr_text(text):
    """
    预处理 OCR 文本：去除冗余字符、空格、换行，统一格式（提升匹配准确性）
    :param text: 原始 OCR 文本（document.page_content）
    :return: 清洗后的文本
    """
    if not text:
        return ""
    # 1. 去除换行、制表符、多余空格
    text = text.replace("\n", "").replace("\t", "").strip()
    # 2. 去除特殊符号（保留中文、字母、数字）
    text = re.sub(r"[^\u4e00-\u9fa5a-zA-Z0-9]", "", text)
    # 3. 去除连续空格
    text = re.sub(r"\s+", "", text)
    return text
