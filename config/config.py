import os


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "datasets")

# LLM配置
LLM_CONFIG = {
    "model": "qwen-32b",
    "api_key": "43234",
    "base_url": "http://www.wlhcloud.top:9111/v1",
    "timeout": 300,
    "temperature": 0.3,
}

# 阈值配置
THRESHOLD = {
    "file_match": 50,  # 文件相似度阈值
    "name_match": 70,  # 文保单位名称匹配阈值
}

# 导出配置
EXPORT_CONFIG = {
    "unit": "county",  # 导出单位（province,city,county）
}

# 语义分割小模型
LOCAL_TEXT_EMB_PATH = "/home/gybwg/ai-project/models/Qwen/Qwen3-Embedding-0___6B"

# OCR地址
DOTS_OCR_IP = "www.wlhcloud.top"
DOTS_OCR_PORT = 9114
