import os
from typing import List
from core.ocr.ocr_document_processor import OCRDocumentProcessor
from loguru import logger as log


def get_folder_files(folder_path):
    """
    获取指定文件夹下的所有文件（仅文件，不含子文件夹），返回文件路径+文件名列表
    :param folder_path: 目标文件夹路径
    :return: list，每个元素是 (文件完整路径, 文件名)
    """
    file_list = []
    if not os.path.exists(folder_path):
        print(f"错误：文件夹 {folder_path} 不存在")
        return file_list

    for file_name in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file_name)
        if os.path.isfile(file_path):  # 仅保留文件，排除子文件夹
            file_list.append((file_path, file_name))
    return file_list


def get_dirs(dir_path):
    """
    获取目录下的所有目录
    :param dir 上级目录
    :return: 目录路径列表
    """
    dirs = []
    for item in os.listdir(dir_path):
        item_path = os.path.join(dir_path, item)
        if os.path.isdir(item_path):
            dirs.append(item_path)
    return dirs


def get_dir_name(path):
    """
    从完整路径中提取最后一级目录的名称（即省/市/区县名称）
    """
    return os.path.basename(path)


def create_output_dir(county_dir):
    """为区县创建output目录（无则新建）"""
    output_dir = os.path.join(county_dir, "output")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    return output_dir


def find_excel_in_county(county_dir: str) -> str:
    """
    在区县目录中自动查找“公布名录.xlsx”文件
    """
    for file_name in os.listdir(county_dir):
        if "公布名录" in file_name and file_name.endswith(".xlsx"):
            return os.path.join(county_dir, file_name)
    return ""


def find_published_folder_in_county(county_dir: str) -> str:
    """
    在区县目录中自动查找“附件1：xxxx/公布文件”的OCR文档目录
    """
    # 第一步：找到“附件1：xxxx”目录
    attachment1_dir = ""
    for item in os.listdir(county_dir):
        item_path = os.path.join(county_dir, item)
        if os.path.isdir(item_path) and "附件1" in item:
            attachment1_dir = item_path
            return attachment1_dir

    return attachment1_dir


def get_folder_recursion_files(published_folder: str) -> List[object]:
    """
    递归读取目录（含所有子目录）下的所有文件，返回兼容的文档对象列表
    :param published_folder: 根目录
    :return: 列表，每个元素为 (文件完整路径, 文件名)
    """
    files = []

    if not os.path.exists(published_folder):
        log.error(f"文件目录 {published_folder} 不存在")
        return files

    def _recursive_scan(current_dir: str):
        """内部递归函数：遍历当前目录及所有子目录"""
        for item in os.listdir(current_dir):
            item_path = os.path.join(current_dir, item)

            if os.path.isfile(item_path):
                files.append((item_path, item))

            elif os.path.isdir(item_path):
                _recursive_scan(item_path)

    _recursive_scan(published_folder)

    print(f"成功读取 {published_folder} 及其子目录下 {len(files)} 个文档")
    return files


def get_document_files(file_path: str) -> List[object]:
    """
    OCR解析单个文档
    :param file_path: 文件路径
    :return: 列表，每个元素为 (文件完整路径, 文件名, OCR处理后的documents)
    """
    try:
        ocr_processor = OCRDocumentProcessor()
        documents, stats = ocr_processor.process_pdf_to_documents(file_path)
        return documents, stats
    except Exception as e:
        log.error(f"读取文件 {file_path} 失败：{str(e)}")
    return None, None


def get_prov_city_county_from_path(county_dir):
    """
    从区县完整路径中提取省、市、区县名称
    前提：路径格式为 根目录/省份/城市/区县 (固定4级结构)
    """
    # 1. 规范化路径（统一处理/和\，去掉结尾的/）
    county_dir = os.path.normpath(county_dir)

    # 2. 拆分路径为层级列表（比如：./data/黑龙江省/哈尔滨市/南岗区 → ['.', 'data', '黑龙江省', '哈尔滨市', '南岗区']）
    path_parts = county_dir.split(
        os.sep
    )  # os.sep 自动适配系统分隔符（Windows是\，Linux/Mac是/）

    # 3. 反向提取三级名称（根据层级位置）
    # 假设路径结构是：根目录/省/市/区县 → 倒数第3位是省，倒数第2位是市，倒数第1位是区县
    try:
        province = path_parts[-3]  # 省份（倒数第3级）
        city = path_parts[-2]  # 城市（倒数第2级）
        county = path_parts[-1]  # 区县（倒数第1级）
        return province, city, county
    except IndexError:
        # 路径层级不足时返回空值，避免报错
        print(f"路径格式错误，层级不足：{county_dir}")
        return None, None, None
