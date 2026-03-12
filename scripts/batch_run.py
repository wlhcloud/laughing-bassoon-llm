import os
from typing import Dict, List, Optional, Tuple
import pandas as pd

from fuzzywuzzy import fuzz, process
from config.config import THRESHOLD
from llm.llm_tool import extract_site_info_structured
from scripts.similarity_match import (
    match_notice_with_files,
    match_site_with_ocr_docs,
)
from utils.file_utils import (
    find_excel_in_county,
    get_document_files,
    find_published_folder_in_county,
    get_folder_recursion_files,
    get_prov_city_county_from_path, find_dir_excels,
)
from scripts.data_process import read_excel_get_notices
from logger import log


def batch_process_county(county_dir: str, result_data):
    """批量处理哈尔滨市所有区县的文保单位信息，并生成结果Excel"""
    # 获取省市
    province_name, city_name, county_name = get_prov_city_county_from_path(county_dir)
    log.info(
        f"\n=====开始处理：省：{province_name} 市：{city_name} 县：{county_name} ====="
    )

    # 1. 基础校验与初始化
    if not os.path.isdir(county_dir):
        log.error(f"区县目录不存在：{county_dir}")
        return

    # 2. 获取Excel文件
    excel_path = find_excel_in_county(county_dir)
    if not excel_path:
        log.warning(f"未找到 {county_name} 的公布名录 Excel，跳过")
        return

    # 3. 读取Excel提取通知数据
    try:
        notice_wenbao_map = read_excel_get_notices(excel_path, check_col=1)
    except Exception as e:
        log.error(f"读取{county_name} Excel失败：{str(e)}", exc_info=True)
        return

    if not notice_wenbao_map:
        log.warning(f"{county_name} 未提取到有效通知，跳过")
        return

    # 4. 获取公布文件目录
    # published_folder = find_published_folder_in_county(county_dir)
    # if not published_folder:
    #     log.warning(f"未找到 {county_name} 的附件1 公布文件目录，跳过")
    #     return

    # 5. 读取公布文件列表
    pub_files = get_folder_recursion_files(county_dir)
    if not pub_files:
        log.warning(f"{county_name} 无有效公布文档，跳过")
        return

    # 6. 缓存OCR解析结果和匹配结果
    documents_map: Dict[str, List] = {}

    # 7. 遍历每个通知处理
    for target_notice, unit_lists in notice_wenbao_map.items():
        log.info(f"\n处理通知：{target_notice}")

        # 7.1 匹配对应的公布文档
        try:
            best_matched_doc = match_notice_with_files(
                target_notice, pub_files, THRESHOLD["file_match"]
            )
        except Exception as e:
            log.error(f"匹配{target_notice}文档失败：{str(e)}", exc_info=True)
            continue

        if not best_matched_doc:
            log.error(f"{target_notice} 未找到匹配的公布文档，跳过")
            continue

        file_name, doc_match_score, file_path = best_matched_doc[0]
        log.info(
            f"匹配到文档：{file_name}（路径：{file_path}），文档相似度：{doc_match_score}%"
        )

        # 7.2 解析OCR内容（缓存复用）
        if file_path not in documents_map:
            try:
                documents, parse_status = get_document_files(file_path)
                if not documents or not parse_status:
                    log.error(f"解析{file_path} OCR失败，跳过该文件！")
                    documents_map[file_path] = []
                    continue
                documents_map[file_path] = documents
            except Exception as e:
                log.error(f"解析{file_path} OCR异常：{str(e)}", exc_info=True)
                documents_map[file_path] = []
                continue

        documents = documents_map[file_path]
        if not documents:
            continue

        # 7.3 遍历处理每个文保单位
        for unit_row in unit_lists:
            # 初始化当前行数据
            row_data = {
                "省": province_name,
                "市": city_name,
                "区/县": county_name,
                "通知": target_notice,
                "公布名录中的单位名称": "",
                "公布名录中的单位地址": "",
                "公布文件中的单位名称": "",
                "公布文件中的单位地址": "",
                "单位名称相似度": 0,
                "单位名称是否匹配": "否",
                "单位地址相似度": 0,
                "单位地址是否匹配": "否",
            }

            # 安全获取公布名录中的基础信息
            try:
                site_name = unit_row[3].strip() if len(unit_row) > 3 else ""
                site_address = unit_row[8].strip() if len(unit_row) > 8 else ""
                row_data["公布名录中的单位名称"] = site_name
                row_data["公布名录中的单位地址"] = site_address
            except (IndexError, AttributeError):
                log.warning("文保单位数据行格式异常，跳过")
                result_data.append(row_data)
                continue

            if not site_name:
                log.warning("文保单位名称为空，跳过")
                result_data.append(row_data)
                continue

            log.info(f"\n处理文保单位：{site_name}（地址：{site_address}）")

            # 7.5 匹配文保单位与OCR文档
            try:
                matched_docs = match_site_with_ocr_docs(
                    site_name, documents, THRESHOLD["file_match"]
                )
            except Exception as e:
                log.error(f"匹配{site_name} OCR文档失败：{str(e)}", exc_info=True)
                result_data.append(row_data)
                continue

            if not matched_docs:
                log.warning(f"公布文件中未匹配到 {site_name}")
                result_data.append(row_data)
                continue

            #对匹配文档做抽取，如果对所有请注释
            if THRESHOLD["documents_match"] < len(matched_docs):
                matched_docs = matched_docs[:THRESHOLD["documents_match"]]

            # 7.6 提取结构化信息
            site_info = None
            final_name_similarity = 0
            final_addr_similarity = 0

            for doc, source in matched_docs:
                try:
                    structured_info = extract_site_info_structured(
                        site_name, site_address, doc.page_content
                    )
                except Exception as e:
                    log.error(f"LLM抽取{site_name}信息失败：{str(e)}", exc_info=True)
                    continue

                if not structured_info:
                    log.info(f"LLM未抽取到{site_name}的结构化信息")
                    continue

                # 计算名称相似度
                llm_match_result = process.extractOne(
                    site_name,
                    [structured_info.site_name or ""],
                    scorer=fuzz.partial_ratio,
                )

                if llm_match_result:
                    matched_name, match_score = llm_match_result
                    final_name_similarity = match_score

                    # 计算地址相似度
                    _, final_addr_similarity = process.extractOne(
                        site_address,
                        [structured_info.detailed_address or ""],
                        scorer=fuzz.partial_ratio,
                    )

                    # 阈值判断
                    if match_score >= THRESHOLD["name_match"]:
                        log.info(
                            f"名称匹配成功 | 原始名称：{site_name} | 抽取名称：{matched_name} | 相似度：{match_score}%"
                        )
                        site_info = structured_info
                        if (
                            structured_info.site_name
                            and structured_info.detailed_address
                        ):
                            break  # 匹配成功，退出循环
                    else:
                        log.info(
                            f"名称匹配失败 | 原始名称：{site_name} | 抽取名称：{matched_name} | 相似度：{match_score}%（低于阈值{THRESHOLD['name_match']}%）"
                        )

            # 7.7 填充最终数据
            if site_info:
                row_data["公布文件中的单位名称"] = site_info.site_name or ""
                row_data["公布文件中的单位地址"] = site_info.detailed_address or ""
                row_data["单位名称相似度"] = final_name_similarity
                row_data["单位名称是否匹配"] = (
                    "是" if final_name_similarity >= THRESHOLD["name_match"] else "否"
                )
                row_data["单位地址相似度"] = final_addr_similarity
                row_data["单位地址是否匹配"] = (
                    "是" if final_addr_similarity >= THRESHOLD["name_match"] else "否"
                )
                log.info(f"最终匹配结果：{row_data}")
            else:
                log.warning(f"{site_name} 未提取到有效结构化信息")

            # 将当前行数据加入结果列表
            result_data.append(row_data)

    log.info(f"===== 完成处理：{county_name} =====")
